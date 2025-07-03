import os

import torch
from sentence_transformers import SentenceTransformer

from services.utils.types.main import EmbedStatus, SQSPayload, process_status


def handle_msg_feedback(
    sqs_payload: SQSPayload, process_result: process_status
) -> EmbedStatus:
    file_id = sqs_payload.get("file_id", "")
    message_id = sqs_payload.get("message_id", "")
    note_id = sqs_payload.get("note_id", "")
    user_id = sqs_payload.get("user_id", "")
    transcript_s3_key = sqs_payload.get("transcript_s3_key", "")
    sqs_receipt_handle = sqs_payload.get("sqs_receipt_handle", "")

    return {
        "file_id": file_id,
        "message_id": message_id,
        "note_id": note_id,
        "user_id": user_id,
        "transcript_s3_key": transcript_s3_key,
        "sqs_receipt_handle": sqs_receipt_handle,
        "process_status": process_result,
    }


def get_embedd_model() -> SentenceTransformer:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"✅ Using device for embedd model: {device}")

    model_name = os.getenv("EMBEDDING_MODEL", "multi-qa-MiniLM-L6-cos-v1")

    embedding_model = SentenceTransformer(model_name_or_path=model_name, device=device)

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
