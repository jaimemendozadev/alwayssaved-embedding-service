from urllib.parse import urlparse

import boto3


def download_file_from_s3(s3_client: boto3.client, s3_url: str) -> bytes:
    parsed_url = urlparse(s3_url)
    bucket = parsed_url.netloc.split(".")[
        0
    ]  # Gets 'my-bucket' from 'my-bucket.s3.us-west-2.amazonaws.com'
    key = parsed_url.path.lstrip("/")  # Remove leading slash
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
