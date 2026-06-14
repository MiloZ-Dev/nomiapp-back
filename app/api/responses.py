from typing import Any


def envelope(data: Any = None, message: str = "OK") -> dict[str, Any]:
    """Respuesta consistente para todos los endpoints: {data, message}."""
    return {"data": data, "message": message}
