import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.import_queue import get_queue_url, sqs
from app.importer import import_game
from app.models import ImportJob, LibraryEntry

# Same value as maxReceiveCount on the queue
MAX_ATTEMPTS = 3


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
            job_id = json.loads(message["Body"])["job_id"]
            try:
                with SessionLocal() as db:
                    process_job(db, job_id)
            except Exception as error:
                print(f"Job {job_id} failed: {error}")
                handle_failure(job_id, error)
                continue
            sqs.delete_message(
                QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
            )


def process_job(db: Session, job_id: int) -> None:
    job = db.get(ImportJob, job_id)

    if job is None:
        return

    job.status = "running"
    job.attempts += 1
    db.commit()

    game = import_game(db, job.igdb_id)
    if game is None:
        job.status = "failed"
        job.error = "Game not found on IGDB"
        db.commit()
        return

    job.game_id = game.id
    existing = db.scalar(
        select(LibraryEntry).where(
            LibraryEntry.user_id == job.user_id,
            LibraryEntry.game_id == game.id,
        )
    )
    if existing is None:
        db.add(LibraryEntry(user_id=job.user_id, game_id=game.id))
    job.status = "succeeded"
    db.commit()


def handle_failure(job_id, error):
    with SessionLocal() as db:
        job = db.get(ImportJob, job_id)
        if job is None:
            return

        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
            job.error = str(error)
        else:
            job.status = "pending"
        db.commit()


if __name__ == "__main__":
    main()
