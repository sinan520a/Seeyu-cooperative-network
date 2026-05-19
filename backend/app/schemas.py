from datetime import date
from pydantic import BaseModel


# --- Seiyuu ---

class SeiyuuBrief(BaseModel):
    id: int
    name_zh: str | None = None
    name_ja: str | None = None
    gender: str | None = None
    agency: str | None = None
    debut_year: int | None = None
    role_count: int = 0

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    work_id: int
    work_title: str | None = None
    character_name: str | None = None
    year: int | None = None

    model_config = {"from_attributes": True}


class CoStarBrief(BaseModel):
    id: int
    name_zh: str | None = None
    work_count: int = 0

    model_config = {"from_attributes": True}


class SeiyuuDetail(BaseModel):
    id: int
    name_zh: str | None = None
    name_ja: str | None = None
    name_romaji: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    blood_type: str | None = None
    height_cm: int | None = None
    agency: str | None = None
    debut_year: int | None = None
    image_url: str | None = None
    roles: list[RoleOut] = []
    top_co_stars: list[CoStarBrief] = []

    model_config = {"from_attributes": True}


class SeiyuuListResponse(BaseModel):
    total: int
    items: list[SeiyuuBrief]


# --- Work ---

class WorkBrief(BaseModel):
    id: int
    title_zh: str | None = None
    title_ja: str | None = None
    type: str | None = None
    premiere_year: int | None = None
    studio: str | None = None

    model_config = {"from_attributes": True}


class CastMember(BaseModel):
    seiyuu_id: int
    name_zh: str | None = None
    character_name: str | None = None

    model_config = {"from_attributes": True}


class WorkDetail(BaseModel):
    id: int
    title_zh: str | None = None
    title_ja: str | None = None
    type: str | None = None
    premiere_year: int | None = None
    episodes: int | None = None
    studio: str | None = None
    image_url: str | None = None
    cast: list[CastMember] = []

    model_config = {"from_attributes": True}


class WorkListResponse(BaseModel):
    total: int
    items: list[WorkBrief]


# --- Graph ---

class GraphNode(BaseModel):
    id: int
    name_zh: str | None = None
    agency: str | None = None
    is_center: bool = False


class SharedWork(BaseModel):
    id: int
    title: str | None = None
    year: int | None = None


class GraphEdge(BaseModel):
    source: int
    target: int
    weight: int = 1
    shared_works: list[SharedWork] = []


class NetworkResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathStep(BaseModel):
    seiyuu_id: int | None = None
    name_zh: str | None = None
    work_id: int | None = None
    title_zh: str | None = None


class PathResponse(BaseModel):
    path: list[PathStep]
    length: int


class IntersectionMember(BaseModel):
    id: int
    name_zh: str | None = None
    role_in_a: str | None = None
    role_in_b: str | None = None


class IntersectionResponse(BaseModel):
    work_a: WorkBrief | None = None
    work_b: WorkBrief | None = None
    common_seiyuu: list[IntersectionMember]
