from appwrite.client import Client

from app.core.config import settings


def build_appwrite_client() -> Client:
    client = Client()
    client.set_endpoint(settings.appwrite_endpoint)
    client.set_project(settings.appwrite_project_id)
    client.set_key(settings.appwrite_api_key)
    return client
