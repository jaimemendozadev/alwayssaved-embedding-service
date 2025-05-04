import os
from concurrent.futures import Executor, ProcessPoolExecutor

import boto3
from dotenv import load_dotenv

from dev_utils.main import _generate_fake_sqs_msg
from services.embedding.main import embed_and_upload, get_embedd_model

# from services.aws.sqs import get_messages_from_extractor_service
from services.qdrant.main import create_qdrant_collection, get_qdrant_client

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


qdrant_client = get_qdrant_client()
embedding_model = get_embedd_model()


def run_service():

    create_qdrant_collection(qdrant_client)
    executor: Executor = ProcessPoolExecutor()

    while True:
        try:
            # get_messages_from_extractor_service()
            fake_sqs_payload = _generate_fake_sqs_msg()

            print(f"fake_sqs_payload: {fake_sqs_payload}")
            print("\n")

            sqs_msg_list = fake_sqs_payload.get("Messages", [])

            if len(sqs_msg_list) == 0:
                continue

            embed_invoke_args = [
                (embedding_model, qdrant_client, s3_client, msg) for msg in sqs_msg_list
            ]

            embed_results = executor.map(
                lambda embed_args: embed_and_upload(*embed_args), embed_invoke_args
            )

            print(f"embed_results: {embed_results} \n")

            # TODO: Fire SES Email, might have to be async with ThreadPoolExecutor

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
