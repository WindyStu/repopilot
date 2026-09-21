"""Strong-model providers used by RepoPilot's coding stage."""

from __future__ import annotations

import os
from collections.abc import Mapping

from minisweagent.models.litellm_model import LitellmModel


class MissingProviderCredential(RuntimeError):
    """Raised when a selected provider is not configured before an agent run."""


def build_gemini_model(environ: Mapping[str, str] | None = None) -> LitellmModel:
    """Build the stable Gemini Flash model without retaining its API key.

    LiteLLM reads ``GEMINI_API_KEY`` from the process environment at request
    time. Keeping the value out of ``model_kwargs`` prevents it from appearing
    in serialized trajectories, reports, or debug output.
    """

    env = os.environ if environ is None else environ
    if not env.get("GEMINI_API_KEY"):
        raise MissingProviderCredential(
            "GEMINI_API_KEY is required for the Gemini strong model. "
            "Export a rotated key in the current shell before starting RepoPilot."
        )

    return LitellmModel(
        model_name="gemini/gemini-3.8-flash",
        cost_tracking="ignore_errors",
        model_kwargs={"drop_params": True, "timeout": 60, "num_retries": 2},
    )
