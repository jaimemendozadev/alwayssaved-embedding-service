from typing import Literal, TypedDict


class SQSPayload(TypedDict):
    message_id: str
    note_id: str
    user_id: str
    transcript_key: str
    sqs_receipt_handle: str


process_status = Literal["complete", "failed"]


class EmbedStatus(SQSPayload):
    process_status: process_status
