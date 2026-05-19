const BASE = "/api";

async function request(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export function searchSeiyuu(params) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  }
  return request(`/seiyuu?${qs}`);
}

export function getSeiyuu(id) {
  return request(`/seiyuu/${id}`);
}

export function searchWorks(params) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  }
  return request(`/works?${qs}`);
}

export function getWork(id) {
  return request(`/works/${id}`);
}

export function getNetwork(seiyuuId, depth = 1) {
  return request(`/graph/network?seiyuu_id=${seiyuuId}&depth=${depth}`);
}

export function getPath(fromId, toId) {
  return request(`/graph/path?from=${fromId}&to=${toId}`);
}

export function getIntersection(workA, workB) {
  return request(`/graph/intersection?work_a=${workA}&work_b=${workB}`);
}
