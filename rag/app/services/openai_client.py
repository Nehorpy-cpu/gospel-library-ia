from collections.abc import AsyncIterator

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class OpenAIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    @retry(retry=retry_if_exception(lambda exc: not _is_insufficient_quota(exc)), stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=60), reraise=True)
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
            dimensions=self.settings.openai_embedding_dimensions,
        )
        return [item.embedding for item in response.data]

    async def complete(self, messages: list[dict], temperature: float = 0.1) -> str:
        response = await self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def stream_complete(self, messages: list[dict], temperature: float = 0.1) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta


def _is_insufficient_quota(exc: BaseException) -> bool:
    value = str(exc).lower()
    return "insufficient_quota" in value
