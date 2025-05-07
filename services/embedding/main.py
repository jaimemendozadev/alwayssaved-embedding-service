import os
import uuid

import boto3
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from services.aws.s3 import download_file_from_s3, extract_text_from_s3_bytes
from services.embedding.utils.main import (
    chunk_text,
    get_embedd_model,
    handle_error_feedback,
)
from services.qdrant.main import get_qdrant_client
from services.utils.types.main import EmbedStatus, SQSPayload

QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "user_files")


def embed_and_upload(
    s3_client: boto3.client,
    sqs_payload: SQSPayload,
) -> EmbedStatus:
    try:
        embedding_model: SentenceTransformer = get_embedd_model()
        qdrant_client: QdrantClient = get_qdrant_client()

        if embedding_model is None or qdrant_client is None:
            raise ValueError(
                "Can't process sqs_payload due to missing embedding model or qdrant client."
            )

        note_id = sqs_payload.get("note_id", None)
        transcript_url = sqs_payload.get("transcript_url", None)
        user_id = sqs_payload.get("user_id", None)
        sqs_receipt_handle = sqs_payload.get("sqs_receipt_handle", None)

        if (
            note_id is None
            or transcript_url is None
            or user_id is None
            or sqs_receipt_handle is None
        ):
            raise ValueError(
                f"SQS Message Payload from Extractor Service is missing note_id: {note_id}, user_id: {user_id}, transcript_url: {transcript_url}, or sqs_receipt_handle: {sqs_receipt_handle} \n"
            )

        file_bytes = download_file_from_s3(s3_client, transcript_url)

        if file_bytes is None:
            raise ValueError(
                f"Could not get the requested s3 file: {transcript_url} \n"
            )

        _, file_extension = os.path.splitext(transcript_url)

        file_extension = file_extension.lower()

        full_text = extract_text_from_s3_bytes(file_bytes, file_extension)

        if full_text is None:
            raise ValueError(
                f"Could not extract text from downloaded s3 file: {transcript_url} \n"
            )

        chunks = chunk_text(full_text)

        # NOTE: Do we need to add error handling for encoding chunks or upserting? 🤔
        vectors = embedding_model.encode(chunks, normalize_embeddings=True)

        points = []

        for idx, (chunked_text, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),  # unique ID per chunk
                    vector=vector.tolist(),
                    payload={
                        "_id": str(note_id),
                        "user_id": user_id,
                        "source_transcript_url": transcript_url,
                        "original_chunk_text": chunked_text,
                    },
                )
            )
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)

        print(f"✅ Uploaded {len(points)} chunks to Qdrant!")

        # ReceiptHandle
        return {
            "note_id": note_id,
            "sqs_receipt_handle": sqs_receipt_handle,
            "transcript_url": transcript_url,
            "user_id": user_id,
            "process_status": "complete",
        }
    except TypeError as e:
        print(f"An error occurred: {e}")

        return handle_error_feedback(sqs_payload)

    except ValueError as e:
        print(f"❌ Value Error: {e}")

        return handle_error_feedback(sqs_payload)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

        return handle_error_feedback(sqs_payload)


def executor_worker(args):
    return embed_and_upload(*args)
