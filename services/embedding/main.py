import os
import uuid

import boto3
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from services.aws.s3 import download_file_from_s3, extract_text_from_s3_bytes
from services.utils.types.main import SQSPayload


def get_embedd_model() -> SentenceTransformer:
    embedd_model_name = os.getenv("EMBEDDING_MODEL", "multi-qa-MiniLM-L6-cos-v1")

    embedding_model = SentenceTransformer(embedd_model_name)

    return embedding_model


def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def embed_and_upload(
    embedding_model: SentenceTransformer,
    qdrant_client: QdrantClient,
    s3_client: boto3.client,
    sqs_payload: SQSPayload,
):
    try:
        note_id = sqs_payload.get("note_id", None)
        transcript_url = sqs_payload.get("transcript_url", None)
        user_id = sqs_payload.get("user_id", None)

        if note_id is None or transcript_url is None or user_id is None:
            raise ValueError(
                f"SQS Message Payload from Extractor Service is missing note_id: {note_id}, user_id: {user_id}, or transcript_url: {transcript_url} \n"
            )

        file_bytes = download_file_from_s3(s3_client, transcript_url)

        if file_bytes is None:
            raise ValueError(
                f"Could not get the requested s3 file: {transcript_url} \n"
            )

        _, file_extension = os.path.splitext(transcript_url)

        file_extension = file_extension.lower()

        full_text = extract_text_from_s3_bytes(file_bytes, file_extension)

        chunks = chunk_text(full_text)

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
        qdrant_client.upsert(collection_name="notecasts-transcripts", points=points)

        print(f"✅ Uploaded {len(points)} chunks to Qdrant!")

    except ValueError as e:
        print(f"❌ Value Error: {e}")
