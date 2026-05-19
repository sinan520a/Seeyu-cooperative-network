"""
Bangumi API scraper for seiyuu and work data.

Respects:
- robots.txt (only /pic/, /img/, /js/ disallowed — API paths are fine)
- Rate limit: 1.5s between requests
- User-Agent identifies the project

API docs: https://bangumi.github.io/api/

Usage:
  python data/scraper/bangumi_scraper.py                      # interactive
  python data/scraper/bangumi_scraper.py --seed-top 50         # seed top anime cast
  python data/scraper/bangumi_scraper.py --person-id 1855      # fetch one seiyuu
  python data/scraper/bangumi_scraper.py --subject-id 265      # fetch anime cast
  python data/scraper/bangumi_scraper.py --keyword "花泽"      # search & import
"""

import argparse
import asyncio
import json
import os
import sys
from urllib.parse import quote
import time

import aiohttp

# Force UTF-8 to handle CJK + Korean names (Windows GBK can't encode them)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///E:/seyuu/seiyuugraph.db",
)

# Old API (still works for search)
SEARCH_URL = "https://api.bgm.tv/search/subject"
# v0 API (works for individual resources)
V0_URL = "https://api.bgm.tv/v0"

USER_AGENT = "SeiyuuGraph/0.1 (non-commercial; contact@example.com)"
REQUEST_DELAY = 1.5


class BangumiScraper:
    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url
        self.session: aiohttp.ClientSession | None = None
        self._db = None
        self._engine = None
        self.last_request = 0.0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
        if self._db:
            await self._db.close()
        if self._engine:
            await self._engine.dispose()

    async def _rate_limit(self):
        elapsed = time.monotonic() - self.last_request
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)

    async def _get(self, url: str, retries: int = 3) -> dict | list | None:
        """GET with rate limiting and retry."""
        await self._rate_limit()
        for attempt in range(retries):
            try:
                self.last_request = time.monotonic()
                async with self.session.get(url) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status == 429:
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    text = await resp.text()
                    return json.loads(text)
            except (aiohttp.ClientError, json.JSONDecodeError) as e:
                if attempt == retries - 1:
                    print(f"  [error] {type(e).__name__}: {e}")
                    return None
                await asyncio.sleep(2)
        return None

    # ── Search ───────────────────────────────────────────────────────

    async def search_subjects(self, keyword: str, limit: int = 10) -> list[dict]:
        """Search for anime subjects. Uses old API (v0 search is offline)."""
        url = f"{SEARCH_URL}/{quote(keyword)}?type=2&responseGroup=medium&max_results={limit}"
        data = await self._get(url)
        return data.get("list", []) if data else []

    async def search_persons_via_works(self, keyword: str, limit: int = 5) -> list[dict]:
        """Search for seiyuu by searching an anime first, then extracting its cast.

        This is a workaround because Bangumi's person search endpoint is offline.
        """
        subjects = await self.search_subjects(keyword, limit=1)
        if not subjects:
            print(f"  No anime found for '{keyword}'")
            return []

        subject_id = subjects[0]["id"]
        title = subjects[0].get("name_cn", subjects[0].get("name", "?"))
        print(f"  Searching cast of: {title} (id={subject_id})")

        persons = await self.get_subject_characters(subject_id)
        # Filter to voice actors only
        va_list = persons  # characters endpoint returns only voice actors

        # Sort by relevance (heuristic: characters with more lines are listed first)
        results = []
        seen = set()
        for p in va_list:
            pid = p["id"]
            if pid in seen:
                continue
            seen.add(pid)
            results.append({
                "id": pid,
                "name": p.get("name", ""),
                "name_cn": p.get("name_cn", ""),
            })

        print(f"  Found {len(results)} voice actors")
        return results[:limit]

    # ── Person API ───────────────────────────────────────────────────

    async def get_person(self, person_id: int) -> dict | None:
        return await self._get(f"{V0_URL}/persons/{person_id}")

    async def get_person_subjects(self, person_id: int) -> list[dict]:
        """Get all anime works a seiyuu appeared in. Filters to anime type only."""
        data = await self._get(f"{V0_URL}/persons/{person_id}/subjects")
        if not data:
            return []
        results = []
        for item in data:
            # Handle both old format (nested "subject" key) and new format (flat)
            if "subject" in item:
                subject = item["subject"]
                if not subject:
                    continue
                subject["_character_name"] = item.get("name", "")
                subject["_staff"] = item.get("staff", "")
            else:
                # New format: item is the subject itself
                subject = dict(item)
                subject["_character_name"] = ""
                subject["_staff"] = item.get("staff", "")
            # Only anime: type 2=TV, 6=Movie
            if subject.get("type") not in (2, 6):
                continue
            results.append(subject)
        return results

    # ── Subject API ──────────────────────────────────────────────────

    async def get_subject(self, subject_id: int) -> dict | None:
        return await self._get(f"{V0_URL}/subjects/{subject_id}")

    async def get_subject_characters(self, subject_id: int) -> list[dict]:
        """Get characters with their voice actors for a subject."""
        data = await self._get(f"{V0_URL}/subjects/{subject_id}/characters")
        if not data:
            return []
        results = []
        for char in data:
            for actor in char.get("actors", []):
                actor["_character_name"] = char.get("name", "")
                actor["_relation"] = char.get("relation", "")
                results.append(actor)
        return results

    # ── Database ─────────────────────────────────────────────────────

    async def _init_db(self):
        if not self._engine:
            self._engine = create_async_engine(self.db_url)
            self._db = async_sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)()
            # Ensure columns exist
            async with self._engine.begin() as conn:
                try:
                    await conn.execute(text("ALTER TABLE seiyuu ADD COLUMN bangumi_id VARCHAR(20)"))
                except Exception:
                    pass
                try:
                    await conn.execute(text("ALTER TABLE work ADD COLUMN bangumi_id VARCHAR(20)"))
                except Exception:
                    pass

    async def _get_db(self) -> AsyncSession:
        if not self._db:
            await self._init_db()
        return self._db

    async def upsert_seiyuu(self, person: dict) -> int | None:
        db = await self._get_db()
        bangumi_id = str(person["id"])

        # Parse infobox
        infobox = {}
        for item in person.get("infobox", []):
            k = item.get("key", "")
            v = item.get("value", "")
            if isinstance(v, list):
                v = ", ".join(str(x.get("v", x)) if isinstance(x, dict) else str(x) for x in v)
            infobox[k] = str(v).strip() if v else ""

        name_zh = person.get("name_cn", "") or person.get("name", "")
        name_ja = person.get("name", "") if person.get("name_cn") else ""
        name_romaji = infobox.get("罗马字", "") or infobox.get("Romaji", "")
        gender = "F" if person.get("gender") == "female" else ("M" if person.get("gender") == "male" else None)
        blood_type = person.get("blood_type") or infobox.get("血型", "")
        agency = infobox.get("所属公司", "") or infobox.get("Website", "")

        birth_year = person.get("birth_year") or 0
        birth_mon = person.get("birth_mon") or 1
        birth_day = person.get("birth_day") or 1
        birth_date = None
        if birth_year:
            birth_date = f"{birth_year}-{birth_mon:02d}-{birth_day:02d}"

        height_cm = None
        height_str = infobox.get("身高", "")
        if height_str and "cm" in height_str:
            try:
                height_cm = int(height_str.replace("cm", "").strip())
            except ValueError:
                pass

        # Check existing
        result = await db.execute(
            text("SELECT id FROM seiyuu WHERE bangumi_id = :bid"), {"bid": bangumi_id}
        )
        existing = result.first()

        params = {
            "name_zh": name_zh or name_ja,
            "name_ja": name_ja or None,
            "name_romaji": name_romaji or None,
            "gender": gender,
            "birth_date": birth_date,
            "blood_type": blood_type or None,
            "height_cm": height_cm,
            "agency": agency or None,
            "bangumi_id": bangumi_id,
        }

        if existing:
            await db.execute(
                text(
                    "UPDATE seiyuu SET name_zh=:name_zh, name_ja=:name_ja, name_romaji=:name_romaji, "
                    "gender=:gender, birth_date=:birth_date, blood_type=:blood_type, "
                    "height_cm=:height_cm, agency=:agency WHERE id=:id"
                ),
                {**params, "id": existing.id},
            )
            return existing.id
        else:
            await db.execute(
                text(
                    "INSERT INTO seiyuu (name_zh, name_ja, name_romaji, gender, birth_date, blood_type, height_cm, agency, bangumi_id) "
                    "VALUES (:name_zh, :name_ja, :name_romaji, :gender, :birth_date, :blood_type, :height_cm, :agency, :bangumi_id)"
                ),
                params,
            )
            result = await db.execute(text("SELECT last_insert_rowid()"))
            return result.scalar()

    async def upsert_work(self, subject: dict) -> int | None:
        db = await self._get_db()
        bangumi_id = str(subject["id"])

        title_zh = subject.get("name_cn", "") or subject.get("name", "")
        title_ja = subject.get("name", "") if subject.get("name_cn") else ""
        type_map = {1: "Book", 2: "TV", 3: "Music", 4: "Game", 6: "Other"}
        work_type = type_map.get(subject.get("type", 2), "TV")

        premiere_year = None
        date_str = subject.get("date", "") or ""
        if date_str and len(date_str) >= 4:
            try:
                premiere_year = int(date_str[:4])
            except ValueError:
                pass

        episodes = subject.get("eps") or subject.get("total_episodes", None)

        # Studio from infobox
        studio = ""
        for item in subject.get("infobox", []):
            if item.get("key") in ("动画制作", "Studio", "製作"):
                v = item.get("value", "")
                if isinstance(v, list):
                    v = ", ".join(str(x.get("v", x)) if isinstance(x, dict) else str(x) for x in v)
                studio = str(v).strip()
                break

        result = await db.execute(
            text("SELECT id FROM work WHERE bangumi_id = :bid"), {"bid": bangumi_id}
        )
        existing = result.first()

        params = {
            "title_zh": title_zh or title_ja,
            "title_ja": title_ja or None,
            "type": work_type,
            "premiere_year": premiere_year,
            "episodes": episodes,
            "studio": studio or None,
            "bangumi_id": bangumi_id,
        }

        if existing:
            await db.execute(
                text(
                    "UPDATE work SET title_zh=:title_zh, title_ja=:title_ja, type=:type, "
                    "premiere_year=:premiere_year, episodes=:episodes, studio=:studio WHERE id=:id"
                ),
                {**params, "id": existing.id},
            )
            return existing.id
        else:
            await db.execute(
                text(
                    "INSERT INTO work (title_zh, title_ja, type, premiere_year, episodes, studio, bangumi_id) "
                    "VALUES (:title_zh, :title_ja, :type, :premiere_year, :episodes, :studio, :bangumi_id)"
                ),
                params,
            )
            result = await db.execute(text("SELECT last_insert_rowid()"))
            return result.scalar()

    async def upsert_role(self, seiyuu_local_id: int, work_local_id: int, character_name: str):
        db = await self._get_db()
        await db.execute(
            text(
                "INSERT OR IGNORE INTO role (seiyuu_id, work_id, character_name) "
                "VALUES (:sid, :wid, :char)"
            ),
            {"sid": seiyuu_local_id, "wid": work_local_id, "char": character_name or ""},
        )

    async def commit(self):
        if self._db:
            await self._db.commit()

    # ── BFS crawl ──────────────────────────────────────────────────────

    async def crawl_network(self, target_seiyuu: int = 5000):
        """BFS expansion: iterate seiyuu → fetch their works → discover new seiyuu → repeat."""
        db = await self._get_db()
        expanded_bgm_ids = set()  # Track which Bangumi person IDs we've already queried

        while True:
            # Count current state
            total_s = (await db.execute(text("SELECT COUNT(*) FROM seiyuu"))).scalar()
            total_w = (await db.execute(text("SELECT COUNT(*) FROM work"))).scalar()
            print(f"\n=== Seiyuu: {total_s} | Works: {total_w} | Target: {target_seiyuu} ===")

            if total_s >= target_seiyuu:
                print("Target reached!")
                break

            # Pick seiyuu with most roles first (established VA → more works → more discoveries).
            # Skip already-expanded Bangumi IDs.
            if expanded_bgm_ids:
                placeholders = ",".join(f":p{i}" for i in range(len(expanded_bgm_ids)))
                result = await db.execute(
                    text(
                        f"SELECT s.id, s.bangumi_id, s.name_zh, "
                        f"(SELECT COUNT(*) FROM role WHERE seiyuu_id = s.id) AS rc "
                        f"FROM seiyuu s "
                        f"WHERE s.bangumi_id IS NOT NULL AND s.bangumi_id != '' "
                        f"AND s.bangumi_id NOT IN ({placeholders}) "
                        f"ORDER BY rc DESC "
                        f"LIMIT 30"
                    ),
                    {f"p{i}": bid for i, bid in enumerate(expanded_bgm_ids)},
                )
            else:
                result = await db.execute(
                    text(
                        "SELECT s.id, s.bangumi_id, s.name_zh, "
                        "(SELECT COUNT(*) FROM role WHERE seiyuu_id = s.id) AS rc "
                        "FROM seiyuu s "
                        "WHERE s.bangumi_id IS NOT NULL AND s.bangumi_id != '' "
                        "ORDER BY rc DESC "
                        "LIMIT 30"
                    )
                )
            batch = result.fetchall()
            if not batch:
                print("No more seiyuu to expand.")
                break

            print(f"Processing batch of {len(batch)} seiyuu (lowest role counts first)...")

            # Collect all works found in this batch to fetch their full casts
            # Track bangumi_id -> local_db_id mapping
            new_works_fetched = {}  # bangumi_id -> local_work_id
            processed = 0

            for row in batch:
                local_id, bgm_id, name, role_count = row[0], row[1], row[2], row[3]
                processed += 1
                expanded_bgm_ids.add(bgm_id)
                print(f"  [{processed}/{len(batch)}] {name} (bgm={bgm_id}, roles={role_count})")

                # Fetch this seiyuu's works from Bangumi
                subjects = await self.get_person_subjects(int(bgm_id))
                print(f"    -> {len(subjects)} anime works on Bangumi")

                for subject in subjects:
                    work_local_id = await self.upsert_work(subject)
                    char_name = subject.get("_character_name", "")
                    await self.upsert_role(local_id, work_local_id, char_name)

                    # If this work is new to us, queue its full cast fetch
                    work_bgm_id = str(subject["id"])
                    if work_bgm_id not in new_works_fetched:
                        new_works_fetched[work_bgm_id] = work_local_id

                await self.commit()

            # Now fetch full cast for each newly discovered work
            print(f"\n  Fetching full cast for {len(new_works_fetched)} works...")
            for i, (bgm_id, local_work_id) in enumerate(new_works_fetched.items()):
                if (i + 1) % 10 == 0:
                    total_s = (await db.execute(text("SELECT COUNT(*) FROM seiyuu"))).scalar()
                    print(f"    ... {i+1}/{len(new_works_fetched)} (seiyuu: {total_s})")
                try:
                    await self._fetch_work_cast(int(bgm_id), local_work_id)
                except Exception as e:
                    print(f"    [error] work {bgm_id}: {e}")

            await self.commit()
            print(f"  Batch complete. Seiyuu: {(await db.execute(text('SELECT COUNT(*) FROM seiyuu'))).scalar()}")

    async def _fetch_work_cast(self, subject_id: int, work_local_id: int):
        """Fetch characters/cast for a work, with full person details for new seiyuu."""
        persons = await self.get_subject_characters(subject_id)
        for person in persons:
            seiyuu_local_id = await self.upsert_seiyuu(person)
            char_name = person.get("_character_name", "")
            await self.upsert_role(seiyuu_local_id, work_local_id, char_name)

            # Fetch full person details if this seiyuu is missing info
            # (characters endpoint only returns name + id, no gender/birth/agency)
            db = await self._get_db()
            row = (await db.execute(
                text("SELECT gender, birth_date, agency FROM seiyuu WHERE id = :id"),
                {"id": seiyuu_local_id},
            )).first()
            if row and (row[0] is None or row[1] is None or row[2] is None):
                try:
                    full_person = await self.get_person(person["id"])
                    if full_person:
                        await self.upsert_seiyuu(full_person)
                except Exception:
                    pass  # thin data is better than nothing

    async def backfill_person_info(self, limit: int | None = None):
        """Fetch full person details for seiyuu missing gender/birth_date/agency.

        The characters endpoint returns thin actor data (name + id only).
        This method calls /v0/persons/{id} for each seiyuu needing details.
        """
        db = await self._get_db()

        result = await db.execute(
            text(
                "SELECT id, bangumi_id, name_zh FROM seiyuu "
                "WHERE bangumi_id IS NOT NULL AND bangumi_id != '' "
                "AND (gender IS NULL OR birth_date IS NULL OR agency IS NULL) "
                "ORDER BY id"
            )
        )
        rows = result.fetchall()
        total = len(rows)
        if limit:
            rows = rows[:limit]
        print(f"\n=== Backfill: {len(rows)} of {total} seiyuu need details ===")

        updated = 0
        skipped = 0
        errors = 0
        for i, row in enumerate(rows):
            local_id, bgm_id, name = row[0], row[1], row[2]
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(rows)}] updated={updated} skipped={skipped} errors={errors}")

            try:
                person = await self.get_person(int(bgm_id))
                if not person:
                    skipped += 1
                    continue

                # Only update if we got meaningful new data
                has_new = (
                    person.get("gender")
                    or person.get("birth_year")
                    or person.get("blood_type")
                    or any(
                        item.get("key") in ("所属公司", "血型", "Website")
                        for item in person.get("infobox", [])
                    )
                )
                if has_new:
                    await self.upsert_seiyuu(person)
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [error] {name} (bgm={bgm_id}): {e}")

            if (i + 1) % 20 == 0:
                await self.commit()

        await self.commit()
        print(f"  Done: updated={updated} skipped={skipped} errors={errors}")

    # ── High-level operations ─────────────────────────────────────────

    async def fetch_person_with_works(self, person_id: int):
        """Fetch a seiyuu and all their works."""
        print(f"Fetching person {person_id}...")
        person = await self.get_person(person_id)
        if not person:
            print(f"  Person {person_id} not found")
            return

        local_id = await self.upsert_seiyuu(person)
        name = person.get("name_cn", person.get("name", "?"))
        print(f"  Seiyuu: {name} (local id={local_id})")

        subjects = await self.get_person_subjects(person_id)
        print(f"  Found {len(subjects)} works")
        count = 0
        for subject in subjects:
            work_local_id = await self.upsert_work(subject)
            char_name = subject.get("_character_name", "")
            await self.upsert_role(local_id, work_local_id, char_name)
            count += 1
            if count % 20 == 0:
                print(f"    ... {count}/{len(subjects)}")

        await self.commit()
        print(f"  Done: {count} roles imported")

    async def fetch_subject_cast(self, subject_id: int):
        """Fetch an anime and its entire voice cast."""
        print(f"Fetching subject {subject_id}...")
        subject = await self.get_subject(subject_id)
        if not subject:
            print(f"  Subject {subject_id} not found")
            return

        work_local_id = await self.upsert_work(subject)
        name = subject.get("name_cn", subject.get("name", "?"))
        print(f"  Work: {name} (local id={work_local_id})")

        persons = await self.get_subject_characters(subject_id)
        va_persons = persons  # characters endpoint returns only voice actors
        print(f"  Found {len(va_persons)} voice actors")

        for person in va_persons:
            seiyuu_local_id = await self.upsert_seiyuu(person)
            char_name = person.get("_character_name", "")
            await self.upsert_role(seiyuu_local_id, work_local_id, char_name)

        await self.commit()
        print(f"  Done: {len(va_persons)} roles imported")

    async def seed_top_anime(self, count: int = 50):
        """Import anime and voice actor data by searching popular titles."""
        popular_titles = [
            "新世纪福音战士", "星际牛仔", "攻壳机动队", "混沌武士",
            "钢之炼金术师", "命运石之门", "魔法少女小圆",
            "无头骑士异闻录", "未闻花名", "冰菓", "Free!",
            "刀剑神域", "进击的巨人", "CLANNAD", "幸运星",
            "凉宫春日的忧郁", "夏目友人帐", "虫师",
            "四月是你的谎言", "吹响吧上低音号",
            "紫罗兰永恒花园", "咒术回战", "间谍过家家",
            "葬送的芙莉莲", "Re从零开始的异世界生活",
            "鬼灭之刃", "轻音少女", "你的名字",
            "千与千寻", "天气之子", "龙猫",
            "Fate stay night", "三月的狮子",
            "小林家的龙女仆", "阿松", "黑执事",
            "野良神", "工作细胞", "齐木楠雄的灾难",
        ]

        imported = 0
        for title in popular_titles:
            if imported >= count:
                break
            print(f"\n[{imported+1}/{count}] Searching: {title}")
            subjects = await self.search_subjects(title, limit=1)
            if not subjects:
                print(f"  No results")
                continue
            sid = subjects[0]["id"]
            name = subjects[0].get("name_cn", subjects[0].get("name", "?"))
            print(f"  Found: {name} (id={sid})")
            await self.fetch_subject_cast(sid)
            imported += 1


async def interactive(scraper: BangumiScraper):
    print("\n" + "=" * 50)
    print("  SeiyuuGraph Bangumi Scraper")
    print("=" * 50)
    print("\nCommands:")
    print("  s <name>       搜索动漫 → 提取声优卡司")
    print("  p <person_id>   获取声优详情 + 全部作品")
    print("  w <subject_id>  获取动漫详情 + 全部卡司")
    print("  q               退出")
    print()

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue
        if cmd == "q":
            break
        if cmd.startswith("s "):
            keyword = cmd[2:]
            print(f"  搜索 '{keyword}' 的卡司...")
            persons = await scraper.search_persons_via_works(keyword, limit=10)
            if not persons:
                print("  未找到声优")
                continue
            for p in persons:
                print(f"  [{p['id']}] {p.get('name_cn', '')} / {p['name']}")
        elif cmd.startswith("p "):
            await scraper.fetch_person_with_works(int(cmd[2:]))
        elif cmd.startswith("w "):
            await scraper.fetch_subject_cast(int(cmd[2:]))
        else:
            print("  未知命令")

    print("Done.")


async def main():
    parser = argparse.ArgumentParser(description="Bangumi API Scraper for SeiyuuGraph")
    parser.add_argument("--person-id", type=int, help="Fetch a person by Bangumi ID")
    parser.add_argument("--subject-id", type=int, help="Fetch a subject by Bangumi ID")
    parser.add_argument("--keyword", type=str, help="Search keyword (via anime cast lookup)")
    parser.add_argument("--seed-top", type=int, metavar="N", help="Import top N anime + casts")
    parser.add_argument("--crawl", type=int, metavar="N", help="BFS crawl to reach N seiyuu")
    parser.add_argument("--backfill", action="store_true", help="Backfill missing person details (gender, birth, agency)")
    parser.add_argument("--backfill-limit", type=int, metavar="N", help="Limit backfill to N seiyuu")
    parser.add_argument("--db-url", type=str, default=DATABASE_URL, help="Database URL")
    args = parser.parse_args()

    async with BangumiScraper(args.db_url) as scraper:
        if args.person_id:
            await scraper.fetch_person_with_works(args.person_id)
        elif args.subject_id:
            await scraper.fetch_subject_cast(args.subject_id)
        elif args.keyword:
            persons = await scraper.search_persons_via_works(args.keyword, limit=5)
            for p in persons:
                print(f"\n  [{p['id']}] {p.get('name_cn', '')} / {p['name']}")
                await scraper.fetch_person_with_works(p["id"])
        elif args.seed_top:
            await scraper.seed_top_anime(args.seed_top)
        elif args.crawl:
            await scraper.crawl_network(args.crawl)
        elif args.backfill:
            await scraper.backfill_person_info(limit=args.backfill_limit)
        else:
            await interactive(scraper)


if __name__ == "__main__":
    asyncio.run(main())
