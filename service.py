import os
import time
from concurrent.futures import Executor, ProcessPoolExecutor

import boto3
from dotenv import load_dotenv

from services.aws.sqs import (
    delete_extractor_sqs_message,
    get_messages_from_extractor_service,
    process_incoming_sqs_messages,
)
from services.embedding.main import executor_worker
from services.qdrant.main import (
    create_qdrant_collection,
    get_qdrant_client,
    get_qdrant_collection,
)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


qdrant_client = get_qdrant_client()


def run_service():
    executor: Executor = ProcessPoolExecutor()

    # ✅ Validate Qdrant client and collection once before entering loop
    if qdrant_client is None:
        print("❌ Qdrant client could not be instantiated. Exiting.")
        return

    create_qdrant_collection(qdrant_client)

    collection_info = get_qdrant_collection(qdrant_client)

    if collection_info is None:
        print("❌ Qdrant collection not found and could not be created. Exiting.")
        return

    while True:

        try:

            # 1) Get Extractor Queue Messages & Process.
            dequeue_start = time.time()
            sqs_payload = get_messages_from_extractor_service()

            sqs_msg_list = process_incoming_sqs_messages(sqs_payload)

            dequeue_end = time.time()
            dequeue_elapsed_time = dequeue_end - dequeue_start
            print(
                f"Elapsed time for Extractor SQS dequeue/processing: {dequeue_elapsed_time} \n"
            )

            if len(sqs_msg_list) == 0:
                continue

            embed_invoke_args = [(s3_client, msg) for msg in sqs_msg_list]

            # 2) Embedd & Upload Every Message to Qdrant Database.
            embedd_start = time.time()

            # TODO: Handle Message Loss Protection / Idempotency During Embedding
            raw_results = list(executor.map(executor_worker, embed_invoke_args))

            embedd_end = time.time()

            embedd_elapsed_time = embedd_end - embedd_start
            print(
                f"Elapsed time for Embedd and Upload to Qdrant Step: {embedd_elapsed_time} \n"
            )

            successful_results = [
                res for res in raw_results if res.get("process_status") == "complete"
            ]

            print(f"successful_results: {successful_results} \n")

            # 3) Delete Successfully Embedded/Uploaded Messages From SQS.
            delete_extractor_sqs_message(successful_results)

            # 4) TODO: Fire an SES Email For Each Successful Embedd/Upload Message.
            #    Might have to be async with ThreadPoolExecutor

        except ValueError as e:
            print(f"ValueError: {e}")


if __name__ == "__main__":
    run_service()

# pylint: disable=W0105
"""
Dev Notes 5/2/25:

- Decided to organize media uploads and call each upload a "Note".
- If the Note is an .mp3 or .mp4, a Note is created for that file and it'll get uploaded on the Frontend to s3 at /{userID}/{noteID}/{fileName}.{fileExtension}
- When SQS messages arrives in Extractor service, will transcribe and upload the transcript to s3 at /{userID}/{noteID}/{fileName}.txt
- Incoming SQS Message has the following shape:
  {
    note_id: string;
    user_id: string;
    transcript_url: string;
  }


- Outgoing SQS Message has the following shape (may get redone):
{

}
"""
