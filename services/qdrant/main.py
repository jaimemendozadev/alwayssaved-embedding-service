import os

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.conversions.common_types import CollectionInfo
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams

from services.aws.ssm import get_secret

QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "alwayssaved_user_files")


def ensure_payload_indexes(q_client: QdrantClient) -> None:
    """
    Creates keyword payload indexes for filter fields if they don't already exist.
    Safe to call on every startup — Qdrant is idempotent about existing indexes.
    """
    fields_to_index = ["user_id", "note_id", "file_id"]

    for field in fields_to_index:
        try:
            q_client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name=field,
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
        except Exception as e:
            print(f"⚠️ Could not create payload index for '{field}': {e}")


def create_qdrant_collection(q_client: QdrantClient) -> None:

    try:
        q_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)

    except UnexpectedResponse as e:
        print(
            f"❌ QdrantClient UnexpectedResponse Error in create_qdrant_collection: {e}"
        )

        q_client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        return None


def get_qdrant_client() -> QdrantClient | None:

    try:
        qdrant_url = get_secret("/alwayssaved/QDRANT_URL")
        qdrant_api_key = get_secret("/alwayssaved/QDRANT_API_KEY")

        if qdrant_url is None or qdrant_api_key is None:
            raise ValueError(
                "QDRANT_URL or QDRANT_API_KEY environment variables are not set."
            )
        # Connect to Qdrant
        qdrant = QdrantClient(
            url=qdrant_url, api_key=qdrant_api_key, cloud_inference=True
        )

        ensure_payload_indexes(qdrant)

        return qdrant

    except ValueError as e:
        print(f"❌ Value Error in get_qdrant_client: {e}")
        return None


def get_qdrant_collection(q_client: QdrantClient) -> CollectionInfo | None:

    try:
        return q_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)

    except UnexpectedResponse as e:
        print(f"❌ QdrantClient UnexpectedResponse Error in get_qdrant_collection: {e}")

    return None
