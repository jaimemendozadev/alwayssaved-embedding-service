import json
import uuid
from typing import Any, Dict

from bson.objectid import ObjectId

dummy_s3_urls = []

def _generate_fake_sqs_msg() -> Dict[str, Any]:

    fake_payload = {"Messages": []}

    for url in dummy_s3_urls:
        fake_payload["Messages"].append(
            {
                "MessageId": str(uuid.uuid4()),
                "Body": json.dumps({"note_id": str(ObjectId()), "transcript_url": url}),
            }
        )

    return fake_payload