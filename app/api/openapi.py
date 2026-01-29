# 抽出项目中所有API，用于生成说明文档
# 格式相对固定且通用，可抄
from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.http_consts import HDR_CACHE_CONTROL, HDR_REQUEST_ID, HDR_RESPONSE_TIME_MS
from app.api.routes_consts import NO_STORE_PATHS

_COMMON_RESPONSE_HEADERS = {
    HDR_REQUEST_ID: {
        "description": "Request correlation id",
        "schema": {"type": "string"},
    },
    HDR_RESPONSE_TIME_MS: {
        "description": "Server processing time in milliseconds",
        "schema": {"type": "string"},
    },
}

_NO_STORE_HEADER = {
    HDR_CACHE_CONTROL: {
        "description": "Sensitive response, do not store",
        "schema": {"type": "string", "example": "no-store"},
    }
}


def _merge_responses(dest: dict, src: dict) -> None:
    for k, v in src.items():
        if k not in dest:
            dest[k] = v


def _ensure_error_response_schema(schema: dict) -> None:
    comps = schema.setdefault("components", {})
    schemas = comps.setdefault("schemas", {})
    if "ErrorResponse" not in schemas:
        schemas["ErrorInfo"] = {
            "title": "ErrorInfo",
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "message": {},
                "request_id": {"type": "string"},
                "meta": {"type": "object", "additionalProperties": True},
            },
            "required": ["code", "message", "request_id"],
        }
        schemas["ErrorResponse"] = {
            "title": "ErrorResponse",
            "type": "object",
            "properties": {"error": {"$ref": "#/components/schemas/ErrorInfo"}},
            "required": ["error"],
        }


def _err_resp(desc: str) -> dict:
    return {
        "description": desc,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
    }


def install_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=getattr(app, "version", "0.1.0"),
            description=app.description,
            routes=app.routes,
        )

        _ensure_error_response_schema(schema)

        common_error_responses: dict[str, dict] = {
            "400": _err_resp("Bad Request"),
            "401": _err_resp("Unauthorized"),
            "403": _err_resp("Forbidden"),
            "404": _err_resp("Not Found"),
            "409": _err_resp("Conflict"),
            "422": _err_resp("Validation Failed"),
            "429": _err_resp("Rate Limited"),
            "500": _err_resp("Internal Error"),
        }

        paths = schema.get("paths", {})
        if isinstance(paths, dict):
            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue

                for _, op in path_item.items():
                    if not isinstance(op, dict):
                        continue

                    responses = op.get("responses")
                    if not isinstance(responses, dict):
                        responses = {}
                        op["responses"] = responses

                    _merge_responses(responses, common_error_responses)

                    is_no_store_endpoint = path in NO_STORE_PATHS

                    for _, resp in responses.items():
                        if not isinstance(resp, dict):
                            continue

                        hdrs = resp.get("headers")
                        if not isinstance(hdrs, dict):
                            hdrs = {}
                            resp["headers"] = hdrs

                        for hk, hv in _COMMON_RESPONSE_HEADERS.items():
                            hdrs.setdefault(hk, hv)

                        if is_no_store_endpoint:
                            for hk, hv in _NO_STORE_HEADER.items():
                                hdrs.setdefault(hk, hv)

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi