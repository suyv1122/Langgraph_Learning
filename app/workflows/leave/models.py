from enum import Enum   # 引入枚举类型 需要解释枚举类型并强化记忆
from typing import Optional, List, TypedDict, Any
from pydantic import BaseModel, Field
# 定义模型，任何一个业务都先确定数据库/模型

class LeaveType(str, Enum):
    annual = 'annual'   # 年假
    sick = 'sick'       # 病假
    personal = 'personal' # 事假
    other = 'other'

class LeaveRequest(BaseModel):
    # 内容不要限制的太死，需要对外键的解释，需要补充
    # 这是一个请假单类，被称为模型，一组被封装在类中的数据；
    # 模型一般与数据库对应，一个模型类一般对应一个关系型数据库的表结构；
    # 一个对象对应表中的一行，这被称为 ‘对象-关系映射’ ，简称为ORM
    requester: str 
    leave_type: LeaveType = LeaveType.annual
    start_time: Optional[str] = None    # '2025-11-26 09:00', Optional[str]设置为选填内容，需补充解释
    end_time: Optional[str] = None      # 需补充python时间加减方法
    duration_days: Optional[float] = None
    reason: Optional[str] = None

class LeaveState(TypedDict, total=False):
    # 请假状态
    text: str
    requester: str
    user_role: str

    req: dict       # LeaveRequest as dict
    missing_fields: List[str]
    violations: List[str]

    answer: str
    confirmed: bool
    leave_id: Optional[str]
