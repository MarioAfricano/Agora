import boto3
import httpx

from app.config import settings
from app.igdb import cover_url

s3 = boto3.client("s3")


def upload_cover(igdb_id: int, image_id: str) -> str:
    url = cover_url(image_id, "t_cover_big")
    response = httpx.get(url, timeout=10)
    response.raise_for_status()

    key = f"covers/{igdb_id}.jpg"

    s3.put_object(
        Bucket=settings.cover_bucket,
        Key=key,
        Body=response.content,
        ContentType="image/jpeg",
    )

    return key
