from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
# ConfigDict用于配置model行为，比如extra是否允许额外字段

# 定义一个类型变量T，用于泛型
T = TypeVar("T")

class Meta(BaseModel):  # Meta是一个可扩展的meta容器
    model_config = ConfigDict(extra="allow")
    # extra="allow"表示输入里出现未声明字段时不报错，并保留这些字段
    # 我们这里希望meta能带任意额外字段，所以设置extra="allow"


class ApiResponse(BaseModel, Generic[T]):  # Generic[T]表示它是一个泛型模型，data的类型由T决定
    data: T
    meta: Meta | None = None  # meta可选，这里用于分页、调试、附加信息等


class Empty(BaseModel):  	# Empty常用于返回只表示成功但是没有数据的场景
    ok: bool = True


class ActionResult(BaseModel):  # 和Empty差不多意思，但是这个更倾向于某个动作的结果
    ok: bool = True  		# 比如这里默认True表示动作执行成功


class ErrorInfo(BaseModel):  # 统一错误结构
    code: str		# 错误吗
    message: Any	# 错误信息
    request_id: str	# 谁请求的
    meta: dict[str, Any] | None = None  # 额外信息

class ErrorResponse(BaseModel):  # 对上面的类包一层，争取返回{"error":xxxx}
    error: ErrorInfo