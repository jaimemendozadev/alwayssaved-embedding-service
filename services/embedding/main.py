import os
import traceback
import uuid

import boto3
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from services.aws.s3 import download_file_from_s3, extract_text_from_s3_bytes
from services.embedding.utils.main import (
    chunk_text,
    get_embedd_model,
    handle_msg_feedback,
)
from services.qdrant.main import get_qdrant_client
from services.utils.types.main import EmbedStatus, SQSPayload

QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "alwayssaved_user_files")


def get_base_error_feedback(
    error_type: str,
    note_id: str | None,
    user_id: str | None,
    transcript_bucket: str | None,
    transcript_s3_key: str | None,
) -> str:
    return f"❌ Unexpected {error_type} occurred for note_id={note_id}, user_id={user_id}, transcript_bucket={transcript_bucket}, transcript_s3_key={transcript_s3_key}"


def embed_and_upload(
    sqs_payload: SQSPayload,
) -> EmbedStatus:

    try:
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        transcript_bucket = os.getenv("AWS_BUCKET", "alwayssaved")
        s3_client = boto3.client("s3", region_name=aws_region)

        embedding_model: SentenceTransformer = get_embedd_model()
        qdrant_client: QdrantClient = get_qdrant_client()

        if embedding_model is None or qdrant_client is None or s3_client is None:
            raise ValueError(
                "Can't process sqs_payload due to missing embedding model, qdrant client, or s3 client."
            )

        file_id = sqs_payload.get("file_id", None)
        note_id = sqs_payload.get("note_id", None)
        user_id = sqs_payload.get("user_id", None)
        transcript_s3_key = sqs_payload.get("transcript_s3_key", None)

        if (
            file_id is None
            or note_id is None
            or user_id is None
            or transcript_bucket is None
            or transcript_s3_key is None
        ):
            raise ValueError(
                "SQS Message Payload from Extractor Service is missing file_id, note_id, user_id, or transcript_s3_key value."
            )

        file_bytes = download_file_from_s3(s3_client, sqs_payload)

        if file_bytes is None:
            raise ValueError(
                f"Could not get the requested s3 file with key of: {transcript_s3_key}"
            )

        # transcript_key is media file name with .extension
        _, file_extension = os.path.splitext(transcript_s3_key)

        file_extension = file_extension.lower()

        full_text = extract_text_from_s3_bytes(file_bytes, file_extension)

        if full_text is None:
            raise ValueError(
                f"Could not extract text from downloaded s3 file with key of: {transcript_s3_key}"
            )

        chunks = chunk_text(full_text)

        vectors = embedding_model.encode(chunks, normalize_embeddings=True)

        points = []

        for _, (chunked_text, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),  # unique ID per chunk
                    vector=vector.tolist(),
                    payload={
                        "note_id": note_id,
                        "file_id": file_id,
                        "user_id": user_id,
                        "s3_key": transcript_s3_key,
                        "original_chunk_text": chunked_text,
                    },
                )
            )
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)

        print(f"✅ Uploaded {len(points)} chunks to Qdrant!")

        return handle_msg_feedback(sqs_payload, "complete")

    except TypeError as e:
        feedback = get_base_error_feedback(
            "TypeError", note_id, user_id, transcript_bucket, transcript_s3_key
        )
        print(f"{feedback} in embed_and_upload: {e}")
        traceback.print_exc()

        return handle_msg_feedback(sqs_payload, "failed")

    except ValueError as e:
        feedback = get_base_error_feedback(
            "ValueError", note_id, user_id, transcript_bucket, transcript_s3_key
        )
        print(f"{feedback} in embed_and_upload: {e}")
        traceback.print_exc()

        return handle_msg_feedback(sqs_payload, "failed")

    except Exception as e:
        feedback = get_base_error_feedback(
            "Exception", note_id, user_id, transcript_bucket, transcript_s3_key
        )
        print(f"{feedback} in embed_and_upload: {e}")
        traceback.print_exc()

        return handle_msg_feedback(sqs_payload, "failed")
