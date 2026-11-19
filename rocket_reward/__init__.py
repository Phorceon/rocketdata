"""rocket_reward: score one rocket-design answer from 0 to 1.

See DESIGN.md for what the score means. Importing this package does no work:
it reads no files and starts no processes.
"""
from .errors import RewardSetupError
from .records import Requirements, Result, StageCheck, Target
from .scoring import Preflight, preflight, score

__all__ = ["Preflight", "RewardSetupError", "Requirements", "Result", "StageCheck", "Target",
           "preflight", "score"]
