"""
Reddit анализатор
"""
import asyncpraw
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    CRYPTO_SUBREDDITS
)


class RedditAnalyzer:
    """Анализ упоминаний на Reddit"""
    
    def __init__(self):
        self.reddit = None
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента"""
        if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            self.reddit = asyncpraw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT
            )
    
    async def close(self):
        """Закрытие соединения"""
        if self.reddit:
            await self.reddit.close()
    
    async def count_mentions(
        self,
        coin_name: str,
        symbol: str,
        days: int = 7
    ) -> dict:
        """
        Подсчёт упоминаний монеты
        
        Returns:
            {
                "total": int,
                "by_day": {"2024-01-15": 5, ...},
                "by_subreddit": {"cryptocurrency": 10, ...},
                "top_posts": [...],
                "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
            }
        """
        if not self.reddit:
            return self._empty_result()
        
        result = {
            "total": 0,
            "by_day": {},
            "by_subreddit": {},
            "top_posts": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }
        
        # Поисковые запросы
        queries = [
            coin_name.lower(),
            f"${symbol.upper()}",
            symbol.upper()
        ]
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        seen_posts = set()
        
        for subreddit_name in CRYPTO_SUBREDDITS:
            try:
                subreddit = await self.reddit.subreddit(subreddit_name)
                
                for query in queries:
                    async for post in subreddit.search(
                        query,
                        time_filter="week",
                        limit=100
                    ):
                        # Пропускаем дубликаты
                        if post.id in seen_posts:
                            continue
                        seen_posts.add(post.id)
                        
                        post_date = datetime.fromtimestamp(post.created_utc)
                        if post_date < cutoff:
                            continue
                        
                        result["total"] += 1
                        
                        # По дням
                        day_key = post_date.strftime("%Y-%m-%d")
                        result["by_day"][day_key] = result["by_day"].get(day_key, 0) + 1
                        
                        # По сабреддитам
                        result["by_subreddit"][subreddit_name] = \
                            result["by_subreddit"].get(subreddit_name, 0) + 1
                        
                        # Топ посты (по score)
                        if post.score > 50 and len(result["top_posts"]) < 5:
                            result["top_posts"].append({
                                "title": post.title[:150],
                                "score": post.score,
                                "comments": post.num_comments,
                                "url": f"https://reddit.com{post.permalink}",
                                "created": post_date.isoformat(),
                                "subreddit": subreddit_name
                            })
                        
                        # Анализ sentiment
                        sentiment = self._analyze_sentiment(post.title)
                        result["sentiment"][sentiment] += 1
                
                # Небольшая пауза между сабреддитами
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Reddit error for r/{subreddit_name}: {e}")
                continue
        
        # Сортируем топ посты
        result["top_posts"] = sorted(
            result["top_posts"],
            key=lambda x: x["score"],
            reverse=True
        )[:5]
        
        return result
    
    async def get_mention_velocity(self, by_day: dict) -> float:
        """
        Скорость роста упоминаний (%)
        Сравнивает последние 2 дня с предыдущими 2
        """
        if len(by_day) < 3:
            return 0.0
        
        sorted_days = sorted(by_day.items())
        
        if len(sorted_days) >= 4:
            recent = sum(v for k, v in sorted_days[-2:])
            previous = sum(v for k, v in sorted_days[-4:-2])
            
            if previous > 0:
                return ((recent - previous) / previous) * 100
        
        return 0.0
    
    async def get_hot_posts(self, subreddit: str = "cryptocurrency", limit: int = 10) -> list:
        """Горячие посты из сабреддита"""
        if not self.reddit:
            return []
        
        posts = []
        try:
            sub = await self.reddit.subreddit(subreddit)
            async for post in sub.hot(limit=limit):
                posts.append({
                    "title": post.title,
                    "score": post.score,
                    "comments": post.num_comments,
                    "url": f"https://reddit.com{post.permalink}",
                    "created": datetime.fromtimestamp(post.created_utc).isoformat()
                })
        except Exception as e:
            print(f"Reddit hot posts error: {e}")
        
        return posts
    
    async def get_trending_coins_from_reddit(self) -> list[dict]:
        """Определить трендовые монеты по Reddit"""
        if not self.reddit:
            return []
        
        coin_mentions = {}
        
        try:
            for subreddit_name in ["cryptocurrency", "cryptomoonshots"]:
                subreddit = await self.reddit.subreddit(subreddit_name)
                
                async for post in subreddit.hot(limit=100):
                    # Ищем тикеры в заголовке ($BTC, $ETH и т.д.)
                    import re
                    tickers = re.findall(r'\$([A-Z]{2,10})', post.title.upper())
                    
                    for ticker in tickers:
                        if ticker not in coin_mentions:
                            coin_mentions[ticker] = {
                                "symbol": ticker,
                                "mentions": 0,
                                "total_score": 0
                            }
                        coin_mentions[ticker]["mentions"] += 1
                        coin_mentions[ticker]["total_score"] += post.score
                
                await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"Reddit trending error: {e}")
        
        # Сортируем по упоминаниям
        sorted_coins = sorted(
            coin_mentions.values(),
            key=lambda x: x["mentions"],
            reverse=True
        )
        
        return sorted_coins[:20]
    
    def _analyze_sentiment(self, text: str) -> str:
        """Простой анализ sentiment по ключевым словам"""
        text_lower = text.lower()
        
        positive_words = [
            "moon", "bullish", "pump", "gem", "100x", "rocket", "buy",
            "amazing", "great", "best", "profit", "gains", "lambo",
            "undervalued", "potential", "long", "hodl", "diamond"
        ]
        
        negative_words = [
            "scam", "rug", "dump", "bearish", "dead", "avoid", "warning",
            "fake", "fraud", "ponzi", "crash", "sell", "short", "rekt",
            "overvalued", "bubble", "exit"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
    
    def _empty_result(self) -> dict:
        """Пустой результат при отсутствии API"""
        return {
            "total": 0,
            "by_day": {},
            "by_subreddit": {},
            "top_posts": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }