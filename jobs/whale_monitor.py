"""
Мониторинг китов
"""
import logging
from datetime import datetime
from typing import Optional

from telegram import Bot

from services import WhaleTracker
from core import AlertManager
from database.connection import async_session
from database.repositories import AlertRepository, UserRepository

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """Мониторинг крупных транзакций"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.whale_tracker = WhaleTracker()
        self.alert_manager = AlertManager()
        
        self._last_tx_time: int = 0
    
    async def check_whale_activity(self):
        """Проверка активности китов"""
        try:
            transactions = await self.whale_tracker.get_recent_whale_transactions(
                min_usd=5_000_000,  # Только очень крупные
                limit=10
            )
            
            new_transactions = []
            
            for tx in transactions:
                tx_time = tx.get("timestamp", 0)
                if tx_time > self._last_tx_time:
                    new_transactions.append(tx)
            
            if new_transactions:
                # Обновляем время последней транзакции
                self._last_tx_time = max(tx.get("timestamp", 0) for tx in new_transactions)
                
                # Отправляем алерты подписанным пользователям
                await self._notify_subscribers(new_transactions)
            
        except Exception as e:
            logger.error(f"❌ Whale monitor error: {e}")
    
    async def _notify_subscribers(self, transactions: list):
        """Уведомление подписчиков о крупных транзакциях"""
        async with async_session() as session:
            alert_repo = AlertRepository(session)
            user_repo = UserRepository(session)
            
            # Находим всех с whale алертами
            all_alerts = await alert_repo.get_all_active()
            whale_alerts = [a for a in all_alerts if a.alert_type == "whale_move"]
            
            for alert in whale_alerts:
                user = await user_repo.get_by_telegram_id(alert.user_id)
                
                if not user or not user.notifications_enabled:
                    continue
                
                # Проверяем тихие часы
                if self.alert_manager.is_quiet_hours(
                    user.quiet_hours_start,
                    user.quiet_hours_end
                ):
                    continue
                
                # Фильтруем транзакции по монете (если указана)
                relevant_txs = transactions
                if alert.coin_id:
                    coin_symbol = alert.coin_symbol.upper() if alert.coin_symbol else ""
                    relevant_txs = [
                        tx for tx in transactions
                        if tx.get("symbol", "").upper() == coin_symbol
                    ]
                
                # Отправляем
                for tx in relevant_txs[:3]:  # Максимум 3 за раз
                    event = self.alert_manager.check_whale_activity(
                        coin_id=tx.get("symbol", "crypto").lower(),
                        coin_symbol=tx.get("symbol", "?"),
                        coin_name=tx.get("symbol", "Crypto"),
                        transaction_type=tx.get("type", "transfer"),
                        amount_usd=tx.get("amount_usd", 0)
                    )
                    
                    if event:
                        try:
                            message = self.alert_manager.format_alert_message(event)
                            await self.bot.send_message(
                                chat_id=user.telegram_id,
                                text=message,
                                parse_mode="Markdown"
                            )
                            await alert_repo.mark_triggered(alert)
                        except Exception as e:
                            logger.error(f"Failed to send whale alert: {e}")