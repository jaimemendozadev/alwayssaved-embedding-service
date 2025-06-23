import os
from typing import TYPE_CHECKING

from bson.objectid import ObjectId
from pymongo import AsyncMongoClient

if TYPE_CHECKING:
    from mypy_boto3_ses import SESClient

sender = os.getenv("AWS_SES_SENDER_EMAIL", "")
SUBJECT = "Your media file has been processed! 🥳"
BODY_TEXT = "We've finished processing your media file and you're now ready to ask it questions against the LLM. Happy querying! 🎉🙌🏽"


async def send_user_email_notification(
    ses_client: "SESClient", mongo_client: AsyncMongoClient, user_id: str
) -> None:

    print(f"user_id in send_user_email_notification: {user_id}")

    found_user = (
        await mongo_client.get_database("alwayssaved")
        .get_collection("users")
        .find_one({"_id": ObjectId(user_id)})
    )

    print(f"found_user in send_user_email_notification: {found_user}")

    email = found_user

    response = await ses_client.send_email(
        Source=sender,
        Destination={
            "ToAddresses": [email],
        },
        Message={
            "Subject": {
                "Data": SUBJECT,
            },
            "Body": {
                "Text": {
                    "Data": BODY_TEXT,
                },
            },
        },
    )

    print(f"response in send_user_email_notification: {response}")

    print(f"Email sent to {email}! Message ID:", response["MessageId"])
