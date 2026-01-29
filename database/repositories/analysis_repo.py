"""
Репозиторий истории анализов
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import AnalysisHistory, User


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(
        self,
        user: User,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        hype_score: int,
        price: float = None,
        market_cap_rank: int = None,
        reddit_mentions: int = 0,
        twitter_mentions: int = 0,
        sentiment_score: float = None
    ) -> AnalysisHistory:
        """Сохранить анализ"""
        analysis = AnalysisHistory(
            user_id=user.id,
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            coin_name=coin_name,
            hype_score=hype_score,
            price_at_analysis=price,
            market_cap_rank=market_cap_rank,
            reddit_mentions=reddit_mentions,
            twitter_mentions=twitter_mentions,
            sentiment_score=sentiment_score
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis
    
    async def get_user_history(
        self, 
        user: User, 
        limit: int = 20
    ) -> list[AnalysisHistory]:
        """История анализов пользователя"""
        result = await self.session.execute(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user.id)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_coin_history(
        self, 
        coin_id: str, 
        days: int = 7
    ) -> list[AnalysisHistory]:
        """История хайпа монеты"""
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(AnalysisHistory)
            .where(
                AnalysisHistory.coin_id == coin_id,
                AnalysisHistory.created_at >= since
            )
            .order_by(AnalysisHistory.created_at.asc())
        )
        return result.scalars().all()
    
    async def get_today_count(self, user: User) -> int:
        """Количество анализов за сегодня"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(AnalysisHistory.id))
            .where(
                AnalysisHistory.user_id == user.id,
                AnalysisHistory.created_at >= today
            )
        )
        return result.scalar() or 0
    
    async def set_prediction(
        self, 
        analysis_id: int, 
        prediction: str
    ):
        """Установить прогноз пользователя"""
        result = await self.session.execute(
            select(AnalysisHistory).where(AnalysisHistory.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()
        if analysis:
            analysis.user_prediction = prediction
            await self.session.commit()
    
    async def get_pending_predictions(self) -> list[AnalysisHistory]:
        """Анализы с непроверенными прогнозами"""
        # Проверяем прогнозы сделанные 24+ часа назад
        cutoff = datetime.utcnow() - timedelta(hours=24)
        result = await self.session.execute(
            select(AnalysisHistory).where(
                AnalysisHistory.user_prediction.isnot(None),
                AnalysisHistory.prediction_checked == False,
                AnalysisHistory.created_at <= cutoff
            )
        )
        return result.scalars().all()
    
    async def get_most_analyzed(self, days: int = 7, limit: int = 10) -> list[dict]:
        """Самые анализируемые монеты"""
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(
                AnalysisHistory.coin_id,
                AnalysisHistory.coin_symbol,
                AnalysisHistory.coin_name,
                func.count(AnalysisHistory.id).label('count'),
                func.avg(AnalysisHistory.hype_score).label('avg_hype')
            )
            .where(AnalysisHistory.created_at >= since)
            .group_by(
                AnalysisHistory.coin_id,
                AnalysisHistory.coin_symbol,
                AnalysisHistory.coin_name
            )
            .order_by(func.count(AnalysisHistory.id).desc())
            .limit(limit)
        )
        return [
            {
                "coin_id": row.coin_id,
                "symbol": row.coin_symbol,
                "name": row.coin_name,
                "count": row.count,
                "avg_hype": round(row.avg_hype or 0)
            }
            for row in result.fetchall()
        ]