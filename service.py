import os

import boto3
from dotenv import load_dotenv

from services.utils.main import _generate_fake_sqs_msg

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
s3_client = boto3.client("s3", region_name=AWS_REGION)

load_dotenv()

# IMPORTANT: REMEMBER TO SET PYTHON_MODE in .env to 'production' when creating Docker image
PYTHON_MODE = os.getenv("PYTHON_MODE", "production")


def run_service():

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
