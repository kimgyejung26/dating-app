import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class E2EBoundedImagegenSmokeV3Tests(unittest.TestCase):
    def _config(self, root: Path, **kwargs):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import E2EConfig

        return E2EConfig(root=root, chunk_id=kwargs.pop("chunk_id", "e2e_bounded_test"), **kwargs)

    def _fake_run(self, *, help_by_bin=None):
        help_by_bin = help_by_bin or {"omx": "--image -i", "codex": "--image -i"}

        def run(args, **kwargs):
            self.assertFalse(kwargs.get("shell", False))
            if args[:3] == ["git", "status", "--short"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            if "--help" in args:
                return subprocess.CompletedProcess(args, 0, stdout=help_by_bin.get(args[0], ""), stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

        return run

    def _which(self, available=("omx", "codex")):
        return lambda cmd: f"C:/bin/{cmd}.exe" if cmd in available else None

    def _fake_rows(self, root: Path):
        from scripts.ai_image_pipeline_v3.config import prompt_hash

        rows = []
        for shot in ("face_card", "silhouette_card", "vibe_card"):
            prompt = f"prompt for female_997 {shot}"
            rows.append(
                {
                    "assetId": f"female_997__{shot}__v001",
                    "profileId": "female_997",
                    "gender": "female",
                    "numericId": "997",
                    "shotType": shot,
                    "targetFaceType": "deer_like",
                    "targetLooksLevel": 3.0,
                    "targetLooksLevelBand": "2.5-3.2",
                    "prompt": prompt,
                    "promptHash": prompt_hash(prompt),
                    "status": "prepared",
                    "attempt": 0,
                    "attemptCount": 0,
                    "activeForTarget": True,
                    "isReserve": False,
                    "finalPath": str(root / "ai_image" / "female" / "997" / f"{shot}.png"),
                    "localPath": str(root / "ai_image" / "raw" / f"female_997__{shot}__v001__attempt01.png"),
                }
            )
        return rows

    def test_refuses_real_generation_without_env_guard_and_writes_report(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import run_e2e_smoke

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {}, clear=True):
                result = run_e2e_smoke(self._config(root), run_func=self._fake_run(), which_func=self._which())
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failureReason"], "real_e2e_guard_missing")
            self.assertTrue((root / "ai_image" / "reports" / "e2e" / "e2e_bounded_test" / "e2e_report.json").exists())

    def test_preflight_reports_agent_and_visual_unavailable(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import run_e2e_smoke

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_e2e_smoke(self._config(root, preflight_only=True), run_func=self._fake_run(), which_func=self._which(()))
            self.assertEqual(result["status"], "preflight_failed")
            self.assertFalse(result["artifacts"]["preflight"]["agentAvailable"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_e2e_smoke(
                self._config(root, preflight_only=True),
                run_func=self._fake_run(help_by_bin={"omx": "--image", "codex": "usage only"}),
                which_func=self._which(),
            )
            self.assertEqual(result["status"], "preflight_failed")
            self.assertFalse(result["artifacts"]["preflight"]["visualVerdictAvailable"])

    def test_materializes_exact_one_identity_three_assets_no_overlevel(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import build_e2e_asset_rows

        specs, rows = build_e2e_asset_rows(self._config(Path.cwd()))
        self.assertEqual(len(specs), 1)
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["shotType"] for row in rows], ["face_card", "silhouette_card", "vibe_card"])
        self.assertTrue(all(row["targetLooksLevelBand"] != "4.4-5.0" for row in rows))

    def test_plan_has_deterministic_order_and_reference_requirements(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import build_context, build_e2e_chunk_plan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = build_context(self._config(root))
            plan = build_e2e_chunk_plan(context, self._fake_rows(root))
            assets = plan["identities"][0]["assets"]
            self.assertEqual([asset["shotType"] for asset in assets], ["face_card", "silhouette_card", "vibe_card"])
            self.assertIsNone(assets[0]["requiresReferenceAssetId"])
            self.assertEqual(assets[1]["requiresReferenceAssetId"], assets[0]["assetId"])
            self.assertEqual(assets[2]["requiresReferenceAssetId"], assets[0]["assetId"])

    def test_reference_validation_requires_file_qa_and_existing_face_image(self):
        from scripts.ai_image_pipeline_v3.config import pipeline_paths
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import (
            AgentReferenceForm,
            E2EBoundedSmokeError,
            assert_reference_ready,
            build_context,
        )
        from scripts.ai_image_pipeline_v3.manifest import write_generation_outputs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = build_context(self._config(root))
            context.reference_form = AgentReferenceForm("image")
            rows = self._fake_rows(root)
            write_generation_outputs(pipeline_paths(root), rows)
            with self.assertRaises(E2EBoundedSmokeError) as cm:
                assert_reference_ready(context, rows[1], False)
            self.assertEqual(cm.exception.reason, "face_card_not_file_qa_passed")
            with self.assertRaises(E2EBoundedSmokeError) as cm:
                assert_reference_ready(context, rows[1], True)
            self.assertEqual(cm.exception.reason, "reference_image_missing")

    def test_backup_restores_manifest_on_failure(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import run_e2e_smoke

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "ai_image" / "manifests" / "generation_manifest.jsonl"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text('{"original": true}\n', encoding="utf-8")
            with patch.dict(os.environ, {"SEOLLEYEON_ALLOW_REAL_IMAGEGEN_E2E": "1"}, clear=True):
                with patch(
                    "scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3.build_e2e_asset_rows",
                    side_effect=RuntimeError("boom"),
                ):
                    result = run_e2e_smoke(self._config(root), run_func=self._fake_run(), which_func=self._which())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(manifest.read_text(encoding="utf-8"), '{"original": true}\n')

    def test_run_one_asset_uses_shell_false_and_writes_reportable_status(self):
        from scripts.ai_image_pipeline_v3.config import pipeline_paths
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import (
            AgentReferenceForm,
            build_context,
            build_e2e_chunk_plan,
            run_one_asset,
        )
        from scripts.ai_image_pipeline_v3.manifest import write_generation_outputs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = build_context(self._config(root))
            context.selected_agent = "omx"
            context.reference_form = AgentReferenceForm("image")
            rows = self._fake_rows(root)
            write_generation_outputs(pipeline_paths(root), rows)
            build_e2e_chunk_plan(context, rows)

            def fake_recover(*, root, pending, **kwargs):
                from scripts.ai_image_pipeline_v3.codex_imagegen import read_pending
                from scripts.ai_image_pipeline_v3.manifest import load_generation_manifest, write_generation_outputs

                payload = read_pending(Path(pending))
                final = Path(payload["expectedFinalPath"])
                final.parent.mkdir(parents=True, exist_ok=True)
                final.write_bytes(b"png")
                updated = []
                for row in load_generation_manifest(pipeline_paths(root)):
                    out = dict(row)
                    if out["assetId"] == payload["assetId"]:
                        out["finalPath"] = str(final)
                        out["localPath"] = str(final)
                        out["status"] = "recovered_pending_qa"
                    updated.append(out)
                write_generation_outputs(pipeline_paths(root), updated)
                return type("RecoverResult", (), {"final_path": final})()

            def fake_file_qa(**kwargs):
                return {"checked": 1, "approved": 0, "needs_manual_review": 1, "rejected": 0, "missing": 0}

            calls = []

            def fake_run(args, **kwargs):
                calls.append((args, kwargs))
                self.assertFalse(kwargs.get("shell", False))
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

            self.assertTrue(run_one_asset(context, rows[0], face_file_qa_passed=False, run_func=fake_run, recover_func=fake_recover, file_qa_func=fake_file_qa))
            self.assertEqual(len(calls), 1)
            self.assertTrue(context.commands)
            self.assertFalse(context.commands[0].shell)

    def test_dispatcher_exposes_e2e_command(self):
        from scripts.ai_image_pipeline_v3.cli import build_parser

        choices = next(action.choices for action in build_parser()._actions if action.dest == "command")
        self.assertIn("bounded-chunk-e2e-smoke", choices)

    def test_recommender_hashes_include_actual_lib_paths(self):
        from scripts.ai_image_pipeline_v3.e2e_bounded_imagegen_smoke_v3 import recommender_hashes

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "lib" / "ai_recommend_model" / "seolleyeon_run_all.py"
            protected.parent.mkdir(parents=True, exist_ok=True)
            protected.write_text("print('protected')\n", encoding="utf-8")
            hashes = recommender_hashes(root)
            self.assertIn("lib/ai_recommend_model/seolleyeon_run_all.py", hashes)
            self.assertNotEqual(hashes["lib/ai_recommend_model/seolleyeon_run_all.py"], "<missing>")


if __name__ == "__main__":
    unittest.main()
