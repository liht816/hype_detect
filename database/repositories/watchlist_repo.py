"""
Репозиторий списка отслеживания
"""
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import WatchlistItem, User


class WatchlistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(
        self, 
        user: User, 
        coin_id: str, 
        coin_symbol: str, 
        coin_name: str,
        price: float = None,
        hype_score: int = None
    ) -> WatchlistItem:
        """Добавить монету в watchlist"""
        item = WatchlistItem(
            user_id=user.id,
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            coin_name=coin_name,
            added_price=price,
            added_hype_score=hype_score
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item
    
    async def remove(self, user: User, coin_id: str) -> bool:
        """Удалить монету из watchlist"""
        result = await self.session.execute(
            delete(WatchlistItem).where(
                WatchlistItem.user_id == user.id,
                WatchlistItem.coin_id == coin_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_all(self, user: User) -> list[WatchlistItem]:
        """Получить весь watchlist пользователя"""
        result = await self.session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.added_at.desc())
        )
        return result.scalars().all()
    
    async def exists(self, user: User, coin_id: str) -> bool:
        """Проверить, есть ли монета в watchlist"""
        result = await self.session.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user.id,
                WatchlistItem.coin_id == coin_id
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_all_users_with_coin(self, coin_id: str) -> list[WatchlistItem]:
        """Получить всех пользователей, отслеживающих монету"""
        result = await self.session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.coin_id == coin_id)
        )
        return result.scalars().all()
    
    async def count(self, user: User) -> int:
        """Количество монет в watchlist"""
        result = await self.session.execute(
            select(WatchlistItem).where(WatchlistItem.user_id == user.id)
        )
        return len(result.scalars().all())