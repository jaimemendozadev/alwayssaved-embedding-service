import asyncio
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import TYPE_CHECKING

import boto3
from dotenv import load_dotenv

from services.aws.ses import send_user_email_notification
from services.aws.sqs import (
    delete_embedding_sqs_message,
    get_messages_from_extractor_service,
    process_incoming_sqs_messages,
)
from services.embedding.main import embed_and_upload
from services.qdrant.main import (
    create_qdrant_collection,
    get_qdrant_client,
    get_qdrant_collection,
)
from services.utils.mongodb.main import create_mongodb_instance
from services.utils.types.main import EmbedStatus

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


qdrant_client = get_qdrant_client()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if TYPE_CHECKING:
    from mypy_boto3_ses import SESClient

ses_client: "SESClient" = boto3.client("ses", region_name=AWS_REGION)

mongo_client = create_mongodb_instance()


def executor_worker(json_payload: str):
    payload_dict = json.loads(json_payload)
    return embed_and_upload(payload_dict)


def thread_executor_worker(embed_status: EmbedStatus):
    user_id = embed_status["user_id"]
    asyncio.run(send_user_email_notification(ses_client, mongo_client, user_id))


def run_service():

    # ✅ Validate Qdrant client and collection once before entering loop
    if qdrant_client is None:
        print("❌ Qdrant client could not be instantiated in run_service. Exiting.")
        return

    create_qdrant_collection(qdrant_client)

    collection_info = get_qdrant_collection(qdrant_client)

    if collection_info is None:
        print("❌ Qdrant collection not found and could not be created. Exiting.")
        return

    while True:

        try:

            if mongo_client is None:
                continue

            # 1) Get Extractor Queue Messages & Process.
            print("Start Extracting and Processing Queue Messages.")
            dequeue_start = time.time()
            sqs_payload = get_messages_from_extractor_service()

            sqs_msg_list = process_incoming_sqs_messages(sqs_payload)

            if len(sqs_msg_list) == 0:
                time.sleep(2)
                continue

            dequeue_end = time.time()
            dequeue_elapsed_time = dequeue_end - dequeue_start
            print(
                f"Elapsed time for Extracting and Processing Queue Messages: {dequeue_elapsed_time}"
            )

            # 2) Embedd & Upload Every Message to Qdrant Database.
            print("Start Embedding and Uploading Messages to Qdrant Database.")
            embedd_start = time.time()

            # Need to stingify each dictionary to avoid executor Pickle issue.
            jsonified_inputs = [json.dumps(msg) for msg in sqs_msg_list]

            # TODO: Handle Message Loss Protection / Idempotency During Embedding
            # Ensures Fresh Worker Processes Each Batch
            with ProcessPoolExecutor() as executor:
                raw_results = list(executor.map(executor_worker, jsonified_inputs))

            embedd_end = time.time()

            embedd_elapsed_time = embedd_end - embedd_start
            print(
                f"Elapsed time for Embedding and Uploading Messages to Qdrant Database: {embedd_elapsed_time}"
            )

            successful_results = [
                res for res in raw_results if res.get("process_status") == "complete"
            ]

            print(
                f"successfully process messages after embedding and uploading step: {successful_results}"
            )

            # 3) Delete Successfully Embedded/Uploaded Messages From SQS.
            print(
                "Start deleting successfully process messages from Embedding Push Queue."
            )
            delete_embedding_sqs_message(successful_results)

            # 4) Fire an SES Email For Each Successful Embedd/Upload Message.
            with ThreadPoolExecutor() as executor:
                list(executor.map(thread_executor_worker, successful_results))

        except ValueError as e:
            print(f"ValueError in run_service function: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    run_service()

# pylint: disable=W0105
"""
Notes:

- Decided to organize media uploads and call each upload a "Note".
- If the Note is an .mp3 or .mp4, a Note is created for that file and it'll get uploaded on the Frontend to s3 at /{userID}/{noteID}/{fileName}.{fileExtension}
- When SQS messages arrives in Extractor service, will transcribe and upload the transcript to s3 at /{userID}/{noteID}/{fileName}.txt
- Incoming SQS Message has the following shape:

  {
      note_id: string;
      user_id: string;
      transcript_key: string; # media file name with .extension
  }


- Outgoing SQS Message has the following shape (may get redone):
{

}
"""
