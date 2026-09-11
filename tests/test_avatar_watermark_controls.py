"""Known controls for watermark evaluation: non-user, deterministic, bounded use.

The G004 worksheet has zero known-positive controls, so an evaluation run on it
could not tell "the model sees no overlays" from "there were no overlays to
see". These controls close that gap for policy reachability and model
capability. They are never evidence of production prevalence, precision or
recall, and the manifest says so.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import avatar_watermark_controls as controls_module  # noqa: E402
from avatar_watermark_controls import (  # noqa: E402
    REQUIRED_CONTROL_KINDS,
    build_controls,
    build_manifest,
    png_bytes,
)

SCHEMA = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "avatar_watermark_label_schema_v2.json").read_text(encoding="utf-8")
)


def test_every_required_control_kind_exists():
    kinds = {spec.control_kind for spec, _ in build_controls()}
    assert set(REQUIRED_CONTROL_KINDS) <= kinds


def test_labels_are_human_image_labels_never_model_errors():
    human = set(SCHEMA["humanImageLabels"])
    derived = set(SCHEMA["derivedModelErrors"])
    for spec, _ in build_controls():
        assert spec.primary_label in human, spec.evaluation_id
        assert spec.primary_label not in derived, spec.evaluation_id
        assert set(spec.all_visible_classes) <= human, spec.evaluation_id


def test_known_positives_exist_for_every_risk_positive_class_that_can_be_drawn():
    labels = {spec.primary_label for spec, _ in build_controls()}
    assert {"OVERLAY_WATERMARK", "GRAPHICAL_LOGO"} <= labels
    assert labels & set(SCHEMA["sceneNativeClasses"]) >= {"GARMENT_TEXT", "BACKGROUND_SIGNAGE", "NO_VISIBLE_RELEVANT_TEXT_OR_MARK"}


def test_generation_is_deterministic_in_process():
    first = [png_bytes(image) for _, image in build_controls()]
    second = [png_bytes(image) for _, image in build_controls()]
    assert first == second


def test_controls_differ_from_the_no_text_baseline():
    rendered = {spec.control_kind: png_bytes(image) for spec, image in build_controls()}
    baseline = rendered["no_text"]
    for kind, data in rendered.items():
        if kind != "no_text":
            assert data != baseline, kind


def test_manifest_states_its_bounded_purpose_and_carries_no_identifiers():
    manifest = build_manifest(build_controls())
    assert manifest["labelSchema"] == SCHEMA["schemaVersion"]
    assert manifest["provenanceCategory"] == "locally_generated_synthetic_without_user_data"
    assert "prevalence" in manifest["forbiddenUse"]
    serialized = json.dumps(manifest).lower()
    for forbidden in ("uid", "email", "gs://", "http", "signed", "bbox", "embedding", "landmark", "participant"):
        assert forbidden not in serialized, forbidden
    allowed = set(SCHEMA["storage"]["allowedFields"]) | {"controlKind", "construction", "pngSha256"}
    for entry in manifest["controls"]:
        assert set(entry) <= allowed, set(entry) - allowed


def test_generator_has_no_network_dependency():
    for name in ("socket", "urllib", "requests", "http", "google"):
        assert name not in vars(controls_module), name


def test_cli_writes_only_into_the_requested_directory(tmp_path):
    out = tmp_path / "controls"
    assert controls_module.main(["--out", str(out)]) == 0
    written = sorted(path.name for path in out.iterdir())
    assert written == sorted([f"ctl-{i:02d}.png" for i in range(1, 11)] + ["manifest.json"])


# ---------------------------------------------------------------------------
# Approved schema contract (2026-09-11)
# ---------------------------------------------------------------------------


def test_negative_class_name_covers_marks_not_only_text():
    """Renamed while zero labels existed: the class means no lettering, logo,
    brand mark or watermark, and GRAPHICAL_LOGO / BRAND_TEXT_OR_MARK are in the
    same taxonomy, so a text-only name was narrower than its meaning."""

    human = set(SCHEMA["humanImageLabels"])
    assert "NO_VISIBLE_RELEVANT_TEXT_OR_MARK" in human
    assert "NO_VISIBLE_RELEVANT_TEXT" not in human
    assert SCHEMA["renamedClasses"] == {"NO_VISIBLE_RELEVANT_TEXT": "NO_VISIBLE_RELEVANT_TEXT_OR_MARK"}
    assert "NO_VISIBLE_RELEVANT_TEXT_OR_MARK" in SCHEMA["sceneNativeClasses"]
    assert "NO_VISIBLE_RELEVANT_TEXT_OR_MARK" in SCHEMA["primaryLabelPrecedence"]
    assert "NO_VISIBLE_RELEVANT_TEXT_OR_MARK" in SCHEMA["derivedModelErrors"]["OCR_HALLUCINATION"]["derivation"]


def test_transcriptions_are_ephemeral_and_only_a_typed_outcome_is_stored():
    handling = SCHEMA["transcriptionHandling"]
    assert set(handling["appliesTo"]) == {"human transcription", "raw OCR transcription"}
    assert "ephemeral" in handling["allowedUse"]
    assert handling["afterDerivation"] == "discard"
    for store in ("persistent label dataset", "committed file", "Firestore", "logs"):
        assert any(store in entry for entry in handling["mustNotBeStoredIn"]), store
    mismatch = SCHEMA["derivedModelErrors"]["OCR_TRANSCRIPTION_MISMATCH"]
    assert mismatch["storedOutcome"] == "typed only: match | mismatch | not_evaluated"
    assert {"raw OCR text", "human transcription"} <= set(SCHEMA["storage"]["forbidden"])
    assert not {"transcription", "rawText", "ocrText"} & set(SCHEMA["storage"]["allowedFields"])


def test_approval_does_not_extend_to_g004_or_production_images():
    approval = SCHEMA["approval"]
    assert SCHEMA["status"] == "APPROVED"
    assert set(approval["scope"]) == {
        "label schema", "label guide", "storage and privacy contract", "synthetic controls",
    }
    not_covered = " ".join(approval["notCovered"])
    assert "G004_LABELING_AUTHORIZATION_UNVERIFIED" in not_covered
    assert "production" in not_covered
