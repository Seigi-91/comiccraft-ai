import asyncio

from chromadb import Collection, HttpClient

from app.core.config import settings


class ChromaClient:
    def __init__(self):
        auth_creds = settings.CHROMA_DB_AUTH_CREDENTIALS
        if auth_creds:
            auth_creds = tuple(auth_creds.split(":"))

        self.client = HttpClient(
            host=settings.CHROMA_DB_URL.replace("http://", "").replace(":8001", ""),
            port=8001,
            auth=auth_creds,
        )
        self.character_collection = self._get_or_create_collection("characters")
        self.event_collection = self._get_or_create_collection("events")

    def _get_or_create_collection(self, name: str) -> Collection:
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(name)

    async def add_character(self, character_id: str, character_data: dict):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._add_character_sync, character_id, character_data)

    def _add_character_sync(self, character_id: str, character_data: dict):
        self.character_collection.add(
            ids=[character_id],
            documents=[str(character_data)],
            metadatas=[character_data],
        )

    async def search_characters(self, query: str, n_results: int = 5) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_characters_sync, query, n_results)

    def _search_characters_sync(self, query: str, n_results: int = 5) -> list:
        results = self.character_collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        return results.get("metadatas", [[]])[0]

    async def add_event(self, event_id: str, event_data: dict):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._add_event_sync, event_id, event_data)

    def _add_event_sync(self, event_id: str, event_data: dict):
        self.event_collection.add(
            ids=[event_id],
            documents=[str(event_data)],
            metadatas=[event_data],
        )

    async def search_events(self, query: str, n_results: int = 10) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_events_sync, query, n_results)

    def _search_events_sync(self, query: str, n_results: int = 10) -> list:
        results = self.event_collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        return results.get("metadatas", [[]])[0]
