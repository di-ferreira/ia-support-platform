from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_perfil
from app.core.config import settings
from app.schemas.evolution import (
    InstanceCreate,
    SendTextRequest,
    WebhookConfig,
)
from app.services.evolution_service import EvolutionService

router = APIRouter(
    prefix="/evolution",
    tags=["Evolution API"],
    dependencies=[Depends(require_perfil("admin"))],
)


def get_evolution_service() -> EvolutionService:
    return EvolutionService()


@router.post("/instance")
async def criar_instancia(
    body: InstanceCreate = InstanceCreate(),
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.criar_instancia(body.instanceName)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao criar instância na Evolution API: {e}",
        )


@router.get("/instance/qrcode/{instance_name}")
async def obter_qrcode(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.obter_qrcode_base64(instance_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao obter QR code: {e}",
        )


@router.get("/instance/status/{instance_name}")
async def get_instance_status(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.get_status(instance_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao obter status: {e}",
        )


@router.post("/instance/webhook/{instance_name}")
async def configurar_webhook(
    instance_name: str,
    body: WebhookConfig,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.configurar_webhook(
            instance_name, body.webhookUrl, body.events
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao configurar webhook: {e}",
        )


@router.post("/instance/webhook/default/{instance_name}")
async def configurar_webhook_default(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    webhook_url = "http://n8n:5678/webhook/emsoft-whatsapp"
    try:
        return await service.configurar_webhook(instance_name, webhook_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao configurar webhook padrão: {e}",
        )


@router.post("/send-text/{instance_name}")
async def enviar_texto(
    instance_name: str,
    body: SendTextRequest,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.enviar_texto(
            instance_name, body.number, body.text, body.delay
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao enviar mensagem: {e}",
        )


@router.post("/instance/disconnect/{instance_name}")
async def desconectar(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.desconectar(instance_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao desconectar: {e}",
        )
