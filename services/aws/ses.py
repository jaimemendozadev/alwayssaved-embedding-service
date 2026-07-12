import os
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ParamValidationError
from bson.objectid import ObjectId
from pymongo import AsyncMongoClient
from services.utils.types.main import EmbedStatus

if TYPE_CHECKING:
    from types_aiobotocore_ses.client import SESClient

sender = os.getenv("AWS_SES_SENDER_EMAIL", "no-reply@alwayssaved.com").strip()
SUBJECT = "Your media file has been processed! 🥳"
INTRO_TEXT = "We've finished processing your media files. \n"
ENDING_TEXT = (
    "You may now ask the LLM questions about your files. Happy querying! 🎉🙌🏽"
)


async def send_user_email_notification(
    ses_client: "SESClient", mongo_client: AsyncMongoClient, embed_result: EmbedStatus
) -> None:

    try:
        user_id = embed_result.get("user_id", "")

        original_filename = embed_result.get("original_filename", "")

        found_user = (
            await mongo_client.get_database("alwayssaved")
            .get_collection("users")
            .find_one({"_id": ObjectId(user_id)})
        )

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

        BODY_TEXT = f"- {original_filename}"

        FINALIZED_BODY = "".join([INTRO_TEXT, BODY_TEXT, ENDING_TEXT])

        # aioboto3's ses_client is a genuine async client (unlike plain
        # boto3), so send_email here actually returns a coroutine and
        # this await is doing real work, not a no-op.
        await ses_client.send_email(
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
                        "Data": FINALIZED_BODY,
                    },
                },
            },
        )

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
