"""
Twitter/X анализатор
"""
import tweepy
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_BEARER_TOKEN
)


class TwitterAnalyzer:
    """Анализ упоминаний в Twitter/X"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента"""
        if TWITTER_BEARER_TOKEN:
            self.client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=True
            )
    
    async def count_mentions(
        self,
        coin_name: str,
        symbol: str,
        days: int = 7
    ) -> dict:
        """
        Подсчёт упоминаний монеты в Twitter
        
        Returns:
            {
                "total": int,
                "by_day": {"2024-01-15": 5, ...},
                "top_tweets": [...],
                "influencer_mentions": [...],
                "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
            }
        """
        if not self.client:
            return self._empty_result()
        
        result = {
            "total": 0,
            "by_day": {},
            "top_tweets": [],
            "influencer_mentions": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }
        
        # Поисковый запрос
        query = f"({coin_name} OR ${symbol.upper()}) crypto -is:retweet lang:en"
        
        try:
            # Twitter API v2
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=min(days, 7))  # Бесплатный лимит 7 дней
            
            # Выполняем в отдельном потоке (tweepy не полностью async)
            tweets = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.search_recent_tweets(
                    query=query,
                    max_results=100,
                    start_time=start_time.isoformat("T") + "Z",
                    end_time=end_time.isoformat("T") + "Z",
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    user_fields=["username", "public_metrics"],
                    expansions=["author_id"]
                )
            )
            
            if not tweets.data:
                return result
            
            # Создаём словарь пользователей
            users_dict = {}
            if tweets.includes and "users" in tweets.includes:
                for user in tweets.includes["users"]:
                    users_dict[user.id] = user
            
            for tweet in tweets.data:
                result["total"] += 1
                
                # По дням
                day_key = tweet.created_at.strftime("%Y-%m-%d")
                result["by_day"][day_key] = result["by_day"].get(day_key, 0) + 1
                
                # Метрики твита
                metrics = tweet.public_metrics or {}
                engagement = (
                    metrics.get("like_count", 0) +
                    metrics.get("retweet_count", 0) * 2 +
                    metrics.get("reply_count", 0)
                )
                
                # Топ твиты
                if engagement > 50 and len(result["top_tweets"]) < 5:
                    author = users_dict.get(tweet.author_id)
                    result["top_tweets"].append({
                        "text": tweet.text[:200],
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "author": author.username if author else "unknown",
                        "url": f"https://twitter.com/x/status/{tweet.id}",
                        "created": tweet.created_at.isoformat()
                    })
                
                # Инфлюенсеры (>10k подписчиков)
                author = users_dict.get(tweet.author_id)
                if author:
                    author_metrics = author.public_metrics or {}
                    followers = author_metrics.get("followers_count", 0)
                    
                    if followers > 10000 and len(result["influencer_mentions"]) < 10:
                        result["influencer_mentions"].append({
                            "username": author.username,
                            "followers": followers,
                            "tweet": tweet.text[:100],
                            "url": f"https://twitter.com/x/status/{tweet.id}"
                        })
                
                # Sentiment
                sentiment = self._analyze_sentiment(tweet.text)
                result["sentiment"][sentiment] += 1
            
            # Сортируем
            result["top_tweets"] = sorted(
                result["top_tweets"],
                key=lambda x: x["likes"] + x["retweets"] * 2,
                reverse=True
            )[:5]
            
            result["influencer_mentions"] = sorted(
                result["influencer_mentions"],
                key=lambda x: x["followers"],
                reverse=True
            )[:5]
            
        except Exception as e:
            print(f"Twitter API error: {e}")
        
        return result
    
    async def get_mention_velocity(self, by_day: dict) -> float:
        """Скорость роста упоминаний"""
        if len(by_day) < 3:
            return 0.0
        
        sorted_days = sorted(by_day.items())
        
        if len(sorted_days) >= 4:
            recent = sum(v for k, v in sorted_days[-2:])
            previous = sum(v for k, v in sorted_days[-4:-2])
            
            if previous > 0:
                return ((recent - previous) / previous) * 100
        
        return 0.0
    
    async def get_trending_crypto(self) -> list[dict]:
        """Трендовые крипто-темы в Twitter"""
        if not self.client:
            return []
        
        # К сожалению, trends API требует Premium
        # Используем поиск по популярным хештегам
        crypto_hashtags = [
            "#Bitcoin", "#Ethereum", "#Crypto", "#DeFi",
            "#NFT", "#Altcoin", "#BTC", "#ETH"
        ]
        
        results = []
        
        for hashtag in crypto_hashtags[:3]:  # Лимитируем запросы
            try:
                tweets = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda h=hashtag: self.client.search_recent_tweets(
                        query=f"{h} -is:retweet",
                        max_results=50,
                        tweet_fields=["public_metrics"]
                    )
                )
                
                if tweets.data:
                    total_engagement = sum(
                        (t.public_metrics or {}).get("like_count", 0)
                        for t in tweets.data
                    )
                    results.append({
                        "hashtag": hashtag,
                        "tweets": len(tweets.data),
                        "engagement": total_engagement
                    })
                
                await asyncio.sleep(1)  # Rate limit
                
            except Exception as e:
                print(f"Twitter trending error: {e}")
        
        return sorted(results, key=lambda x: x["engagement"], reverse=True)
    
    async def get_influencer_sentiment(self, coin_symbol: str) -> dict:
        """
        Анализ мнений крупных крипто-инфлюенсеров
        """
        if not self.client:
            return {"bullish": 0, "bearish": 0, "neutral": 0, "influencers": []}
        
        # Список известных крипто-инфлюенсеров
        influencers = [
            "VitalikButerin", "caborek", "elikistein", 
            "CryptoCapo_", "CryptoCred", "loomdart"
        ]
        
        result = {
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "influencers": []
        }
        
        for username in influencers[:5]:
            try:
                # Получаем последние твиты пользователя
                user = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda u=username: self.client.get_user(username=u)
                )
                
                if not user.data:
                    continue
                
                tweets = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda uid=user.data.id: self.client.get_users_tweets(
                        uid,
                        max_results=20,
                        tweet_fields=["created_at"]
                    )
                )
                
                if not tweets.data:
                    continue
                
                # Ищем упоминания монеты
                for tweet in tweets.data:
                    if coin_symbol.upper() in tweet.text.upper():
                        sentiment = self._analyze_sentiment(tweet.text)
                        
                        if sentiment == "positive":
                            result["bullish"] += 1
                        elif sentiment == "negative":
                            result["bearish"] += 1
                        else:
                            result["neutral"] += 1
                        
                        result["influencers"].append({
                            "username": username,
                            "sentiment": sentiment,
                            "tweet": tweet.text[:100]
                        })
                        break
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Influencer check error for {username}: {e}")
        
        return result
    
    def _analyze_sentiment(self, text: str) -> str:
        """Анализ sentiment твита"""
        text_lower = text.lower()
        
        bullish_words = [
            "moon", "bullish", "buy", "long", "pump", "breakout",
            "ath", "rocket", "gem", "undervalued", "accumulate",
            "green", "profit", "gains", "100x", "1000x"
        ]
        
        bearish_words = [
            "dump", "bearish", "sell", "short", "crash", "scam",
            "rug", "dead", "overvalued", "bubble", "exit", "rekt",
            "red", "loss", "avoid", "warning"
        ]
        
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        if bullish_count > bearish_count:
            return "positive"
        elif bearish_count > bullish_count:
            return "negative"
        return "neutral"
    
    def _empty_result(self) -> dict:
        """Пустой результат"""
        return {
            "total": 0,
            "by_day": {},
            "top_tweets": [],
            "influencer_mentions": [],
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }