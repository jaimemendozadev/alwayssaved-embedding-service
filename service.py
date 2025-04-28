import os

import boto3
from dotenv import load_dotenv

from services.embedding.main import get_embedd_model
from services.qdrant.main import create_qdrant_collection, get_qdrant_client
from services.utils.main import _generate_fake_sqs_msg

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


qdrant_client = get_qdrant_client()
embedding_model = get_embedd_model()


def run_service():

    create_qdrant_collection(qdrant_client)

    while True:
        try:
            fake_sqs_payload = _generate_fake_sqs_msg()

            print(f"fake_sqs_payload: {fake_sqs_payload}")
            print("\n")

            if PYTHON_MODE == "development":
                break

            # get_messages_from_extractor_service()
        except ValueError as e:
            print(f"ValueError: {e}")


run_service()
