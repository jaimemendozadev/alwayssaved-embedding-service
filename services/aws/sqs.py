import json
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from services.aws.ssm import get_secret

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def get_messages_from_extractor_service(
    max_messages=10, wait_time=20
) -> Dict[str, Any]:

    try:

        embedding_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

        if not embedding_push_queue_url:
            raise ValueError("⚠️ ERROR: SQS Embedding PushQueue URL not set!")

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

    except ValueError as e:
        print(f"❌ Unexpected Error: {str(e)}")

    return {}


def process_incoming_sqs_messages(
    incoming_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    sqs_msg_list = incoming_payload.get("Messages", [])

    if len(sqs_msg_list) == 0:
        return sqs_msg_list

    processed_list: List[Dict[str, Any]] = []

    for msg in sqs_msg_list:
        payload_body = json.loads(msg.get("Body", {}))
        receipt_handle = msg.get("ReceiptHandle", None)
        processed_msg = {}

        processed_msg["note_id"] = payload_body.get("note_id", None)
        processed_msg["transcript_url"] = payload_body.get("transcript_url", None)
        processed_msg["user_id"] = payload_body.get("user_id", None)
        processed_msg["sqs_receipt_handle"] = receipt_handle

        processed_list.append(processed_msg)

    return processed_list


def send_embedding_sqs_message(sqs_payload):
    """Sends a message to the SQS embedding_push_queue indicating the transcript is ready for embedding process."""

    embedding_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

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


def delete_embedding_sqs_message(processed_sqs_msg: Dict[str, Any]):

    embedding_push_queue_url = get_secret("/alwayssaved/EMBEDDING_PUSH_QUEUE_URL")

    if not embedding_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set for delete_embedding_sqs_message!")
        return

    try:
        receipt_handle = processed_sqs_msg.get("ReceiptHandle", None)

        sqs_client.delete_message(
            QueueUrl=embedding_push_queue_url, ReceiptHandle=receipt_handle
        )
        print(
            f"✅ SQS Message Deleted from Embedding Push Queue: {processed_sqs_msg['MessageId']}"
        )

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")


def delete_extractor_sqs_message(processed_msg_list: List[Dict[str, Any]]):

    extractor_push_queue_url = get_secret("/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL")

    if not extractor_push_queue_url:
        print("⚠️ ERROR: SQS Queue URL not set for delete_extractor_sqs_message!")
        return

    try:
        for msg in processed_msg_list:
            receipt_handle = msg.get("sqs_receipt_handle", None)

            sqs_client.delete_message(
                QueueUrl=extractor_push_queue_url, ReceiptHandle=receipt_handle
            )

            print(
                f"✅ SQS Message Deleted from Extractor Push Queue: {msg['MessageId']}"
            )

    except ClientError as e:
        print(
            f"❌ AWS Client Error sending SQS message: {e.response['Error']['Message']}"
        )

    except BotoCoreError as e:
        print(f"❌ Boto3 Internal Error: {str(e)}")

    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
