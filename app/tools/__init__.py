"""Tool adapters are loaded on demand; optional SD/Chroma/MinIO are not startup dependencies."""

import importlib


def __getattr__(name):
    modules = {
        "ChromaClient": "chroma_client",
        "LLMClient": "llm_client",
        "VisionLLMClient": "llm_client",
        "ImageGeneratorClient": "image_gen",
        "SDClient": "sd_client",
        "SAMClient": "sam_client",
        "CharacterConsistencyService": "sam_client",
        "MinioClient": "minio_client",
    }
    if name not in modules:
        raise AttributeError(name)
    return getattr(importlib.import_module(f"app.tools.{modules[name]}"), name)
