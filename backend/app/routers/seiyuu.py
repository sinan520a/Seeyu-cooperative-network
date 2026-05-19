from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import SeiyuuListResponse, SeiyuuDetail
from ..services import seiyuu_service

router = APIRouter(prefix="/api/seiyuu", tags=["seiyuu"])


@router.get("", response_model=SeiyuuListResponse)
async def list_seiyuu(
    q: str | None = None,
    agency: str | None = None,
    gender: str | None = None,
    birth_from: int | None = None,
    birth_to: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await seiyuu_service.search_seiyuu(db, q, agency, gender, birth_from, birth_to, page, size)


@router.get("/{seiyuu_id}", response_model=SeiyuuDetail)
async def get_seiyuu(seiyuu_id: int, db: AsyncSession = Depends(get_db)):
    result = await seiyuu_service.get_seiyuu_detail(db, seiyuu_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(404, "Seiyuu not found")
    return result
