from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from app.tools.llm_client import LLMClient, VisionLLMClient


class BaseAgent(ABC):
    def __init__(self, model: Union[str, None] = None, temperature: float = 0.7):
        self.system_prompt = ""
        self.model = model
        self.temperature = temperature
        self.llm_client = None
        self._init_llm_client()

    def _init_llm_client(self):
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass

    def format_prompt(self, template: str, **kwargs) -> str:
        return template.format(**kwargs)


class TextAgent(BaseAgent):
    def _init_llm_client(self):
        self.llm_client = LLMClient(model=self.model, temperature=self.temperature)

    async def generate(self, prompt: str) -> str:
        if not self.llm_client:
            return "LLM client not configured"
        return await self.llm_client.generate(prompt)

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.llm_client:
            return {"error": "LLM client not configured"}
        return await self.llm_client.generate_json(prompt)


class VisionAgent(BaseAgent):
    def _init_llm_client(self):
        self.llm_client = VisionLLMClient(model=self.model, temperature=self.temperature)

    async def review_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        if not self.llm_client:
            return {"error": "Vision LLM client not configured"}
        return await self.llm_client.review_image(image_url, prompt)
