"""Thin wrappers that let RL trainers call the one scoring core (scoring.py).

    rocket_reward.adapters.trl        Hugging Face TRL / Unsloth GRPO reward functions
    rocket_reward.adapters.verifiers  a reward for Prime Intellect verifiers 0.4.x (not yet
                                      run against the real library)

Importing this package or either module imports no trainer library, reads no
files and starts no processes. See README.md in this folder for how to use them.
"""
