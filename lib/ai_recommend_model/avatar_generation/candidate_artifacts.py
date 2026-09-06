from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import io
import json
from typing import Any, Mapping, Optional

from PIL import Image

from avatar_generation.model_adapters.azure_contracts import AzureProviderError


ARTIFACT_SCHEMA = "azure_candidate_artifact_v2"
_METADATA_PARAMS = "generationParamsB64"


class CandidateArtifactNeedsReview(AzureProviderError):
    def __init__(self, error_code: str) -> None:
        super().__init__(error_code, retryable=False, failure_class="artifact_recovery")


@dataclass(frozen=True)
class RecoveredCandidateArtifact:
    image_bytes: bytes
    seed: int
    generation_params: dict[str, Any]
    generation_id: str
    candidate_index: int
    recovery_source: str = "deterministic_storage_object"


def generation_id_for(*, job_id: str, idempotency_key: str) -> str:
    material = f"{job_id}\x00{idempotency_key}".encode("utf-8")
    return "gen_" + hashlib.sha256(material).hexdigest()[:24]


def source_identity_hash_for(
    *,
    source_photo_ids: list[str],
    source_photo_refs: list[str],
    source_photo_object_generations: list[str],
) -> str:
    material = json.dumps(
        {
            "sourcePhotoIds": list(source_photo_ids),
            "sourcePhotoRefs": list(source_photo_refs),
            "sourcePhotoObjectGenerations": list(source_photo_object_generations),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "src_" + hashlib.sha256(material).hexdigest()[:24]


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not str(uri).startswith("gs://"):
        raise CandidateArtifactNeedsReview("azure_candidate_artifact_ref_invalid")
    bucket_and_path = str(uri)[5:]
    bucket, separator, path = bucket_and_path.partition("/")
    if not separator or not bucket or not path:
        raise CandidateArtifactNeedsReview("azure_candidate_artifact_ref_invalid")
    return bucket, path


def _blob(storage_client: Any, image_ref: str) -> Any:
    bucket, path = _parse_gcs_uri(image_ref)
    return storage_client.bucket(bucket).blob(path)


def _encoded_params(params: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(params), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decoded_params(raw: str) -> dict[str, Any]:
    try:
        decoded = base64.urlsafe_b64decode(str(raw).encode("ascii"))
        value = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise CandidateArtifactNeedsReview(
            "azure_candidate_artifact_manifest_invalid"
        ) from exc
    if not isinstance(value, dict):
        raise CandidateArtifactNeedsReview("azure_candidate_artifact_manifest_invalid")
    return dict(value)


def _validate_png(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG" or image.width <= 0 or image.height <= 0:
                raise ValueError("invalid PNG")
            if max(image.size) > 3840:
                raise ValueError("image dimensions too large")
    except Exception as exc:
        raise CandidateArtifactNeedsReview("azure_candidate_artifact_invalid") from exc


def persist_candidate_artifact(
    storage_client: Any,
    *,
    image_ref: str,
    image_bytes: bytes,
    generation_id: str,
    candidate_index: int,
    candidate_id: str,
    source_identity_hash: str,
    seed: int,
    generation_params: Mapping[str, Any],
) -> RecoveredCandidateArtifact:
    _validate_png(image_bytes)
    try:
        existing = recover_candidate_artifact(
            storage_client,
            image_ref=image_ref,
            expected_generation_id=generation_id,
            expected_candidate_index=candidate_index,
            expected_candidate_id=candidate_id,
            expected_source_identity_hash=source_identity_hash,
        )
    except CandidateArtifactNeedsReview:
        raise
    except AzureProviderError as exc:
        # This function is entered only after Azure returned image bytes. A
        # pre-create existence check that cannot complete must never turn into
        # a retryable provider regeneration.
        raise CandidateArtifactNeedsReview(
            "azure_candidate_artifact_precondition_unknown_after_provider_success"
        ) from exc
    if existing is not None:
        return existing

    blob = _blob(storage_client, image_ref)
    digest = hashlib.sha256(image_bytes).hexdigest()
    blob.metadata = {
        "artifactSchema": ARTIFACT_SCHEMA,
        "generationId": generation_id,
        "candidateIndex": str(int(candidate_index)),
        "candidateId": candidate_id,
        "sourceIdentityHash": source_identity_hash,
        "seed": str(int(seed)),
        "sha256": digest,
        _METADATA_PARAMS: _encoded_params(generation_params),
    }
    blob.cache_control = "private, max-age=0, no-store"
    try:
        blob.upload_from_string(
            image_bytes,
            content_type="image/png",
            predefined_acl=None,
            if_generation_match=0,
        )
    except Exception as upload_error:
        # A concurrent recovery may have won the create-only race. Accept only
        # an object whose complete deterministic manifest validates. Once the
        # provider has succeeded, an upload error is itself ambiguous: if the
        # object cannot be proven valid, never purchase another generation.
        try:
            recovered = recover_candidate_artifact(
                storage_client,
                image_ref=image_ref,
                expected_generation_id=generation_id,
                expected_candidate_index=candidate_index,
                expected_candidate_id=candidate_id,
                expected_source_identity_hash=source_identity_hash,
            )
        except Exception as recovery_error:
            raise CandidateArtifactNeedsReview(
                "azure_candidate_artifact_write_outcome_unknown"
            ) from recovery_error
        if recovered is None:
            raise CandidateArtifactNeedsReview(
                "azure_candidate_artifact_missing_after_provider_success"
            ) from upload_error
        return recovered
    if hasattr(blob, "patch"):
        blob.patch()
    return RecoveredCandidateArtifact(
        image_bytes=image_bytes,
        seed=int(seed),
        generation_params=dict(generation_params),
        generation_id=generation_id,
        candidate_index=int(candidate_index),
        recovery_source="provider_success_storage_write",
    )


def recover_candidate_artifact(
    storage_client: Any,
    *,
    image_ref: str,
    expected_generation_id: str,
    expected_candidate_index: int,
    expected_candidate_id: str,
    expected_source_identity_hash: str,
) -> Optional[RecoveredCandidateArtifact]:
    blob = _blob(storage_client, image_ref)
    try:
        if not blob.exists():
            return None
        if hasattr(blob, "reload"):
            blob.reload()
        data = bytes(blob.download_as_bytes())
    except CandidateArtifactNeedsReview:
        raise
    except Exception as exc:
        raise AzureProviderError(
            "azure_candidate_artifact_storage_unavailable",
            retryable=True,
            failure_class="artifact_storage",
        ) from exc

    metadata = getattr(blob, "metadata", None)
    if not isinstance(metadata, Mapping) or metadata.get("artifactSchema") != ARTIFACT_SCHEMA:
        raise CandidateArtifactNeedsReview(
            "azure_candidate_artifact_manifest_incomplete"
        )
    if (
        str(metadata.get("generationId") or "") != expected_generation_id
        or str(metadata.get("candidateId") or "") != expected_candidate_id
        or str(metadata.get("candidateIndex") or "") != str(int(expected_candidate_index))
        or str(metadata.get("sourceIdentityHash") or "")
        != expected_source_identity_hash
    ):
        raise CandidateArtifactNeedsReview(
            "azure_candidate_artifact_identity_mismatch"
        )
    _validate_png(data)
    digest = hashlib.sha256(data).hexdigest()
    if digest != str(metadata.get("sha256") or ""):
        raise CandidateArtifactNeedsReview("azure_candidate_artifact_hash_mismatch")
    try:
        seed = int(str(metadata.get("seed") or ""))
    except (TypeError, ValueError) as exc:
        raise CandidateArtifactNeedsReview(
            "azure_candidate_artifact_manifest_invalid"
        ) from exc
    return RecoveredCandidateArtifact(
        image_bytes=data,
        seed=seed,
        generation_params=_decoded_params(str(metadata.get(_METADATA_PARAMS) or "")),
        generation_id=expected_generation_id,
        candidate_index=int(expected_candidate_index),
    )


__all__ = [
    "ARTIFACT_SCHEMA",
    "CandidateArtifactNeedsReview",
    "RecoveredCandidateArtifact",
    "generation_id_for",
    "source_identity_hash_for",
    "persist_candidate_artifact",
    "recover_candidate_artifact",
]
