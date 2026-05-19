"""
AniDB UDP API scraper for seiyuu and work data.
Rate limit: 1 request per 2 seconds per AniDB ToS.

The AniDB UDP API is a proprietary protocol. This is a skeleton that
demonstrates the approach. In production, you would:

1. Register for an AniDB API client: https://wiki.anidb.net/UDP_API_Definition
2. Use the AUTH, ANIME, and CREATOR commands to fetch data
3. Parse the responses and insert into PostgreSQL

For now, seed data is the primary data source.
See: data/pipeline/seed_data.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

# AniDB UDP API endpoint
ANIDB_HOST = "api.anidb.net"
ANIDB_PORT = 9000
# Rate limit: 1 request / 2 seconds
REQUEST_DELAY = 2.0

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seiyuu:seiyuu123@localhost:5432/seiyuugraph",
)


class AniDBClient:
    """Minimal AniDB UDP API client."""

    def __init__(self, client_name: str, client_version: int = 1):
        self.client_name = client_name
        self.client_version = client_version
        self.session_key = None
        self.last_request = 0

    async def _send(self, command: str) -> str:
        """Send a command to AniDB and return the response."""
        elapsed = time.monotonic() - self.last_request
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)

        # In production: open UDP socket, send command, read response
        # For now, this is a placeholder
        self.last_request = time.monotonic()

        # TODO: Implement actual UDP communication
        # For reference: https://wiki.anidb.net/UDP_API_Definition
        raise NotImplementedError(
            "UDP API not implemented. Use seed_data.py for initial data."
        )

    async def auth(self, username: str, password: str):
        """Authenticate with AniDB."""
        # response = await self._send(f"AUTH user={username}&pass={password}&...")
        # self.session_key = parse_session(response)
        pass

    async def get_anime(self, aid: int):
        """Fetch anime details by AniDB ID."""
        # response = await self._send(f"ANIME aid={aid}&...")
        # parse and return anime info + cast list
        pass

    async def get_creator(self, creator_id: int):
        """Fetch creator (seiyuu) details by AniDB creator ID."""
        # response = await self._send(f"CREATOR creatorid={creator_id}&...")
        # parse and return seiyuu info
        pass


async def main():
    """Example usage — not functional without API credentials."""
    client = AniDBClient("seiyuugraph")
    print("AniDB scraper skeleton loaded.")
    print("Set ANIDB_USERNAME and ANIDB_PASSWORD env vars to use.")
    print("For now, run: python data/pipeline/seed_data.py")


if __name__ == "__main__":
    asyncio.run(main())
