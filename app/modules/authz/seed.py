from __future__ import annotations

from typing import Final

ROLES: Final[tuple[tuple[str, str], ...]] = (
    ("owner", "Workspace/Project owner"),
    ("admin", "Workspace/Project admin"),
    ("editor", "Can create/update resources"),
    ("viewer", "Read-only access"),
)

BASE_PERMISSIONS: Final[tuple[tuple[str, str], ...]] = (
    ("workspace.manage", "Manage workspace settings/members"),
    ("project.manage", "Manage projects"),
    ("doc.read", "Read documents"),
    ("doc.write", "Create/update documents"),
    ("doc.delete", "Delete documents"),
    ("audio.read", "Read audio resources"),
    ("audio.search", "Search audio content"),
    ("audio.write", "Upload/update audio"),
    ("audio.delete", "Delete audio"),
    ("image.read", "Read images"),
    ("image.write", "Upload/update images"),
    ("image.delete", "Delete images"),
    ("ticket.read", "Read tickets"),
    ("ticket.create", "Create tickets"),
    ("ticket.approve", "Approve tickets"),
    ("ticket.close", "Close tickets"),
)

AGENT_PERMISSIONS: Final[tuple[tuple[str, str], ...]] = (
    ("agent.use", "Use agent chat/run endpoints"),
    ("agent.approval.review", "Review and decide agent approvals"),
)

PERMISSIONS: Final[tuple[tuple[str, str], ...]] = BASE_PERMISSIONS + AGENT_PERMISSIONS

_ALL_PERM_CODES: Final[tuple[str, ...]] = tuple(code for code, _ in PERMISSIONS)

DEFAULT_ROLE_PERMS: Final[dict[str, tuple[str, ...]]] = {
    "owner": _ALL_PERM_CODES,
    "admin": _ALL_PERM_CODES,
    "editor": (
        "doc.read",
        "doc.write",
        "audio.read",
        "audio.search",
        "audio.write",
        "image.read",
        "image.write",
        "ticket.read",
        "ticket.create",
        "agent.use",
    ),
    "viewer": (
        "doc.read",
        "audio.read",
        "audio.search",
        "image.read",
        "ticket.read",
    ),
}