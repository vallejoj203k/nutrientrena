from typing import Any, Optional
from fastapi.responses import JSONResponse


def send_response(data: Any, message: str, success: bool = True) -> dict:
    return {"success": success, "data": data, "message": message}


def send_error(error: str, data: Any = None, code: int = 404) -> JSONResponse:
    body = {"success": False, "message": error}
    if data is not None:
        body["data"] = data
    return JSONResponse(status_code=code, content=body)
