import json

from app.import_queue import get_queue_url, sqs


def main():
    queue_url = get_queue_url()
    print("worker started")
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )
        for message in response.get("Messages", []):
            print(json.loads(message["Body"])["job_id"])
            sqs.delete_message(
                QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
            )


if __name__ == "__main__":
    main()
