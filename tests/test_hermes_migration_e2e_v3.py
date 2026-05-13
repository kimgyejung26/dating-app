import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE_E_DOC = ROOT / "docs" / "hermes-migration" / "phase-e-hermes-execution.md"
CONSOLIDATED_DOC = ROOT / "docs" / "hermes-image-pipeline-migration.md"
HANDOFF_DOC = ROOT / "docs" / "hermes-migration" / "handoffs" / "run-e-handoff.md"
VALIDATOR_SCRIPT = ROOT / "hermes" / "skills" / "creative" / "visual-verdict" / "scripts" / "validate_visual_verdict_schema.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("hermes_visual_verdict_validator_e2e", VALIDATOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load validator from {VALIDATOR_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HermesMigrationE2EV3Tests(unittest.TestCase):
    def _write_manifest(self, root: Path, identities=("female_001",)) -> None:
        from scripts.ai_image_pipeline_v3.config import pipeline_paths, prompt_hash
        from scripts.ai_image_pipeline_v3.manifest import write_generation_outputs

        rows = []
        for identity_id in identities:
            gender, numeric = identity_id.split("_", 1)
            for shot in ("face_card", "silhouette_card", "vibe_card"):
                prompt = f"fixture prompt for {identity_id} {shot}"
                rows.append(
                    {
                        "assetId": f"{identity_id}__{shot}__v001",
                        "profileId": identity_id,
                        "gender": gender,
                        "numericId": numeric,
                        "shotType": shot,
                        "prompt": prompt,
                        "promptHash": prompt_hash(prompt),
                        "status": "prepared",
                        "activeForTarget": True,
                        "isReserve": False,
                        "attempt": 0,
                        "attemptCount": 0,
                        "targetFaceType": "deer_like",
                        "targetLooksLevelBand": "2.5-3.2",
                        "localPath": str(root / "ai_image" / "raw" / f"{identity_id}__{shot}__v001__attempt01.png"),
                        "finalPath": str(root / "ai_image" / gender / numeric / f"{shot}.png"),
                    }
                )
        write_generation_outputs(pipeline_paths(root), rows)

    def test_fixture_e2e_covers_wrapper_identity_pending_recovery_and_visual_verdict_without_generation(self):
        from scripts.ai_image_pipeline_v3.hermes_wrapper import HermesWrapperConfig, run_hermes_wrapper
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityParallelConfig, identity_parallel_status, run_identity_parallel

        validator = load_validator_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, identities=("female_001",))

            wrapper = run_hermes_wrapper(
                HermesWrapperConfig(
                    root=root,
                    run_id="run_e_fixture",
                    task_brief="Run E fixture e2e: no real image generation.",
                    execution_mode="fixture",
                )
            )
            self.assertEqual(wrapper.status, "fixture_complete")
            manifest_rows = [
                json.loads(line)
                for line in wrapper.manifest_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(manifest_rows[0]["provider"], "codex-built-in-imagegen")
            self.assertEqual(manifest_rows[0]["command_used"], ["fixture"])
            validator.validate_normalized_verdict(json.loads(Path(manifest_rows[0]["verdict_path"]).read_text(encoding="utf-8")))

            identity = run_identity_parallel(
                IdentityParallelConfig(root=root, run_id="run_e_identity_fixture", workers=1, fixture=True)
            )
            self.assertEqual(identity["status"], "complete")
            self.assertEqual(identity["selectedIdentities"], ["female_001"])

            status = identity_parallel_status(root, asset_id="female_001__silhouette_card__v001")
            self.assertTrue(status["exists"])
            pending = status["pending"]
            self.assertTrue(pending["perAssetPending"])
            self.assertTrue(pending["resolved"])
            self.assertIn("face_card.png", pending["referenceImagePath"])
            self.assertTrue((root / "ai_image" / "female" / "001" / "face_card.png").exists())
            self.assertTrue((root / "ai_image" / "female" / "001" / "silhouette_card.png").exists())
            self.assertTrue((root / "ai_image" / "female" / "001" / "vibe_card.png").exists())

    def test_run_e_docs_and_handoff_cover_required_hermes_execution_contract(self):
        for path in (PHASE_E_DOC, CONSOLIDATED_DOC, HANDOFF_DOC):
            self.assertTrue(path.exists(), path)

        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (PHASE_E_DOC, CONSOLIDATED_DOC, HANDOFF_DOC)
        )
        required_phrases = (
            "OMX mode",
            "Hermes background terminal mode",
            "Hermes /goal mode",
            "Hermes Kanban mode",
            "bounded-identity-parallel-run",
            "per-asset pending status",
            "asset recovery",
            "visual-verdict Skill installation",
            "provider/backend limitations",
            "Do not use Hermes delegate_task as the durable long-running mechanism",
            "Example command",
            "fixture/mock only",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

        handoff_text = HANDOFF_DOC.read_text(encoding="utf-8")
        self.assertIn('"docs_changed"', handoff_text)
        self.assertIn('"e2e_fixture_command"', handoff_text)
        self.assertIn('"final_run_instructions"', handoff_text)


if __name__ == "__main__":
    unittest.main()
