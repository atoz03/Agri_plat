from typing import Any


def standardize_device_data(payload: dict) -> dict:
    return {
        "deviceCode": payload.get("deviceCode"),
        "messageType": payload.get("messageType"),
        "reportTime": payload.get("reportTime"),
        "content": payload.get("content"),
    }


def to_semantic_vector_stub(payload: dict) -> dict:
    return {
        "source": "demo",
        "vector": [],
        "raw": payload,
    }
