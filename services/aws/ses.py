import os
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ParamValidationError
from bson.objectid import ObjectId
from pymongo import AsyncMongoClient

if TYPE_CHECKING:
    from types_aiobotocore_ses.client import SESClient

sender = os.getenv("AWS_SES_SENDER_EMAIL", "").strip()
SUBJECT = "Your media file has been processed! 🥳"
BODY_TEXT = "We've finished processing your media files. You may now ask the LLM questions about your files. Happy querying! 🎉🙌🏽"


async def send_user_email_notification(
    ses_client: "SESClient", mongo_client: AsyncMongoClient, user_id: str
) -> None:

    print(f"user_id in send_user_email_notification: {user_id}")

    try:
        found_user = (
            await mongo_client.get_database("alwayssaved")
            .get_collection("users")
            .find_one({"_id": ObjectId(user_id)})
        )
        print(f"found_user in send_user_email_notification: {found_user}")

        if found_user is None:
            raise ValueError(
                f"User with id of {user_id} not found in database. Can't send a transcription notification email."
            )

        email = found_user.get("email", "").strip()

        print(f"plucked email from found_user {email}")

        if not email:
            raise ValueError(
                f"User with id of {user_id} has no email. Can't send a transcription notification email."
            )

        # aioboto3's ses_client is a genuine async client (unlike plain
        # boto3), so send_email here actually returns a coroutine and
        # this await is doing real work, not a no-op.
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

    except (ParamValidationError, BotoCoreError) as e:
        print(f"❌ SES error ({type(e).__name__}): {str(e)} — user_id: {user_id}")

    except ValueError as e:
        print(
            f"❌ Unexpected ValueError in send_user_email_notification for user_id {user_id}: {str(e)}"
        )

    except Exception as e:
        print(
            f"❌ Unexpected Exception in send_user_email_notification for user_id {user_id}: {str(e)}"
        )
