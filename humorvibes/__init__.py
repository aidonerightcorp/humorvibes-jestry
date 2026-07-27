"""Public integration surface for Humor Genome Wave 2.

The deployable API is intentionally separate from the immutable Kaggle
measurement path. Importing this package never loads a model or makes a network
request.
"""

__version__ = "0.3.0"

from .config import Settings
from .embeddings import EmbeddingRegistry, cosine_similarity
from .llm import LLMRegistry
from .service import HumorVibesService

__all__ = [
    "EmbeddingRegistry",
    "HumorVibesService",
    "LLMRegistry",
    "Settings",
    "cosine_similarity",
]
