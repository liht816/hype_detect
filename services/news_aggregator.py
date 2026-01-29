"""
Агрегатор крипто-новостей
"""
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio
from typing import Optional


class NewsAggregator:
    """Агрегация новостей из разных источников"""
    
    # RSS фиды крипто-новостей
    RSS_FEEDS = {
        "cointelegraph": "https://cointelegraph.com/rss",
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "decrypt": "https://decrypt.co/feed",
    }
    
    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._cache_ttl = 300  # 5 минут
    
    async def get_latest_news(self, limit: int = 10) -> list[dict]:
        """
        Последние новости из всех источников
        
        Returns:
            [{
                "title": str,
                "url": str,
                "source": str,
                "published": datetime,
                "summary": str
            }, ...]
        """
        # Проверяем кэш
        if self._cache_time and (datetime.now() - self._cache_time).seconds < self._cache_ttl:
            return self._cache.get("news", [])[:limit]
        
        all_news = []
        
        for source, url in self.RSS_FEEDS.items():
            try:
                news = await self._fetch_rss(source, url)
                all_news.extend(news)
            except Exception as e:
                print(f"News fetch error for {source}: {e}")
        
        # Сортируем по дате
        all_news = sorted(
            all_news,
            key=lambda x: x.get("published", datetime.min),
            reverse=True
        )
        
        # Кэшируем
        self._cache["news"] = all_news
        self._cache_time = datetime.now()
        
        return all_news[:limit]
    
    async def _fetch_rss(self, source: str, url: str) -> list[dict]:
        """Парсинг RSS фида"""
        news = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    
                    content = await resp.text()
                    soup = BeautifulSoup(content, "lxml-xml")
                    
                    items = soup.find_all("item")[:20]
                    
                    for item in items:
                        title = item.find("title")
                        link = item.find("link")
                        pub_date = item.find("pubDate")
                        description = item.find("description")
                        
                        if title and link:
                            published = None
                            if pub_date:
                                try:
                                    published = datetime.strptime(
                                        pub_date.text.strip(),
                                        "%a, %d %b %Y %H:%M:%S %z"
                                    )
                                except:
                                    published = datetime.now()
                            
                            news.append({
                                "title": title.text.strip(),
                                "url": link.text.strip() if link.text else link.get("href", ""),
                                "source": source,
                                "published": published or datetime.now(),
                                "summary": description.text[:200].strip() if description else ""
                            })
        
        except Exception as e:
            print(f"RSS parse error for {source}: {e}")
        
        return news
    
    async def search_coin_news(
        self,
        coin_name: str,
        coin_symbol: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Поиск новостей о конкретной монете
        """
        all_news = await self.get_latest_news(100)
        
        # Фильтруем
        keywords = [
            coin_name.lower(),
            coin_symbol.lower(),
            f"${coin_symbol.upper()}"
        ]
        
        relevant = []
        for news in all_news:
            title_lower = news["title"].lower()
            summary_lower = news.get("summary", "").lower()
            
            if any(kw in title_lower or kw in summary_lower for kw in keywords):
                relevant.append(news)
        
        return relevant[:limit]
    
    async def get_sentiment_from_news(self, coin_name: str, coin_symbol: str) -> dict:
        """
        Анализ sentiment по новостям
        
        Returns:
            {
                "positive": int,
                "negative": int,
                "neutral": int,
                "overall": "bullish" | "bearish" | "neutral"
            }
        """
        news = await self.search_coin_news(coin_name, coin_symbol, limit=20)
        
        sentiment = {"positive": 0, "negative": 0, "neutral": 0}
        
        positive_words = [
            "surge", "soar", "rally", "bullish", "breakout", "ath",
            "gains", "profit", "adoption", "partnership", "launch"
        ]
        
        negative_words = [
            "crash", "drop", "plunge", "bearish", "dump", "scam",
            "hack", "fraud", "lawsuit", "ban", "warning", "loss"
        ]
        
        for item in news:
            text = (item["title"] + " " + item.get("summary", "")).lower()
            
            pos_count = sum(1 for w in positive_words if w in text)
            neg_count = sum(1 for w in negative_words if w in text)
            
            if pos_count > neg_count:
                sentiment["positive"] += 1
            elif neg_count > pos_count:
                sentiment["negative"] += 1
            else:
                sentiment["neutral"] += 1
        
        # Определяем overall
        total = sum(sentiment.values())
        if total == 0:
            overall = "neutral"
        elif sentiment["positive"] / total > 0.5:
            overall = "bullish"
        elif sentiment["negative"] / total > 0.5:
            overall = "bearish"
        else:
            overall = "neutral"
        
        return {**sentiment, "overall": overall}