import os
from io import BytesIO

import boto3
import botocore
import pdfplumber
from bs4 import BeautifulSoup

from services.utils.types.main import SQSPayload


def extract_text_from_s3_bytes(file_bytes: bytes, file_extension: str) -> str | None:
    try:
        if file_extension == ".txt":
            return file_bytes.decode("utf-8")  # Simple text
        elif file_extension == ".pdf":
            text = ""
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        elif file_extension == ".html":
            soup = BeautifulSoup(file_bytes, "html.parser")
            return soup.get_text()
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")

    except ValueError as e:
        print(f"❌ Value Error in extract_text_from_s3_bytes: {e}")

    return None


def download_file_from_s3(
    s3_client: boto3.client, sqs_payload: SQSPayload
) -> bytes | None:

    try:
        print(f"sqs_payload in download_file_from_s3: {sqs_payload}")

        print(f"s3_client in download_file_from_s3 {s3_client}")

        s3_key = sqs_payload.get("transcript_s3_key", None)

        print(f"s3_key in download_file_from_s3 {s3_key}")

        bucket = os.getenv("AWS_BUCKET", "alwayssaved")

        print(f"bucket in download_file_from_s3 {bucket}")

        if s3_key is None or bucket is None:
            return None

        response = s3_client.get_object(Bucket=bucket, Key=s3_key)

        print(f"response from download_file_from_s3: {response} \n")

        return response["Body"].read()
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            print(f"Object with key of {s3_key} does not exist! \n")
        elif e.response["Error"]["Code"] == "404":
            print(f"Object with key of {s3_key} does not exist! \n")
        else:
            print("An error occurred: ", e)
    return None
