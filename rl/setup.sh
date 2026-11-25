#!/usr/bin/env bash
# One-shot setup for a fresh GPU box. Run from anywhere: bash rl/setup.sh
set -euo pipefail
cd "$(dirname "$0")"

# 1. Java 17+ (OpenRocket needs it)
if ! command -v javac >/dev/null 2>&1; then
  echo "== installing OpenJDK 17"
  (sudo apt-get update && sudo apt-get install -y openjdk-17-jdk-headless) || apt-get install -y openjdk-17-jdk-headless
fi
java -version

# 2. Python deps
python -m pip install -U pip
python -m pip install -r requirements.txt

# 3. OpenRocket 24.12 jar (SHA-256 checked) + helper smoke check
python -m rocket_reward fetch-jar
python -m rocket_reward check

# 4. No-GPU wiring check: prompts, reward, SimPool
python train_grpo.py --dry-run
echo "== setup OK. Next: python train_grpo.py --smoke 15 --wandb-project rocket-ai"
