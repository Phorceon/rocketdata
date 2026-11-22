"""Supervised fine-tuning of Qwen/Qwen3.5-4B (or another Qwen3.5-family model) on the rocketdata designs with Unsloth.

16-bit LoRA (Unsloth advises against 4-bit QLoRA for the Qwen3.5 family). Trains on
new_results/sft_v2.jsonl, minus every design with --max-parts components or more, and logs the loss on
new_results/sft_test_v2.jsonl after every epoch. The final adapter is the last epoch (the test set is not
used to pick an epoch, so its scores stay unbiased); every epoch's checkpoint is kept in <out>/checkpoints.
Loss is computed on the assistant answer only.

By default each answer is trained verbatim (<thought>...</thought><design>{json}</design>), so chat with
thinking off. --move-thought instead moves the <thought> text into the model's native <think> slot
(thinking on), as in the 2026-10-19 Agents-A1-4B run.

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
NEW_RESULTS = REPO / "new_results"
THOUGHT_RE = re.compile(r"^\s*<thought>\s*(.*?)\s*</thought>\s*(<design>.*</design>)\s*$", re.S)
INSTRUCTION_PART = "<|im_start|>user\n"
RESPONSE_PART = "<|im_start|>assistant\n"


def load_messages(path, keep_thought, max_parts=0):
    """Return one message list per JSONL row, optionally moving <thought> into reasoning_content.

    With max_parts > 0, rows whose design has that many components or more are skipped (see filter_data.py).
    """
    from filter_data import part_count

    out, skipped = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if max_parts and part_count(row) >= max_parts:
                skipped += 1
                continue
            msgs = [dict(m) for m in row["messages"]]
            if not keep_thought:
                m = THOUGHT_RE.match(msgs[-1]["content"])
                if m is None:
                    raise ValueError(f"{row['id']}: assistant answer is not <thought>...</thought><design>...</design>")
                msgs[-1]["reasoning_content"] = m.group(1)
                msgs[-1]["content"] = m.group(2)
            out.append(msgs)
    if skipped:
        print(f"[data] {path}: skipped {skipped} rows with {max_parts}+ design components", flush=True)
    return out


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--out", default=r"C:\ft\qwen35-rocket", help="keep this path short on Windows")
    ap.add_argument("--train", default=str(NEW_RESULTS / "sft_v2.jsonl"))
    ap.add_argument("--test", default=str(NEW_RESULTS / "sft_test_v2.jsonl"))
    ap.add_argument("--max-parts", type=int, default=60,
                    help="skip training rows whose design has this many components or more (0 keeps all)")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=16)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=6400, help="sft_v2 has answers up to ~6,300 tokens")
    ap.add_argument("--seed", type=int, default=42, help="LoRA init and data order (42 = the shipped model)")
    ap.add_argument("--keep-thought", dest="keep_thought", action="store_true", default=True,
                    help="train on <thought> verbatim, then chat with thinking off (the default)")
    ap.add_argument("--move-thought", dest="keep_thought", action="store_false",
                    help="move <thought> into the <think> slot instead (thinking-on training)")
    ap.add_argument("--smoke", type=int, default=0, help="run only N optimizer steps, then stop (no saving)")
    ap.add_argument("--max-vram-gb", type=float, default=0,
                    help="cap PyTorch's GPU memory in GiB (e.g. 14 on a 16 GB card; also sets PYTORCH_CUDA_ALLOC_CONF="
                         "garbage_collection_threshold:0.8 unless set): on Windows its cache otherwise grows past the "
                         "card into system RAM, and steps run several times slower")
    ap.add_argument("--resume", metavar="CHECKPOINT",
                    help="continue an interrupted run from <out>/checkpoints/checkpoint-N (same settings otherwise)")
    ap.add_argument("--no-export", action="store_true", help="save the LoRA adapter only")
    ap.add_argument("--export-only", action="store_true", help="skip training; export from <out>/lora")
    ap.add_argument("--gguf", default="q8_0",
                    help="llama.cpp quantization for the GGUF export (q4_k_m breaks far more of the JSON)")
    ap.add_argument("--name", help="GGUF file name stem (default: <model name>-rocketdata); "
                                   "with --export-only pass the same --model or --name as the training run")
    args = ap.parse_args()
    if args.resume and (args.smoke or args.export_only):
        ap.error("--resume can't be combined with --smoke or --export-only")
    return args


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


def export_gguf(model, processor, out, quant, name, base):
    """Write <out>/gguf/<name>.*.gguf (model + mmproj); files Unsloth names after the base model get renamed.

    Unsloth merges into a scratch folder, takes the GGUF's display name from that folder's name and
    writes the files to "<scratch>_gguf". The new files are staged in <out>/gguf.new and swapped in for
    <out>/gguf in one rename, so a failure (for example a file still open in Studio or llama-server)
    leaves the previous GGUFs untouched instead of a mix of old and new.
    """
    scratch, built = out / name, out / f"{name}_gguf"
    dest, staged, old = out / "gguf", out / "gguf.new", out / "gguf.old"
    if scratch in (dest, staged, old):
        raise ValueError(f"--name {name!r} collides with an output folder")
    try:
        model.save_pretrained_gguf(str(scratch), processor, quantization_method=quant)
        files = sorted(built.glob("*.gguf"))
        if not any("mmproj" not in f.name for f in files):
            raise RuntimeError(f"Unsloth produced no model GGUF in {built}")
        shutil.rmtree(staged, ignore_errors=True)
        shutil.rmtree(old, ignore_errors=True)
        staged.mkdir()
        for f in files:
            os.replace(f, staged / f.name.replace(f"{base}.", f"{name}.", 1))
        if dest.exists():
            dest.rename(old)  # raises, changing nothing, if a file inside is open
        staged.rename(dest)
        shutil.rmtree(old, ignore_errors=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(built, ignore_errors=True)
    final = sorted(p.name for p in dest.glob("*.gguf"))
    print(f"[export] GGUF files: {final}", flush=True)
    if not any("mmproj" not in f for f in final):
        raise RuntimeError(f"no model GGUF in {dest} after export")


def export(model, processor, out, quant, name, base):
    """Save merged 16-bit weights and a GGUF. Each step runs even if the other fails; returns the failed ones."""
    # Chat turns end with <|im_end|>, but the base config's eos is <|endoftext|>; stop on either.
    tok = getattr(processor, "tokenizer", processor)
    model.generation_config.eos_token_id = [tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")]
    failed = []
    for step, fn in [
        ("merged_16bit", lambda: model.save_pretrained_merged(str(out / "merged_16bit"), processor, save_method="merged_16bit")),
        ("gguf", lambda: export_gguf(model, processor, out, quant, name, base)),
    ]:
        t = time.time()
        try:
            fn()
            print(f"[export] {step} done in {time.time() - t:.0f}s", flush=True)
        except Exception:
            failed.append(step)
            print(f"[export] {step} FAILED:", flush=True)
            traceback.print_exc()
    return failed


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = args.model.rstrip("/\\").replace("\\", "/").split("/")[-1]
    name = args.name or f"{base}-rocketdata"
    # Unsloth writes generated kernels to ./unsloth_compiled_cache by default; keep them out of the repo.
    os.environ.setdefault("UNSLOTH_COMPILE_LOCATION", str(out / "unsloth_compiled_cache"))
    if args.max_vram_gb:  # must be set before torch starts CUDA; frees cached blocks as usage nears the cap
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "garbage_collection_threshold:0.8")

    from unsloth import FastModel  # import unsloth before trl/transformers so its patches apply
    from unsloth.chat_templates import train_on_responses_only
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    if args.max_vram_gb:
        fraction = args.max_vram_gb * 2**30 / torch.cuda.get_device_properties(0).total_memory
        if fraction < 1:
            torch.cuda.set_per_process_memory_fraction(fraction)

    load_kw = dict(max_seq_length=args.max_len, dtype=None, load_in_4bit=False, load_in_16bit=True,
                   full_finetuning=False, use_gradient_checkpointing="unsloth")

    if args.export_only:
        model, processor = FastModel.from_pretrained(model_name=str(out / "lora"), **load_kw)
        return 1 if export(model, processor, out, args.gguf, name, base) else 0

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

    train_text = [render(m) for m in load_messages(args.train, args.keep_thought, args.max_parts)]
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

    start = 0
    if args.resume:
        start = json.loads((Path(args.resume) / "trainer_state.json").read_text(encoding="utf-8"))["global_step"]
    t0 = time.time()
    stats = trainer.train(resume_from_checkpoint=args.resume)
    # stats.training_loss is wrong after a resume (transformers divides this session's loss by every step), so
    # average the logged per-step losses instead; the log history is restored from the checkpoint
    losses = [h["loss"] for h in trainer.state.log_history if "loss" in h]
    print(f"[train] {stats.global_step - start} steps in {(time.time() - t0) / 60:.1f} min"
          f"{f' (resumed at step {start})' if start else ''}, mean train loss {sum(losses) / len(losses):.4f} "
          f"over {len(losses)} steps", flush=True)
    vram("after training")
    if smoke:
        return 0

    evals = [(h["epoch"], h["eval_loss"]) for h in trainer.state.log_history if "eval_loss" in h]
    print(f"[train] test loss per epoch: {', '.join(f'{e:g}: {l:.4f}' for e, l in evals)}; "
          f"lowest at {trainer.state.best_model_checkpoint}; saving the last epoch", flush=True)
    (out / "train_log.json").write_text(json.dumps({
        "args": vars(args),
        "resumed_at_step": start,
        "lowest_test_loss_checkpoint": trainer.state.best_model_checkpoint,
        "lowest_test_loss": trainer.state.best_metric,
        "log_history": trainer.state.log_history,
    }, indent=1), encoding="utf-8")

    model.save_pretrained(str(out / "lora"))
    processor.save_pretrained(str(out / "lora"))
    print(f"[save] LoRA adapter (last epoch) -> {out / 'lora'}", flush=True)
    if args.no_export:
        return 0
    return 1 if export(model, processor, out, args.gguf, name, base) else 0


if __name__ == "__main__":
    sys.exit(main())
