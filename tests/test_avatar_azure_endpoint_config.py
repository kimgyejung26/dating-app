from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_endpoint_config import (  # noqa: E402
    AzureEndpointConfigError,
    load_azure_endpoint_configs,
)


def _multi_env() -> dict[str, str]:
    env = {
        "AZURE_OPENAI_ENDPOINT_IDS": "ep1,ep2",
        "AZURE_OPENAI_ENDPOINT_QUOTAS": "ep1=2,ep2=6",
    }
    for endpoint_id in ("EP1", "EP2"):
        env.update(
            {
                f"AZURE_OPENAI_{endpoint_id}_ENDPOINT": f"https://{endpoint_id.lower()}.example.invalid",
                f"AZURE_OPENAI_{endpoint_id}_DEPLOYMENT": "gpt-image-2",
                f"AZURE_OPENAI_{endpoint_id}_API_VERSION": "preview",
                f"AZURE_OPENAI_{endpoint_id}_API_KEY": f"SECRET_{endpoint_id}",
            }
        )
    return env


def test_multi_endpoint_config_is_quota_driven_and_secret_free_in_repr():
    configs = load_azure_endpoint_configs(env=_multi_env())

    assert [config.endpoint_id for config in configs] == ["ep1", "ep2"]
    assert [config.rpm_limit for config in configs] == [2.0, 6.0]
    assert [config.provider_config.requests_per_minute for config in configs] == [2, 6]
    rendered = repr(configs)
    assert "SECRET_EP1" not in rendered
    assert "SECRET_EP2" not in rendered
    assert "https://ep1.example.invalid" not in repr(configs[0].safe_dict())


def test_quota_change_requires_config_only_not_code_change():
    env = _multi_env()
    env["AZURE_OPENAI_ENDPOINT_QUOTAS"] = "ep1=6,ep2=6"

    configs = load_azure_endpoint_configs(env=env)

    assert configs[0].rpm_limit == 6.0
    assert configs[0].provider_config.requests_per_minute == 6


def test_legacy_single_endpoint_env_remains_a_supported_router_input():
    configs = load_azure_endpoint_configs(
        env={
            "AZURE_OPENAI_ENDPOINT": "https://legacy.example.invalid",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-image-2",
            "AZURE_OPENAI_API_VERSION": "preview",
            "AZURE_OPENAI_API_KEY": "LEGACY_SECRET",
            "AZURE_OPENAI_ENDPOINT_DEFAULT_RPM": "2",
        }
    )

    assert len(configs) == 1
    assert configs[0].endpoint_id == "primary"
    assert configs[0].rpm_limit == 2.0


def test_endpoint_ids_are_bounded_to_five_and_safe_env_tokens():
    env = _multi_env()
    env["AZURE_OPENAI_ENDPOINT_IDS"] = "ep1,ep2,ep3,ep4,ep5,ep6"
    with pytest.raises(AzureEndpointConfigError, match="at_most_five"):
        load_azure_endpoint_configs(env=env)

    env["AZURE_OPENAI_ENDPOINT_IDS"] = "../kr"
    with pytest.raises(AzureEndpointConfigError, match="endpoint_id_invalid"):
        load_azure_endpoint_configs(env=env)


def test_hyphenated_endpoint_id_maps_to_safe_env_token():
    env = {
        "AZURE_OPENAI_ENDPOINT_IDS": "kr-1",
        "AZURE_OPENAI_ENDPOINT_QUOTAS": "kr-1=2",
        "AZURE_OPENAI_KR_1_ENDPOINT": "https://example.invalid",
        "AZURE_OPENAI_KR_1_DEPLOYMENT": "gpt-image-2",
        "AZURE_OPENAI_KR_1_API_VERSION": "preview",
        "AZURE_OPENAI_KR_1_API_KEY": "SECRET",
    }

    configs = load_azure_endpoint_configs(env=env)

    assert configs[0].endpoint_id == "kr-1"


def test_missing_endpoint_secret_fails_closed():
    env = _multi_env()
    del env["AZURE_OPENAI_EP2_API_KEY"]

    with pytest.raises(AzureEndpointConfigError, match="configuration_missing"):
        load_azure_endpoint_configs(env=env)


def test_multi_endpoint_quota_must_be_explicit_or_have_configured_default():
    env = _multi_env()
    env["AZURE_OPENAI_ENDPOINT_QUOTAS"] = "ep1=2"

    with pytest.raises(AzureEndpointConfigError, match="quota_missing"):
        load_azure_endpoint_configs(env=env)

    env["AZURE_OPENAI_ENDPOINT_DEFAULT_RPM"] = "2"
    configs = load_azure_endpoint_configs(env=env)
    assert configs[1].rpm_limit == 2.0
