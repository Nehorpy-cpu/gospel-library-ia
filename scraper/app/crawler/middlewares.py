import random

from app.core.config import get_settings


class RandomUserAgentMiddleware:
    def __init__(self) -> None:
        self.user_agents = get_settings().crawler_user_agent_pool

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(self.user_agents)
        request.headers.setdefault("Accept-Language", "es,en-US;q=0.8,en;q=0.6,pt;q=0.5")
