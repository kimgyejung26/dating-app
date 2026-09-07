"""readyz release posture must report the Azure config the runtime actually uses.

Production finding (2026-09-07): the worker served five router endpoints
(AZURE_OPENAI_ENDPOINT_IDS=ep1..ep5) and generated images successfully, while
``/readyz`` reported ``endpointConfigured/credentialConfigured=false`` because
the posture only inspected the legacy single-endpoint variables. The posture
now derives from the same endpoint loader the router uses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation import worker_service  # noqa: E402

SECRET_MARKER = "sk-test-secret-value"
ENDPOINT_MARKER = "example-resource.services.ai.azure.com"

LEGACY_SINGLE_KEYS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_API_KEY",
)


def _clear_azure_env(monkeypatch):
    import os

    for name in list(os.environ):
        if name.startswith("AZURE_OPENAI_") or name.startswith("AVATAR_AZURE_"):
            monkeypatch.delenv(name, raising=False)


def _set_multi_endpoint_env(monkeypatch, count=5):
    ids = [f"ep{i}" for i in range(1, count + 1)]
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT_IDS", ",".join(ids))
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT_QUOTAS", ",".join(f"{i}=2" for i in ids))
    for i, endpoint_id in enumerate(ids, start=1):
        prefix = f"AZURE_OPENAI_{endpoint_id.upper()}_"
        monkeypatch.setenv(prefix + "ENDPOINT", f"https://{i}-{ENDPOINT_MARKER}")
        monkeypatch.setenv(prefix + "DEPLOYMENT", "gpt-image-2")
        monkeypatch.setenv(prefix + "API_VERSION", "preview")
        monkeypatch.setenv(prefix + "API_STYLE", "foundry_v1")
        monkeypatch.setenv(prefix + "API_KEY", f"{SECRET_MARKER}-{i}")
    monkeypatch.setenv("AZURE_OPENAI_IMAGE_SIZE", "1024x1536")
    monkeypatch.setenv("AZURE_OPENAI_IMAGE_QUALITY", "high")


def test_multi_endpoint_production_posture_reports_all_endpoints(monkeypatch):
    _clear_azure_env(monkeypatch)
    _set_multi_endpoint_env(monkeypatch, count=5)

    azure = worker_service._release_posture()["azureConfig"]

    assert azure["routingMode"] == "multi_endpoint"
    assert azure["configuredEndpointCount"] == 5
    assert azure["providerConfigured"] is True
    assert azure["endpointConfigured"] is True
    assert azure["deploymentConfigured"] is True
    assert azure["apiVersionConfigured"] is True
    assert azure["credentialConfigured"] is True
    assert azure["sizeConfigured"] is True
    assert azure["qualityConfigured"] is True
    assert azure["configError"] is None
    assert [e["endpointId"] for e in azure["endpoints"]] == ["ep1", "ep2", "ep3", "ep4", "ep5"]
    assert all(e["rpmLimit"] == 2 for e in azure["endpoints"])

    serialized = json.dumps(azure)
    assert SECRET_MARKER not in serialized
    assert ENDPOINT_MARKER not in serialized


def test_multi_endpoint_posture_flags_a_missing_credential(monkeypatch):
    _clear_azure_env(monkeypatch)
    _set_multi_endpoint_env(monkeypatch, count=5)
    monkeypatch.delenv("AZURE_OPENAI_EP3_API_KEY")

    azure = worker_service._release_posture()["azureConfig"]

    assert azure["routingMode"] == "multi_endpoint"
    assert azure["configuredEndpointCount"] == 0
    assert azure["providerConfigured"] is False
    assert azure["credentialConfigured"] is False
    assert azure["configError"] == "azure_endpoint_configuration_missing_azure_openai_ep3_api_key"


def test_single_endpoint_posture_keeps_legacy_semantics(monkeypatch):
    _clear_azure_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", f"https://{ENDPOINT_MARKER}")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-image-2")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "preview")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", SECRET_MARKER)

    azure = worker_service._release_posture()["azureConfig"]

    assert azure["routingMode"] == "single_endpoint"
    assert azure["configuredEndpointCount"] == 1
    assert azure["providerConfigured"] is True
    assert azure["credentialConfigured"] is True
    assert azure["endpointConfigured"] is True
    assert SECRET_MARKER not in json.dumps(azure)
    assert ENDPOINT_MARKER not in json.dumps(azure)


def test_unconfigured_posture_is_explicit_and_does_not_raise(monkeypatch):
    _clear_azure_env(monkeypatch)

    azure = worker_service._release_posture()["azureConfig"]

    assert azure["routingMode"] == "single_endpoint"
    assert azure["configuredEndpointCount"] == 0
    assert azure["providerConfigured"] is False
    assert azure["credentialConfigured"] is False
    assert azure["endpoints"] == []
    assert isinstance(azure["configError"], str) and azure["configError"]


@pytest.mark.parametrize("name", LEGACY_SINGLE_KEYS)
def test_legacy_single_variables_do_not_mask_multi_endpoint_authority(monkeypatch, name):
    _clear_azure_env(monkeypatch)
    _set_multi_endpoint_env(monkeypatch, count=2)
    monkeypatch.setenv(name, "legacy-value-that-the-router-ignores")

    azure = worker_service._release_posture()["azureConfig"]

    assert azure["routingMode"] == "multi_endpoint"
    assert azure["configuredEndpointCount"] == 2
    assert azure["providerConfigured"] is True
