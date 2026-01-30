from __future__ import annotations

import hashlib


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def asset_original_key(*, workspace_id: int, asset_id: int, filename: str) -> str:
    fn = str(filename or "").strip() or "file"
    salt = _h(f"{int(workspace_id)}:{int(asset_id)}:{fn}")[:16]
    return f"kb/ws/{int(workspace_id)}/assets/{int(asset_id)}/original/{salt}/{fn}"


def asset_derivative_key(*, workspace_id: int, asset_id: int, name: str) -> str:
    nm = str(name or "").strip() or "derivative"
    salt = _h(f"{int(workspace_id)}:{int(asset_id)}:{nm}")[:16]
    return f"kb/ws/{int(workspace_id)}/assets/{int(asset_id)}/derived/{salt}/{nm}"
