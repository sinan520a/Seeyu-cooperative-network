import json
from collections import deque

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Seiyuu, Work, Role, CoAppearance


def _parse_ids(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


async def get_network(db: AsyncSession, seiyuu_id: int, depth: int = 1):
    """Return nodes and edges for a 1-degree or 2-degree co-appearance network."""
    center = await db.get(Seiyuu, seiyuu_id)
    if not center:
        return {"nodes": [], "edges": []}

    # Get direct co-stars
    edge_stmt = select(CoAppearance).where(
        or_(CoAppearance.seiyuu_a_id == seiyuu_id, CoAppearance.seiyuu_b_id == seiyuu_id)
    )
    edges_1 = (await db.execute(edge_stmt)).scalars().all()

    seen_ids = {seiyuu_id}
    node_ids = {seiyuu_id}
    all_edges = []

    for e in edges_1:
        other = e.seiyuu_b_id if e.seiyuu_a_id == seiyuu_id else e.seiyuu_a_id
        node_ids.add(other)
        seen_ids.add(other)
        all_edges.append(e)

    # 2-degree: get edges among the direct neighbors
    if depth >= 2:
        neighbor_ids = list(node_ids - {seiyuu_id})
        if neighbor_ids:
            # Edges between the center's neighbors (excluding center)
            second_stmt = select(CoAppearance).where(
                or_(
                    CoAppearance.seiyuu_a_id.in_(neighbor_ids),
                    CoAppearance.seiyuu_b_id.in_(neighbor_ids),
                )
            )
            second_edges = (await db.execute(second_stmt)).scalars().all()
            for e in second_edges:
                # Only include if at least one endpoint is in our neighbor set
                # and both endpoints are in the expanded set
                a_in = e.seiyuu_a_id in node_ids or e.seiyuu_a_id == seiyuu_id
                b_in = e.seiyuu_b_id in node_ids or e.seiyuu_b_id == seiyuu_id
                if a_in or b_in:
                    node_ids.add(e.seiyuu_a_id)
                    node_ids.add(e.seiyuu_b_id)
                    if e not in all_edges:
                        all_edges.append(e)

            # Also get co-stars of neighbors (2nd degree from center)
            for nid in neighbor_ids:
                ext_stmt = select(CoAppearance).where(
                    or_(CoAppearance.seiyuu_a_id == nid, CoAppearance.seiyuu_b_id == nid)
                )
                ext_edges = (await db.execute(ext_stmt)).scalars().all()
                for e in ext_edges:
                    other = e.seiyuu_b_id if e.seiyuu_a_id == nid else e.seiyuu_a_id
                    if other not in seen_ids:
                        node_ids.add(other)
                        seen_ids.add(other)
                    if e not in all_edges:
                        all_edges.append(e)

    # Fetch node names
    seiyuu_rows = (
        (await db.execute(select(Seiyuu.id, Seiyuu.name_zh, Seiyuu.agency).where(Seiyuu.id.in_(list(node_ids)))))
    ).all()
    name_map = {r.id: (r.name_zh, r.agency) for r in seiyuu_rows}

    # Fetch shared work titles for each edge
    all_work_ids = set()
    for e in all_edges:
        wids = _parse_ids(e.shared_work_ids)
        all_work_ids.update(wids)
    work_info = {}
    if all_work_ids:
        work_rows = (await db.execute(
            select(Work.id, Work.title_zh, Work.premiere_year).where(Work.id.in_(list(all_work_ids)))
        )).all()
        work_info = {r.id: (r.title_zh, r.premiere_year) for r in work_rows}

    nodes = [
        {
            "id": nid,
            "name_zh": name_map.get(nid, ("", ""))[0],
            "agency": name_map.get(nid, ("", ""))[1],
            "is_center": nid == seiyuu_id,
        }
        for nid in node_ids
    ]

    edges_out = []
    for e in all_edges:
        wids = _parse_ids(e.shared_work_ids)
        sw = [
            {"id": wid, "title": work_info.get(wid, (None, None))[0], "year": work_info.get(wid, (None, None))[1]}
            for wid in wids
        ]
        edges_out.append({
            "source": e.seiyuu_a_id,
            "target": e.seiyuu_b_id,
            "weight": e.work_count,
            "shared_works": sw,
        })

    return {"nodes": nodes, "edges": edges_out}


async def find_path(db: AsyncSession, from_id: int, to_id: int):
    """BFS shortest path between two seiyuu via co_appearance edges."""
    if from_id == to_id:
        s = await db.get(Seiyuu, from_id)
        return {"path": [{"seiyuu_id": from_id, "name_zh": s.name_zh if s else None, "work_id": None, "title_zh": None}], "length": 0}

    # Build adjacency list from co_appearance table
    edges = (await db.execute(select(CoAppearance))).scalars().all()

    adj = {}  # seiyuu_id -> list of (neighbor_id, shared_work_ids)
    for e in edges:
        adj.setdefault(e.seiyuu_a_id, []).append((e.seiyuu_b_id, _parse_ids(e.shared_work_ids)))
        adj.setdefault(e.seiyuu_b_id, []).append((e.seiyuu_a_id, _parse_ids(e.shared_work_ids)))

    if from_id not in adj or to_id not in adj:
        return {"path": [], "length": -1}

    # BFS
    queue = deque([(from_id, [])])
    visited = {from_id}

    while queue:
        current, path = queue.popleft()
        for neighbor, shared_works in adj.get(current, []):
            if neighbor in visited:
                continue
            if len(shared_works) == 0:
                continue
            work_id = shared_works[0]
            new_step = {"seiyuu_id": neighbor, "work_id": work_id}
            new_path = path + [new_step]
            if neighbor == to_id:
                # Resolve names
                all_sids = {from_id} | {s["seiyuu_id"] for s in new_path}
                all_wids = {s["work_id"] for s in new_path}
                s_rows = (await db.execute(select(Seiyuu.id, Seiyuu.name_zh).where(Seiyuu.id.in_(list(all_sids))))).all()
                s_map = {r.id: r.name_zh for r in s_rows}
                w_rows = (await db.execute(select(Work.id, Work.title_zh).where(Work.id.in_(list(all_wids))))).all()
                w_map = {r.id: r.title_zh for r in w_rows}

                result_path = [{"seiyuu_id": from_id, "name_zh": s_map.get(from_id), "work_id": None, "title_zh": None}]
                for step in new_path:
                    result_path.append({
                        "seiyuu_id": None, "name_zh": None,
                        "work_id": step["work_id"], "title_zh": w_map.get(step["work_id"]),
                    })
                    result_path.append({
                        "seiyuu_id": step["seiyuu_id"], "name_zh": s_map.get(step["seiyuu_id"]),
                        "work_id": None, "title_zh": None,
                    })
                return {"path": result_path, "length": len(new_path)}

            visited.add(neighbor)
            queue.append((neighbor, new_path))

    return {"path": [], "length": -1}


async def get_intersection(db: AsyncSession, work_a_id: int, work_b_id: int):
    """Find seiyuu common to both works."""
    work_a = await db.get(Work, work_a_id)
    work_b = await db.get(Work, work_b_id)

    # Get seiyuu for work A
    roles_a = (await db.execute(
        select(Role.seiyuu_id, Role.character_name).where(Role.work_id == work_a_id)
    )).all()
    # Get seiyuu for work B
    roles_b = (await db.execute(
        select(Role.seiyuu_id, Role.character_name).where(Role.work_id == work_b_id)
    )).all()

    map_a = {r.seiyuu_id: r.character_name for r in roles_a}
    map_b = {r.seiyuu_id: r.character_name for r in roles_b}

    common_ids = set(map_a.keys()) & set(map_b.keys())

    seiyuu_names = {}
    if common_ids:
        rows = (await db.execute(select(Seiyuu.id, Seiyuu.name_zh).where(Seiyuu.id.in_(list(common_ids))))).all()
        seiyuu_names = {r.id: r.name_zh for r in rows}

    common = [
        {
            "id": sid,
            "name_zh": seiyuu_names.get(sid),
            "role_in_a": map_a.get(sid),
            "role_in_b": map_b.get(sid),
        }
        for sid in common_ids
    ]

    return {
        "work_a": {"id": work_a.id, "title_zh": work_a.title_zh, "title_ja": work_a.title_ja, "type": work_a.type, "premiere_year": work_a.premiere_year, "studio": work_a.studio} if work_a else None,
        "work_b": {"id": work_b.id, "title_zh": work_b.title_zh, "title_ja": work_b.title_ja, "type": work_b.type, "premiere_year": work_b.premiere_year, "studio": work_b.studio} if work_b else None,
        "common_seiyuu": common,
    }
