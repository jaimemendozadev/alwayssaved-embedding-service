import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ses import SESClient

sender = os.getenv("AWS_SES_SENDER_EMAIL", "")
subject = "Your media file has been processed! 🥳"
body_text = "We've finished processing your media file and you're now ready to ask it questions against the LLM. Happy querying! 🎉🙌🏽"


async def send_user_email_notification(
    ses_client: "SESClient", user_email: str
) -> None:
    response = await ses_client.send_email(
        Source=sender,
        Destination={
            "ToAddresses": [user_email],
        },
        Message={
            "Subject": {
                "Data": subject,
            },
            "Body": {
                "Text": {
                    "Data": body_text,
                },
            },
        },
    )

    print(f"Email sent to {user_email}! Message ID:", response["MessageId"])
