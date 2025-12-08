# backend/utils/log.py
import logging
import uuid

def get_logger(name: str = "app"):
    """获取统一 logger"""
    return logging.getLogger(name)


def new_trace_id() -> str:
    """生成唯一 traceId"""
    return uuid.uuid4().hex[:16]


def set_trace_id(logger, traceId: str):
    """
    给 logger 注入 traceId
    
    """
    return logging.LoggerAdapter(logger, {"traceId": traceId})


# 快捷方式：为当前模块获取 traceId 注入版 logger
def get_trace_logger(name: str = "app", traceId: str = None):
    if traceId is None:
        traceId = new_trace_id()
    base_logger = get_logger(name)
    return set_trace_id(base_logger, traceId)

