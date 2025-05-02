from typing import TypedDict


class SQSPayload(TypedDict):
    note_id: str
    transcript_url: str
    user_id: str
