import { useState } from "react";
import { getPath } from "../api/client";
import SearchBar from "./SearchBar";
import styles from "./PathFinder.module.css";

export default function PathFinder() {
  const [from, setFrom] = useState(null);
  const [to, setTo] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  function find() {
    if (!from || !to) return;
    setLoading(true);
    setResult(null);
    getPath(from.id, to.id)
      .then(setResult)
      .finally(() => setLoading(false));
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.inputs}>
        <div className={styles.field}>
          <label>声优 A</label>
          <SearchBar type="seiyuu" compact placeholder="选择起始声优..." onSelect={setFrom} />
          {from && <span className={styles.chip}>{from.name_zh}</span>}
        </div>
        <div className={styles.field}>
          <label>声优 B</label>
          <SearchBar type="seiyuu" compact placeholder="选择目标声优..." onSelect={setTo} />
          {to && <span className={styles.chip}>{to.name_zh}</span>}
        </div>
        <button className={styles.btn} disabled={!from || !to || loading} onClick={find}>
          {loading ? "搜索中..." : "查找路径"}
        </button>
      </div>

      {result && (
        <div className={styles.result}>
          {result.length === -1 ? (
            <p className={styles.noPath}>未找到连接路径</p>
          ) : (
            <div>
              <p className={styles.len}>最短距离: {result.length} 步</p>
              <div className={styles.chain}>
                {result.path.map((step, i) => (
                  <span key={i} className={step.seiyuu_id ? styles.seiyuuNode : styles.workNode}>
                    {step.name_zh || step.title_zh}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
