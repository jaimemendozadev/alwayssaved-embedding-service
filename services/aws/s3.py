from io import BytesIO
from urllib.parse import urlparse

import boto3
import pdfplumber
from bs4 import BeautifulSoup


def extract_text_from_s3_bytes(file_bytes: bytes, file_extension: str) -> str:
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


def download_file_from_s3(s3_client: boto3.client, s3_url: str) -> bytes:
    parsed_url = urlparse(s3_url)
    bucket = parsed_url.netloc.split(".")[
        0
    ]  # Gets 'my-bucket' from 'my-bucket.s3.us-west-2.amazonaws.com'
    key = parsed_url.path.lstrip("/")  # Remove leading slash
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
