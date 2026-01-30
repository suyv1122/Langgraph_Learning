# 7.2
from __future__ import annotations

from dataclasses import dataclass

SCOPE_GLOBAL = "global"

_PREFIX_WORKSPACE = "workspace:"
_PREFIX_PROJECT = "project:"
_PREFIX_RESOURCE = "resource:"

_MAX_LEN = 128  # scope_key的最大长度


def scope_global() -> str:
    return SCOPE_GLOBAL


def scope_workspace(workspace_id: int) -> str:
    return f"{_PREFIX_WORKSPACE}{int(workspace_id)}"


def scope_project(project_id: int) -> str:
    return f"{_PREFIX_PROJECT}{int(project_id)}"


def scope_resource(resource_type: str, ref_id: int) -> str:
# 生成resource scope_key，格式是这样的，比如resource:doc:100，后面100是id
    rt = str(resource_type or "").strip()
    if not rt:
        raise ValueError("bad_resource_type")
    if ":" in rt:
        raise ValueError("bad_resource_type")
    return f"{_PREFIX_RESOURCE}{rt}:{int(ref_id)}"


@dataclass(frozen=True)
class ParsedScope:  #  解析后的scope_key结构体
    kind: str
    workspace_id: int | None = None
    project_id: int | None = None
    resource_type: str | None = None
    ref_id: int | None = None


def parse_scope_key(scope_key: str) -> ParsedScope:  # 把scope_key字符串解析成ParsedScope
    sk = str(scope_key or "").strip()
    if not sk or len(sk) > _MAX_LEN:
        raise ValueError("bad_scope_key")

    if sk == SCOPE_GLOBAL:
        return ParsedScope(kind="global")

    if sk.startswith(_PREFIX_WORKSPACE):
        v = sk[len(_PREFIX_WORKSPACE) :]
        return ParsedScope(kind="workspace", workspace_id=int(v))

    if sk.startswith(_PREFIX_PROJECT):
        v = sk[len(_PREFIX_PROJECT) :]
        return ParsedScope(kind="project", project_id=int(v))

    if sk.startswith(_PREFIX_RESOURCE):
        rest = sk[len(_PREFIX_RESOURCE) :]
        if ":" not in rest:
            raise ValueError("bad_scope_key")
        rt, rid = rest.split(":", 1)
        rt = rt.strip()
        if not rt or ":" in rt:
            raise ValueError("bad_scope_key")
        return ParsedScope(kind="resource", resource_type=rt, ref_id=int(rid))

    raise ValueError("bad_scope_key")


def scopes_with_global(scope_key: str) -> list[str]:
# 给定一个scope_key，返回当前的scope和global列表，用于权限查询时包含全局授权
    sk = str(scope_key or "").strip()
    if not sk:
        return [SCOPE_GLOBAL]
    if sk == SCOPE_GLOBAL:
        return [SCOPE_GLOBAL]
    return [sk, SCOPE_GLOBAL]
