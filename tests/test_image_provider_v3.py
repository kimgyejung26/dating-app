import tempfile
import unittest
from pathlib import Path


class ImageProviderV3Tests(unittest.TestCase):
    def test_default_provider_preserves_codex_builtin_imagegen_backend(self):
        from scripts.ai_image_pipeline_v3.config import DEFAULT_MODEL
        from scripts.ai_image_pipeline_v3.image_provider import default_image_provider

        provider = default_image_provider()

        self.assertEqual(DEFAULT_MODEL, "codex-built-in-imagegen")
        self.assertEqual(provider.name, "codex-built-in-imagegen")
        self.assertEqual(provider.metadata()["backend"], "codex_builtin_imagegen_omx")
        self.assertFalse(provider.metadata()["runs_real_generation"])

    def test_fixture_provider_writes_local_ai_image_output_and_metadata(self):
        from scripts.ai_image_pipeline_v3.image_provider import (
            FixtureImageProvider,
            ImageProviderRequest,
            assert_output_persisted_locally,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "ai_image" / "raw" / "female_001__face_card__v001__attempt01.png"
            request = ImageProviderRequest(
                prompt="realistic adult Korean university student profile photo",
                output_path=output,
                provider_metadata={"assetId": "female_001__face_card__v001", "shotType": "face_card"},
            )

            result = FixtureImageProvider().generate(request)

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            self.assertTrue(result.persisted)
            self.assertEqual(result.provider_name, "fixture-local-image")
            self.assertEqual(result.metadata["assetId"], "female_001__face_card__v001")
            self.assertEqual(assert_output_persisted_locally(output, root=root), output.resolve())

    def test_local_persistence_check_rejects_missing_empty_and_out_of_tree_outputs(self):
        from scripts.ai_image_pipeline_v3.image_provider import LocalPersistenceError, assert_output_persisted_locally

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "ai_image" / "raw" / "missing.png"
            empty = root / "ai_image" / "raw" / "empty.png"
            outside = root / "other" / "raw.png"
            empty.parent.mkdir(parents=True)
            empty.write_bytes(b"")
            outside.parent.mkdir(parents=True)
            outside.write_bytes(b"not under ai_image")

            for path in (missing, empty, outside):
                with self.subTest(path=path):
                    with self.assertRaises(LocalPersistenceError):
                        assert_output_persisted_locally(path, root=root)

    def test_hermes_native_provider_rejects_reference_images_until_capability_verified(self):
        from scripts.ai_image_pipeline_v3.image_provider import (
            HermesNativeImageProvider,
            ImageProviderRequest,
            ReferenceImagesUnsupportedError,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "ai_image" / "female" / "001" / "face_card.png"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"reference")
            request = ImageProviderRequest(
                prompt="same person silhouette card",
                output_path=root / "ai_image" / "raw" / "female_001__silhouette_card__v001__attempt01.png",
                reference_image_paths=(reference,),
                provider_metadata={"shotType": "silhouette_card"},
            )

            with self.assertRaises(ReferenceImagesUnsupportedError):
                HermesNativeImageProvider().generate(request)

    def test_hermes_native_provider_scaffold_requires_executor_for_text_to_image(self):
        from scripts.ai_image_pipeline_v3.image_provider import (
            HermesNativeImageProvider,
            ImageProviderRequest,
            ProviderUnavailableError,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = ImageProviderRequest(
                prompt="text only face card",
                output_path=root / "ai_image" / "raw" / "female_001__face_card__v001__attempt01.png",
            )

            with self.assertRaises(ProviderUnavailableError):
                HermesNativeImageProvider().generate(request)

    def test_reference_capable_hermes_provider_validates_reference_paths_before_executor(self):
        from scripts.ai_image_pipeline_v3.image_provider import HermesNativeImageProvider, ImageProviderRequest, LocalPersistenceError

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "ai_image" / "raw" / "female_001__silhouette_card__v001__attempt01.png"
            missing_reference = root / "ai_image" / "female" / "001" / "face_card.png"

            def should_not_run(request):
                raise AssertionError("executor should not receive an invalid reference")

            request = ImageProviderRequest(
                prompt="same person silhouette",
                output_path=output,
                reference_image_paths=(missing_reference,),
            )
            with self.assertRaises(LocalPersistenceError):
                HermesNativeImageProvider(text_to_image_executor=should_not_run, supports_reference_images=True).generate(request)

            other_root = Path(tmp) / "other_project"
            outside_reference = other_root / "ai_image" / "female" / "001" / "face_card.png"
            outside_reference.parent.mkdir(parents=True)
            outside_reference.write_bytes(b"reference")
            request = ImageProviderRequest(
                prompt="same person silhouette",
                output_path=output,
                reference_image_paths=(outside_reference,),
            )
            with self.assertRaises(LocalPersistenceError):
                HermesNativeImageProvider(text_to_image_executor=should_not_run, supports_reference_images=True).generate(request)


if __name__ == "__main__":
    unittest.main()
