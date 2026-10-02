from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "knowledge_bases")
