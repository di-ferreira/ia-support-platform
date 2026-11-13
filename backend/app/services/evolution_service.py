import httpx

from app.core.config import settings


class EvolutionAuthError(Exception):
    """Credencial recusada pela Evolution — não confundir com instância já existente."""


class EvolutionService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.api_key = settings.evolution_api_key
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["apiKey"] = self.api_key
        self._transport = transport

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(
            timeout=30, transport=self._transport
        ) as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def criar_instancia(self, instance_name: str | None = None) -> dict:
        instance_name = instance_name or settings.evolution_instance_name
        try:
            return await self._request(
                "POST", "/instance/create",
                json={"instanceName": instance_name, "integration": "WHATSAPP-BAILEYS"},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # 403 ambíguo: pode ser conflito de criação (instância já
                # existe) ou credencial recusada. Consulta o status para
                # distinguir os dois casos.
                try:
                    status_atual = await self.get_status(instance_name)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        # Sem instância: o 403 era da credencial, não de
                        # conflito de criação.
                        raise EvolutionAuthError(
                            "Evolution recusou a credencial (403) e a instância não existe"
                        ) from exc
                    # Erro inesperado do get_status: propaga como erro de
                    # autenticação sem mascarar a causa original.
                    raise EvolutionAuthError(
                        "Falha ao verificar a instância após 403 na criação"
                    ) from exc
                # Instância já existe: o 403 era só conflito de criação.
                return {
                    "instance": {"instanceName": instance_name},
                    "hash": None,
                    "ja_existia": True,
                    "status": status_atual,
                }
            raise

    async def obter_qrcode(self, instance_name: str) -> dict:
        return await self._request(
            "GET", f"/instance/connect/{instance_name}",
        )

    async def obter_qrcode_base64(self, instance_name: str) -> dict:
        return await self._request(
            "GET", f"/instance/qrcode/{instance_name}",
        )

    async def get_status(self, instance_name: str) -> dict:
        return await self._request(
            "GET", f"/instance/connectionState/{instance_name}",
        )

    async def configurar_webhook(
        self, instance_name: str, webhook_url: str,
        events: list[str] | None = None,
    ) -> dict:
        if events is None:
            events = ["MESSAGES_UPSERT"]
        return await self._request(
            "POST", f"/webhook/set/{instance_name}",
            json={"webhook": {"url": webhook_url, "enabled": True, "events": events}},
        )

    async def desconectar(self, instance_name: str) -> dict:
        return await self._request(
            "DELETE", f"/instance/logout/{instance_name}",
        )

    async def deletar_instancia(self, instance_name: str) -> dict:
        return await self._request(
            "DELETE", f"/instance/delete/{instance_name}",
        )

    async def enviar_texto(
        self, instance_name: str, number: str, text: str, delay: int = 1200
    ) -> dict:
        return await self._request(
            "POST", f"/message/sendText/{instance_name}",
            json={"number": number, "text": text, "delay": delay},
        )
