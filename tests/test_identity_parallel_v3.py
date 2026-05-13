import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


class IdentityParallelV3Tests(unittest.TestCase):
    def _write_manifest(self, root: Path, identities=("female_001", "female_002")) -> None:
        from scripts.ai_image_pipeline_v3.config import pipeline_paths, prompt_hash
        from scripts.ai_image_pipeline_v3.manifest import write_generation_outputs

        rows = []
        for identity_id in identities:
            gender, numeric = identity_id.split("_", 1)
            for shot in ("face_card", "silhouette_card", "vibe_card"):
                prompt = f"prompt for {identity_id} {shot}"
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

    def test_identity_worker_writes_per_asset_pending_receipts_and_face_reference(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityWorkerConfig, run_identity_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))
            result = run_identity_worker(
                IdentityWorkerConfig(
                    root=root,
                    identity_id="female_001",
                    run_id="run_b_worker",
                    worker_id="worker-1",
                    fixture=True,
                )
            )

            self.assertEqual(result["status"], "complete")
            pending_dir = root / "ai_image" / "manifests" / "pending"
            pending_files = sorted(path.name for path in pending_dir.glob("*.json"))
            self.assertEqual(
                pending_files,
                [
                    "female_001__face_card__v001.json",
                    "female_001__silhouette_card__v001.json",
                    "female_001__vibe_card__v001.json",
                ],
            )
            receipts = {row["shotType"]: row for row in result["assetReceipts"]}
            face_final = receipts["face_card"]["finalPath"]
            self.assertTrue(Path(face_final).exists())
            self.assertEqual(receipts["silhouette_card"]["referenceImagePath"], face_final)
            self.assertEqual(receipts["vibe_card"]["referenceImagePath"], face_final)
            self.assertTrue((root / "ai_image" / "reports" / "identity_parallel" / "run_b_worker" / "receipts" / "identities" / "female_001.json").exists())

    def test_face_failure_blocks_dependent_generation(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityWorkerConfig, run_identity_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))
            result = run_identity_worker(
                IdentityWorkerConfig(
                    root=root,
                    identity_id="female_001",
                    run_id="run_b_face_fail",
                    worker_id="worker-1",
                    fixture=True,
                    fixture_fail_shot="face_card",
                )
            )

            self.assertEqual(result["status"], "failed")
            by_shot = {row["shotType"]: row for row in result["assetReceipts"]}
            self.assertEqual(by_shot["face_card"]["status"], "failed")
            self.assertEqual(by_shot["silhouette_card"]["status"], "skipped")
            self.assertEqual(by_shot["vibe_card"]["status"], "skipped")
            self.assertFalse((root / "ai_image" / "female" / "001" / "silhouette_card.png").exists())

    def test_parallel_fixture_workers_do_not_collide_and_parent_updates_state(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityParallelConfig, run_identity_parallel

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001", "female_002"))
            result = run_identity_parallel(
                IdentityParallelConfig(
                    root=root,
                    run_id="run_b_parallel",
                    workers=2,
                    fixture=True,
                )
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(set(result["selectedIdentities"]), {"female_001", "female_002"})
            pending_files = sorted((root / "ai_image" / "manifests" / "pending").glob("*.json"))
            self.assertEqual(len(pending_files), 6)
            self.assertEqual(len({path.name for path in pending_files}), 6)
            state = json.loads((root / "ai_image" / "manifests" / "current_chunk_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["assetStates"]["female_001__face_card__v001"], "file_qa_passed")
            self.assertEqual(state["assetStates"]["female_002__vibe_card__v001"], "file_qa_passed")

    def test_workers_limit_concurrency_not_total_identity_count(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityParallelConfig, run_identity_parallel

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001", "female_002", "female_003"))
            result = run_identity_parallel(
                IdentityParallelConfig(
                    root=root,
                    run_id="run_b_parallel_all",
                    workers=1,
                    fixture=True,
                    max_identities=3,
                )
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(set(result["selectedIdentities"]), {"female_001", "female_002", "female_003"})
            pending_files = sorted((root / "ai_image" / "manifests" / "pending").glob("*.json"))
            self.assertEqual(len(pending_files), 9)

    def test_fixture_worker_refuses_to_overwrite_existing_final_image(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityWorkerConfig, run_identity_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))
            existing = root / "ai_image" / "female" / "001" / "face_card.png"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"existing-approved-like-file")

            result = run_identity_worker(
                IdentityWorkerConfig(
                    root=root,
                    identity_id="female_001",
                    run_id="run_b_overwrite_refusal",
                    worker_id="worker-1",
                    fixture=True,
                )
            )

            self.assertEqual(result["status"], "failed")
            self.assertIn("Refusing to overwrite", result["assetReceipts"][0]["error"])
            self.assertEqual(existing.read_bytes(), b"existing-approved-like-file")

    def test_lease_prevents_duplicate_worker_and_parent_can_reclaim_stale(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import (
            IdentityLeaseError,
            acquire_identity_lease,
            identity_lease_path,
            reclaim_stale_leases,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acquire_identity_lease(root=root, identity_id="female_001", run_id="run1", worker_id="worker1", ttl_sec=60)
            with self.assertRaises(IdentityLeaseError):
                acquire_identity_lease(root=root, identity_id="female_001", run_id="run1", worker_id="worker2", ttl_sec=60)

            lease_path = identity_lease_path(root, "female_001")
            lease = json.loads(lease_path.read_text(encoding="utf-8"))
            lease["expires_at"] = "2000-01-01T00:00:00+00:00"
            lease["expiresAt"] = "2000-01-01T00:00:00+00:00"
            lease_path.write_text(json.dumps(lease), encoding="utf-8")
            reclaimed = reclaim_stale_leases(root)
            self.assertEqual(len(reclaimed), 1)
            self.assertEqual(json.loads(lease_path.read_text(encoding="utf-8"))["status"], "stale_reclaimed")

    def test_parent_detects_child_forbidden_global_mutation(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityParallelConfig, run_identity_parallel

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))
            manifest = root / "ai_image" / "manifests" / "generation_manifest.jsonl"
            before_manifest = manifest.read_text(encoding="utf-8")

            def malicious_worker(config):
                manifest_path = config.root / "ai_image" / "manifests" / "generation_manifest.jsonl"
                rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                rows[0]["status"] = "child_mutated_global_manifest"
                manifest_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
                return {"status": "complete", "identityId": config.identity_id, "assetReceipts": []}

            result = run_identity_parallel(
                IdentityParallelConfig(root=root, run_id="run_b_forbidden", workers=1, fixture=True),
                worker_func=malicious_worker,
            )

            self.assertEqual(result["status"], "failed")
            self.assertIn("female_001", result["forbiddenGlobalMutations"])
            self.assertEqual(manifest.read_text(encoding="utf-8"), before_manifest)
            self.assertEqual(result["parentUpdate"]["skipped"], "forbidden_global_mutation")

    def test_parent_records_worker_exception_and_marks_lease_failed(self):
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityParallelConfig, identity_lease_path, run_identity_parallel

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))

            def raising_worker(config):
                raise RuntimeError(f"fixture boom for {config.identity_id}")

            result = run_identity_parallel(
                IdentityParallelConfig(root=root, run_id="run_b_exception", workers=1, fixture=True),
                worker_func=raising_worker,
            )

            self.assertEqual(result["status"], "failed")
            self.assertTrue(Path(result["reportPath"]).exists())
            self.assertIn("fixture boom", result["identityResults"][0]["error"])
            lease = json.loads(identity_lease_path(root, "female_001").read_text(encoding="utf-8"))
            self.assertEqual(lease["status"], "failed")
            self.assertTrue((root / "ai_image" / "reports" / "identity_parallel" / "run_b_exception" / "receipts" / "identities" / "female_001.json").exists())

    def test_dispatcher_exposes_identity_parallel_commands_and_pending_asset_status(self):
        from scripts.ai_image_pipeline_v3.cli import build_parser
        from scripts.ai_image_pipeline_v3.cli import main as dispatcher_main
        from scripts.ai_image_pipeline_v3.identity_parallel import main as identity_parallel_main
        from scripts.ai_image_pipeline_v3.identity_parallel import IdentityWorkerConfig, per_asset_pending_path, run_identity_worker
        from scripts.ai_image_pipeline_v3.pending_admin import pending_status_report

        choices = next(action.choices for action in build_parser()._actions if action.dest == "command")
        self.assertIn("bounded-identity-worker", choices)
        self.assertIn("bounded-identity-parallel-run", choices)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ("female_001",))
            run_identity_worker(IdentityWorkerConfig(root=root, identity_id="female_001", run_id="run_b_status", worker_id="worker-1", fixture=True))
            self.assertTrue(per_asset_pending_path(root, "female_001__face_card__v001").exists())
            report = pending_status_report(root=root)
            self.assertEqual(report["perAssetPending"]["perAssetPendingCount"], 3)
            with self.assertRaises(Exception):
                per_asset_pending_path(root, "../escape")
            with self.assertRaises(Exception):
                per_asset_pending_path(root, "female_001/face_card")

            with redirect_stdout(StringIO()):
                blocked = dispatcher_main(["bounded-identity-parallel-run", "--root", str(root), "--run-id", "run_b_missing_fixture"])
            self.assertEqual(blocked, 2)
            with redirect_stdout(StringIO()):
                blocked_worker = dispatcher_main(["bounded-identity-worker", "--root", str(root), "--run-id", "run_b_missing_fixture", "--identity-id", "female_001"])
            self.assertEqual(blocked_worker, 2)
            with self.assertRaises(SystemExit):
                identity_parallel_main(["worker", "--root", str(root), "--run-id", "run_b_missing_fixture", "--identity-id", "female_001"])
            with self.assertRaises(SystemExit):
                identity_parallel_main(["parallel-run", "--root", str(root), "--run-id", "run_b_missing_fixture"])


if __name__ == "__main__":
    unittest.main()
