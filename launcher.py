#!/usr/bin/env python3
"""
launcher.py - 校园餐饮管理系统启动器 (Campus Dining System Launcher)
功能：环境检查、依赖验证、服务管理、Pygame状态监控面板
Author: AI Assistant
Date: 2025-12-21
"""

#========== 导入模块 ==========
import os          # 文件和目录操作
import sys         # 系统相关功能，如退出程序
import threading   # 多线程支持，用于后台任务
import subprocess  # 子进程管理，用于启动Redis和Flask
import signal      # 信号处理（当前未使用）
import time        # 时间相关功能，用于日志时间戳
import queue       # 线程安全的队列，用于日志传递
import platform    # 平台检测，用于跨平台兼容
import pygame      # GUI界面库，用于状态监控面板

#========== 常量配置 ==========
# 项目路径配置
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # 项目根目录
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")        # 后端目录
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")      # 前端目录
IMG_REPO_DIR = os.path.join(PROJECT_ROOT, "imgRepo")       # 图片仓库目录
ENV_FILE = os.path.join(BACKEND_DIR, ".env")               # 环境变量配置文件
PORTAL_SCRIPT = os.path.join(BACKEND_DIR, "portal.py")     # Flask入口脚本

# GUI界面常量
WINDOW_SIZE = (800, 600)           # 窗口尺寸：宽800像素，高600像素
FPS = 30                           # 帧率：每秒30帧
COLOR_BG = (30, 30, 30)            # 背景色：深灰色
COLOR_TEXT = (220, 220, 220)       # 文字色：浅灰色
COLOR_SUCCESS = (50, 200, 50)      # 成功状态色：绿色
COLOR_ERROR = (200, 50, 50)        # 错误状态色：红色
COLOR_WARNING = (200, 200, 50)     # 警告状态色：黄色
COLOR_BUTTON = (60, 60, 80)        # 按钮默认色：深蓝灰
COLOR_BUTTON_HOVER = (80, 80, 100) # 按钮悬停色：浅蓝灰
# 字体大小配置（适应中文显示）
FONT_SIZE_TITLE = 32               # 标题字体大小
FONT_SIZE_NORMAL = 16              # 普通文字字体大小
FONT_SIZE_LOG = 14                 # 日志文字字体大小

#========== 状态机定义 ==========
class AppState:
    """应用程序状态枚举类，定义系统的各种运行状态"""
    UNINITIALIZED = "未初始化"  # 程序刚启动，尚未进行初始化检查
    CHECKING = "自检中"          # 正在进行环境和依赖检查
    INITIAL = "就绪"             # 检查完成，系统就绪，可以启动服务
    RUNNING = "运行中"           # 服务正在运行
    ERROR = "错误"               # 初始化或运行过程中出现错误

#========== 全局变量/信号 ==========
log_queue = queue.Queue()  # 线程安全的日志队列，用于从后台线程传递日志到GUI线程
app_running = True         # 应用运行标志，控制主循环
redis_process = None       # Redis服务的子进程对象
flask_process = None       # Flask服务的子进程对象

#========== 辅助函数 ==========
def log(message, level="信息"):
    """
    线程安全的日志记录函数
    将日志消息添加到队列中，供GUI线程显示

    参数:
        message: 日志消息内容
        level: 日志级别（信息/警告/错误/成功等）
    """
    timestamp = time.strftime("%H:%M:%S")  # 获取当前时间（时:分:秒）
    formatted_msg = f"[{timestamp}] [{level}] {message}"  # 格式化日志消息
    print(formatted_msg)  # 同时输出到控制台
    log_queue.put(formatted_msg)  # 放入队列供GUI显示

def open_file_in_editor(filepath):
    """
    使用系统默认编辑器打开文件
    跨平台支持：Windows/macOS/Linux

    参数:
        filepath: 要打开的文件路径
    """
    if platform.system() == 'Windows':
        os.startfile(filepath)  # Windows系统使用startfile
    elif platform.system() == 'Darwin':
        subprocess.call(('open', filepath))  # macOS使用open命令
    else:
        subprocess.call(('xdg-open', filepath))  # Linux使用xdg-open

#========== 核心逻辑 ==========
class ServiceManager:
    """
    服务管理器类
    负责管理Redis和Flask服务的启动、停止和状态监控
    """
    def __init__(self):
        """初始化服务管理器，设置服务状态为False"""
        self.redis_status = False   # Redis服务运行状态
        self.flask_status = False   # Flask服务运行状态

    def check_dependencies(self):
        """
        检查项目结构和Python依赖
        验证必要的目录、文件和Python包是否存在

        返回:
            bool: 检查通过返回True，否则返回False
        """
        log("正在检查环境配置...", "初始化")

        # 1. 检查目录结构
        if not os.path.exists(FRONTEND_DIR):
            log(f"错误: 未找到前端目录 {FRONTEND_DIR}", "错误")
            log("请确保您在项目根目录下运行此脚本。", "错误")
            return False

        # 检查关键文件是否存在
        if not (os.path.exists(PORTAL_SCRIPT) or os.path.exists(ENV_FILE)):
            if not os.path.exists(PORTAL_SCRIPT):
                log(f"缺失文件: {PORTAL_SCRIPT}", "错误")
            if not os.path.exists(ENV_FILE):
                log(f"缺失文件: {ENV_FILE}", "错误")

            log("请确保您在项目根目录下运行此脚本。", "错误")
            return False

        # 2. 检查Python依赖包
        requirements = ["flask", "mysql.connector", "redis", "jwt", "dotenv"]

        # 依赖包映射表：检查名 -> pip包名
        req_map = {
            "flask": "Flask",
            "mysql.connector": "mysql-connector",
            "redis": "redis",
            "pyjwt": "PyJWT",
            "python-dotenv": "python-dotenv"
        }

        missing_pkgs = []  # 缺失的包列表
        try:
            # 获取已安装的包列表
            installed_packages = subprocess.check_output([sys.executable, '-m', 'pip', 'list']).decode('utf-8', errors='ignore').lower()
        except Exception as e:
            log(f"无法检测 Python 包: {e}", "警告")
            installed_packages = ""

        # 检查每个必需的包是否已安装
        for check_name, pkg_name in req_map.items():
            if pkg_name.lower() not in installed_packages:
                missing_pkgs.append(pkg_name)

        # 如果有缺失的包，提示用户安装
        if missing_pkgs:
            log(f"缺失依赖包: {', '.join(missing_pkgs)}", "警告")
            log(f"请运行: pip install {' '.join(missing_pkgs)}", "警告")
        else:
            log("所有 Python 依赖已满足。", "成功")

        # 3. 检查/创建图片仓库目录
        if not os.path.exists(IMG_REPO_DIR):
            try:
                os.makedirs(IMG_REPO_DIR)  # 创建目录
                log(f"已创建图片仓库目录: {IMG_REPO_DIR}", "成功")
            except Exception as e:
                log(f"创建图片仓库失败: {e}", "错误")
                return False

        return True  # 所有检查通过

    def start_services(self):
        """
        启动Redis和Flask服务
        在后台启动两个子进程，并监控它们的输出
        """
        global redis_process, flask_process

        # 启动Redis服务
        log("正在启动 Redis 服务...", "命令")
        try:
            redis_cmd = "redis-server"
            redis_process = subprocess.Popen(
                redis_cmd,
                shell=True,
                stdout=subprocess.PIPE,  # 捕获标准输出
                stderr=subprocess.PIPE   # 捕获错误输出
            )
            self.redis_status = True
            log("Redis 服务已启动 (PID: {})".format(redis_process.pid), "成功")

            # 启动后台线程监控Redis的stdout和stderr输出
            threading.Thread(target=self._monitor_output, args=(redis_process.stdout, "Redis"), daemon=True).start()
            threading.Thread(target=self._monitor_output, args=(redis_process.stderr, "Redis-ERR"), daemon=True).start()
        except Exception as e:
            log(f"Redis 启动失败: {e}", "错误")
            self.redis_status = False

        # 启动Flask后端服务
        log("正在启动 Flask 后端...", "命令")
        try:
            # 强制子进程使用UTF-8输出，避免中文乱码
            flask_env = os.environ.copy()
            flask_env["PYTHONIOENCODING"] = "utf-8"

            # 构建Flask启动命令：使用flask命令行工具，指定portal模块，端口8000
            flask_cmd = [sys.executable, "-m", "flask", "--app", "portal", "run", "--port", "8000"]
            flask_process = subprocess.Popen(
                flask_cmd,
                cwd=BACKEND_DIR,         # 设置工作目录为backend
                env=flask_env,           # 使用修改后的环境变量
                stdout=subprocess.PIPE,  # 捕获标准输出
                stderr=subprocess.PIPE   # 捕获错误输出
            )
            self.flask_status = True
            log("Flask 后端已启动 (PID: {})".format(flask_process.pid), "成功")

            # 启动后台线程监控Flask的stdout和stderr输出
            threading.Thread(target=self._monitor_output, args=(flask_process.stdout, "Flask"), daemon=True).start()
            threading.Thread(target=self._monitor_output, args=(flask_process.stderr, "Flask-LOG"), daemon=True).start()

        except Exception as e:
            log(f"Flask 启动失败: {e}", "错误")
            self.flask_status = False
            # 如果Flask启动失败，同时停止Redis
            if redis_process:
                redis_process.terminate()
                self.redis_status = False

    def stop_services(self):
        """
        停止所有服务
        优雅地关闭Redis和Flask子进程
        """
        global redis_process, flask_process
        log("正在停止所有服务...", "命令")

        # 停止Redis服务
        if redis_process:
            # 尝试更优雅地关闭进程
            try:
                if platform.system() == 'Windows':
                    # Windows使用taskkill命令强制终止进程树
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(redis_process.pid)])
                else:
                    # Unix系统使用terminate信号
                    redis_process.terminate()
            except:
                pass  # 忽略关闭过程中的错误
            redis_process = None
            self.redis_status = False
            log("Redis 服务已停止。", "信息")

        # 停止Flask服务
        if flask_process:
            try:
                if platform.system() == 'Windows':
                    # Windows使用taskkill命令强制终止进程树
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(flask_process.pid)])
                else:
                    # Unix系统使用terminate信号
                    flask_process.terminate()
            except:
                pass  # 忽略关闭过程中的错误
            flask_process = None
            self.flask_status = False
            log("Flask 后端已停止。", "信息")

    def _monitor_output(self, stream, name):
        """
        监控子进程输出流的辅助方法
        在后台线程中运行，实时读取并记录子进程的输出

        参数:
            stream: 输出流对象（stdout或stderr）
            name: 进程名称（用于日志标识）
        """
        try:
            # 逐行读取输出流
            for line in iter(stream.readline, b''):
                if line:
                    text = ""
                    # 智能解码：优先UTF-8，失败则尝试GBK（适配Windows）
                    try:
                        text = line.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            text = line.decode('gbk')  # Windows中文编码
                        except UnicodeDecodeError:
                            text = line.decode('utf-8', errors='ignore')  # 忽略错误字符

                    # 过滤掉空行，记录有内容的日志
                    if text.strip():
                        log(f"[{name}] {text.strip()}", "日志")
        except Exception as e:
            # 如果读取出错，记录错误信息
            log(f"[{name}] 输出监控异常: {e}", "警告")

#========== GUI 组件 ==========
class Button:
    """
    按钮组件类
    提供可点击的GUI按钮，支持悬停效果和禁用状态
    """
    def __init__(self, x, y, w, h, text, callback, enabled=True):
        """
        初始化按钮

        参数:
            x, y: 按钮左上角坐标
            w, h: 按钮宽度和高度
            text: 按钮显示文字
            callback: 点击时调用的回调函数
            enabled: 是否启用按钮（默认True）
        """
        self.rect = pygame.Rect(x, y, w, h)  # 按钮矩形区域
        self.text = text                      # 按钮文字
        self.callback = callback              # 点击回调函数
        self.enabled = enabled                # 启用状态
        self.hover = False                    # 鼠标悬停状态

    def draw(self, surface, font):
        """
        绘制按钮到指定表面

        参数:
            surface: Pygame表面对象
            font: 字体对象
        """
        # 根据状态选择颜色
        color = COLOR_BUTTON_HOVER if self.hover and self.enabled else COLOR_BUTTON
        if not self.enabled:
            color = (40, 40, 40)  # 禁用状态为深灰色

        # 绘制按钮背景（圆角矩形）
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        # 绘制按钮边框
        pygame.draw.rect(surface, (100, 100, 100), self.rect, 2, border_radius=5)

        # 绘制按钮文字（居中）
        text_surf = font.render(self.text, True, COLOR_TEXT if self.enabled else (100, 100, 100))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        """
        处理鼠标事件

        参数:
            event: Pygame事件对象

        返回:
            bool: 如果按钮被点击返回True，否则返回False
        """
        if not self.enabled:
            return False  # 禁用状态不响应事件

        if event.type == pygame.MOUSEMOTION:
            # 检测鼠标是否悬停在按钮上
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # 检测鼠标左键点击
            if self.hover and event.button == 1:
                self.callback()  # 调用回调函数
                return True
        return False

class StatusPanel:
    """
    状态监控面板类
    提供图形化界面，显示系统状态、服务状态和日志信息
    """
    def __init__(self):
        """初始化状态面板，创建窗口和UI组件"""
        pygame.init()  # 初始化Pygame
        pygame.display.set_caption("校园餐饮管理系统 - 服务启动器")  # 设置窗口标题
        self.screen = pygame.display.set_mode(WINDOW_SIZE)  # 创建窗口
        self.clock = pygame.time.Clock()  # 创建时钟对象，用于控制帧率

        # === 字体配置（解决中文乱码）===
        # 优先尝试"Microsoft YaHei"（微软雅黑），其次"SimHei"（黑体）
        # SysFont接受字体名称字符串
        font_name = "microsoftyahei"
        if "microsoftyahei" not in pygame.font.get_fonts():
            if "simhei" in pygame.font.get_fonts():
                font_name = "simhei"
            else:
                # 最后的保底，可能会乱码，但在Windows上通常都有微软雅黑
                font_name = "arial"

        # 创建不同大小的字体对象
        self.font_title = pygame.font.SysFont(font_name, FONT_SIZE_TITLE, bold=True)  # 标题字体（粗体）
        self.font_normal = pygame.font.SysFont(font_name, FONT_SIZE_NORMAL)           # 普通字体
        self.font_log = pygame.font.SysFont(font_name, FONT_SIZE_LOG)                 # 日志字体

        self.state = AppState.UNINITIALIZED  # 初始状态为未初始化
        self.service_manager = ServiceManager()  # 创建服务管理器实例
        self.logs = []  # 日志消息列表

        # 定义按钮
        btn_w, btn_h = 160, 40  # 按钮宽度和高度
        start_x = 50            # 第一个按钮的X坐标

        # 创建三个按钮：启动、停止、编辑配置
        self.btn_start = Button(start_x, 500, btn_w, btn_h, "启动所有服务", self.action_start)
        self.btn_stop = Button(start_x + 180, 500, btn_w, btn_h, "停止所有服务", self.action_stop, enabled=False)
        self.btn_edit = Button(start_x + 360, 500, btn_w, btn_h, "编辑配置文件", self.action_edit)

        self.buttons = [self.btn_start, self.btn_stop, self.btn_edit]  # 按钮列表

    def init_check(self):
        """
        后台初始化检查
        在独立线程中执行环境检查，避免阻塞GUI主线程
        """
        self.state = AppState.CHECKING  # 设置状态为检查中

        def _check():
            """内部检查函数，在后台线程中运行"""
            success = self.service_manager.check_dependencies()  # 执行依赖检查
            if success:
                self.state = AppState.INITIAL  # 检查成功，状态设为就绪
                log("初始化完成，系统就绪。", "系统")
            else:
                self.state = AppState.ERROR  # 检查失败，状态设为错误
                log("初始化失败，请检查上方日志。", "系统")

        # 启动后台线程执行检查（daemon=True表示主程序退出时自动结束）
        threading.Thread(target=_check, daemon=True).start()

    def action_start(self):
        """
        启动服务按钮的回调函数
        启动Redis和Flask服务，并更新按钮状态
        """
        if self.state == AppState.INITIAL:
            self.state = AppState.RUNNING  # 更新状态为运行中
            self.btn_start.enabled = False  # 禁用启动按钮
            self.btn_stop.enabled = True    # 启用停止按钮
            self.btn_edit.enabled = False   # 禁用编辑按钮（运行时不允许编辑配置）
            # 在后台线程中启动服务
            threading.Thread(target=self.service_manager.start_services, daemon=True).start()

    def action_stop(self):
        """
        停止服务按钮的回调函数
        停止所有服务，并恢复按钮状态
        """
        if self.state == AppState.RUNNING:
            self.service_manager.stop_services()  # 停止服务
            self.state = AppState.INITIAL  # 恢复状态为就绪
            self.btn_start.enabled = True   # 启用启动按钮
            self.btn_stop.enabled = False   # 禁用停止按钮
            self.btn_edit.enabled = True    # 启用编辑按钮

    def action_edit(self):
        """
        编辑配置文件按钮的回调函数
        使用系统默认编辑器打开.env配置文件
        """
        if self.state == AppState.INITIAL:
            log(f"正在打开 {ENV_FILE} ...", "系统")
            # 如果配置文件不存在，创建一个空的
            if not os.path.exists(ENV_FILE):
                with open(ENV_FILE, 'w') as f:
                    f.write("# Environment Variables\n")
            open_file_in_editor(ENV_FILE)  # 打开文件
        else:
            log("服务运行时无法编辑配置文件。", "警告")

    def draw_status_indicator(self, x, y, label, status):
        """
        绘制服务状态指示灯
        显示一个圆形指示灯和标签文字

        参数:
            x, y: 指示灯中心坐标
            label: 标签文字
            status: 状态（True为成功/绿色，False为错误/红色）
        """
        color = COLOR_SUCCESS if status else COLOR_ERROR  # 根据状态选择颜色
        # 绘制圆形指示灯
        pygame.draw.circle(self.screen, color, (x, y), 10)
        # 绘制标签文字（在指示灯右侧）
        text = self.font_normal.render(label, True, COLOR_TEXT)
        self.screen.blit(text, (x + 20, y - 10))

    def run(self):
        """
        主运行循环
        处理事件、更新日志、绘制界面
        """
        self.init_check()  # 启动初始化检查

        while app_running:
            # 1. 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭事件
                    self.cleanup()  # 清理资源
                    return
                # 将事件传递给所有按钮处理
                for btn in self.buttons:
                    btn.handle_event(event)

            # 2. 日志处理（从队列中获取新日志）
            while not log_queue.empty():
                try:
                    msg = log_queue.get_nowait()  # 非阻塞获取
                    self.logs.append(msg)  # 添加到日志列表
                    if len(self.logs) > 100:  # 限制日志数量，避免内存溢出
                        self.logs.pop(0)  # 删除最旧的日志
                except queue.Empty:
                    break

            # 3. 绘制界面
            self.screen.fill(COLOR_BG)  # 填充背景色

            # 绘制标题
            title = self.font_title.render("校园餐饮管理系统 - 状态监控", True, COLOR_TEXT)
            self.screen.blit(title, (20, 20))

            # 绘制当前状态
            state_text = self.font_normal.render(f"当前状态: {self.state}", True, COLOR_WARNING)
            self.screen.blit(state_text, (20, 70))

            # 绘制服务状态指示灯
            self.draw_status_indicator(400, 80, "Redis 服务", self.service_manager.redis_status)
            self.draw_status_indicator(550, 80, "Flask 后端", self.service_manager.flask_status)

            # 绘制日志区域
            log_rect = pygame.Rect(20, 120, 760, 350)  # 日志显示区域
            pygame.draw.rect(self.screen, (10, 10, 10), log_rect)  # 深色背景
            pygame.draw.rect(self.screen, (100, 100, 100), log_rect, 1)  # 边框

            # 计算可显示的日志行数
            lines_visible = log_rect.height // (FONT_SIZE_LOG + 4)
            start_index = max(0, len(self.logs) - lines_visible)  # 从最新的日志开始显示

            # 绘制日志内容
            for i, log_msg in enumerate(self.logs[start_index:]):
                color = COLOR_TEXT  # 默认颜色
                # 根据日志级别设置颜色
                if "[错误]" in log_msg: color = COLOR_ERROR
                elif "[警告]" in log_msg: color = COLOR_WARNING
                elif "[成功]" in log_msg: color = COLOR_SUCCESS

                txt_surf = self.font_log.render(log_msg, True, color)
                self.screen.blit(txt_surf, (log_rect.x + 5, log_rect.y + 5 + i * (FONT_SIZE_LOG + 4)))

            # 绘制所有按钮
            for btn in self.buttons:
                btn.draw(self.screen, self.font_normal)

            pygame.display.flip()  # 更新显示
            self.clock.tick(FPS)  # 控制帧率

    def cleanup(self):
        """
        清理资源并退出程序
        停止所有服务，关闭Pygame，退出程序
        """
        log("正在退出...", "系统")
        self.service_manager.stop_services()  # 停止所有后台服务
        pygame.quit()  # 关闭Pygame
        sys.exit()     # 退出程序

#========== 主入口 ==========
if __name__ == "__main__":
    """
    程序主入口
    创建状态面板并启动主循环
    """
    try:
        panel = StatusPanel()  # 创建状态面板实例
        panel.run()            # 启动主循环
    except KeyboardInterrupt:
        # 捕获Ctrl+C键盘中断
        print("\n检测到键盘中断，正在退出...")
        sys.exit()