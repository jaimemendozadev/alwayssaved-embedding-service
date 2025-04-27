import os

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


def get_collection(Q_Client: QdrantClient):
    pass


def get_embedd_model() -> SentenceTransformer:
    embedd_model_name = os.getenv("EMBEDDING_MODEL", "multi-qa-MiniLM-L6-cos-v1")
    # Load model
    embedding_model = SentenceTransformer(embedd_model_name)

    return embedding_model


def get_qdrant_client() -> QdrantClient:

    # Connect to Qdrant
    qdrant = QdrantClient(
        url="https://your-qdrant-cloud-url", api_key="your-qdrant-api-key"
    )

    return qdrant
