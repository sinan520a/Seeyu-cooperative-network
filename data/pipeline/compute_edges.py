"""
Compute co-appearance edges from the role table and store them in co_appearance.
Run after importing new data.
"""

import asyncio
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///E:/seyuu/seiyuugraph.db",
)


async def compute():
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Fetch all roles
        rows = (await db.execute(text("SELECT seiyuu_id, work_id FROM role"))).all()

        # Build work -> [seiyuu_ids]
        work_to_seiyuu = defaultdict(set)
        for sid, wid in rows:
            work_to_seiyuu[wid].add(sid)

        # Build seiyuu pairs with shared works
        pairs = defaultdict(lambda: {"count": 0, "works": set()})
        for wid, sids in work_to_seiyuu.items():
            sid_list = sorted(sids)
            for i in range(len(sid_list)):
                for j in range(i + 1, len(sid_list)):
                    a, b = sid_list[i], sid_list[j]
                    key = (a, b) if a < b else (b, a)
                    pairs[key]["count"] += 1
                    pairs[key]["works"].add(wid)

        # Upsert into co_appearance
        await db.execute(text("DELETE FROM co_appearance"))

        for (a, b), data in pairs.items():
            await db.execute(
                text(
                    "INSERT INTO co_appearance (seiyuu_a_id, seiyuu_b_id, work_count, shared_work_ids) "
                    "VALUES (:a, :b, :cnt, :works)"
                ),
                {"a": a, "b": b, "cnt": data["count"], "works": json.dumps(sorted(data["works"]))},
            )

        await db.commit()
        print(f"Computed {len(pairs)} co-appearance edges from {len(work_to_seiyuu)} works.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(compute())
