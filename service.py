import json
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

from dotenv import load_dotenv

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

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


qdrant_client = get_qdrant_client()


def executor_worker(json_payload: str):
    payload_dict = json.loads(json_payload)
    return embed_and_upload(payload_dict)


def run_service():

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
            print("Start Extracting and Processing Queue Messages. \n")
            dequeue_start = time.time()
            sqs_payload = get_messages_from_extractor_service()

            sqs_msg_list = process_incoming_sqs_messages(sqs_payload)

            dequeue_end = time.time()
            dequeue_elapsed_time = dequeue_end - dequeue_start
            print(
                f"Elapsed time for Extracting and Processing Queue Messages: {dequeue_elapsed_time} \n"
            )

            if len(sqs_msg_list) == 0:
                time.sleep(2)
                continue

            # 2) Embedd & Upload Every Message to Qdrant Database.
            print("Start Embedding and Uploading Messages to Qdrant Database. \n")
            embedd_start = time.time()

            jsonified_inputs = [json.dumps(msg) for msg in sqs_msg_list]

            # TODO: Handle Message Loss Protection / Idempotency During Embedding
            # Ensures Fresh Worker Processes Each Batch
            with ProcessPoolExecutor() as executor:
                raw_results = list(executor.map(executor_worker, jsonified_inputs))

            embedd_end = time.time()

            embedd_elapsed_time = embedd_end - embedd_start
            print(
                f"Elapsed time for Embedding and Uploading Messages to Qdrant Database: {embedd_elapsed_time} \n"
            )

            successful_results = [
                res for res in raw_results if res.get("process_status") == "complete"
            ]

            print(
                f"successfully process messages after embedding and uploading step: {successful_results} \n"
            )

            # 3) Delete Successfully Embedded/Uploaded Messages From SQS.
            print(
                "Start deleting successfully process messages from Embedding Push Queue. \n"
            )
            delete_embedding_sqs_message(successful_results)

            # 4) TODO: Fire an SES Email For Each Successful Embedd/Upload Message.
            #    Might have to be async with ThreadPoolExecutor

        except ValueError as e:
            print(f"ValueError: {e}")
            traceback.print_exc()


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
    transcript_url: string;
    transcript_key: string;
    user_id: string;
  }


- Outgoing SQS Message has the following shape (may get redone):
{

}
"""
