"""Public integration surface for Humor Genome Wave 2.

The deployable API is intentionally separate from the immutable Kaggle
measurement path. Importing this package never loads a model or makes a network
request.
"""

__version__ = "0.8.0"

from .config import Settings
from .client import HumorVibesClient
from .embeddings import EmbeddingRegistry, cosine_similarity
from .llm import LLMRegistry
from .open_controls import generation_contract, sample_rows
from .service import HumorVibesService

__all__ = [
    "EmbeddingRegistry",
    "HumorVibesClient",
    "HumorVibesService",
    "LLMRegistry",
    "Settings",
    "cosine_similarity",
    "generation_contract",
    "sample_rows",
]
