from pydantic import BaseModel
from typing import List

class Constant(BaseModel):
    cancel : List[str] = ['cancel', 'cancelled', '取消', '撤销', '作废']
    check : List[str] = ['search', 'check', '查询', '查', '状态', '进度', '结果']
    leave : List[str] = ['请假', '年假', '病假', '事假', '休假', '调休', '假期', '申请', '单']

decide = Constant()
