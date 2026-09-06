from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AzureTransportFailure:
    error_code: str
    request_sent: bool


def _isinstance_named(error: BaseException, module: Any, *names: str) -> bool:
    classes = tuple(
        candidate
        for name in names
        if isinstance((candidate := getattr(module, name, None)), type)
    )
    return bool(classes) and isinstance(error, classes)


def classify_azure_transport_failure(
    error: BaseException,
    *,
    httpx_module: Any,
) -> AzureTransportFailure:
    """Classify transport failures by whether a paid generation may have started.

    Only failures that prove no request bytes reached Azure are pre-send safe.
    Everything else is deliberately ambiguous so callers never fail over and
    purchase a duplicate image merely because the client lost the response.
    """

    if _isinstance_named(error, httpx_module, "ConnectError", "ConnectTimeout", "PoolTimeout"):
        return AzureTransportFailure(
            error_code="azure_connect_error",
            request_sent=False,
        )
    return AzureTransportFailure(
        error_code="azure_transport_outcome_ambiguous",
        request_sent=True,
    )


__all__ = ["AzureTransportFailure", "classify_azure_transport_failure"]
