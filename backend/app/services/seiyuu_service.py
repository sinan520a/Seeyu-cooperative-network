from sqlalchemy import select, func, or_, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ..models import Seiyuu, Role, Work, CoAppearance


async def search_seiyuu(
    db: AsyncSession,
    q: str | None = None,
    agency: str | None = None,
    gender: str | None = None,
    birth_from: int | None = None,
    birth_to: int | None = None,
    page: int = 1,
    size: int = 20,
):
    sub = select(Role.seiyuu_id, func.count(Role.id).label("cnt")).group_by(Role.seiyuu_id).subquery()

    stmt = select(
        Seiyuu.id,
        Seiyuu.name_zh,
        Seiyuu.name_ja,
        Seiyuu.gender,
        Seiyuu.agency,
        Seiyuu.debut_year,
        func.coalesce(sub.c.cnt, 0).label("role_count"),
    ).outerjoin(sub, Seiyuu.id == sub.c.seiyuu_id)

    conditions = []
    if q:
        conditions.append(
            or_(
                Seiyuu.name_zh.ilike(f"%{q}%"),
                Seiyuu.name_ja.ilike(f"%{q}%"),
                Seiyuu.name_romaji.ilike(f"%{q}%"),
            )
        )
    if agency:
        conditions.append(Seiyuu.agency.ilike(f"%{agency}%"))
    if gender:
        conditions.append(Seiyuu.gender == gender.upper())
    if birth_from:
        conditions.append(func.extract("year", Seiyuu.birth_date) >= birth_from)
    if birth_to:
        conditions.append(func.extract("year", Seiyuu.birth_date) <= birth_to)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(func.coalesce(sub.c.cnt, 0).desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).all()

    items = [
        {
            "id": r.id,
            "name_zh": r.name_zh,
            "name_ja": r.name_ja,
            "gender": r.gender,
            "agency": r.agency,
            "debut_year": r.debut_year,
            "role_count": r.role_count,
        }
        for r in rows
    ]
    return {"total": total, "items": items}


async def get_seiyuu_detail(db: AsyncSession, seiyuu_id: int):
    seiyuu = await db.get(Seiyuu, seiyuu_id)
    if not seiyuu:
        return None

    role_stmt = (
        select(Role.work_id, Work.title_zh.label("work_title"), Role.character_name, Work.premiere_year.label("year"))
        .join(Work, Role.work_id == Work.id)
        .where(Role.seiyuu_id == seiyuu_id)
        .order_by(Work.premiere_year.desc())
        .limit(200)
    )
    roles = [
        {"work_id": r.work_id, "work_title": r.work_title, "character_name": r.character_name, "year": r.year}
        for r in (await db.execute(role_stmt)).all()
    ]

    co_stmt = (
        select(
            func.coalesce(
                case((CoAppearance.seiyuu_a_id == seiyuu_id, CoAppearance.seiyuu_b_id), else_=CoAppearance.seiyuu_a_id),
                0,
            ).label("co_id"),
            CoAppearance.work_count,
        )
        .where(
            or_(CoAppearance.seiyuu_a_id == seiyuu_id, CoAppearance.seiyuu_b_id == seiyuu_id)
        )
        .order_by(CoAppearance.work_count.desc())
        .limit(10)
    )
    co_rows = (await db.execute(co_stmt)).all()

    co_ids = [r.co_id for r in co_rows if r.co_id]
    co_names = {}
    if co_ids:
        names_stmt = select(Seiyuu.id, Seiyuu.name_zh).where(Seiyuu.id.in_(co_ids))
        co_names = {r.id: r.name_zh for r in (await db.execute(names_stmt)).all()}

    top_co_stars = [
        {"id": r.co_id, "name_zh": co_names.get(r.co_id), "work_count": r.work_count}
        for r in co_rows
    ]

    return {
        "id": seiyuu.id,
        "name_zh": seiyuu.name_zh,
        "name_ja": seiyuu.name_ja,
        "name_romaji": seiyuu.name_romaji,
        "gender": seiyuu.gender,
        "birth_date": seiyuu.birth_date,
        "blood_type": seiyuu.blood_type,
        "height_cm": seiyuu.height_cm,
        "agency": seiyuu.agency,
        "debut_year": seiyuu.debut_year,
        "image_url": seiyuu.image_url,
        "roles": roles,
        "top_co_stars": top_co_stars,
    }
