# log-dev/patched_launcher.py
import sys
import os
import json
import time
import threading
import subprocess
from datetime import datetime

# 1. 将项目根目录加入路径，以便导入 launcher
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

import launcher

# ==================== 补丁逻辑 ====================

# 1. 替换 log 函数
def json_log(message, level="INFO"):
    log_entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "msg": message,
        "component": "launcher",
        "pid": os.getpid()
    }
    print(json.dumps(log_entry, ensure_ascii=False), flush=True)
    # 保持 GUI 显示
    launcher.log_queue.put(f"[{level}] {message}")

launcher.log = json_log

# 2. 增强 ServiceManager
class EnhancedServiceManager(launcher.ServiceManager):
    
    def _monitor_output(self, stream, name):
        """重写监控：支持 JSON 解析"""
        try:
            for line in iter(stream.readline, b''):
                if not line: continue
                # 解码
                try:
                    text = line.decode('utf-8').strip()
                except:
                    text = line.decode('gbk', errors='ignore').strip()
                if not text: continue

                # 尝试解析 JSON (透传) 或 包装文本
                try:
                    data = json.loads(text)
                    data["component"] = name
                    print(json.dumps(data, ensure_ascii=False), flush=True)
                except json.JSONDecodeError:
                    launcher.log(text, "INFO") # 使用 json_log 包装
                
                # GUI 显示纯文本
                launcher.log_queue.put(f"[{name}] {text}")
        except Exception as e:
            launcher.log(f"[{name}] 监控异常: {e}", "WARN")

    def _restart_flask(self):
        """重写：启动 patched_portal.py 而不是原版 portal"""
        launcher.log("正在启动 Flask (Patched)...", "INFO")
        try:
            flask_env = os.environ.copy()
            flask_env["PYTHONIOENCODING"] = "utf-8"
            
            # 【关键修改】指向 log-dev 下的 patched_portal.py
            patch_script = os.path.join(ROOT_DIR, "log-dev", "patched_portal.py")
            
            # 使用 python 直接运行脚本
            flask_cmd = [sys.executable, patch_script]
            
            launcher.flask_process = subprocess.Popen(
                flask_cmd,
                cwd=launcher.BACKEND_DIR, # 保持工作目录在 backend，确保 import 正常
                env=flask_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.flask_status = True
            launcher.log(f"Flask 已启动 (PID: {launcher.flask_process.pid})", "INFO")

            threading.Thread(target=self._monitor_output, args=(launcher.flask_process.stdout, "Flask"), daemon=True).start()
            threading.Thread(target=self._monitor_output, args=(launcher.flask_process.stderr, "Flask-LOG"), daemon=True).start()
        except Exception as e:
            launcher.log(f"Flask 启动失败: {e}", "ERROR")
            self.flask_status = False

    def _watchdog_thread(self):
        """新增：看门狗自动重启"""
        restart_counts = 0
        while launcher.app_running:
            proc = launcher.flask_process
            if proc and proc.poll() is not None:
                exit_code = proc.returncode
                launcher.log(f"Flask 异常退出 (码: {exit_code})", "ERROR")
                
                if restart_counts < 5:
                    backoff = min(2 ** restart_counts, 30)
                    launcher.log(f"{backoff}秒后尝试重启...", "INFO")
                    time.sleep(backoff)
                    self._restart_flask()
                    restart_counts += 1
                else:
                    launcher.log("重启失败次数过多，停止尝试", "FATAL")
            time.sleep(5)

    def start_services(self):
        """重写启动流程"""
        # 1. 启动 Redis (复用代码)
        launcher.log("正在启动 Redis...", "INFO")
        try:
            launcher.redis_process = subprocess.Popen(
                "redis-server", shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.redis_status = True
            launcher.log(f"Redis 已启动 (PID: {launcher.redis_process.pid})", "INFO")
            threading.Thread(target=self._monitor_output, args=(launcher.redis_process.stdout, "Redis"), daemon=True).start()
            threading.Thread(target=self._monitor_output, args=(launcher.redis_process.stderr, "Redis-ERR"), daemon=True).start()
        except Exception as e:
            launcher.log(f"Redis 启动失败: {e}", "ERROR")

        # 2. 启动 Patched Flask
        self._restart_flask()

        # 3. 启动看门狗
        threading.Thread(target=self._watchdog_thread, daemon=True).start()

# 应用类补丁
launcher.ServiceManager = EnhancedServiceManager

if __name__ == "__main__":
    try:
        # 启动 GUI
        panel = launcher.StatusPanel()
        panel.run()
    except KeyboardInterrupt:
        sys.exit()
