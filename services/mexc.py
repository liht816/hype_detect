import aiohttp
from datetime import datetime, timedelta

class MexcService:
    SPOT = "https://api.mexc.com"
    FUT = "https://contract.mexc.com"

    def __init__(self):
        self._spot_symbols_cache = None
        self._spot_symbols_cache_time = None

    async def _get_json(self, url, params=None):
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, timeout=20) as r:
                r.raise_for_status()
                return await r.json()

    # ---------- SPOT ----------
    async def spot_exchange_info(self):
        # MEXC spot exchangeInfo (как у Binance)
        return await self._get_json(f"{self.SPOT}/api/v3/exchangeInfo")

    async def spot_tickers_24h(self):
        # возвращает список по всем парам
        return await self._get_json(f"{self.SPOT}/api/v3/ticker/24hr")

    async def spot_klines(self, symbol: str, interval="1h", limit=500):
        # interval: 1m,5m,15m,30m,1h,4h,1d...
        return await self._get_json(
            f"{self.SPOT}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit}
        )

    # ---------- FUTURES ----------
    async def futures_tickers(self):
        # обычно отдаёт data:[...]
        data = await self._get_json(f"{self.FUT}/api/v1/contract/ticker")
        return data.get("data") if isinstance(data, dict) else data

    def to_futures_symbol(self, spot_symbol: str) -> str:
        # BTCUSDT -> BTC_USDT
        if spot_symbol.endswith("USDT"):
            return spot_symbol.replace("USDT", "_USDT")
        return spot_symbol

    # ---------- RESOLVE ----------
    async def resolve_symbol(self, query: str, market: str = "spot") -> str | None:
        """
        query: btc / BTCUSDT / BTC/USDT
        return: BTCUSDT
        """
        q = query.strip().upper().replace("/", "").replace("-", "")
        if q.endswith("USDT"):
            return q
        # btc -> BTCUSDT
        if len(q) <= 10:
            return f"{q}USDT"
        return None