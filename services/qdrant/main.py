import os

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from services.aws.ssm import get_secret


def get_collection(Q_Client: QdrantClient):
    pass


def get_embedd_model() -> SentenceTransformer:
    embedd_model_name = os.getenv("EMBEDDING_MODEL", "multi-qa-MiniLM-L6-cos-v1")

    embedding_model = SentenceTransformer(embedd_model_name)

    return embedding_model


def get_qdrant_client() -> QdrantClient | None:

    try:
        qdrant_url = get_secret("/notecasts/QDRANT_URL")
        qdrant_api_key = get_secret("/notecasts/QDRANT_API_KEY")

        if qdrant_url is None or qdrant_api_key is None:
            raise ValueError(
                "QDRANT_URL or QDRANT_API_KEY environment variables are not set."
            )
        # Connect to Qdrant
        qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        return qdrant

    except ValueError as e:
        print(f"❌ Value Error: {e}")
        return None
