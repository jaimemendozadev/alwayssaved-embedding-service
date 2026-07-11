import asyncio
import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

import aioboto3
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

load_dotenv()

qdrant_client = get_qdrant_client()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if TYPE_CHECKING:
    from types_aiobotocore_ses.client import SESClient

# aioboto3 clients are async context managers, not plain objects you can
# instantiate once at module level the way sync boto3.client() worked.
# The Session itself is cheap/stateless and safe to keep as a module-level
# global — it's only the actual client (opened via `session.client(...)`)
# that needs to live inside an `async with` block. See run_service() below,
# where it's opened once and held open for the lifetime of the service loop.
aws_session = aioboto3.Session()

mongo_client = create_mongodb_instance()


def executor_worker(json_payload: str):
    payload_dict = json.loads(json_payload)
    return embed_and_upload(payload_dict)


# TODO: Pass entire payload to send_user_email_notification
async def process_successful_results(ses_client: "SESClient", successful_results):
    tasks = [
        send_user_email_notification(ses_client, mongo_client, result["user_id"])
        for result in successful_results
    ]
    await asyncio.gather(*tasks)


async def run_service():

    # ✅ Validate Qdrant client and collection once before entering loop
    if qdrant_client is None:
        print(
            "❌ App fails preliminary first check where Qdrant client could not be instantiated in run_service. Exiting."
        )
        return

    create_qdrant_collection(qdrant_client)

    collection_info = get_qdrant_collection(qdrant_client)

    if collection_info is None:
        print(
            "❌ App fails preliminary second check where Qdrant collection not found and could not be created. Exiting."
        )
        return

    if mongo_client is None:
        print(
            "❌ App fails final preliminary check where the MongoDB client could not be instantiated. Exiting."
        )
        return

    # Opened ONCE here, held open for the entire lifetime of the service
    # loop below — NOT re-opened per-message. Re-opening per-message would
    # work but adds unnecessary connection setup/teardown on every single
    # iteration for no benefit, since this loop runs effectively forever.
    async with aws_session.client("ses", region_name=AWS_REGION) as ses_client:
        while True:
            try:
                # 1) Get Extractor Queue Messages & Process.

                # For MVP, will only dequee one SQS message at a time.
                sqs_payload = get_messages_from_extractor_service()

                sqs_msg_list = process_incoming_sqs_messages(sqs_payload)

                if len(sqs_msg_list) == 0:
                    time.sleep(2)
                    continue

                # 2) Embed & Upload Every Message to Qdrant Database.

                # Need to stingify each dictionary to avoid executor Pickle issue.
                json_payloads = [json.dumps(msg) for msg in sqs_msg_list]

                # Ensures Fresh Worker Processes Each Batch
                with ProcessPoolExecutor() as executor:
                    raw_results = list(executor.map(executor_worker, json_payloads))

                successful_results = [
                    res
                    for res in raw_results
                    if res.get("process_status") == "complete"
                ]

                # 3) Delete Successfully Embedded/Uploaded Messages From SQS.
                if len(successful_results) == 0:
                    # Transcription embedding failed -> Don't delete -> Let SQS retry.
                    for failed_result in raw_results:
                        print(
                            f"❌ Transcript embedding failed for sqs_payload with message_id of {failed_result.get('message_id')} — skipping deletion."
                        )

                else:
                    print(
                        "Start deleting successfully process messages from Embedding Push Queue."
                    )
                    delete_embedding_sqs_message(successful_results)

                    # 4) Fire an SES Email For Each Successful Embedd/Upload Message.
                    await process_successful_results(ses_client, successful_results)

            except ValueError as e:
                print(f"ValueError in run_service function: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_service())

# pylint: disable=W0105
"""
Notes:
- Incoming SQS Message has the following shape:

  {
      note_id: string;
      file_id: string;
      user_id: string;
      transcript_s3_key: string; # media file name with .extension
  }
"""
