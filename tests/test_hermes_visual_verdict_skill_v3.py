import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "hermes" / "skills" / "creative" / "visual-verdict"
SKILL_MD = SKILL_DIR / "SKILL.md"
SCHEMA_MD = SKILL_DIR / "references" / "verdict-schema.md"
VALIDATOR_SCRIPT = SKILL_DIR / "scripts" / "validate_visual_verdict_schema.py"
PHASE_DOC = ROOT / "docs" / "hermes-migration" / "phase-c-visual-verdict.md"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("hermes_visual_verdict_validator", VALIDATOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load validator from {VALIDATOR_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HermesVisualVerdictSkillV3Tests(unittest.TestCase):
    def _asset_payload(self):
        from scripts.ai_image_pipeline_v3.visual_verdict import ASSET_QA_TYPE

        return {
            "qaType": ASSET_QA_TYPE,
            "sheetId": "fixture_asset_sheet",
            "assets": [
                {
                    "assetId": "female_001__face_card__v001",
                    "profileId": "female_001",
                    "gender": "female",
                    "shotType": "face_card",
                    "targetFaceType": "deer_like",
                    "observedFaceType": "deer_like",
                    "faceTypeConfidence": 0.92,
                    "targetLooksLevelBand": "2.5-3.2",
                    "observedLooksLevelBand": "2.5-3.2",
                    "looksLevelConfidence": 0.88,
                    "adultVisual": True,
                    "photoRealism": 4.6,
                    "campusRealism": 4.4,
                    "brandFit": 4.5,
                    "shotTypeReadable": True,
                    "influencerRisk": 0.2,
                    "childlikeRisk": 0.0,
                    "schoolUniformRisk": 0.0,
                    "sexualizationRisk": 0.0,
                    "artifactRisk": 0.2,
                    "metadataMismatch": False,
                    "mismatchFields": [],
                    "decision": "approved",
                    "rejectReasons": [],
                    "notes": "fixture only",
                }
            ],
            "summary": {"approvedCount": 1, "needsReviewCount": 0, "rejectedCount": 0},
        }

    def _identity_payload(self):
        from scripts.ai_image_pipeline_v3.visual_verdict import IDENTITY_QA_TYPE

        return {
            "qaType": IDENTITY_QA_TYPE,
            "sheetId": "fixture_identity_sheet",
            "identities": [
                {
                    "profileId": "female_001",
                    "gender": "female",
                    "targetFaceType": "deer_like",
                    "observedFaceType": "deer_like",
                    "targetLooksLevelBand": "2.5-3.2",
                    "observedLooksLevelBand": "2.5-3.2",
                    "assetIds": {
                        "face_card": "female_001__face_card__v001",
                        "silhouette_card": "female_001__silhouette_card__v001",
                        "vibe_card": "female_001__vibe_card__v001",
                    },
                    "assetDecisions": {"face_card": "approved", "silhouette_card": "approved", "vibe_card": "approved"},
                    "faceToSilhouetteConsistency": 4.2,
                    "faceToVibeConsistency": 4.2,
                    "sameIdentity": True,
                    "completeIdentityDecision": "approved",
                    "countsTowardDistribution": True,
                    "failedShotTypes": [],
                    "retryShotTypes": [],
                    "rejectReasons": [],
                    "notes": "fixture only",
                }
            ],
            "summary": {"approvedCompleteIdentities": 1, "needsReviewIdentities": 0, "rejectedIdentities": 0},
        }

    def _distribution_payload(self):
        from scripts.ai_image_pipeline_v3.visual_verdict import DISTRIBUTION_QA_TYPE

        return {
            "qaType": DISTRIBUTION_QA_TYPE,
            "finalDecision": "needs_more_generation",
            "approvedCompleteIdentityCount": 1,
            "approvedImageCount": 3,
            "femaleApprovedIdentityCount": 1,
            "maleApprovedIdentityCount": 0,
            "globalFaceTypeCounts": {"deer_like": 1},
            "globalFaceTypeDeficits": {},
            "globalFaceTypeSurpluses": {},
            "genderFaceTypeCounts": {"female": {"deer_like": 1}, "male": {}},
            "genderFaceTypeDeficits": {"female": {}, "male": {}},
            "genderFaceTypeSurpluses": {"female": {}, "male": {}},
            "globalLooksLevelBandCounts": {"2.5-3.2": 1},
            "globalLooksLevelBandDeficits": {},
            "globalLooksLevelBandSurpluses": {},
            "genderLooksLevelBandCounts": {"female": {"2.5-3.2": 1}, "male": {}},
            "genderLooksLevelBandDeficits": {"female": {}, "male": {}},
            "genderLooksLevelBandSurpluses": {"female": {}, "male": {}},
            "invalidIdentities": [],
            "nextGenerationDirective": {"shouldGenerateMore": True, "targetBuckets": [], "stopGeneratingBuckets": []},
            "notes": "fixture only",
        }

    def test_skill_files_schema_reference_and_install_notes_exist(self):
        from scripts.ai_image_pipeline_v3.visual_verdict import ASSET_QA_TYPE, DISTRIBUTION_QA_TYPE, IDENTITY_QA_TYPE

        for path in (SKILL_MD, SCHEMA_MD, VALIDATOR_SCRIPT, PHASE_DOC):
            self.assertTrue(path.exists(), path)

        skill_text = SKILL_MD.read_text(encoding="utf-8")
        schema_text = SCHEMA_MD.read_text(encoding="utf-8")
        phase_text = PHASE_DOC.read_text(encoding="utf-8")

        self.assertIn("name: visual-verdict", skill_text)
        self.assertRegex(skill_text, r"description:\s+Use when")
        self.assertIn("references/verdict-schema.md", skill_text)
        self.assertIn("~/.hermes/skills/creative/visual-verdict/", phase_text)
        for qa_type in (ASSET_QA_TYPE, IDENTITY_QA_TYPE, DISTRIBUTION_QA_TYPE):
            self.assertIn(qa_type, schema_text)
        for safety_phrase in (
            "no attractiveness scoring",
            "no face rating",
            "no real-person identification",
            "no sensitive trait inference",
        ):
            self.assertIn(safety_phrase, schema_text)

    def test_normalized_verdict_schema_enforces_strict_shape_threshold_and_retry_alias(self):
        validator = load_validator_module()
        good = {
            "score": 92,
            "verdict": "pass",
            "category_match": True,
            "differences": [],
            "suggestions": [],
            "reasoning": "Reference and generated image match the intended visual category.",
        }
        self.assertEqual(validator.validate_normalized_verdict(good)["verdict"], "pass")

        retry_alias = dict(good, score=72, verdict="retry", differences=["Spacing differs"], suggestions=["Adjust spacing"])
        self.assertEqual(validator.validate_normalized_verdict(retry_alias)["verdict"], "revise")

        with self.assertRaises(ValueError):
            validator.validate_normalized_verdict(dict(good, score=89))
        with self.assertRaises(ValueError):
            validator.validate_normalized_verdict(dict(good, extra="not strict"))
        with self.assertRaises(ValueError):
            validator.validate_normalized_verdict(dict(good, reasoning="Rate attractiveness against the reference."))

    def test_project_payloads_preserve_current_visual_verdict_contracts(self):
        from scripts.ai_image_pipeline_v3.active_visual_verdict_runner import (
            validate_asset_qa_json,
            validate_distribution_qa_json,
            validate_identity_qa_json,
        )
        from scripts.ai_image_pipeline_v3.visual_verdict import ASSET_QA_TYPE, DISTRIBUTION_QA_TYPE, IDENTITY_QA_TYPE

        validator = load_validator_module()
        self.assertEqual(validator.ASSET_QA_TYPE, ASSET_QA_TYPE)
        self.assertEqual(validator.IDENTITY_QA_TYPE, IDENTITY_QA_TYPE)
        self.assertEqual(validator.DISTRIBUTION_QA_TYPE, DISTRIBUTION_QA_TYPE)

        asset = self._asset_payload()
        identity = self._identity_payload()
        distribution = self._distribution_payload()

        validate_asset_qa_json(asset)
        validate_identity_qa_json(identity)
        validate_distribution_qa_json(distribution)

        self.assertEqual(validator.validate_project_visual_verdict_payload(asset)["kind"], "asset")
        self.assertEqual(validator.validate_project_visual_verdict_payload(identity)["kind"], "identity")
        self.assertEqual(validator.validate_project_visual_verdict_payload(distribution)["kind"], "distribution")

    def test_project_retry_is_not_a_decision_but_external_retry_normalizes_to_revise(self):
        validator = load_validator_module()
        asset = self._asset_payload()
        asset["assets"][0]["decision"] = "retry"
        with self.assertRaises(ValueError):
            validator.validate_project_visual_verdict_payload(asset)

        normalized = {
            "score": 70,
            "verdict": "retry",
            "category_match": True,
            "differences": ["One visible mismatch remains."],
            "suggestions": ["Revise the mismatch and rerun visual-verdict."],
            "reasoning": "Compatibility alias should not leak into the stored verdict.",
        }
        self.assertEqual(validator.validate_any_visual_verdict_payload(normalized)["verdict"], "revise")

    def test_json_examples_are_parseable_and_validate_without_vision_or_generation(self):
        validator = load_validator_module()
        combined = SKILL_MD.read_text(encoding="utf-8") + "\n" + SCHEMA_MD.read_text(encoding="utf-8")
        examples = re.findall(r"```json\s*(.*?)\s*```", combined, flags=re.DOTALL | re.IGNORECASE)
        self.assertGreaterEqual(len(examples), 4)
        seen_kinds = set()
        for example in examples:
            payload = json.loads(example)
            validated = validator.validate_any_visual_verdict_payload(payload)
            seen_kinds.add(validated.get("kind", "normalized"))
        self.assertTrue({"normalized", "asset", "identity", "distribution"}.issubset(seen_kinds))


if __name__ == "__main__":
    unittest.main()
