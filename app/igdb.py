import time

import httpx

from app.config import settings

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API_URL = "https://api.igdb.com/v4"


class IGDBClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        if self._token is None or time.time() > self._token_expires_at - 60:
            response = httpx.post(
                TOKEN_URL,
                params={
                    "client_id": settings.igdb_client_id,
                    "client_secret": settings.igdb_client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._token_expires_at = time.time() + data["expires_in"]
        return self._token

    def search_games(self, query: str) -> list[dict]:
        query = query.replace('"', "")
        body = (
            f'search "{query}";'
            " fields name, first_release_date, cover.image_id;"
            " limit 10;"
        )
        response = httpx.post(
            f"{API_URL}/games",
            headers={
                "Client-ID": settings.igdb_client_id,
                "Authorization": f"Bearer {self._get_token()}",
            },
            content=body,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


def cover_url(image_id: str, size: str = "t_cover_small") -> str:
    return f"https://images.igdb.com/igdb/image/upload/{size}/{image_id}.jpg"


igdb = IGDBClient()
