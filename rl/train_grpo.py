"""GRPO reinforcement learning for RocketData/Qwen3.5-4B-rocketdata-v5 using Unsloth + TRL.

Runs on a single 40 GB A100 (or 24-80 GB GPU) with 16-bit LoRA by default (Unsloth advises
16-bit LoRA over 4-bit QLoRA for the Qwen3.5 Gated DeltaNet family; pass --load-in-4bit if
VRAM-constrained). Uses rocket_reward.adapters.trl on a shared OpenRocket 24.12 SimPool.

Examples (run from rl/):
    python train_grpo.py --dry-run                       # no GPU: checks Java, data, reward wiring
    python train_grpo.py --smoke 10                      # 10-step GPU smoke test
    python train_grpo.py --max-steps 300 --wandb-project rocket-ai
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

RL_DIR = Path(__file__).resolve().parent
if str(RL_DIR) not in sys.path:
    sys.path.insert(0, str(RL_DIR))

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

DEFAULT_MODEL = "RocketData/Qwen3.5-4B-rocketdata-v5"
DEFAULT_PROMPTS = str(RL_DIR / "rocket_reward" / "prompts" / "synthetic" / "rl_prompts_v2.jsonl")


def load_prompt_rows(path: Path, split: str | None = "train") -> list[dict[str, Any]]:
    """Load RL prompt rows and validate every requirements dict before touching the GPU."""
    from rocket_reward.records import Requirements

    if not path.is_file():
        raise FileNotFoundError(f"prompts file not found: {path}")
    opener = gzip.open if path.name.endswith(".gz") else open
    want = split or None
    rows: list[dict[str, Any]] = []
    with opener(path, "rt", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if want is not None and row.get("split") != want:
                continue
            Requirements.from_dict(row["requirements"])
            rows.append({
                "id": str(row.get("id", f"row-{i}")),
                "system": str(row["system"]),
                "user": str(row["prompt"]),
                "requirements": json.dumps(row["requirements"], sort_keys=True, ensure_ascii=False),
            })
    if not rows:
        raise ValueError(f"no rows in {path} for split={want!r}")
    return rows


def format_prompt(tokenizer: Any, system: str, user: str) -> str:
    """Format one chat prompt with thinking OFF (matching SFT v5 verbatim <thought> format)."""
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        return tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def check_lora_targets(model: Any) -> None:
    """Verify vision modules stay frozen and language / linear_attn modules received LoRA."""
    names = [n for n, _ in model.named_modules() if n.endswith(".lora_A")]
    families = sorted({re.sub(r"\.\d+\.", ".N.", n.rsplit(".lora_A", 1)[0]) for n in names})
    print(f"[lora] {len(names)} adapted linear layers in {len(families)} families:", flush=True)
    for fam in families:
        print("  ", fam, flush=True)
    vision = [n for n in names if "visual" in n or "vision" in n]
    if vision:
        raise RuntimeError(f"LoRA reached {len(vision)} vision modules, e.g. {vision[0]}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--prompts", default=DEFAULT_PROMPTS)
    ap.add_argument("--split", default="train")
    ap.add_argument("--out", default="outputs/grpo-qwen35-4b")
    ap.add_argument("--max-steps", type=int, default=300)
    ap.add_argument("--smoke", type=int, default=0, help="Run only N steps and skip final export")
    ap.add_argument("--num-generations", type=int, default=8, help="GRPO group size G per prompt")
    ap.add_argument("--batch-size", type=int, default=8,
                    help="Completions per device micro-step (Unsloth expects a multiple of --num-generations)")
    ap.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    ap.add_argument("--max-prompt-len", type=int, default=1024)
    ap.add_argument("--max-completion-len", type=int, default=8192,
                    help="Max tokens generated per rocket (raise to 12288-16384 if VRAM allows)")
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--beta", type=float, default=0.04, help="KL penalty coefficient")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--load-in-4bit", action="store_true",
                    help="Use 4-bit QLoRA instead of 16-bit LoRA (default False; Unsloth advises 16-bit for Qwen3.5)")
    ap.add_argument("--fast-inference", action="store_true",
                    help="Enable Unsloth vLLM colocated fast generation (needs vllm installed)")
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.55,
                    help="vLLM VRAM share when --fast-inference is enabled")
    ap.add_argument("--workers", type=int, default=4, help="OpenRocket Java helper processes in SimPool")
    ap.add_argument("--save-steps", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--wandb-project", default="", help="Enable W&B logging under this project name")
    ap.add_argument("--run-name", default="")
    ap.add_argument("--resume", default="", help="Resume from checkpoint directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="No GPU needed: validate prompts, start SimPool, and score one canary rollout")
    return ap.parse_args()


def run_dry_run(args: argparse.Namespace) -> int:
    from rocket_reward.adapters.trl import make_diagnostics, make_reward
    from rocket_reward.sim import SimPool

    rows = load_prompt_rows(Path(args.prompts), args.split)
    print(f"[dry-run] loaded {len(rows)} valid '{args.split}' prompts from {args.prompts}")
    print(f"[dry-run] sample prompt[0]: {rows[0]['user'][:120]}")

    canary_ans = (RL_DIR / "rocket_reward" / "tests" / "data" / "gold_val.jsonl.gz")
    with gzip.open(canary_ans, "rt", encoding="utf-8") as fh:
        gold = json.loads(fh.readline())
    reqs_map = json.loads((RL_DIR / "rocket_reward" / "tests" / "data" / "model_val_requirements.json").read_text("utf-8"))
    gold_req = json.dumps(reqs_map[gold["id"]], sort_keys=True)

    with SimPool(min(2, max(1, args.workers))) as pool:
        reward = make_reward(simulator=pool, max_completion_tokens=args.max_completion_len)
        diags = make_diagnostics(reward)
        prompts = [[{"role": "user", "content": "gold"}], [{"role": "user", "content": "bad"}]]
        completions = [gold["answer"], "not a valid design"]
        comp_ids = [[1] * 100, [1] * args.max_completion_len]
        scores = reward(prompts, completions, completion_ids=comp_ids, requirements=[gold_req, rows[0]["requirements"]])
        reached = {
            k: fn(prompts, completions, completion_ids=comp_ids, requirements=[gold_req, rows[0]["requirements"]])
            for k, fn in diags.items()
        }
    print(f"[dry-run] reward scores: {scores}")
    print(f"[dry-run] reached targets: {reached['targets']}, parts: {reached['parts']}")
    assert scores[0] is not None and scores[0] > 0.70, f"expected gold to reach targets, got {scores[0]}"
    assert scores[1] == 0.0, f"expected truncated garbage to score 0.0, got {scores[1]}"
    print("[dry-run] PASS: prompts, OpenRocket SimPool, and TRL reward/diagnostics are ready")
    return 0


def main() -> int:
    args = parse_args()
    if args.dry_run:
        return run_dry_run(args)
    if (args.batch_size * args.grad_accum) % args.num_generations != 0:
        raise SystemExit(
            f"--batch-size ({args.batch_size}) * --grad-accum ({args.grad_accum}) "
            f"must be divisible by --num-generations ({args.num_generations})"
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("UNSLOTH_COMPILE_LOCATION", str(out / "unsloth_compiled_cache"))
    if args.wandb_project:
        os.environ["WANDB_PROJECT"] = args.wandb_project

    # Load and validate every prompt + requirements record BEFORE spinning up the GPU model
    rows = load_prompt_rows(Path(args.prompts), args.split)
    print(f"[data] loaded {len(rows)} '{args.split}' prompts from {args.prompts}", flush=True)

    # Import Unsloth before TRL/transformers so its patches apply cleanly
    from unsloth import FastModel
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer
    from rocket_reward.adapters.trl import make_diagnostics, make_reward
    from rocket_reward.sim import SimPool

    max_seq_len = args.max_prompt_len + args.max_completion_len
    t0 = time.time()
    load_kw: dict[str, Any] = dict(
        model_name=args.model,
        max_seq_length=max_seq_len,
        load_in_4bit=bool(args.load_in_4bit),
        load_in_16bit=not bool(args.load_in_4bit),
        fast_inference=bool(args.fast_inference),
    )
    if args.fast_inference:
        load_kw["max_lora_rank"] = args.rank
        load_kw["gpu_memory_utilization"] = args.gpu_memory_utilization
    model, processor = FastModel.from_pretrained(**load_kw)
    tokenizer = getattr(processor, "tokenizer", processor)
    print(f"[load] {args.model} loaded in {time.time() - t0:.1f}s (4bit={args.load_in_4bit})", flush=True)

    model = FastModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=0.0,
        bias="none",
        target_modules=None,  # Unsloth adapts attention + Gated DeltaNet + MLP projections
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )
    model.print_trainable_parameters()
    check_lora_targets(model)

    # Chat turns end with <|im_end|>, while Qwen3.5 base config eos is <|endoftext|>; stop on either.
    eos_ids = [
        tid for t in ("<|im_end|>", "<|endoftext|>")
        if isinstance((tid := tokenizer.convert_tokens_to_ids(t)), int) and tid >= 0
    ]
    if eos_ids:
        model.generation_config.eos_token_id = eos_ids
    eos_id = eos_ids[0] if eos_ids else tokenizer.eos_token_id

    ds = Dataset.from_list([
        {
            "id": r["id"],
            "prompt": format_prompt(tokenizer, r["system"], r["user"]),
            "requirements": r["requirements"],
        }
        for r in rows
    ])
    print(f"[data] sample formatted prompt:\n{ds[0]['prompt'][:260]!r}", flush=True)

    steps = args.smoke if args.smoke > 0 else args.max_steps
    report_to = "wandb" if args.wandb_project else "none"

    with SimPool(args.workers) as pool:
        reward = make_reward(
            simulator=pool,
            max_completion_tokens=args.max_completion_len,
            eos_token_id=eos_id,
        )
        diags = make_diagnostics(reward)

        grpo_args = GRPOConfig(
            output_dir=str(out / "checkpoints"),
            run_name=args.run_name or f"grpo-{Path(args.model).name}",
            max_steps=steps,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.05,
            optim="adamw_8bit",
            weight_decay=0.01,
            max_grad_norm=1.0,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_generations=args.num_generations,
            max_prompt_length=args.max_prompt_len,
            max_completion_length=args.max_completion_len,
            temperature=args.temperature,
            beta=args.beta,
            scale_rewards="batch",
            mask_truncated_completions=False,
            reward_weights=[1.0] + [0.0] * len(diags),
            logging_steps=1,
            save_steps=args.save_steps,
            save_total_limit=3,
            bf16=True,
            seed=args.seed,
            report_to=report_to,
        )

        trainer = GRPOTrainer(
            model=model,
            processing_class=tokenizer,
            reward_funcs=[reward, *diags.values()],
            args=grpo_args,
            train_dataset=ds,
        )
        trainer.train(resume_from_checkpoint=args.resume or None)

    if args.smoke <= 0:
        lora_dir = out / "lora"
        model.save_pretrained(str(lora_dir))
        processor.save_pretrained(str(lora_dir))
        print(f"[save] saved final LoRA adapter to {lora_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
