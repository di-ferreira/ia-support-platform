from pydantic import BaseModel


class InstanceCreate(BaseModel):
    instanceName: str = "emsoft-support"  # noqa: N815


class InstanceResponse(BaseModel):
    instance: dict | None = None
    hash: str | None = None
    status: str | None = None

    model_config = {"from_attributes": True}


class QRCodeResponse(BaseModel):
    qrcode: str | None = None
    pairing_code: str | None = None
    expires_at: int | None = None
    base64: str | None = None


class InstanceStatusResponse(BaseModel):
    instance_name: str
    state: str
    connected: bool


class WebhookConfig(BaseModel):
    webhookUrl: str  # noqa: N815
    events: list[str] = ["MESSAGES_UPSERT"]


class SendTextRequest(BaseModel):
    number: str
    text: str
    delay: int = 1200
