import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import * as d3 from "d3";
import { getNetwork, getPath, getSeiyuu } from "../api/client";
import styles from "./NetworkGraph.module.css";

const NODE_R = 4;
const CENTER_R = 10;
const PATH_R = 7;
const CHARGE = -350;
const LINK_DIST = 100;

// ── Pure drawing helpers ───────────────────────────────────────────────

function nodeRadius(d, pathIds) {
  if (d.isCenter) return CENTER_R;
  if (pathIds.has(d.id)) return PATH_R;
  return d.level === 1 ? NODE_R + 2 : NODE_R;
}

function hitTest(wx, wy, nodes, pathIds) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    const r = nodeRadius(n, pathIds) + 5;
    const dx = n.x - wx;
    const dy = n.y - wy;
    if (dx * dx + dy * dy <= r * r) return n;
  }
  return null;
}

function drawGraph(ctx, w, h, t, graph, opts) {
  const { nodes, edges, nodeMap } = graph;
  const { hovered, pathIds, pathEdgeKeys, threshold, timelineYear, centerId } = opts;

  // Filter visible
  const visibleEdges = [];
  const visibleNodes = new Set();
  if (centerId != null) visibleNodes.add(String(centerId));

  for (const e of edges) {
    if (e.weight < threshold) continue;
    if (timelineYear != null) {
      if (!(e.shared_works || []).some(ww => !ww.year || ww.year <= timelineYear)) continue;
    }
    visibleEdges.push(e);
    visibleNodes.add(e.sourceId);
    visibleNodes.add(e.targetId);
  }

  ctx.save();
  ctx.clearRect(0, 0, w, h);
  ctx.translate(t.x, t.y);
  ctx.scale(t.k, t.k);

  // ── Edges: default batch ──
  ctx.beginPath();
  ctx.strokeStyle = "rgba(74,96,128,0.22)";
  ctx.lineWidth = 0.5;
  for (const e of visibleEdges) {
    if (pathEdgeKeys.has(e.id)) continue;
    if (hovered && (e.sourceId === hovered || e.targetId === hovered)) continue;
    const src = nodeMap.get(e.sourceId), tgt = nodeMap.get(e.targetId);
    if (!src || !tgt) continue;
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
  }
  ctx.stroke();

  // ── Edges: hover highlight ──
  if (hovered) {
    ctx.beginPath();
    ctx.strokeStyle = "rgba(240,192,96,0.65)";
    ctx.lineWidth = 2;
    for (const e of visibleEdges) {
      if (e.sourceId !== hovered && e.targetId !== hovered) continue;
      if (pathEdgeKeys.has(e.id)) continue;
      const src = nodeMap.get(e.sourceId), tgt = nodeMap.get(e.targetId);
      if (!src || !tgt) continue;
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
    }
    ctx.stroke();
  }

  // ── Edges: path highlight ──
  if (pathEdgeKeys.size > 0) {
    ctx.beginPath();
    ctx.strokeStyle = "#ff6b9d";
    ctx.lineWidth = 3;
    for (const e of visibleEdges) {
      if (!pathEdgeKeys.has(e.id)) continue;
      const src = nodeMap.get(e.sourceId), tgt = nodeMap.get(e.targetId);
      if (!src || !tgt) continue;
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
    }
    ctx.stroke();
  }

  // ── Nodes ──
  const hoverNeighbors = new Set();
  if (hovered) {
    for (const e of edges) {
      if (e.sourceId === hovered) hoverNeighbors.add(e.targetId);
      if (e.targetId === hovered) hoverNeighbors.add(e.sourceId);
    }
  }

  for (const n of nodes) {
    if (!visibleNodes.has(n.id) && !n.isCenter) continue;

    const r = nodeRadius(n, pathIds);
    const isPath = pathIds.has(n.id);
    const isHovered = hovered === n.id;
    const isNeighbor = hoverNeighbors.has(n.id);
    const isDimmed = hovered && !isHovered && !isNeighbor;

    if (isHovered || isNeighbor) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + (isHovered ? 5 : 3), 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? "rgba(240,192,96,0.25)" : "rgba(240,192,96,0.12)";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);

    if (isPath) ctx.fillStyle = "#ff6b9d";
    else if (n.isCenter) ctx.fillStyle = "#f0c060";
    else if (n.level === 1) ctx.fillStyle = "#5a9cf5";
    else ctx.fillStyle = "#3a5a8a";

    ctx.globalAlpha = isDimmed ? 0.25 : (n.level === 2 && !isPath ? 0.7 : 1);
    ctx.fill();
    ctx.globalAlpha = 1;

    ctx.strokeStyle = n.isCenter ? "#f5d080" : isPath ? "#ff8db5" : "rgba(255,255,255,0.18)";
    ctx.lineWidth = n.isCenter ? 2 : 1;
    ctx.stroke();
  }

  // ── Node labels ──
  const showLabels = t.k >= 0.35;
  if (showLabels) {
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";

    for (const n of nodes) {
      if (!visibleNodes.has(n.id)) continue;
      if (n.isCenter) continue;
      if (n.level === 1) {
        const r = nodeRadius(n, pathIds);
        const isDimmed = hovered && !hoverNeighbors.has(n.id) && hovered !== n.id;
        ctx.fillStyle = isDimmed ? "rgba(200,210,225,0.4)" : "rgba(200,210,225,0.85)";
        ctx.font = "8px sans-serif";
        ctx.fillText(n.name, n.x, n.y - r - 3);
      }
    }

    const centerNode = nodes.find(n => n.isCenter);
    if (centerNode && visibleNodes.has(centerNode.id)) {
      ctx.fillStyle = "#f0c060";
      ctx.font = "bold 11px sans-serif";
      ctx.fillText(centerNode.name, centerNode.x, centerNode.y - CENTER_R - 6);
    }
  }

  ctx.restore();
}

// ── Component ──────────────────────────────────────────────────────────

export default function NetworkGraph({ centerId, centerName, onCenterChange, onBack, canGoBack }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const tooltipRef = useRef(null);
  const simRef = useRef(null);
  const navigate = useNavigate();

  const graphRef = useRef({ nodes: [], edges: [], nodeMap: new Map() });
  const zoomRef = useRef(null);
  const transformRef = useRef(d3.zoomIdentity);
  const hoveredRef = useRef(null);
  const dragRef = useRef(null);
  const pathNodeIdsRef = useRef(new Set());
  const pathEdgeKeysRef = useRef(new Set());
  const filterRef = useRef({ threshold: 1, timelineYear: null, centerId: null });
  const drawRafRef = useRef(null);
  const dprRef = useRef(1);

  // React state
  const [depth, setDepth] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState([]);
  const [pathInfo, setPathInfo] = useState(null);
  const [threshold, setThreshold] = useState(1);
  const [maxWeight, setMaxWeight] = useState(1);
  const [timelineYear, setTimelineYear] = useState(null);
  const [timelinePlaying, setTimelinePlaying] = useState(false);
  const [timelineRange, setTimelineRange] = useState([0, 0]);
  const [floatingPerson, setFloatingPerson] = useState(null);
  const [dimensions, setDimensions] = useState({ w: 800, h: 600 });
  const [canvasReady, setCanvasReady] = useState(false);

  // ── Tooltip ──────────────────────────────────────────────────────────
  const showTooltip = useCallback((e, works) => {
    const tip = tooltipRef.current;
    if (!tip) return;
    tip.innerHTML = "";
    tip.style.display = "block";
    works.forEach((w) => {
      const row = document.createElement("div");
      row.className = styles.tooltipRow;
      row.textContent = w.year ? `${w.title} (${w.year})` : w.title;
      tip.appendChild(row);
    });
    const rect = tip.getBoundingClientRect();
    let x = e.clientX + 14;
    let y = e.clientY - rect.height / 2;
    if (x + rect.width > window.innerWidth - 10) x = e.clientX - rect.width - 14;
    if (y < 10) y = 10;
    if (y + rect.height > window.innerHeight - 10) y = window.innerHeight - rect.height - 10;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }, []);

  const hideTooltip = useCallback(() => {
    if (tooltipRef.current) tooltipRef.current.style.display = "none";
  }, []);

  const showTooltipForNode = useCallback((event, node) => {
    const { edges } = graphRef.current;
    const connected = edges.filter(e => e.sourceId === node.id || e.targetId === node.id);
    const worksMap = new Map();
    connected.forEach(e => {
      (e.shared_works || []).forEach(w => {
        if (!worksMap.has(w.id)) worksMap.set(w.id, w);
      });
    });
    const works = [...worksMap.values()]
      .sort((a, b) => (b.year || 0) - (a.year || 0))
      .slice(0, 12);
    if (works.length > 0) showTooltip(event, works);
  }, [showTooltip]);

  // ── Draw scheduling ──────────────────────────────────────────────────
  const drawRef = useRef(() => {});
  drawRef.current = () => {
    const ctx = ctxRef.current;
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    const dpr = dprRef.current;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    drawGraph(ctx, w, h, transformRef.current, graphRef.current, {
      hovered: hoveredRef.current,
      pathIds: pathNodeIdsRef.current,
      pathEdgeKeys: pathEdgeKeysRef.current,
      ...filterRef.current,
    });
  };

  const scheduleDrawRef = useRef(() => {});
  scheduleDrawRef.current = () => {
    if (drawRafRef.current) return;
    drawRafRef.current = requestAnimationFrame(() => {
      drawRafRef.current = null;
      drawRef.current();
    });
  };

  // ── Canvas + zoom + sim init (runs once) ─────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const updateCanvasSize = () => {
      if (!container || !canvas) return;
      const { width, height } = container.getBoundingClientRect();
      if (width === 0 || height === 0) return;
      const dpr = window.devicePixelRatio || 1;
      dprRef.current = dpr;
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        canvas.style.width = width + "px";
        canvas.style.height = height + "px";
        const ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);
        ctxRef.current = ctx;
      }
      setDimensions({ w: width, h: height });
      setCanvasReady(true);
    };
    updateCanvasSize();
    window.addEventListener("resize", updateCanvasSize);

    // Zoom — simple, no hit-testing in filter
    const zoom = d3.zoom()
      .scaleExtent([0.05, 6])
      .filter((event) => {
        if (event.type === "dblclick") return false;
        return true;
      })
      .on("zoom", (event) => {
        transformRef.current = event.transform;
        scheduleDrawRef.current();
      });

    d3.select(canvas).call(zoom).on("dblclick.zoom", null);
    zoomRef.current = zoom;

    // Force simulation — persisted across center changes
    const sim = d3.forceSimulation()
      .force("charge", d3.forceManyBody().strength(CHARGE))
      .force("center", d3.forceCenter(dimensions.w / 2, dimensions.h / 2))
      .force("collide", d3.forceCollide().radius(CENTER_R + 6))
      .alphaDecay(0.06)
      .alphaMin(0.005)
      .on("tick", () => {
        scheduleDrawRef.current();
      })
      .on("end", () => {
        if (drawRafRef.current) {
          cancelAnimationFrame(drawRafRef.current);
          drawRafRef.current = null;
        }
        drawRef.current();
      });
    simRef.current = sim;

    // ── Pointer event handlers (capture phase for node interception) ──

    const onPointerDown = (event) => {
      const t = transformRef.current;
      const [mx, my] = d3.pointer(event, canvas);
      const wx = (mx - t.x) / t.k;
      const wy = (my - t.y) / t.k;
      const hit = hitTest(wx, wy, graphRef.current.nodes, pathNodeIdsRef.current);

      if (hit) {
        // Intercept node interaction — prevent d3.zoom from panning.
        // IMPORTANT: do NOT call preventDefault() — it blocks subsequent pointermove/up.
        event.stopPropagation();
        dragRef.current = { node: hit, startX: hit.x, startY: hit.y, moved: false };
        if (simRef.current) simRef.current.alphaTarget(0.3);
      }
    };

    const onPointerMove = (event) => {
      if (dragRef.current) {
        // Prevent d3.zoom from also handling this event during drag
        event.stopPropagation();
        const t = transformRef.current;
        const [mx, my] = d3.pointer(event, canvas);
        const wx = (mx - t.x) / t.k;
        const wy = (my - t.y) / t.k;
        const d = dragRef.current;
        if (Math.abs(wx - d.startX) > 2 || Math.abs(wy - d.startY) > 2) {
          d.moved = true;
        }
        d.node.fx = wx;
        d.node.fy = wy;
        scheduleDrawRef.current();
        return;
      }

      // Hover detection
      const t = transformRef.current;
      const [mx, my] = d3.pointer(event, canvas);
      const wx = (mx - t.x) / t.k;
      const wy = (my - t.y) / t.k;
      const hit = hitTest(wx, wy, graphRef.current.nodes, pathNodeIdsRef.current);
      const prev = hoveredRef.current;
      const hitId = hit ? hit.id : null;

      if (hitId !== prev) {
        hoveredRef.current = hitId;
        if (hit) showTooltipForNode(event, hit);
        else hideTooltip();
        scheduleDrawRef.current();
      }
    };

    const onPointerUp = (event) => {
      if (dragRef.current) {
        event.stopPropagation();
        const d = dragRef.current;
        if (!d.moved) {
          handleNodeClick(event, d.node);
        }
        if (!d.node.isCenter) {
          d.node.fx = null;
          d.node.fy = null;
        }
        if (simRef.current) simRef.current.alphaTarget(0);
        dragRef.current = null;
        scheduleDrawRef.current();
      }
    };

    const onClickCanvas = (event) => {
      const t = transformRef.current;
      const [mx, my] = d3.pointer(event, canvas);
      const wx = (mx - t.x) / t.k;
      const wy = (my - t.y) / t.k;
      const hit = hitTest(wx, wy, graphRef.current.nodes, pathNodeIdsRef.current);
      if (!hit) {
        setSelected([]);
        setPathInfo(null);
        hideTooltip();
      }
    };

    const onDblClickCanvas = (event) => {
      const t = transformRef.current;
      const [mx, my] = d3.pointer(event, canvas);
      const wx = (mx - t.x) / t.k;
      const wy = (my - t.y) / t.k;
      const hit = hitTest(wx, wy, graphRef.current.nodes, pathNodeIdsRef.current);
      if (hit) {
        event.stopPropagation();
        navigate(`/seiyuu/${hit.id}`);
      }
    };

    // Capture phase: intercept node clicks before d3.zoom
    canvas.addEventListener("pointerdown", onPointerDown, { capture: true });
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("click", onClickCanvas);
    canvas.addEventListener("dblclick", onDblClickCanvas);

    return () => {
      window.removeEventListener("resize", updateCanvasSize);
      canvas.removeEventListener("pointerdown", onPointerDown, { capture: true });
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("click", onClickCanvas);
      canvas.removeEventListener("dblclick", onDblClickCanvas);
      sim.stop();
      simRef.current = null;
      zoomRef.current = null;
    };
  }, []); // runs once — canvas always in DOM

  // ── Node click dispatch (stable ref, reads fresh state) ──────────────
  const handleNodeClickRef = useRef(() => {});
  handleNodeClickRef.current = (event, node) => {
    if (event.ctrlKey || event.metaKey) {
      setSelected((prev) => {
        const next = prev.includes(Number(node.id))
          ? prev.filter((x) => x !== Number(node.id))
          : [...prev, Number(node.id)].slice(0, 2);
        return next;
      });
    } else {
      if (onCenterChange) onCenterChange(Number(node.id), node.name);
      getSeiyuu(Number(node.id))
        .then((data) => setFloatingPerson(data))
        .catch(() => setFloatingPerson(null));
    }
  };
  const handleNodeClick = useCallback((event, node) => {
    handleNodeClickRef.current(event, node);
  }, []);

  // ── Update center force on resize ────────────────────────────────────
  useEffect(() => {
    if (simRef.current) {
      simRef.current.force("center", d3.forceCenter(dimensions.w / 2, dimensions.h / 2));
    }
  }, [dimensions]);

  // ── Sync filter state to ref ─────────────────────────────────────────
  useEffect(() => {
    filterRef.current = { threshold, timelineYear, centerId };
    scheduleDrawRef.current();
  }, [threshold, timelineYear, centerId]);

  // ── Load graph data ──────────────────────────────────────────────────
  useEffect(() => {
    if (!centerId || !simRef.current) return;

    setLoading(true);
    setSelected([]);
    setPathInfo(null);
    setFloatingPerson(null);
    setTimelineYear(null);
    setTimelinePlaying(false);
    setThreshold(1);

    // Reset zoom to identity for new graph
    const canvas = canvasRef.current;
    if (canvas && zoomRef.current) {
      d3.select(canvas).call(zoomRef.current.transform, d3.zoomIdentity);
      transformRef.current = d3.zoomIdentity;
    }

    getNetwork(centerId, depth).then((data) => {
      const maxW = (data.edges || []).reduce((m, e) => Math.max(m, e.weight || 0), 0);
      setMaxWeight(maxW || 1);

      let minYear = Infinity, maxYear = -Infinity;
      (data.edges || []).forEach((e) => {
        (e.shared_works || []).forEach((w) => {
          if (w.year) { minYear = Math.min(minYear, w.year); maxYear = Math.max(maxYear, w.year); }
        });
      });
      setTimelineRange([minYear === Infinity ? 2000 : minYear, maxYear === -Infinity ? 2025 : maxYear]);

      const nodeMap = new Map();
      const nodes = data.nodes.map((n) => {
        const obj = {
          id: String(n.id),
          name: n.name_zh || "",
          isCenter: n.is_center,
          level: n.is_center ? 0 : 1,
          x: dimensions.w / 2 + (Math.random() - 0.5) * 100,
          y: dimensions.h / 2 + (Math.random() - 0.5) * 100,
        };
        nodeMap.set(obj.id, obj);
        return obj;
      });

      const cid = String(centerId);
      const directNeighbors = new Set();
      const edges = (data.edges || []).map((e) => {
        const src = String(e.source), tgt = String(e.target);
        if (src === cid) directNeighbors.add(tgt);
        if (tgt === cid) directNeighbors.add(src);
        return {
          id: `${src}-${tgt}`,
          source: src,
          target: tgt,
          weight: e.weight || 1,
          shared_works: e.shared_works || [],
          sourceId: src,
          targetId: tgt,
        };
      });

      nodes.forEach((n) => {
        if (!n.isCenter && directNeighbors.has(n.id)) n.level = 1;
        else if (!n.isCenter) n.level = 2;
      });

      edges.forEach((e) => {
        const srcN = nodeMap.get(e.sourceId), tgtN = nodeMap.get(e.targetId);
        e.innerLevel = Math.min(srcN?.level ?? 2, tgtN?.level ?? 2);
      });

      graphRef.current = { nodes, edges, nodeMap };
      filterRef.current = { threshold: 1, timelineYear: null, centerId };

      const sim = simRef.current;
      sim.stop();

      const centerNode = nodes.find((n) => n.isCenter);
      if (centerNode) {
        centerNode.fx = dimensions.w / 2;
        centerNode.fy = dimensions.h / 2;
      }

      sim.nodes(nodes);
      sim.force("link", d3.forceLink(edges).id((d) => d.id).distance((e) => e.innerLevel === 0 ? LINK_DIST : LINK_DIST * 1.6));
      sim.alpha(0.4).restart();

      setLoading(false);
    });
  }, [centerId, depth, dimensions]);

  // ── Path highlighting ────────────────────────────────────────────────
  useEffect(() => {
    if (selected.length !== 2) {
      pathNodeIdsRef.current = new Set();
      pathEdgeKeysRef.current = new Set();
      scheduleDrawRef.current();
      setPathInfo(null);
      return;
    }

    getPath(Number(selected[0]), Number(selected[1])).then((data) => {
      if (!data.path) return;
      setPathInfo(data);
      const pathIds = data.path.filter((s) => s.seiyuu_id).map((s) => String(s.seiyuu_id));
      const pathIdSet = new Set(pathIds);
      const edgeKeySet = new Set();
      for (let i = 0; i < pathIds.length - 1; i++) {
        const a = pathIds[i], b = pathIds[i + 1];
        edgeKeySet.add(`${a}-${b}`);
        edgeKeySet.add(`${b}-${a}`);
      }
      pathNodeIdsRef.current = pathIdSet;
      pathEdgeKeysRef.current = edgeKeySet;
      scheduleDrawRef.current();
    }).catch(() => {});
  }, [selected]);

  // ── Timeline auto-play ───────────────────────────────────────────────
  useEffect(() => {
    if (!timelinePlaying) return;
    const [minY, maxY] = timelineRange;
    if (minY >= maxY) { setTimelinePlaying(false); return; }
    const timer = setInterval(() => {
      setTimelineYear((prev) => {
        const current = prev ?? minY;
        if (current >= maxY) { setTimelinePlaying(false); return null; }
        return current + 1;
      });
    }, 150);
    return () => clearInterval(timer);
  }, [timelinePlaying, timelineRange]);

  // ── Fetch person info when center changes ────────────────────────────
  useEffect(() => {
    if (!centerId) return;
    getSeiyuu(centerId)
      .then((data) => setFloatingPerson(data))
      .catch(() => {});
  }, [centerId]);

  const pathNames = pathInfo?.path?.filter((s) => s.seiyuu_id).map((s) => s.name_zh) || [];

  return (
    <div className={styles.wrap}>
      {/* Canvas graph — always mounted so init effect can set it up */}
      <div ref={containerRef} className={styles.graph}>
        <canvas ref={canvasRef} style={{ display: "block", width: "100%", height: "100%" }} />
      </div>

      {/* Placeholder overlay — only when no centerId */}
      {!centerId && (
        <div className={styles.placeholder}>
          <p>搜索并选择一位声优，查看其合作网络</p>
          <p className={styles.hint}>
            点击节点切换中心 | 双击查看详情 | Ctrl+点击两个节点可高亮最短路径
          </p>
        </div>
      )}

      {/* Controls — only when centerId exists */}
      {centerId && (
        <>
          <div className={styles.controlsPanel}>
            <div className={styles.controlRow}>
              {canGoBack && (
                <button className={styles.backBtn} onClick={onBack} title="返回上一个中心声优">← 返回</button>
              )}
              <select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>
                <option value={1}>1 度网络</option>
                <option value={2}>2 度网络</option>
              </select>
              <span className={styles.centerLabel} title={centerName}>中心: {centerName}</span>
              {loading && <span className={styles.loadingBadge}>加载中...</span>}
            </div>

            <div className={styles.controlRow}>
              <label className={styles.sliderLabel}>共演 ≥ {threshold}</label>
              <input type="range" className={styles.slider} min={1} max={maxWeight} value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))} />
              <span className={styles.sliderMax}>{maxWeight}</span>
            </div>

            <div className={styles.controlRow}>
              <button className={styles.timelineBtn}
                onClick={() => {
                  if (timelinePlaying) { setTimelinePlaying(false); }
                  else { setTimelineYear((prev) => prev ?? timelineRange[0]); setTimelinePlaying(true); }
                }}
                title={timelinePlaying ? "暂停" : "播放时间轴动画"}
                disabled={timelineRange[0] >= timelineRange[1]}>
                {timelinePlaying ? "⏸" : "▶"}
              </button>
              <button className={styles.timelineBtn}
                onClick={() => { setTimelinePlaying(false); setTimelineYear(null); }} title="重置时间轴">⟲</button>
              <input type="range" className={styles.slider}
                min={timelineRange[0]} max={timelineRange[1]}
                value={timelineYear ?? timelineRange[1]}
                onChange={(e) => { setTimelinePlaying(false); setTimelineYear(Number(e.target.value)); }} />
              <span className={styles.yearLabel}>{timelineYear !== null ? timelineYear : "全部"}</span>
            </div>

            {pathInfo && pathInfo.length >= 0 && (
              <div className={styles.pathInfo}>路径 ({pathInfo.length} 步): {pathNames.join(" → ")}</div>
            )}
            {selected.length > 0 && (
              <div className={styles.selectHint}>已选 {selected.length}/2 节点 (Ctrl+点击选择)</div>
            )}
          </div>

          {floatingPerson && (
            <div className={styles.personCard}>
              <button className={styles.personCardClose} onClick={() => setFloatingPerson(null)}>×</button>
              <div className={styles.personCardName}>{floatingPerson.name_zh}</div>
              {floatingPerson.name_ja && <div className={styles.personCardJa}>{floatingPerson.name_ja}</div>}
              <div className={styles.personCardDetail}>
                {floatingPerson.gender && <span className={styles.personTag}>{floatingPerson.gender === "F" ? "♀ 女" : "♂ 男"}</span>}
                {floatingPerson.birth_date && <span className={styles.personTag}>{floatingPerson.birth_date}</span>}
                {floatingPerson.blood_type && <span className={styles.personTag}>{floatingPerson.blood_type}型</span>}
                {floatingPerson.debut_year && <span className={styles.personTag}>出道 {floatingPerson.debut_year}</span>}
                {floatingPerson.agency && <span className={styles.personTag}>{floatingPerson.agency}</span>}
              </div>
            </div>
          )}
        </>
      )}

      <div ref={tooltipRef} className={styles.tooltip} />
    </div>
  );
}
