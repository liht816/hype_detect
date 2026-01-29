"""
GitHub анализатор активности разработки
"""
import aiohttp
from datetime import datetime, timedelta
from typing import Optional


class GitHubAnalyzer:
    """Анализ активности проекта на GitHub"""
    
    # Известные репозитории криптопроектов
    KNOWN_REPOS = {
        "bitcoin": "bitcoin/bitcoin",
        "ethereum": "ethereum/go-ethereum",
        "solana": "solana-labs/solana",
        "cardano": "input-output-hk/cardano-node",
        "polkadot": "paritytech/polkadot",
        "polygon": "maticnetwork/bor",
        "avalanche": "ava-labs/avalanchego",
        "cosmos": "cosmos/cosmos-sdk",
        "chainlink": "smartcontractkit/chainlink",
        "uniswap": "Uniswap/v3-core",
    }
    
    def __init__(self):
        self.base_url = "https://api.github.com"
    
    async def get_repo_activity(self, coin_id: str) -> Optional[dict]:
        """
        Получить активность репозитория
        
        Returns:
            {
                "repo": str,
                "stars": int,
                "forks": int,
                "open_issues": int,
                "commits_30d": int,
                "contributors": int,
                "last_commit": datetime,
                "activity_score": int (0-100),
                "health": "active" | "moderate" | "inactive"
            }
        """
        repo = self.KNOWN_REPOS.get(coin_id.lower())
        
        if not repo:
            # Пробуем найти по имени
            repo = await self._search_repo(coin_id)
        
        if not repo:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Основная информация о репо
                async with session.get(
                    f"{self.base_url}/repos/{repo}",
                    headers={"Accept": "application/vnd.github.v3+json"}
                ) as resp:
                    if resp.status != 200:
                        return None
                    repo_data = await resp.json()
                
                # Коммиты за 30 дней
                since = (datetime.now() - timedelta(days=30)).isoformat()
                async with session.get(
                    f"{self.base_url}/repos/{repo}/commits",
                    params={"since": since, "per_page": 100},
                    headers={"Accept": "application/vnd.github.v3+json"}
                ) as resp:
                    commits_data = await resp.json() if resp.status == 200 else []
                
                # Контрибьюторы
                async with session.get(
                    f"{self.base_url}/repos/{repo}/contributors",
                    params={"per_page": 1},
                    headers={"Accept": "application/vnd.github.v3+json"}
                ) as resp:
                    # Количество из заголовка Link
                    link_header = resp.headers.get("Link", "")
                    contributors = self._parse_last_page(link_header)
                
                # Расчёт activity score
                stars = repo_data.get("stargazers_count", 0)
                forks = repo_data.get("forks_count", 0)
                commits_30d = len(commits_data) if isinstance(commits_data, list) else 0
                open_issues = repo_data.get("open_issues_count", 0)
                
                # Score формула
                activity_score = min(100, int(
                    (min(stars, 10000) / 10000 * 30) +
                    (min(commits_30d, 100) / 100 * 40) +
                    (min(forks, 5000) / 5000 * 20) +
                    (min(contributors, 100) / 100 * 10)
                ))
                
                # Health статус
                if commits_30d > 50 and activity_score > 60:
                    health = "active"
                elif commits_30d > 10 and activity_score > 30:
                    health = "moderate"
                else:
                    health = "inactive"
                
                # Последний коммит
                last_commit = None
                if commits_data and isinstance(commits_data, list):
                    last_commit_date = commits_data[0].get("commit", {}).get("committer", {}).get("date")
                    if last_commit_date:
                        last_commit = datetime.fromisoformat(last_commit_date.replace("Z", "+00:00"))
                
                return {
                    "repo": repo,
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "commits_30d": commits_30d,
                    "contributors": contributors,
                    "last_commit": last_commit.isoformat() if last_commit else None,
                    "activity_score": activity_score,
                    "health": health,
                    "url": f"https://github.com/{repo}"
                }
        
        except Exception as e:
            print(f"GitHub API error: {e}")
            return None
    
    async def _search_repo(self, query: str) -> Optional[str]:
        """Поиск репозитория по названию"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/search/repositories",
                    params={
                        "q": f"{query} crypto OR blockchain",
                        "sort": "stars",
                        "per_page": 1
                    },
                    headers={"Accept": "application/vnd.github.v3+json"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        if items:
                            return items[0].get("full_name")
        except Exception as e:
            print(f"GitHub search error: {e}")
        
        return None
    
    def _parse_last_page(self, link_header: str) -> int:
        """Парсинг количества страниц из Link header"""
        if not link_header:
            return 0
        
        try:
            import re
            match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        except:
            pass
        
        return 0
    
    async def compare_projects(self, coin_ids: list[str]) -> list[dict]:
        """
        Сравнение активности нескольких проектов
        """
        results = []
        
        for coin_id in coin_ids:
            activity = await self.get_repo_activity(coin_id)
            if activity:
                activity["coin_id"] = coin_id
                results.append(activity)
        
        return sorted(results, key=lambda x: x["activity_score"], reverse=True)
    
    def format_activity(self, data: dict) -> str:
        """Форматирование для отображения"""
        if not data:
            return "❓ Репозиторий не найден"
        
        health_emoji = {
            "active": "🟢",
            "moderate": "🟡",
            "inactive": "🔴"
        }
        
        return f"""
*GitHub активность*

{health_emoji.get(data['health'], '⚪')} Статус: {data['health'].title()}
📊 Activity Score: {data['activity_score']}/100

⭐ Stars: {data['stars']:,}
🍴 Forks: {data['forks']:,}
👥 Contributors: {data['contributors']}
📝 Commits (30d): {data['commits_30d']}

🔗 [{data['repo']}]({data['url']})
"""