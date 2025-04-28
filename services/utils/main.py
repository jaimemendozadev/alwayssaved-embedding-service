import json
import uuid
from typing import Any, Dict

from bson.objectid import ObjectId

dummy_s3_urls = [
    "https://notecasts.s3.us-east-1.amazonaws.com/680ce8f5d772ddb30773476d/680ce8f5d772ddb30773476e/Palmer%2BLuckey%2BWants%2Bto%2BBe%2BSilicon%2BValley's%2BWar%2BKing%2B%EF%BD%9C%2BThe%2BCircuit.txt",
    "https://notecasts.s3.us-east-1.amazonaws.com/680e48fafdcf6fb234249594/680e48fafdcf6fb234249595/Ilya+Sutskever+Deep+Learning++Lex+Fridman+Podcast+%2394.txt",
    "https://notecasts.s3.us-east-1.amazonaws.com/680e546c6226e2384723f059/680e546c6226e2384723f05a/Jensen+Huang%2C+Founder+and+CEO+of+NVIDIA.txt",
    "https://notecasts.s3.us-east-1.amazonaws.com/680e60514d433a74bfdab40c/680e60514d433a74bfdab40d/How+China%E2%80%99s+New+AI+Model+DeepSeek+Is+Threatening+U.S.+Dominance.txt",
    "https://notecasts.s3.us-east-1.amazonaws.com/680ee45ee9f12ec29105903b/680ee45ee9f12ec29105903c/NVIDIA+CEO+Jensen+Huang's+Vision+for+the+Future.txt",
    "https://notecasts.s3.us-east-1.amazonaws.com/680ee9b692dce86ef5f47c42/680ee9b692dce86ef5f47c43/Geoffrey+Hinton++On+working+with+Ilya%2C+choosing+problems%2C+and+the+power+of+intuition.txt",
]


def _generate_fake_sqs_msg() -> Dict[str, Any]:

    fake_payload = {"Messages": []}

    for url in dummy_s3_urls:
        fake_payload["Messages"].append(
            {
                "MessageId": str(uuid.uuid4()),
                "Body": json.dumps({"userID": str(ObjectId()), "transcriptURL": url}),
            }
        )

    return fake_payload
