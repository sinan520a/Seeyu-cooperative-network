import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getWork } from "../api/client";
import styles from "./WorkPage.module.css";

export default function WorkPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getWork(id)
      .then(setData)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className={styles.status}>加载中...</div>;
  if (!data) return <div className={styles.status}>未找到该作品</div>;

  return (
    <div className={styles.page}>
      <button onClick={() => navigate(-1)} className={styles.back}>
        &larr; 返回
      </button>

      <div className={styles.profile}>
        <h1>
          {data.title_zh}
          {data.title_ja && <span className={styles.titleJa}> / {data.title_ja}</span>}
        </h1>
        <div className={styles.meta}>
          {data.type && <span className={styles.tag}>{data.type}</span>}
          {data.premiere_year && <span>{data.premiere_year}年</span>}
          {data.episodes && <span>{data.episodes}集</span>}
          {data.studio && <span>制作: {data.studio}</span>}
        </div>
      </div>

      <section className={styles.section}>
        <h2>声优阵容 ({data.cast?.length || 0})</h2>
        <div className={styles.castGrid}>
          {data.cast?.map((c) => (
            <div
              key={c.seiyuu_id}
              className={styles.castItem}
              onClick={() => navigate(`/seiyuu/${c.seiyuu_id}`)}
            >
              <span className={styles.castName}>{c.name_zh}</span>
              <span className={styles.castRole}>{c.character_name || "-"}</span>
            </div>
          ))}
          {(!data.cast || data.cast.length === 0) && (
            <p className={styles.empty}>暂无数据</p>
          )}
        </div>
      </section>
    </div>
  );
}
