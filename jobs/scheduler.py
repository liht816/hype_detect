"""
Планировщик фоновых задач
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from jobs.alert_checker import AlertChecker
from jobs.trending_updater import TrendingUpdater
from jobs.whale_monitor import WhaleMonitor
from config import (
    ALERT_CHECK_INTERVAL,
    TRENDING_UPDATE_INTERVAL,
    WHALE_CHECK_INTERVAL,
)

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик фоновых задач"""
    
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.tasks: list[asyncio.Task] = []
        
        # Инициализация чекеров
        self.alert_checker = AlertChecker(bot)
        self.trending_updater = TrendingUpdater()
        self.whale_monitor = WhaleMonitor(bot)
    
    async def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        
        self.running = True
        logger.info("📅 Scheduler started")
        
        # Создаём задачи
        self.tasks = [
            asyncio.create_task(self._run_periodic(
                self.alert_checker.check_all_alerts,
                ALERT_CHECK_INTERVAL,
                "AlertChecker"
            )),
            asyncio.create_task(self._run_periodic(
                self.trending_updater.update_trending,
                TRENDING_UPDATE_INTERVAL,
                "TrendingUpdater"
            )),
            asyncio.create_task(self._run_periodic(
                self.whale_monitor.check_whale_activity,
                WHALE_CHECK_INTERVAL,
                "WhaleMonitor"
            )),
        ]
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
        logger.info("📅 Scheduler stopped")
    
    async def _run_periodic(
        self,
        func,
        interval: int,
        name: str
    ):
        """Периодический запуск функции"""
        while self.running:
            try:
                logger.debug(f"🔄 Running {name}")
                await func()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in {name}: {e}")
            
            await asyncio.sleep(interval)


# Глобальный планировщик
_scheduler: Optional[Scheduler] = None


async def start_scheduler(bot):
    """Запуск глобального планировщика"""
    global _scheduler
    
    if _scheduler is not None:
        return
    
    _scheduler = Scheduler(bot)
    await _scheduler.start()


async def stop_scheduler():
    """Остановка глобального планировщика"""
    global _scheduler
    
    if _scheduler is not None:
        await _scheduler.stop()
        _scheduler = None