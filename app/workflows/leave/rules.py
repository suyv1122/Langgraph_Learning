# 规则校验
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta

def validate_leave(req: Dict[str, Any], balance_days: float = 5.0) -> Tuple[List[str], List[str]]:

    missing = []    # 存放缺失值的键名
    violations =[]  # 存放错误信息

    for f in ['leave_type', 'start_time', 'end_time']:
        if not req.get(f):      # 如果某一项标签的值缺失
            missing.append(f)   # 缺失标签加入missing

    if missing:
        return missing, violations

    # parse time 如没有缺失开始对时间解析
    # 对时间的解析必须抛异常
    try:
        # 所有前台取出的内容均为str类型，即使数字也是str类型
        start = datetime.fromisoformat(req['start_time'])
        end = datetime.fromisoformat(req['end_time'])
    except Exception:
        violations.append('start_time/end_time 格式应为 ISO 格式 (YYYY-MM-DD HH:MM)')
        return missing, violations

    if end <= start:
        violations.append('结束时间必须晚于开始时间')

    duration = (end - start).total_seconds() / 3600.0 / 8.0
    if duration < 0.5:
        violations.append('最小请假单位为0.5天')

    leave_type = req.get('leave_type')
    if leave_type == 'annual':
        if duration > balance_days:
            violations.append(f'年假余额不足 (剩余 {balance_days} 天)')
        # 提前一个工作日 (简化版: 提前24小时)
        if start < datetime.now() + timedelta(hours=1): # todo: 逻辑可能有问题
            violations.append(f'年假需提前至少一个工作日提交')

    if leave_type == 'sick':
        if duration >= 1 and not req.get('reason'):
            violations.append('病假超过一天需提供病假原因/证明说明')

    req['duration_days'] = round(duration, 2)   # round 使duration保留 2 位小数
    return missing, violations