import json

import httpx

from app.core.config import settings
from app.ai.openai_service import Message


class OllamaService:
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "llama3.2"

    async def chat(self, messages: list[Message], temperature: float = 0.3) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "options": {"temperature": temperature},
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    async def chat_json(self, messages: list[Message], temperature: float = 0.3) -> dict:
        content = await self.chat(messages, temperature)
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]
