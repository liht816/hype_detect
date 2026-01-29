"""
Проверка алертов
"""
import logging
from datetime import datetime
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from services import CoinGeckoService, WhaleTracker
from core import AlertManager, HypeCalculator
from database.connection import async_session
from database.repositories import (
    UserRepository,
    AlertRepository,
    WatchlistRepository,
)
from database.models import Alert, User, CoinCache

logger = logging.getLogger(__name__)


class AlertChecker:
    """Проверка и отправка алертов"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.coingecko = CoinGeckoService()
        self.whale_tracker = WhaleTracker()
        self.alert_manager = AlertManager()
        self.hype_calc = HypeCalculator()
        
        # Кэш предыдущих значений для сравнения
        self._previous_values: dict[str, dict] = {}
    
    async def check_all_alerts(self):
        """Проверка всех активных алертов"""
        async with async_session() as session:
            alert_repo = AlertRepository(session)
            user_repo = UserRepository(session)
            
            # Получаем все активные алерты
            alerts = await alert_repo.get_all_active()
            
            if not alerts:
                return
            
            # Группируем по coin_id для оптимизации запросов
            coins_to_check = set()
            for alert in alerts:
                if alert.coin_id:
                    coins_to_check.add(alert.coin_id)
            
            # Получаем данные для всех монет
            coin_data = {}
            for coin_id in coins_to_check:
                try:
                    data = await self.coingecko.get_coin_data(coin_id)
                    if data:
                        coin_data[coin_id] = data
                except Exception as e:
                    logger.error(f"Error fetching {coin_id}: {e}")
            
            # Проверяем каждый алерт
            for alert in alerts:
                try:
                    await self._check_alert(alert, coin_data, user_repo, alert_repo)
                except Exception as e:
                    logger.error(f"Error checking alert {alert.id}: {e}")
    
    async def _check_alert(
        self,
        alert: Alert,
        coin_data: dict,
        user_repo: UserRepository,
        alert_repo: AlertRepository
    ):
        """Проверка одного алерта"""
        user = await user_repo.get_by_telegram_id(alert.user_id)
        if not user:
            return
        
        # Проверяем тихие часы
        current_hour = datetime.now().hour
        if self.alert_manager.is_quiet_hours(
            user.quiet_hours_start,
            user.quiet_hours_end,
            current_hour
        ):
            return
        
        # Проверяем уведомления включены
        if not user.notifications_enabled:
            return
        
        event = None
        coin_id = alert.coin_id
        
        # Получаем данные монеты
        data = coin_data.get(coin_id) if coin_id else None
        
        if alert.alert_type == "hype_spike":
            event = await self._check_hype_spike(alert, data, user)
        
        elif alert.alert_type == "price_change":
            event = await self._check_price_change(alert, data)
        
        elif alert.alert_type == "whale_move":
            event = await self._check_whale_move(alert)
        
        elif alert.alert_type == "trending":
            event = await self._check_trending(alert)
        
        # Отправляем уведомление
        if event:
            await self._send_alert(user, event, alert_repo, alert)
    
    async def _check_hype_spike(
        self,
        alert: Alert,
        coin_data: Optional[dict],
        user: User
    ):
        """Проверка скачка хайпа"""
        if not coin_data:
            return None
        
        coin_id = alert.coin_id
        coin_name = coin_data.get("name", "")
        coin_symbol = coin_data.get("symbol", "")
        
        # Получаем предыдущее значение
        prev = self._previous_values.get(coin_id, {})
        prev_hype = prev.get("hype_score", 0)
        
        # Рассчитываем текущий хайп (упрощённо)
        market_data = coin_data.get("market_data", {})
        price_change = market_data.get("price_change_percentage_24h", 0) or 0
        
        # Простой расчёт хайпа на основе цены
        current_hype = min(100, abs(price_change) * 2)
        
        # Сохраняем текущее значение
        self._previous_values[coin_id] = {"hype_score": current_hype}
        
        # Получаем порог из условий алерта или настроек пользователя
        threshold = (alert.condition or {}).get("threshold", user.alert_threshold)
        
        # Проверяем условие
        if current_hype >= threshold and current_hype > prev_hype + 10:
            return self.alert_manager.check_hype_spike(
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_hype=int(current_hype),
                previous_hype=int(prev_hype),
                threshold=10
            )
        
        return None
    
    async def _check_price_change(self, alert: Alert, coin_data: Optional[dict]):
        """Проверка изменения цены"""
        if not coin_data:
            return None
        
        coin_id = alert.coin_id
        market_data = coin_data.get("market_data", {})
        current_price = market_data.get("current_price", {}).get("usd", 0)
        
        prev = self._previous_values.get(coin_id, {})
        prev_price = prev.get("price", current_price)
        
        self._previous_values[coin_id] = {
            **self._previous_values.get(coin_id, {}),
            "price": current_price
        }
        
        threshold = (alert.condition or {}).get("threshold", 10)
        
        return self.alert_manager.check_price_change(
            coin_id=coin_id,
            coin_symbol=coin_data.get("symbol", ""),
            coin_name=coin_data.get("name", ""),
            current_price=current_price,
            previous_price=prev_price,
            threshold_percent=threshold
        )
    
    async def _check_whale_move(self, alert: Alert):
        """Проверка движения китов"""
        coin_id = alert.coin_id
        
        transactions = await self.whale_tracker.get_recent_whale_transactions(
            coin_symbol=coin_id.upper() if coin_id else None,
            min_usd=1_000_000,
            limit=5
        )
        
        for tx in transactions:
            # Проверяем только новые транзакции
            tx_time = tx.get("timestamp", 0)
            last_check = self._previous_values.get(f"whale_{coin_id}", {}).get("last_tx", 0)
            
            if tx_time > last_check:
                self._previous_values[f"whale_{coin_id}"] = {"last_tx": tx_time}
                
                return self.alert_manager.check_whale_activity(
                    coin_id=coin_id or "crypto",
                    coin_symbol=tx.get("symbol", "?"),
                    coin_name=coin_id or "Cryptocurrency",
                    transaction_type=tx.get("type", "transfer"),
                    amount_usd=tx.get("amount_usd", 0)
                )
        
        return None
    
    async def _check_trending(self, alert: Alert):
        """Проверка входа в тренды"""
        coin_id = alert.coin_id
        
        trending = await self.coingecko.get_trending()
        trending_ids = [t.get("item", {}).get("id") for t in trending]
        
        is_trending = coin_id in trending_ids
        was_trending = self._previous_values.get(f"trending_{coin_id}", {}).get("is_trending", False)
        
        self._previous_values[f"trending_{coin_id}"] = {"is_trending": is_trending}
        
        if is_trending and not was_trending:
            # Получаем данные о монете
            coin_data = await self.coingecko.get_coin_data(coin_id)
            
            return self.alert_manager.check_trending(
                coin_id=coin_id,
                coin_symbol=coin_data.get("symbol", "") if coin_data else "",
                coin_name=coin_data.get("name", "") if coin_data else coin_id,
                is_trending=True,
                was_trending=False
            )
        
        return None
    
    async def _send_alert(
        self,
        user: User,
        event,
        alert_repo: AlertRepository,
        alert: Alert
    ):
        """Отправка алерта пользователю"""
        try:
            message = self.alert_manager.format_alert_message(event)
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            
            # Отмечаем срабатывание
            await alert_repo.mark_triggered(alert)
            
            logger.info(f"✅ Alert sent to user {user.telegram_id}")
            
        except TelegramError as e:
            logger.error(f"❌ Failed to send alert to {user.telegram_id}: {e}")