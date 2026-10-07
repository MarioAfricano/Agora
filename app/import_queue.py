import json

import boto3

from app.config import settings

sqs = boto3.client("sqs")


def send_import_job(job_id: int) -> None:
    queue_url = sqs.get_queue_url(QueueName=settings.import_queue_name)["QueueUrl"]
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"job_id": job_id}))
