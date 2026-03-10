from __future__ import annotations

# RUN的一些状态
RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_WAITING_APPROVAL = "waiting_approval"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELED = "canceled"

# Step的类型
STEP_KIND_WORKFLOW = "workflow"
STEP_KIND_TOOL = "tool"
STEP_KIND_LLM = "llm"

# Step的状态
STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_WAITING_APPROVAL = "waiting_approval"
STEP_STATUS_SUCCEEDED = "succeeded"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_CANCELED = "canceled"

# 事件的类型
EVENT_RUN_CREATED = "run_created"
EVENT_STEP_STARTED = "step_started"
EVENT_STEP_FINISHED = "step_finished"
EVENT_TOKEN = "token"
EVENT_RUN_FINISHED = "run_finished"

# 默认配置
DEFAULT_ENGINE = "langgraph"
DEFAULT_WORKFLOW = "rag_qa"

# 限制和超时函数
MAX_INPUT_CHARS = 20_000
DEFAULT_MAX_STEPS = 40
DEFAULT_MAX_TOOL_CALLS = 40
DEFAULT_TOOL_TIMEOUT_SECONDS = 30