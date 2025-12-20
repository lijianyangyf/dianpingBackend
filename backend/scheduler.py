# -*- coding: utf-8 -*-
"""
定时任务调度器模块
- 每天指定时间自动更新所有店铺评分和招牌菜品
- 使用 asyncio 协程减少资源消耗
- 作为守护线程附着在 Flask 主进程中
"""

"""
测试指令：
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/background/triggerRatingUpdate" `
  -Method GET `
  -Headers @{
    "Authorization" = "Bearer <admin_token_here>"
  }
"""

import asyncio
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取执行时间，格式 HH:MM，默认 00:00 (午夜)
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "00:00")
# 线程池大小，用于并发执行数据库操作
SCHEDULER_POOL_SIZE = int(os.getenv("SCHEDULER_POOL_SIZE", "5"))


class RatingScheduler:
    """
    评分定时更新调度器

    使用协程实现定时任务，在后台守护线程中运行事件循环，
    到达指定时间后并发更新所有店铺的评分和招牌菜品。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式，确保只有一个调度器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._running = False
        self._thread = None
        self._loop = None
        self._executor = ThreadPoolExecutor(max_workers=SCHEDULER_POOL_SIZE)

    def start(self):
        """启动调度器（非阻塞）"""
        if self._running:
            print("[Scheduler] 调度器已在运行中")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_event_loop,
            name="RatingSchedulerThread",
            daemon=True  # 守护线程，主进程退出时自动结束
        )
        self._thread.start()
        print(f"[Scheduler] 定时任务调度器已启动")
        print(f"[Scheduler] 每日执行时间: {SCHEDULE_TIME}")

    def stop(self):
        """停止调度器"""
        if not self._running:
            return

        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self._executor.shutdown(wait=False)
        print("[Scheduler] 调度器已停止")

    def _run_event_loop(self):
        """在后台线程中运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._scheduler_main())
        except Exception as e:
            print(f"[Scheduler] 事件循环异常: {e}")
        finally:
            self._loop.close()
            print("[Scheduler] 事件循环已关闭")

    async def _scheduler_main(self):
        """调度器主协程，循环等待并执行定时任务"""
        while self._running:
            try:
                # 计算下次执行时间
                wait_seconds = self._calculate_wait_seconds()
                next_run = datetime.now() + timedelta(seconds=wait_seconds)

                print(f"[Scheduler] 下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"[Scheduler] 等待 {wait_seconds:.0f} 秒 ({wait_seconds/3600:.1f} 小时)")

                # 分段等待，便于响应停止信号
                while wait_seconds > 0 and self._running:
                    sleep_time = min(wait_seconds, 60)  # 每次最多等待60秒
                    await asyncio.sleep(sleep_time)
                    wait_seconds -= sleep_time

                # 执行更新任务
                if self._running:
                    await self._execute_update_task()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Scheduler] 调度循环异常: {e}")
                # 发生异常后等待一段时间再重试
                await asyncio.sleep(60)

    def _calculate_wait_seconds(self) -> float:
        """计算距离下次执行时间的秒数"""
        now = datetime.now()

        try:
            hour, minute = map(int, SCHEDULE_TIME.split(":"))
        except ValueError:
            print(f"[Scheduler] 时间格式错误: {SCHEDULE_TIME}，使用默认值 00:00")
            hour, minute = 0, 0

        # 构建今天的目标时间
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # 如果今天的执行时间已过，则设为明天
        if target <= now:
            target += timedelta(days=1)

        return (target - now).total_seconds()

    async def _execute_update_task(self):
        """执行更新任务：更新所有店铺评分和招牌菜品"""
        start_time = datetime.now()
        print(f"[Scheduler] ========== 开始执行定时更新任务 ==========")
        print(f"[Scheduler] 执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # 获取所有店铺ID
            stall_ids = await self._get_all_stall_ids()

            if not stall_ids:
                print("[Scheduler] 没有找到店铺数据，跳过更新")
                return

            print(f"[Scheduler] 共找到 {len(stall_ids)} 个店铺需要更新")

            # 创建所有更新任务
            tasks = [
                self._update_single_stall(stall_id)
                for stall_id in stall_ids
            ]

            # 并发执行所有更新任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            success_count = sum(1 for r in results if r is True)
            fail_count = len(results) - success_count

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"[Scheduler] ========== 更新任务完成 ==========")
            print(f"[Scheduler] 成功: {success_count}, 失败: {fail_count}")
            print(f"[Scheduler] 耗时: {duration:.2f} 秒")

        except Exception as e:
            print(f"[Scheduler] 更新任务执行失败: {e}")
            import traceback
            traceback.print_exc()

    async def _get_all_stall_ids(self) -> list:
        """异步获取所有店铺ID"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._sync_get_stall_ids)

    def _sync_get_stall_ids(self) -> list:
        """同步获取所有店铺ID（在线程池中执行）"""
        import Database

        db = Database.Database()
        stall_ids = []

        try:
            db.connect()
            result = db.execute_query("SELECT ID FROM Stall")
            db.disconnect()

            if result:
                for row in result:
                    if isinstance(row, dict):
                        stall_ids.append(row.get("ID"))
                    elif isinstance(row, tuple) and len(row) > 0:
                        stall_ids.append(row[0])

        except Exception as e:
            print(f"[Scheduler] 获取店铺列表失败: {e}")

        return stall_ids

    async def _update_single_stall(self, stall_id) -> bool:
        """
        异步更新单个店铺的评分和招牌菜品

        Args:
            stall_id: 店铺ID

        Returns:
            bool: 更新是否成功
        """
        loop = asyncio.get_event_loop()

        try:
            # 并发执行评分更新和招牌菜品更新
            rating_task = loop.run_in_executor(
                self._executor,
                self._sync_update_rating,
                stall_id
            )
            dish_task = loop.run_in_executor(
                self._executor,
                self._sync_update_signature_dish,
                stall_id
            )

            rating_result, dish_result = await asyncio.gather(
                rating_task, dish_task, return_exceptions=True
            )

            # 处理异常结果
            if isinstance(rating_result, Exception):
                print(f"[Scheduler] 店铺 {stall_id} 评分更新异常: {rating_result}")
                rating_result = False
            if isinstance(dish_result, Exception):
                print(f"[Scheduler] 店铺 {stall_id} 招牌菜更新异常: {dish_result}")
                dish_result = False

            return bool(rating_result) or bool(dish_result)

        except Exception as e:
            print(f"[Scheduler] 更新店铺 {stall_id} 失败: {e}")
            return False

    def _sync_update_rating(self, stall_id) -> bool:
        """同步更新店铺评分（在线程池中执行）"""
        from api import food
        try:
            return food.evaluateStallRating(stall_id)
        except Exception as e:
            print(f"[Scheduler] 评分更新失败 (店铺ID={stall_id}): {e}")
            return False

    def _sync_update_signature_dish(self, stall_id) -> bool:
        """同步更新招牌菜品（在线程池中执行）"""
        from api import food
        try:
            return food.evaluatesignatureDish(stall_id)
        except Exception as e:
            print(f"[Scheduler] 招牌菜更新失败 (店铺ID={stall_id}): {e}")
            return False

    def trigger_now(self):
        """
        立即触发一次更新任务（用于测试或手动触发）

        Returns:
            bool: 是否成功触发
        """
        if not self._running or not self._loop:
            print("[Scheduler] 调度器未运行，无法触发任务")
            return False

        # 在事件循环中安排任务
        asyncio.run_coroutine_threadsafe(
            self._execute_update_task(),
            self._loop
        )
        print("[Scheduler] 已触发立即更新任务")
        return True


# 全局调度器实例
scheduler = RatingScheduler()


def init_scheduler():
    """
    初始化并启动调度器

    在 Flask 应用启动时调用此函数
    """
    scheduler.start()


def stop_scheduler():
    """
    停止调度器

    在 Flask 应用关闭时调用此函数
    """
    scheduler.stop()


def trigger_update():
    """
    手动触发一次更新

    可用于测试或管理员手动触发
    """
    return scheduler.trigger_now()
