"""
全局GC管理模块
定期执行垃圾回收，避免频繁触发GC导致的GIL锁问题
"""

import gc
import asyncio
import threading
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class GlobalGCManager:
    """全局垃圾回收管理器"""

    def __init__(self, interval_seconds=300):
        self.interval_seconds = interval_seconds
        self._task = None
        self._stop_event = asyncio.Event()
        self._lock = threading.Lock()

    async def start(self):
        if self._task is not None:
            logger.bind(tag=TAG).warning("GC管理器已经在运行")
            return
        logger.bind(tag=TAG).info(f"启动全局GC管理器，间隔{self.interval_seconds}秒")
        self._stop_event.clear()
        self._task = asyncio.create_task(self._gc_loop())

    async def stop(self):
        if self._task is None:
            return
        logger.bind(tag=TAG).info("停止全局GC管理器")
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _gc_loop(self):
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
                    break
                except asyncio.TimeoutError:
                    pass
                await self._run_gc()
        except asyncio.CancelledError:
            logger.bind(tag=TAG).info("GC循环任务被取消")
            raise
        except Exception as e:
            logger.bind(tag=TAG).error(f"GC循环任务异常: {e}")
        finally:
            logger.bind(tag=TAG).info("GC循环任务已退出")

    async def _run_gc(self):
        try:
            loop = asyncio.get_running_loop()
            def do_gc():
                with self._lock:
                    before = len(gc.get_objects())
                    collected = gc.collect()
                    after = len(gc.get_objects())
                    return before, collected, after
            before, collected, after = await loop.run_in_executor(None, do_gc)
            logger.bind(tag=TAG).debug(
                f"全局GC执行完成 - 回收对象: {collected}, 对象数量: {before} -> {after}"
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"执行GC时出错: {e}")


_gc_manager_instance = None


def get_gc_manager(interval_seconds=300):
    global _gc_manager_instance
    if _gc_manager_instance is None:
        _gc_manager_instance = GlobalGCManager(interval_seconds)
    return _gc_manager_instance