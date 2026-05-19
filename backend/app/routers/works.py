from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import WorkListResponse, WorkDetail
from ..services import work_service

router = APIRouter(prefix="/api/works", tags=["works"])


@router.get("", response_model=WorkListResponse)
async def list_works(
    q: str | None = None,
    type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await work_service.search_works(db, q, type, year_from, year_to, page, size)


@router.get("/{work_id}", response_model=WorkDetail)
async def get_work(work_id: int, db: AsyncSession = Depends(get_db)):
    result = await work_service.get_work_detail(db, work_id)
    if not result:
        raise HTTPException(404, "Work not found")
    return result
