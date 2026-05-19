import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getIntersection } from "../api/client";
import SearchBar from "./SearchBar";
import styles from "./WorkIntersection.module.css";

export default function WorkIntersection() {
  const navigate = useNavigate();
  const [workA, setWorkA] = useState(null);
  const [workB, setWorkB] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  function find() {
    if (!workA || !workB) return;
    setLoading(true);
    setResult(null);
    getIntersection(workA.id, workB.id)
      .then(setResult)
      .finally(() => setLoading(false));
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.inputs}>
        <div className={styles.field}>
          <label>作品 A</label>
          <SearchBar type="work" compact placeholder="选择作品..." onSelect={setWorkA} />
          {workA && <span className={styles.chip}>{workA.title_zh}</span>}
        </div>
        <div className={styles.field}>
          <label>作品 B</label>
          <SearchBar type="work" compact placeholder="选择作品..." onSelect={setWorkB} />
          {workB && <span className={styles.chip}>{workB.title_zh}</span>}
        </div>
        <button className={styles.btn} disabled={!workA || !workB || loading} onClick={find}>
          {loading ? "查询中..." : "查询交集"}
        </button>
      </div>

      {result && (
        <div className={styles.result}>
          <p className={styles.summary}>
            {result.work_a?.title_zh} ∩ {result.work_b?.title_zh}：共{" "}
            {result.common_seiyuu?.length || 0} 位声优
          </p>
          <div className={styles.list}>
            {result.common_seiyuu?.map((s) => (
              <div
                key={s.id}
                className={styles.item}
                onClick={() => navigate(`/seiyuu/${s.id}`)}
              >
                <span className={styles.sName}>{s.name_zh}</span>
                <span className={styles.roleInfo}>
                  {s.role_in_a || "-"} / {s.role_in_b || "-"}
                </span>
              </div>
            ))}
            {(!result.common_seiyuu || result.common_seiyuu.length === 0) && (
              <p className={styles.empty}>无共同声优</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
