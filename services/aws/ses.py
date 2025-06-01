import os

import boto3

ses = boto3.client("ses", region_name="us-east-1")  # Use your region


sender = os.getenv("AWS_SES_SENDER_EMAIL", "")
subject = "Your media file has been processed! 🥳"
body_text = "We've finished processing your media file and you're now ready to ask it questions against the LLM. Happy querying! 🎉🙌🏽"


def send_user_email_notification(user_email: str):
    response = ses.send_email(
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
