import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from services.aws.ssm import get_secret

# from bson import ObjectId


# class EmbeddingPayload(TypedDict):
#     _id: ObjectId
#     transcriptURL: str


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def get_messages_from_extractor_service(
    max_messages=10, wait_time=120
) -> Dict[str, Any]:
    embedding_push_queue_url = get_secret("/notecasts/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Embedding PushQueue URL not set!")
        return {}

    try:
        response = sqs_client.receive_message(
            QueueUrl=embedding_push_queue_url,
            MaxNumberOfMessages=max_messages,  # You can adjust this to batch process more users
            WaitTimeSeconds=wait_time,  # Long polling to reduce API calls
        )

        print(f"response from EMBEDDING_PUSH_QUEUE {response}")
        print("\n")

        return response

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")

    return {}


def send_embedding_sqs_message(sqs_payload):
    """Sends a message to the SQS embedding_push_queue indicating the transcript is ready for embedding process."""

    embedding_push_queue_url = get_secret("/notecasts/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Embedding PushQueue URL not set!")
        return

    try:
        # Serialize _id if it's an ObjectId
        payload_json = json.dumps(
            {
                **sqs_payload,
                "_id": str(sqs_payload["_id"]),
            }
        )

        response = sqs_client.send_message(
            QueueUrl=embedding_push_queue_url,
            MessageBody=payload_json,
        )

        print(f"✅ SQS Message Sent! Message ID: {response['MessageId']}")

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
