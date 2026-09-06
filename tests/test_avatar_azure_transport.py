from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_MODEL_DIR = REPO_ROOT / "lib" / "ai_recommend_model"
if str(AI_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(AI_MODEL_DIR))

from avatar_generation.model_adapters.azure_contracts import (  # noqa: E402
    AzureGptImage2Config,
    AzureImageEditRequest,
    AzureTransportError,
)
from avatar_generation.model_adapters.azure_transport import AzureHttpImageTransport  # noqa: E402


def _image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), color=(30, 60, 90)).save(output, format="JPEG")
    return output.getvalue()


class RecordingClient:
    def __init__(self):
        self.calls = []

    def post(self, url, *, headers, data, files):
        self.calls.append({"url": url, "headers": headers, "data": data, "files": files})
        return SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"data": [{"b64_json": base64.b64encode(_image_bytes()).decode("ascii")}]},
        )


class RaisingClient:
    def __init__(self, error):
        self.error = error

    def post(self, *_args, **_kwargs):
        raise self.error


def _request() -> AzureImageEditRequest:
    return AzureImageEditRequest(
        source_image_bytes=_image_bytes(),
        source_content_type="image/jpeg",
        prompt="fixed-test-prompt",
        deployment="gpt-image-2",
        api_version="preview",
    )


def _transport_raising(error: Exception) -> AzureHttpImageTransport:
    transport = AzureHttpImageTransport.__new__(AzureHttpImageTransport)
    transport._config = AzureGptImage2Config(
        endpoint="https://test-resource.services.ai.azure.com",
        deployment="gpt-image-2",
        api_version="preview",
        api_key="SECRET_NOT_IN_ASSERTIONS",
    )
    transport._client = RaisingClient(error)
    transport._httpx = httpx
    return transport


def test_transport_uses_documented_azure_image_edit_multipart_shape():
    config = AzureGptImage2Config(
        endpoint="https://test-resource.services.ai.azure.com",
        deployment="gpt-image-2",
        api_version="preview",
        api_key="SECRET_NOT_IN_ASSERTIONS",
    )
    client = RecordingClient()
    transport = AzureHttpImageTransport.__new__(AzureHttpImageTransport)
    transport._config = config
    transport._client = client
    transport._httpx = SimpleNamespace(TimeoutException=TimeoutError, NetworkError=OSError)

    source_bytes = _image_bytes()
    prompt = (
        "레퍼런스 정면 사진의 인물과 얼굴 특징과 인상을 최대한 동일하게 유지한 2D 아바타를 생성한다.\n\n"
        "스타일은 깔끔한 Live2D 애니메이션 텍스처 스타일로, 자연스러운 애니메이션풍 얼굴 비율, 선명하고 정돈된 라인, "
        "부드러운 셀 셰이딩과 은은한 입체감, 매끈한 피부 표현을 사용한다. 과도한 미화나 눈 확대, 얼굴형 변형은 하지 않는다.\n\n"
        "헤어스타일, 머리색, 눈·코·입 형태, 얼굴형, 피부톤, 의상과 전체적인 인상을 레퍼런스와 충실하게 유지한다.\n\n"
        "정면·눈높이 시점, 가슴 위까지 보이는 중앙 구도, 자연스러운 무표정, 단색 밝은 아이보리 배경.\n\n"
        "표정 시트, 분리 파츠, 텍스트, 장식, 소품은 넣지 않고 완성된 아바타 1명만 출력한다."
    )
    transport.send(
        AzureImageEditRequest(
            source_image_bytes=source_bytes,
            source_content_type="image/jpeg",
            prompt=prompt,
            deployment="gpt-image-2",
            api_version="preview",
        )
    )

    call = client.calls[0]
    assert call["url"] == (
        "https://test-resource.services.ai.azure.com/openai/v1/images/edits"
        "?api-version=preview"
    )
    assert call["data"] == {
        "prompt": prompt,
        "n": "1",
        "model": "gpt-image-2",
    }
    assert call["files"] == {"image": ("source.jpg", source_bytes, "image/jpeg")}


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
def test_only_definitive_connect_failures_are_classified_pre_send(error_type):
    request = httpx.Request("POST", "https://test-resource.services.ai.azure.com")

    with pytest.raises(AzureTransportError) as caught:
        _transport_raising(error_type("connect failed", request=request)).send(_request())

    assert caught.value.request_sent is False
    assert caught.value.retryable is True
    assert caught.value.error_code == "azure_connect_error"


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ReadError,
        httpx.WriteError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.RemoteProtocolError,
    ],
)
def test_post_connect_transport_failures_are_ambiguous(error_type):
    request = httpx.Request("POST", "https://test-resource.services.ai.azure.com")

    with pytest.raises(AzureTransportError) as caught:
        _transport_raising(error_type("connection lost", request=request)).send(_request())

    assert caught.value.request_sent is True
    assert caught.value.retryable is False
    assert caught.value.error_code == "azure_transport_outcome_ambiguous"


def test_unknown_transport_exception_is_ambiguous_fail_closed():
    with pytest.raises(AzureTransportError) as caught:
        _transport_raising(OSError("connection reset after send")).send(_request())

    assert caught.value.request_sent is True
    assert caught.value.retryable is False
