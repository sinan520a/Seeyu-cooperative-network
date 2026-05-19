import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import SearchBar from "../components/SearchBar";
import NetworkGraph from "../components/NetworkGraph";
import PathFinder from "../components/PathFinder";
import WorkIntersection from "../components/WorkIntersection";
import styles from "./GraphPage.module.css";

const TABS = [
  { key: "network", label: "合作网络" },
  { key: "path", label: "最短路径" },
  { key: "intersection", label: "作品交集" },
];

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState("network");
  const [centerId, setCenterId] = useState(null);
  const [centerName, setCenterName] = useState("");

  // Center history stack for back navigation in the graph
  const historyRef = useRef([]);

  // Support URL params: /graph?center=1&name=花泽香菜
  useEffect(() => {
    const cid = searchParams.get("center");
    const cname = searchParams.get("name");
    if (cid) {
      const id = Number(cid);
      const name = cname || "";
      setCenterId((prev) => {
        if (prev && prev !== id) {
          historyRef.current.push({ id: prev, name: centerName });
        }
        return id;
      });
      setCenterName(name);
      setTab("network");
    }
  }, [searchParams]);

  const handleCenterChange = useCallback(
    (newId, newName) => {
      if (centerId && centerId !== newId) {
        historyRef.current.push({ id: centerId, name: centerName });
      }
      setCenterId(newId);
      setCenterName(newName);
    },
    [centerId, centerName]
  );

  const handleBack = useCallback(() => {
    const prev = historyRef.current.pop();
    if (prev) {
      setCenterId(prev.id);
      setCenterName(prev.name);
    }
  }, []);

  return (
    <div className={tab === "network" ? styles.pageFullscreen : styles.page}>
      {tab !== "network" && (
        <div className={styles.toolbar}>
          <div className={styles.tabs}>
            {TABS.map((t) => (
              <button
                key={t.key}
                className={tab === t.key ? styles.tabActive : styles.tab}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className={styles.searchSlot}>
            {tab === "path" && null}
            {tab === "intersection" && null}
          </div>
        </div>
      )}

      {/* Floating search bar for network (fullscreen mode) */}
      {tab === "network" && (
        <div className={styles.floatingSearch}>
          <div className={styles.tabsMini}>
            {TABS.map((t) => (
              <button
                key={t.key}
                className={tab === t.key ? styles.tabActiveMini : styles.tabMini}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <SearchBar
            type="seiyuu"
            compact
            placeholder="选择中心声优..."
            onSelect={(s) => {
              if (centerId && centerId !== s.id) {
                historyRef.current.push({ id: centerId, name: centerName });
              }
              setCenterId(s.id);
              setCenterName(s.name_zh);
            }}
          />
        </div>
      )}

      <div className={tab === "network" ? styles.contentFullscreen : styles.content}>
        {tab === "network" && (
          <NetworkGraph
            centerId={centerId}
            centerName={centerName}
            onCenterChange={handleCenterChange}
            onBack={historyRef.current.length > 0 ? handleBack : null}
            canGoBack={historyRef.current.length > 0}
          />
        )}
        {tab === "path" && <PathFinder />}
        {tab === "intersection" && <WorkIntersection />}
      </div>
    </div>
  );
}
