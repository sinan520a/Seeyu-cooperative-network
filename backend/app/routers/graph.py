from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import NetworkResponse, PathResponse, IntersectionResponse
from ..services import graph_service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/network", response_model=NetworkResponse)
async def get_network(
    seiyuu_id: int = Query(..., description="Center seiyuu ID"),
    depth: int = Query(1, ge=1, le=2, description="Network depth (1 or 2)"),
    db: AsyncSession = Depends(get_db),
):
    return await graph_service.get_network(db, seiyuu_id, depth)


@router.get("/path", response_model=PathResponse)
async def get_path(
    from_: int = Query(..., alias="from"),
    to: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await graph_service.find_path(db, from_, to)
    if result["length"] == -1:
        raise HTTPException(404, "No path found between the two seiyuu")
    return result


@router.get("/intersection", response_model=IntersectionResponse)
async def get_intersection(
    work_a: int = Query(...),
    work_b: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await graph_service.get_intersection(db, work_a, work_b)
