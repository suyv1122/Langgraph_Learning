from pydantic import BaseModel

class LeaveGraphPrompts(BaseModel):
    SLOT_SYSTEM: str = (
        '你是企业HR的请假助手。'
        '你的任务时从用户的请假描述中提取出结构化信息。'
        '只输出JSON，不要解释'
    )

    SLOT_USER: str = """请从下面文本中抽取字段，输出严格按照JSON格式: 
    {{
    'leave_type': 'annual|sick|personal|other',
    'start_time': 'YYYY-MM-DD HH:MM 或 null',
    'end_time': 'YYYY-MM-DD HH:MM 或 null',
    'reason': 'string 或 null'
    }}

    要求：
    - 如果用户没有明确说明开始/结束时间，则json中对应键的值输出null
    - 时间必须输出为 ISO 8601 格式 (YYYY-MM-DD HH:MM)
    - 禁止编造时间
    - 只输出JSON

    文本: {text}
    """

    # 时间解析用prompt，用于将相对时间转换为ISO格式
    TIME_SYSTEM: str = (
        '你是时间解析器。'
        '请把中文自然语言中的请假时间解析为 ISO 8601 start_time/end_time。'
        '只输出json，不需要解释。'
    )

    TIME_USER: str = """现在时间是: {now}
    用户文本: {text}

    请输出严格JSON: 
    {{
    'start_time': 'YYYY-MM-DD HH:MM 或 null',
    'end_time': 'YYYY-MM-DD HH:MM 或 null',
    }}

    规则: 
    - 能明确推断出具体日期就填ISO格式的时间；否则填null 
    - “下周二/明天/后天/本周五”等相对时间需要结合now推断
    - "上午/下午/全天/半天":
        - 全天: 
        - 上午: 
        - 下午: 
        - 半天: 
    - 如果文本里已经出现ISO时间，直接按其输出
    - 不要编造不存在的日期
    - 只输出JSON
    """

leave_graph_prompts = LeaveGraphPrompts()