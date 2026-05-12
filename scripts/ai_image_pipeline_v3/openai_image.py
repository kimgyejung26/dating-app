from __future__ import annotations

from pathlib import Path


class OpenAIImageClient:
    """Disabled compatibility shim.

    The Seolleyeon image pipeline now runs in Codex built-in `$imagegen` mode only.
    This class remains solely so legacy imports fail loudly instead of silently
    using an API path.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError(
            "OpenAI Image API generation is disabled for this workflow. "
            "Use scripts/next_codex_imagegen_prompt_v3.py, built-in $imagegen, "
            "and scripts/recover_pending_imagegen_v3.py instead."
        )

    def generate(self, *, prompt: str) -> bytes:
        raise RuntimeError("OpenAI Image API generation is disabled; use Codex built-in $imagegen.")

    def edit_with_reference(self, *, prompt: str, reference_path: Path) -> bytes:
        raise RuntimeError("OpenAI Image API reference editing is disabled; use Codex built-in $imagegen.")
