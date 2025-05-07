from typing import Literal, TypedDict


class SQSPayload(TypedDict):
    note_id: str
    transcript_url: str
    user_id: str
    sqs_receipt_handle: str


process_status = Literal["complete", "failed"]


class EmbedStatus(SQSPayload):
    process_status: process_status
