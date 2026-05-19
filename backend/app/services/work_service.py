from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Work, Role, Seiyuu


async def search_works(
    db: AsyncSession,
    q: str | None = None,
    type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    page: int = 1,
    size: int = 20,
):
    stmt = select(Work)
    conditions = []

    if q:
        conditions.append(
            or_(Work.title_zh.ilike(f"%{q}%"), Work.title_ja.ilike(f"%{q}%"))
        )
    if type:
        conditions.append(Work.type == type)
    if year_from:
        conditions.append(Work.premiere_year >= year_from)
    if year_to:
        conditions.append(Work.premiere_year <= year_to)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    rows = (
        (await db.execute(stmt.order_by(Work.premiere_year.desc()).offset((page - 1) * size).limit(size)))
    ).scalars().all()

    items = [
        {
            "id": w.id,
            "title_zh": w.title_zh,
            "title_ja": w.title_ja,
            "type": w.type,
            "premiere_year": w.premiere_year,
            "studio": w.studio,
        }
        for w in rows
    ]
    return {"total": total, "items": items}


async def get_work_detail(db: AsyncSession, work_id: int):
    work = await db.get(Work, work_id)
    if not work:
        return None

    cast_stmt = (
        select(Role.seiyuu_id, Seiyuu.name_zh, Role.character_name)
        .join(Seiyuu, Role.seiyuu_id == Seiyuu.id)
        .where(Role.work_id == work_id)
        .order_by(Seiyuu.name_zh)
    )
    cast = [
        {"seiyuu_id": r.seiyuu_id, "name_zh": r.name_zh, "character_name": r.character_name}
        for r in (await db.execute(cast_stmt)).all()
    ]

    return {
        "id": work.id,
        "title_zh": work.title_zh,
        "title_ja": work.title_ja,
        "type": work.type,
        "premiere_year": work.premiere_year,
        "episodes": work.episodes,
        "studio": work.studio,
        "image_url": work.image_url,
        "cast": cast,
    }
