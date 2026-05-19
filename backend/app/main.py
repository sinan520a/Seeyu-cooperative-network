import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from .database import engine, Base, async_session
from .routers import seiyuu, works, graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="SeiyuuGraph API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(seiyuu.router)
app.include_router(works.router)
app.include_router(graph.router)


@app.get("/api/stats")
async def get_stats():
    async with async_session() as db:
        result = await db.execute(text(
            "SELECT "
            "(SELECT COUNT(*) FROM seiyuu) AS seiyuu_count, "
            "(SELECT COUNT(*) FROM work) AS work_count, "
            "(SELECT COUNT(*) FROM role) AS role_count, "
            "(SELECT COUNT(*) FROM co_appearance) AS edge_count"
        ))
        row = result.first()
        return {
            "seiyuu_count": row.seiyuu_count,
            "work_count": row.work_count,
            "role_count": row.role_count,
            "edge_count": row.edge_count,
        }


# Serve frontend static files in production
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
