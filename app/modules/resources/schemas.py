from __future__ import annotations

from pydantic import BaseModel, Field


class CreateWorkspaceReq(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class WorkspaceResp(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: str
    updated_at: str


class CreateProjectReq(BaseModel):
    workspace_id: int
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class ProjectResp(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str | None
    created_at: str
    updated_at: str