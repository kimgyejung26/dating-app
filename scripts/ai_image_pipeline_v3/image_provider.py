from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .config import DEFAULT_MODEL


class ImageProviderError(RuntimeError):
    """Base error for image provider contract failures."""


class LocalPersistenceError(ImageProviderError):
    """Raised when a provider output is not a persisted local ai_image artifact."""


class ProviderUnavailableError(ImageProviderError):
    """Raised when a scaffold provider cannot run generation in this environment."""


class ReferenceImagesUnsupportedError(ImageProviderError):
    """Raised when a provider cannot safely consume reference image inputs."""


@dataclass(frozen=True)
class ImageProviderRequest:
    prompt: str
    output_path: Path
    reference_image_paths: tuple[Path, ...] = ()
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)
    overwrite: bool = False


@dataclass(frozen=True)
class ImageProviderResult:
    provider_name: str
    output_path: Path
    persisted: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ImageProvider(Protocol):
    name: str

    def metadata(self) -> dict[str, Any]:
        ...

    def generate(self, request: ImageProviderRequest) -> ImageProviderResult:
        ...


def _resolved_ai_image_root(root: Path | str | None) -> Path | None:
    if root is None:
        return None
    return (Path(root).resolve() / "ai_image").resolve()


def assert_output_persisted_locally(output_path: Path | str, *, root: Path | str | None = None) -> Path:
    resolved = Path(output_path).resolve()
    if not resolved.exists():
        raise LocalPersistenceError(f"Provider output does not exist: {resolved}")
    if not resolved.is_file():
        raise LocalPersistenceError(f"Provider output is not a file: {resolved}")
    if resolved.stat().st_size <= 0:
        raise LocalPersistenceError(f"Provider output is empty: {resolved}")

    ai_image_root = _resolved_ai_image_root(root)
    if ai_image_root is not None:
        try:
            resolved.relative_to(ai_image_root)
        except ValueError as exc:
            raise LocalPersistenceError(f"Provider output is outside ai_image/: {resolved}") from exc
    elif "ai_image" not in resolved.parts:
        raise LocalPersistenceError(f"Provider output is not under an ai_image/ path: {resolved}")
    return resolved


def _request_root_from_output(output_path: Path) -> Path | None:
    resolved = output_path.resolve()
    parts = resolved.parts
    if "ai_image" not in parts:
        return None
    index = parts.index("ai_image")
    if index == 0:
        return None
    return Path(*parts[:index])


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    tmp.replace(path)


def _validate_reference_images(request: ImageProviderRequest) -> None:
    if not request.reference_image_paths:
        return
    output_root = _request_root_from_output(Path(request.output_path))
    if output_root is None:
        raise LocalPersistenceError("Provider output path must be under ai_image/ when reference images are used.")
    for reference_path in request.reference_image_paths:
        assert_output_persisted_locally(reference_path, root=output_root)


class CodexBuiltInImagegenProvider:
    name = DEFAULT_MODEL

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "codex_builtin_imagegen_omx",
            "runs_real_generation": False,
            "supports_reference_images": True,
            "checkpoint_required": "ai_image/manifests/pending-imagegen.json",
            "recovery_required": "scripts/recover_pending_imagegen_v3.py",
        }

    def generate(self, request: ImageProviderRequest) -> ImageProviderResult:
        raise ProviderUnavailableError(
            "Codex built-in imagegen is driven by the existing pending-imagegen checkpoint and recovery flow; "
            "this provider descriptor does not invoke real generation directly."
        )


class FixtureImageProvider:
    name = "fixture-local-image"

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "fixture",
            "runs_real_generation": False,
            "supports_reference_images": True,
            "writes_local_output": True,
        }

    def generate(self, request: ImageProviderRequest) -> ImageProviderResult:
        output_path = Path(request.output_path)
        if output_path.exists() and not request.overwrite:
            raise LocalPersistenceError(f"Refusing to overwrite existing provider output: {output_path.resolve()}")
        _write_bytes_atomic(output_path, _FIXTURE_PNG_BYTES)
        root = _request_root_from_output(output_path)
        persisted_path = assert_output_persisted_locally(output_path, root=root)
        return ImageProviderResult(
            provider_name=self.name,
            output_path=persisted_path,
            persisted=True,
            metadata={
                **dict(request.provider_metadata),
                "backend": "fixture",
                "referenceImagePaths": [str(path) for path in request.reference_image_paths],
            },
        )


class HermesNativeImageProvider:
    name = "hermes-native-imagegen"

    def __init__(
        self,
        *,
        text_to_image_executor: Callable[[ImageProviderRequest], Path | str | ImageProviderResult] | None = None,
        supports_reference_images: bool = False,
    ) -> None:
        self._text_to_image_executor = text_to_image_executor
        self._supports_reference_images = bool(supports_reference_images)

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "hermes_native_scaffold",
            "runs_real_generation": self._text_to_image_executor is not None,
            "supports_reference_images": self._supports_reference_images,
            "text_to_image_only": not self._supports_reference_images,
        }

    def generate(self, request: ImageProviderRequest) -> ImageProviderResult:
        if request.reference_image_paths and not self._supports_reference_images:
            raise ReferenceImagesUnsupportedError(
                "Hermes-native provider scaffold is text-to-image only until a reference-capable plugin is verified."
            )
        _validate_reference_images(request)
        if self._text_to_image_executor is None:
            raise ProviderUnavailableError("Hermes-native text-to-image executor is not configured.")

        result = self._text_to_image_executor(request)
        if isinstance(result, ImageProviderResult):
            output_path = result.output_path
            metadata = dict(result.metadata)
        else:
            output_path = Path(result)
            metadata = {}
        root = _request_root_from_output(Path(output_path))
        persisted_path = assert_output_persisted_locally(output_path, root=root)
        return ImageProviderResult(
            provider_name=self.name,
            output_path=persisted_path,
            persisted=True,
            metadata={**dict(request.provider_metadata), **metadata, "backend": "hermes_native_scaffold"},
        )


def default_image_provider() -> ImageProvider:
    return CodexBuiltInImagegenProvider()


# 1x1 transparent PNG. This is only for fixture tests and never represents a QA-approved image.
_FIXTURE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\x00"
    b"\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)
