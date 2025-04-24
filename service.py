from services.aws.sqs import get_message_from_extractor_service


def run_service():

    while True:
        try:
            get_message_from_extractor_service()
        except ValueError as e:
            print(f"ValueError: {e}")


run_service()
