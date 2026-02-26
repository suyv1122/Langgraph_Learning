from __future__ import annotations

from app.modules.kb.ingestion.utils import sha256_bytes

# import hashlib
# def _h(s: str) -> str:
#     return hashlib.sha256(s.encode("utf-8")).hexdigest()


def asset_original_key(*, workspace_id: int, asset_id: int, filename: str) -> str:
    fn = str(filename or "").strip() or "file"
    salt = sha256_bytes(f"{int(workspace_id)}:{int(asset_id)}:{fn}".encode("utf-8"))[:16]
    return f"kb/ws/{int(workspace_id)}/assets/{int(asset_id)}/original/{salt}/{fn}"


def asset_derivative_key(*, workspace_id: int, asset_id: int, name: str) -> str:
    nm = str(name or "").strip() or "derivative"
    salt = sha256_bytes(f"{int(workspace_id)}:{int(asset_id)}:{nm}".encode("utf-8"))[:16]
    return f"kb/ws/{int(workspace_id)}/assets/{int(asset_id)}/derived/{salt}/{nm}"
