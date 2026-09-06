from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Any, Mapping, Optional

from .azure_contracts import AzureGptImage2Config
from .azure_endpoint_quota import (
    DEFAULT_ENDPOINT_ID,
    ENV_ENDPOINT_DEFAULT_RPM,
    ENV_ENDPOINT_QUOTAS,
    declared_endpoint_quota,
)


ENV_ENDPOINT_IDS = "AZURE_OPENAI_ENDPOINT_IDS"
MAX_ENDPOINTS = 5
_SAFE_ENDPOINT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class AzureEndpointConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AzureEndpointConfig:
    endpoint_id: str
    rpm_limit: float
    provider_config: AzureGptImage2Config = field(repr=False)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "endpointId": self.endpoint_id,
            "rpmLimit": self.rpm_limit,
            **self.provider_config.safe_dict(),
        }


def _required(source: Mapping[str, str], name: str) -> str:
    value = str(source.get(name, "") or "").strip()
    if not value:
        raise AzureEndpointConfigError(f"azure_endpoint_configuration_missing_{name.lower()}")
    return value


def _endpoint_ids(source: Mapping[str, str]) -> list[str]:
    raw = str(source.get(ENV_ENDPOINT_IDS, "") or "").strip()
    if not raw:
        return [DEFAULT_ENDPOINT_ID]
    result: list[str] = []
    for item in raw.split(","):
        endpoint_id = item.strip().lower()
        if not _SAFE_ENDPOINT_ID.fullmatch(endpoint_id):
            raise AzureEndpointConfigError("azure_endpoint_id_invalid")
        if endpoint_id in result:
            raise AzureEndpointConfigError("azure_endpoint_id_duplicate")
        result.append(endpoint_id)
    if not result:
        raise AzureEndpointConfigError("azure_endpoint_ids_empty")
    if len(result) > MAX_ENDPOINTS:
        raise AzureEndpointConfigError("azure_endpoint_count_at_most_five")
    env_tokens = [_endpoint_env_token(endpoint_id) for endpoint_id in result]
    if len(env_tokens) != len(set(env_tokens)):
        raise AzureEndpointConfigError("azure_endpoint_env_token_collision")
    return result


def _endpoint_env_token(endpoint_id: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", endpoint_id.upper())


def _provider_config_for(
    endpoint_id: str,
    *,
    source: Mapping[str, str],
    multi: bool,
) -> AzureGptImage2Config:
    if multi:
        prefix = f"AZURE_OPENAI_{_endpoint_env_token(endpoint_id)}_"
        endpoint = _required(source, prefix + "ENDPOINT")
        deployment = _required(source, prefix + "DEPLOYMENT")
        api_version = _required(source, prefix + "API_VERSION")
        api_key = _required(source, prefix + "API_KEY")
        api_style = str(source.get(prefix + "API_STYLE", "foundry_v1") or "foundry_v1").strip()
    else:
        endpoint = _required(source, "AZURE_OPENAI_ENDPOINT")
        deployment = _required(source, "AZURE_OPENAI_DEPLOYMENT")
        api_version = _required(source, "AZURE_OPENAI_API_VERSION")
        api_key = _required(source, "AZURE_OPENAI_API_KEY")
        api_style = str(source.get("AZURE_OPENAI_API_STYLE", "foundry_v1") or "foundry_v1").strip()
    if api_style not in {"foundry_v1", "legacy_deployment"}:
        raise AzureEndpointConfigError("azure_endpoint_api_style_invalid")
    quota = declared_endpoint_quota(endpoint_id, env=source)
    rpm_as_int = int(quota.rpm_limit)
    if float(rpm_as_int) != float(quota.rpm_limit):
        raise AzureEndpointConfigError("azure_endpoint_rpm_must_be_integer")
    return AzureGptImage2Config(
        endpoint=endpoint,
        deployment=deployment,
        api_version=api_version,
        api_key=api_key,
        api_style=api_style,
        max_attempts=1,
        request_timeout_seconds=_float_env(source, "AZURE_OPENAI_TIMEOUT_SECONDS", 90.0, 5.0, 300.0),
        max_concurrency=_int_env(source, "AZURE_OPENAI_MAX_CONCURRENCY", 1, 1, 64),
        requests_per_minute=rpm_as_int,
        backoff_base_seconds=0.0,
        max_backoff_seconds=0.0,
        quality=_optional(source.get("AZURE_OPENAI_IMAGE_QUALITY")),
        size=_optional(source.get("AZURE_OPENAI_IMAGE_SIZE")),
    )


def _require_multi_endpoint_quota(source: Mapping[str, str], endpoint_id: str) -> None:
    entries = str(source.get(ENV_ENDPOINT_QUOTAS, "") or "").split(",")
    explicit_ids = {
        name.strip()
        for entry in entries
        if "=" in entry
        for name, _separator, _value in [entry.partition("=")]
    }
    has_default = bool(str(source.get(ENV_ENDPOINT_DEFAULT_RPM, "") or "").strip())
    if endpoint_id not in explicit_ids and not has_default:
        raise AzureEndpointConfigError("azure_endpoint_quota_missing")


def load_azure_endpoint_configs(
    *, env: Optional[Mapping[str, str]] = None
) -> list[AzureEndpointConfig]:
    source = os.environ if env is None else env
    ids = _endpoint_ids(source)
    multi = bool(str(source.get(ENV_ENDPOINT_IDS, "") or "").strip())
    if multi:
        for endpoint_id in ids:
            _require_multi_endpoint_quota(source, endpoint_id)
    return [
        AzureEndpointConfig(
            endpoint_id=endpoint_id,
            rpm_limit=declared_endpoint_quota(endpoint_id, env=source).rpm_limit,
            provider_config=_provider_config_for(endpoint_id, source=source, multi=multi),
        )
        for endpoint_id in ids
    ]


def _optional(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _int_env(source: Mapping[str, str], name: str, fallback: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(source.get(name, "") or fallback))
    except (TypeError, ValueError):
        value = fallback
    return max(minimum, min(maximum, value))


def _float_env(
    source: Mapping[str, str], name: str, fallback: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(str(source.get(name, "") or fallback))
    except (TypeError, ValueError):
        value = fallback
    return max(minimum, min(maximum, value))


__all__ = [
    "AzureEndpointConfig",
    "AzureEndpointConfigError",
    "ENV_ENDPOINT_IDS",
    "MAX_ENDPOINTS",
    "load_azure_endpoint_configs",
]
