"""Supervised fine-tuning of InternScience/Agents-A1-4B on the rocketdata SFT split with Unsloth.

16-bit LoRA (Unsloth advises against 4-bit QLoRA for the Qwen3.5 family this model is built on).
Trains on data/sft_v0.jsonl and logs the loss on data/sft_test.jsonl after every epoch. The final
adapter is the last epoch (the test set is not used to pick an epoch, so its scores stay unbiased);
every epoch's checkpoint is kept in <out>/checkpoints. Loss is computed on the assistant answer only.

By default the <thought>...</thought> block of each answer is moved into the model's native
<think> reasoning slot, so the default chat prompt (thinking on) matches training. The
<design>{json}</design> block is unchanged. Pass --keep-thought to train on the data verbatim.

Run with Unsloth Studio's Python (it already has every dependency):
    %USERPROFILE%\\.unsloth\\studio\\unsloth_studio\\Scripts\\python.exe sft\\train_sft.py --smoke 3
    %USERPROFILE%\\.unsloth\\studio\\unsloth_studio\\Scripts\\python.exe sft\\train_sft.py
    %USERPROFILE%\\.unsloth\\studio\\unsloth_studio\\Scripts\\python.exe sft\\train_sft.py --export-only
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
THOUGHT_RE = re.compile(r"^\s*<thought>\s*(.*?)\s*</thought>\s*(<design>.*</design>)\s*$", re.S)
INSTRUCTION_PART = "<|im_start|>user\n"
RESPONSE_PART = "<|im_start|>assistant\n"


def load_messages(path, keep_thought):
    """Return one message list per JSONL row, optionally moving <thought> into reasoning_content."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            msgs = [dict(m) for m in row["messages"]]
            if not keep_thought:
                m = THOUGHT_RE.match(msgs[-1]["content"])
                if m is None:
                    raise ValueError(f"{row['id']}: assistant answer is not <thought>...</thought><design>...</design>")
                msgs[-1]["reasoning_content"] = m.group(1)
                msgs[-1]["content"] = m.group(2)
            out.append(msgs)
    return out


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="InternScience/Agents-A1-4B")
    ap.add_argument("--out", default=r"C:\ft\agents-a1-rocket", help="keep this path short on Windows")
    ap.add_argument("--train", default=str(DATA / "sft_v0.jsonl"))
    ap.add_argument("--test", default=str(DATA / "sft_test.jsonl"))
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=16)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=42, help="LoRA init and data order (42 = the shipped model)")
    ap.add_argument("--keep-thought", action="store_true", help="train on <thought> verbatim (then chat with thinking off)")
    ap.add_argument("--smoke", type=int, default=0, help="run only N optimizer steps, then stop (no saving)")
    ap.add_argument("--no-export", action="store_true", help="save the LoRA adapter only")
    ap.add_argument("--export-only", action="store_true", help="skip training; export from <out>/lora")
    ap.add_argument("--gguf", default="q4_k_m", help="llama.cpp quantization for the GGUF export")
    return ap.parse_args()


def vram(tag):
    import torch
    gb = 1024 ** 3
    print(f"[vram] {tag}: allocated {torch.cuda.memory_allocated() / gb:.2f} GiB, "
          f"peak allocated {torch.cuda.max_memory_allocated() / gb:.2f} GiB, "
          f"peak reserved {torch.cuda.max_memory_reserved() / gb:.2f} GiB", flush=True)


def check_lora_targets(model):
    """Print which module families got LoRA adapters; vision modules must not be among them."""
    names = [n for n, _ in model.named_modules() if n.endswith(".lora_A")]
    families = sorted({re.sub(r"\.\d+\.", ".N.", n.rsplit(".lora_A", 1)[0]) for n in names})
    print(f"[lora] {len(names)} adapted linear layers in {len(families)} families:")
    for fam in families:
        print("   ", fam)
    vision = [n for n in names if "visual" in n or "vision" in n]
    if vision:
        raise RuntimeError(f"LoRA reached {len(vision)} vision modules, e.g. {vision[0]}")
    if not any("linear_attn" in n for n in names):
        print("[lora] WARNING: no linear_attn (Gated DeltaNet) layers adapted", flush=True)


def check_masking(trainer, tokenizer):
    """Show where the trained (unmasked) tokens of the first example start and end."""
    row = trainer.train_dataset[0]
    ids, labels = row["input_ids"], row["labels"]
    kept = [t for t, l in zip(ids, labels) if l != -100]
    text = tokenizer.decode(kept)
    print(f"[mask] example 0: {len(kept)}/{len(ids)} tokens trained")
    print(f"[mask] trained text starts: {text[:80]!r}")
    print(f"[mask] trained text ends:   {text[-60:]!r}", flush=True)
    if "<|im_start|>user" in text or "You are an autonomous" in text:
        raise RuntimeError("prompt tokens are not masked out")


def export_gguf(model, processor, out, quant, name="Agents-A1-4B-rocketdata"):
    """Write <out>/gguf/<name>.*.gguf (model + mmproj).

    Unsloth merges into a scratch folder, takes the GGUF's display name from that folder's name and
    writes the files to "<scratch>_gguf". The new files are staged in <out>/gguf.new and swapped in for
    <out>/gguf in one rename, so a failure (for example a file still open in Studio or llama-server)
    leaves the previous GGUFs untouched instead of a mix of old and new.
    """
    scratch, built = out / name, out / f"{name}_gguf"
    dest, staged, old = out / "gguf", out / "gguf.new", out / "gguf.old"
    try:
        model.save_pretrained_gguf(str(scratch), processor, quantization_method=quant)
        files = sorted(built.glob("*.gguf"))
        if not any("mmproj" not in f.name for f in files):
            raise RuntimeError(f"Unsloth produced no model GGUF in {built}")
        shutil.rmtree(staged, ignore_errors=True)
        shutil.rmtree(old, ignore_errors=True)
        staged.mkdir()
        for f in files:
            os.replace(f, staged / f.name.replace("Agents-A1-4B.", f"{name}.", 1))
        if dest.exists():
            dest.rename(old)  # raises, changing nothing, if a file inside is open
        staged.rename(dest)
        shutil.rmtree(old, ignore_errors=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(built, ignore_errors=True)
    print(f"[export] GGUF files: {sorted(p.name for p in dest.glob('*.gguf'))}", flush=True)


def export(model, processor, out, quant):
    """Save merged 16-bit weights and a GGUF. Each step runs even if the other fails; returns the failed ones."""
    # Chat turns end with <|im_end|>, but the base config's eos is <|endoftext|>; stop on either.
    tok = getattr(processor, "tokenizer", processor)
    model.generation_config.eos_token_id = [tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")]
    failed = []
    for name, fn in [
        ("merged_16bit", lambda: model.save_pretrained_merged(str(out / "merged_16bit"), processor, save_method="merged_16bit")),
        ("gguf", lambda: export_gguf(model, processor, out, quant)),
    ]:
        t = time.time()
        try:
            fn()
            print(f"[export] {name} done in {time.time() - t:.0f}s", flush=True)
        except Exception:
            failed.append(name)
            print(f"[export] {name} FAILED:", flush=True)
            traceback.print_exc()
    return failed


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Unsloth writes generated kernels to ./unsloth_compiled_cache by default; keep them out of the repo.
    os.environ.setdefault("UNSLOTH_COMPILE_LOCATION", str(out / "unsloth_compiled_cache"))

    from unsloth import FastModel  # import unsloth before trl/transformers so its patches apply
    from unsloth.chat_templates import train_on_responses_only
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    load_kw = dict(max_seq_length=args.max_len, dtype=None, load_in_4bit=False, load_in_16bit=True,
                   full_finetuning=False, use_gradient_checkpointing="unsloth")

    if args.export_only:
        model, processor = FastModel.from_pretrained(model_name=str(out / "lora"), **load_kw)
        return 1 if export(model, processor, out, args.gguf) else 0

    t0 = time.time()
    model, processor = FastModel.from_pretrained(model_name=args.model, **load_kw)
    tokenizer = getattr(processor, "tokenizer", processor)
    print(f"[load] {args.model} loaded in {time.time() - t0:.0f}s, dtype {model.dtype}", flush=True)
    vram("after load")

    model = FastModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=0.0,
        bias="none",
        target_modules=None,  # Unsloth picks attention + Gated DeltaNet + MLP projections
        finetune_vision_layers=False,  # text-only task; keep the vision tower frozen
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )
    model.print_trainable_parameters()
    check_lora_targets(model)

    def render(msgs):
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)

    train_text = [render(m) for m in load_messages(args.train, args.keep_thought)]
    test_text = [render(m) for m in load_messages(args.test, args.keep_thought)]
    lengths = [len(tokenizer(t, add_special_tokens=False)["input_ids"]) for t in train_text + test_text]
    print(f"[data] train {len(train_text)}, test {len(test_text)}; tokens per example max {max(lengths)}")
    print(f"[data] example 0 assistant turn: {train_text[0][train_text[0].rfind(RESPONSE_PART):][:160]!r}", flush=True)
    if max(lengths) > args.max_len:
        raise RuntimeError(f"an example has {max(lengths)} tokens, more than --max-len {args.max_len}")

    smoke = args.smoke > 0
    cfg = SFTConfig(
        output_dir=str(out / "checkpoints"),
        dataset_text_field="text",
        max_length=args.max_len,
        packing=False,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.accum,
        num_train_epochs=args.epochs,
        max_steps=args.smoke if smoke else -1,
        learning_rate=args.lr,
        warmup_steps=5,
        lr_scheduler_type="linear",
        weight_decay=0.001,
        optim="adamw_8bit",
        logging_steps=1,
        eval_strategy="no" if smoke else "epoch",
        save_strategy="no" if smoke else "epoch",
        load_best_model_at_end=False,  # keep the last epoch; the test set is for reporting, not selection
        metric_for_best_model="eval_loss",  # still tracked, so the log says which epoch had the lowest test loss
        greater_is_better=False,
        seed=args.seed,
        report_to="none",
        dataset_num_proc=1,  # Windows: dataset workers can't fork
        dataloader_num_workers=0,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=Dataset.from_dict({"text": train_text}),
        eval_dataset=Dataset.from_dict({"text": test_text}),
        args=cfg,
    )
    trainer = train_on_responses_only(trainer, instruction_part=INSTRUCTION_PART, response_part=RESPONSE_PART)
    check_masking(trainer, tokenizer)

    t0 = time.time()
    stats = trainer.train()
    print(f"[train] {stats.global_step} steps in {(time.time() - t0) / 60:.1f} min, "
          f"final train loss {stats.training_loss:.4f}", flush=True)
    vram("after training")
    if smoke:
        return 0

    evals = [(h["epoch"], h["eval_loss"]) for h in trainer.state.log_history if "eval_loss" in h]
    print(f"[train] test loss per epoch: {', '.join(f'{e:g}: {l:.4f}' for e, l in evals)}; "
          f"lowest at {trainer.state.best_model_checkpoint}; saving the last epoch", flush=True)
    (out / "train_log.json").write_text(json.dumps({
        "args": vars(args),
        "lowest_test_loss_checkpoint": trainer.state.best_model_checkpoint,
        "lowest_test_loss": trainer.state.best_metric,
        "log_history": trainer.state.log_history,
    }, indent=1), encoding="utf-8")

    model.save_pretrained(str(out / "lora"))
    processor.save_pretrained(str(out / "lora"))
    print(f"[save] LoRA adapter (last epoch) -> {out / 'lora'}", flush=True)
    if args.no_export:
        return 0
    return 1 if export(model, processor, out, args.gguf) else 0


if __name__ == "__main__":
    sys.exit(main())
