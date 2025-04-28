import os

import boto3

from services.aws.sqs import get_message_from_extractor_service

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3_client = boto3.client("s3", region_name=AWS_REGION)


def run_service():

    while True:
        try:
            get_message_from_extractor_service()
        except ValueError as e:
            print(f"ValueError: {e}")


run_service()
