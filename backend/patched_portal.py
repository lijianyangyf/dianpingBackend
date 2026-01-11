# log-dev/patched_portal.py
import sys
import os
import time
import json
import uuid
import traceback
from datetime import datetime
from flask import request, g, jsonify

# 1. 动态将 backend 目录加入路径，以便导入原版 portal
# 假设当前工作目录是 backend (由 launcher 设置)
CURRENT_DIR = os.getcwd()
sys.path.append(CURRENT_DIR)

# 2. 导入原版应用
try:
    from portal import app
except ImportError:
    # 兼容处理：如果脚本不是从 backend 目录启动的
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))
    from portal import app

# ==================== 注入 JSON 日志中间件 ====================

def _log_json(level, msg, event, **extra):
    """统一 JSON 日志输出"""
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "msg": msg,
        "event": event,
        "component": "backend",
        "pid": os.getpid(),
        **extra
    }
    print(json.dumps(entry, ensure_ascii=False, default=str), flush=True)

@app.before_request
def log_request_start():
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()

@app.after_request
def log_request_end(response):
    if hasattr(g, 'start_time'):
        latency = (time.time() - g.start_time) * 1000
        _log_json("INFO", "HTTP Request", "http_request",
            request_id=g.request_id,
            method=request.method,
            path=request.path,
            status=response.status_code,
            latency_ms=round(latency, 2),
            remote_addr=request.remote_addr
        )
    return response

@app.errorhandler(Exception)
def log_exception(e):
    _log_json("ERROR", str(e), "exception",
        request_id=getattr(g, 'request_id', 'unknown'),
        exception_type=type(e).__name__,
        exception_stack=traceback.format_exc()
    )
    return jsonify(code=999, msg="服务器内部错误"), 500

if __name__ == "__main__":
    # 启动增强后的 Flask
    app.run(host="0.0.0.0", port=8000, debug=True)
