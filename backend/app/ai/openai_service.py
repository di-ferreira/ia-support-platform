import json
from typing import Literal

import httpx

from app.core.config import settings

Role = Literal["system", "user", "assistant"]


class Message:
    role: Role
    content: str

    def __init__(self, role: Role, content: str):
        self.role = role
        self.content = content


class OpenAIService:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model or "gpt-4o-mini"
        self.base_url = "https://api.openai.com/v1"

    async def chat(self, messages: list[Message], temperature: float = 0.3) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": "text-embedding-3-small", "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    async def chat_json(self, messages: list[Message], temperature: float = 0.3) -> dict:
        content = await self.chat(messages, temperature)
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
