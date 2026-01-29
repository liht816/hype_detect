"""
Отслеживание китов (крупных транзакций)
"""
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional
from config import ETHERSCAN_API_KEY


class WhaleTracker:
    """Отслеживание крупных транзакций"""
    
    # Известные кошельки бирж
    EXCHANGE_WALLETS = {
        "binance": [
            "0x28c6c06298d514db089934071355e5743bf21d60",
            "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
        ],
        "coinbase": [
            "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
            "0x503828976d22510aad0201ac7ec88293211d23da",
        ],
        "kraken": [
            "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
        ],
    }
    
    # Минимальные суммы для "кита"
    WHALE_THRESHOLDS = {
        "BTC": 100,      # 100 BTC
        "ETH": 1000,     # 1000 ETH
        "USDT": 1000000, # $1M
        "default": 500000  # $500k в USD
    }
    
    def __init__(self):
        self.etherscan_key = ETHERSCAN_API_KEY
    
    async def get_recent_whale_transactions(
        self,
        coin_symbol: str = None,
        min_usd: float = 1000000,
        limit: int = 20
    ) -> list[dict]:
        """
        Получить недавние транзакции китов
        
        Returns:
            [{
                "hash": "0x...",
                "from": "0x...",
                "to": "0x...",
                "amount": 1000.0,
                "amount_usd": 3000000.0,
                "symbol": "ETH",
                "type": "buy" | "sell" | "transfer",
                "timestamp": 1234567890,
                "from_label": "Binance" | None,
                "to_label": "Unknown Whale" | None
            }, ...]
        """
        # Для ETH используем Etherscan
        if coin_symbol in [None, "ETH", "ETHEREUM"]:
            return await self._get_eth_whale_txs(min_usd, limit)
        
        # Для других монет нужны другие API (Blockchain.com для BTC и т.д.)
        return []
    
    async def _get_eth_whale_txs(self, min_usd: float, limit: int) -> list[dict]:
        """Получить крупные ETH транзакции через Etherscan"""
        if not self.etherscan_key:
            return self._generate_mock_data()  # Мок для демо
        
        transactions = []
        
        try:
            # Получаем последние блоки
            async with aiohttp.ClientSession() as session:
                # Получаем текущую цену ETH
                async with session.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "ethereum", "vs_currencies": "usd"}
                ) as resp:
                    price_data = await resp.json()
                    eth_price = price_data.get("ethereum", {}).get("usd", 3000)
                
                # Порог в ETH
                min_eth = min_usd / eth_price
                
                # Получаем последние транзакции из топ-кошельков
                for exchange, wallets in self.EXCHANGE_WALLETS.items():
                    for wallet in wallets[:1]:  # По одному кошельку с биржи
                        try:
                            async with session.get(
                                "https://api.etherscan.io/api",
                                params={
                                    "module": "account",
                                    "action": "txlist",
                                    "address": wallet,
                                    "startblock": 0,
                                    "endblock": 99999999,
                                    "page": 1,
                                    "offset": 50,
                                    "sort": "desc",
                                    "apikey": self.etherscan_key
                                }
                            ) as resp:
                                data = await resp.json()
                                
                                if data.get("status") == "1":
                                    for tx in data.get("result", []):
                                        value_eth = int(tx.get("value", 0)) / 1e18
                                        
                                        if value_eth >= min_eth:
                                            value_usd = value_eth * eth_price
                                            
                                            # Определяем тип транзакции
                                            from_addr = tx.get("from", "").lower()
                                            to_addr = tx.get("to", "").lower()
                                            
                                            if from_addr == wallet.lower():
                                                tx_type = "sell"  # С биржи
                                            else:
                                                tx_type = "buy"   # На биржу
                                            
                                            transactions.append({
                                                "hash": tx.get("hash"),
                                                "from": from_addr,
                                                "to": to_addr,
                                                "amount": round(value_eth, 4),
                                                "amount_usd": round(value_usd, 2),
                                                "symbol": "ETH",
                                                "type": tx_type,
                                                "timestamp": int(tx.get("timeStamp", 0)),
                                                "from_label": exchange.title() if from_addr == wallet.lower() else None,
                                                "to_label": exchange.title() if to_addr == wallet.lower() else None,
                                            })
                        except Exception as e:
                            print(f"Etherscan error for {wallet}: {e}")
                        
                        await asyncio.sleep(0.2)  # Rate limit
        
        except Exception as e:
            print(f"Whale tracker error: {e}")
        
        # Сортируем по времени
        transactions = sorted(
            transactions,
            key=lambda x: x["timestamp"],
            reverse=True
        )
        
        return transactions[:limit]
    
    async def get_whale_activity_score(self, coin_id: str) -> dict:
        """
        Оценка активности китов для монеты
        
        Returns:
            {
                "score": 0-100,
                "buy_pressure": float,
                "sell_pressure": float,
                "net_flow": float,
                "large_txs_24h": int,
                "interpretation": str
            }
        """
        txs = await self.get_recent_whale_transactions(
            coin_symbol=coin_id.upper(),
            min_usd=500000,
            limit=100
        )
        
        if not txs:
            return {
                "score": 50,
                "buy_pressure": 0,
                "sell_pressure": 0,
                "net_flow": 0,
                "large_txs_24h": 0,
                "interpretation": "Недостаточно данных"
            }
        
        # Считаем buy/sell pressure
        now = datetime.now().timestamp()
        day_ago = now - 86400
        
        buys = [tx for tx in txs if tx["type"] == "buy" and tx["timestamp"] > day_ago]
        sells = [tx for tx in txs if tx["type"] == "sell" and tx["timestamp"] > day_ago]
        
        buy_volume = sum(tx["amount_usd"] for tx in buys)
        sell_volume = sum(tx["amount_usd"] for tx in sells)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            buy_pressure = buy_volume / total_volume
            sell_pressure = sell_volume / total_volume
        else:
            buy_pressure = 0.5
            sell_pressure = 0.5
        
        net_flow = buy_volume - sell_volume
        
        # Score: >50 = bullish, <50 = bearish
        score = int(50 + (buy_pressure - 0.5) * 100)
        score = max(0, min(100, score))
        
        # Интерпретация
        if score >= 70:
            interpretation = "🐋 Киты активно покупают — бычий сигнал"
        elif score >= 55:
            interpretation = "📈 Небольшое давление покупателей"
        elif score <= 30:
            interpretation = "⚠️ Киты сбрасывают — медвежий сигнал"
        elif score <= 45:
            interpretation = "📉 Небольшое давление продавцов"
        else:
            interpretation = "➡️ Баланс между покупками и продажами"
        
        return {
            "score": score,
            "buy_pressure": round(buy_pressure, 2),
            "sell_pressure": round(sell_pressure, 2),
            "net_flow": round(net_flow, 2),
            "large_txs_24h": len(buys) + len(sells),
            "interpretation": interpretation
        }
    
    async def track_wallet(self, address: str) -> dict:
        """Отслеживание конкретного кошелька"""
        if not self.etherscan_key:
            return {"error": "API key not configured"}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Баланс
                async with session.get(
                    "https://api.etherscan.io/api",
                    params={
                        "module": "account",
                        "action": "balance",
                        "address": address,
                        "tag": "latest",
                        "apikey": self.etherscan_key
                    }
                ) as resp:
                    data = await resp.json()
                    balance = int(data.get("result", 0)) / 1e18
                
                # Последние транзакции
                async with session.get(
                    "https://api.etherscan.io/api",
                    params={
                        "module": "account",
                        "action": "txlist",
                        "address": address,
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": 1,
                        "offset": 10,
                        "sort": "desc",
                        "apikey": self.etherscan_key
                    }
                ) as resp:
                    tx_data = await resp.json()
                    transactions = tx_data.get("result", [])
                
                return {
                    "address": address,
                    "balance_eth": round(balance, 4),
                    "recent_transactions": len(transactions),
                    "last_activity": transactions[0].get("timeStamp") if transactions else None
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_mock_data(self) -> list[dict]:
        """Мок-данные для демонстрации"""
        import random
        
        mock_txs = []
        now = datetime.now().timestamp()
        
        for i in range(10):
            tx_type = random.choice(["buy", "sell", "transfer"])
            amount = random.uniform(500, 5000)
            
            mock_txs.append({
                "hash": f"0x{'a' * 64}",
                "from": f"0x{'b' * 40}",
                "to": f"0x{'c' * 40}",
                "amount": round(amount, 4),
                "amount_usd": round(amount * 3200, 2),
                "symbol": "ETH",
                "type": tx_type,
                "timestamp": int(now - i * 3600),
                "from_label": random.choice(["Binance", "Unknown Whale", None]),
                "to_label": random.choice(["Coinbase", "Unknown", None]),
            })
        
        return mock_txs