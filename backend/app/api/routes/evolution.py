import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_perfil
from app.core.config import settings
from app.schemas.evolution import (
    InstanceCreate,
    SendTextRequest,
    WebhookConfig,
)
from app.services.evolution_service import EvolutionAuthError, EvolutionService

router = APIRouter(
    prefix="/evolution",
    tags=["Evolution API"],
    dependencies=[Depends(require_perfil("admin"))],
)


logger = logging.getLogger(__name__)


def get_evolution_service() -> EvolutionService:
    return EvolutionService()


@router.post("/instance")
async def criar_instancia(
    body: InstanceCreate = InstanceCreate(),
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.criar_instancia(body.instanceName)
    except EvolutionAuthError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credencial da Evolution recusada (verifique EVOLUTION_API_KEY)",
        )
    except Exception as e:
        logger.warning("Erro ao criar instância na Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
        )


@router.get("/instance/qrcode/{instance_name}")
async def obter_qrcode(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.obter_qrcode(instance_name)
    except Exception as e:
        logger.warning("Erro ao obter QR code da Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
        )


@router.get("/instance/status/{instance_name}")
async def get_instance_status(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.get_status(instance_name)
    except Exception as e:
        logger.warning("Erro ao obter status da Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
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
        logger.warning("Erro ao configurar webhook na Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
        )


@router.post("/instance/webhook/default/{instance_name}")
async def configurar_webhook_default(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    # URL padrão configurável via EVOLUTION_DEFAULT_WEBHOOK_URL (spec 06).
    webhook_url = settings.evolution_default_webhook_url
    try:
        return await service.configurar_webhook(instance_name, webhook_url)
    except Exception as e:
        logger.warning("Erro ao configurar webhook padrão na Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
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
        logger.warning("Erro ao enviar mensagem na Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
        )


@router.post("/instance/disconnect/{instance_name}")
async def desconectar(
    instance_name: str,
    service: EvolutionService = Depends(get_evolution_service),
):
    try:
        return await service.desconectar(instance_name)
    except Exception as e:
        logger.warning("Erro ao desconectar na Evolution API: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a Evolution API",
        )
