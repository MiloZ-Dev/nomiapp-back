from typing import Any


def envelope(
    data: Any = None,
    message: str = "OK",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Consistent response for all endpoints: {data, message}.

    If ``warnings`` are passed, the ``warnings`` key is included in the response.
    """
    response: dict[str, Any] = {"data": data, "message": message}
    if warnings:
        response["warnings"] = warnings
    return response
