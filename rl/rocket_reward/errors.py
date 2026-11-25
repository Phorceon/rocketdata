"""Errors the reward raises on purpose."""
from __future__ import annotations


class RewardSetupError(RuntimeError):
    """The machine or the installation is broken, so no answer can be scored.

    Raised for things the model did not cause: Java is missing, the OpenRocket
    jar is missing or is the wrong file, a data table is missing, or the
    self-test rocket no longer flies. Training must stop on this error. It is
    never turned into a score, because a made-up score would teach the model
    something that is not true.

    The message always says what to fix.
    """
