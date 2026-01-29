"""
Репозиторий алертов
"""
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Alert, User


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user: User,
        alert_type: str,
        coin_id: str = None,
        coin_symbol: str = None,
        condition: dict = None
    ) -> Alert:
        """Создать новый алерт"""
        alert = Alert(
            user_id=user.id,
            alert_type=alert_type,
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            condition=condition,
            is_active=True
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert
    
    async def get_active_by_user(self, user: User) -> list[Alert]:
        """Активные алерты пользователя"""
        result = await self.session.execute(
            select(Alert).where(
                Alert.user_id == user.id,
                Alert.is_active == True
            )
        )
        return result.scalars().all()
    
    async def get_all_active(self) -> list[Alert]:
        """Все активные алерты (для фонового чекера)"""
        result = await self.session.execute(
            select(Alert).where(Alert.is_active == True)
        )
        return result.scalars().all()
    
    async def get_by_coin(self, coin_id: str) -> list[Alert]:
        """Алерты для конкретной монеты"""
        result = await self.session.execute(
            select(Alert).where(
                Alert.coin_id == coin_id,
                Alert.is_active == True
            )
        )
        return result.scalars().all()
    
    async def deactivate(self, alert_id: int) -> bool:
        """Деактивировать алерт"""
        result = await self.session.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def mark_triggered(self, alert: Alert):
        """Отметить срабатывание"""
        alert.triggered_count += 1
        alert.last_triggered = datetime.utcnow()
        await self.session.commit()
    
    async def delete(self, alert_id: int, user_id: int) -> bool:
        """Удалить алерт"""
        result = await self.session.execute(
            select(Alert).where(
                Alert.id == alert_id,
                Alert.user_id == user_id
            )
        )
        alert = result.scalar_one_or_none()
        if alert:
            await self.session.delete(alert)
            await self.session.commit()
            return True
        return False
    
    async def count_active(self, user: User) -> int:
        """Количество активных алертов"""
        alerts = await self.get_active_by_user(user)
        return len(alerts)