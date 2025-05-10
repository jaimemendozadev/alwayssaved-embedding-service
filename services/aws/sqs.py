import json
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from services.aws.ssm import get_secret
from services.utils.types.main import EmbedStatus, SQSPayload

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client = boto3.client("sqs", region_name=AWS_REGION)

MAX_MESSAGES = 10
WAIT_TIME = 20
VISIBILITY_TIMEOUT = 2700


def get_messages_from_extractor_service() -> Dict[str, Any]:

    try:

        embedding_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

        if not embedding_push_queue_url:
            raise ValueError("⚠️ ERROR: SQS Embedding PushQueue URL not set!")

        response = sqs_client.receive_message(
            QueueUrl=embedding_push_queue_url,
            MaxNumberOfMessages=MAX_MESSAGES,  # You can adjust this to batch process more users
            WaitTimeSeconds=WAIT_TIME,  # Long polling to reduce API calls
            VisibilityTimeout=VISIBILITY_TIMEOUT,
        )

        # TODO: Delete print statement.
        print(
            f"Response from receive_message in get_messages_from_extractor_service: {response}"
        )

        return response

    except ClientError as e:
        print(
            f"❌ AWS Client Error getting SQS message in get_messages_from_extractor_service: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(
            f"❌ Boto3 Internal Error in get_messages_from_extractor_service: {str(e)}"
        )

    except ValueError as e:
        print(f"❌ Unexpected Error in get_messages_from_extractor_service: {str(e)}")

    return {}


def process_incoming_sqs_messages(
    incoming_payload: Dict[str, Any],
) -> List[SQSPayload]:
    sqs_msg_list = incoming_payload.get("Messages", [])

    if len(sqs_msg_list) == 0:
        return sqs_msg_list

    processed_list: List[SQSPayload] = []

    for msg in sqs_msg_list:
        payload_body = json.loads(msg.get("Body", {}))

        processed_msg: SQSPayload = {
            "message_id": msg.get("MessageId", ""),
            "note_id": "",
            "user_id": "",
            "transcript_bucket": "",
            "transcript_key": "",
            "sqs_receipt_handle": msg.get("ReceiptHandle", ""),
        }

        processed_msg["note_id"] = payload_body.get("note_id", "")
        processed_msg["user_id"] = payload_body.get("user_id", "")
        processed_msg["transcript_bucket"] = payload_body.get("transcript_bucket", "")
        processed_msg["transcript_key"] = payload_body.get("transcript_key", "")

        processed_list.append(processed_msg)

    return processed_list


def delete_embedding_sqs_message(processed_success_list: List[EmbedStatus]):

    extractor_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

    if not extractor_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set for delete_embedding_sqs_message!")
        return

    try:
        for msg in processed_success_list:
            receipt_handle = msg.get("sqs_receipt_handle", None)

            sqs_client.delete_message(
                QueueUrl=extractor_push_queue_url, ReceiptHandle=receipt_handle
            )

            print(
                f"✅ SQS Message Deleted from Extractor Push Queue: {msg['message_id']} \n"
            )

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']} \n"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)} \n")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)} \n")
