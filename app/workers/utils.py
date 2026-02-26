# TODO: 可能会出错——迟早会出错？

from __future__ import annotations

import asyncio
from typing import Any, Awaitable

# 这个工具类一般用在celery框架的里面
def run_async(coro: Awaitable[Any]) -> Any:  # 这是一个异步任务的工具函数
    try:
        loop = asyncio.get_running_loop()   # 取一个任务的异步的环境
    except RuntimeError:
        loop = None  # 如果没有，就设置loop变量为空
    if loop and loop.is_running():  #
        return asyncio.run_coroutine_threadsafe(coro, loop).result()  # 如果在执行那就正常执行
    return asyncio.run(coro)  # 否则就创建一个新的异步任务去运行