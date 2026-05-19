import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getSeiyuu } from "../api/client";
import styles from "./SeiyuuPage.module.css";

export default function SeiyuuPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSeiyuu(id)
      .then(setData)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className={styles.status}>加载中...</div>;
  if (!data) return <div className={styles.status}>未找到该声优</div>;

  return (
    <div className={styles.page}>
      <button onClick={() => navigate(-1)} className={styles.back}>
        &larr; 返回
      </button>

      <div className={styles.profile}>
        <div className={styles.header}>
          <h1>
            {data.name_zh}
            {data.name_ja && <span className={styles.nameJa}> / {data.name_ja}</span>}
          </h1>
          {data.name_romaji && <p className={styles.romaji}>{data.name_romaji}</p>}
        </div>

        <div className={styles.meta}>
          {data.gender && <span className={styles.tag}>{data.gender === "F" ? "女" : "男"}</span>}
          {data.birth_date && <span>生日: {data.birth_date}</span>}
          {data.blood_type && <span>血型: {data.blood_type}型</span>}
          {data.height_cm && <span>身高: {data.height_cm}cm</span>}
          {data.agency && <span>事务所: {data.agency}</span>}
          {data.debut_year && <span>出道: {data.debut_year}年</span>}
        </div>
      </div>

      <div className={styles.grid}>
        <section className={styles.section}>
          <h2>参演作品 ({data.roles?.length || 0})</h2>
          <div className={styles.roleList}>
            {data.roles?.map((r, i) => (
              <div key={i} className={styles.roleItem}>
                <span
                  className={styles.workLink}
                  onClick={() => navigate(`/work/${r.work_id}`)}
                >
                  {r.work_title}
                </span>
                <span className={styles.charName}>{r.character_name || "-"}</span>
                <span className={styles.year}>{r.year || ""}</span>
              </div>
            ))}
            {(!data.roles || data.roles.length === 0) && (
              <p className={styles.empty}>暂无数据</p>
            )}
          </div>
        </section>

        <section className={styles.section}>
          <h2>常共演声优 Top 10</h2>
          <div className={styles.coList}>
            {data.top_co_stars?.map((c) => (
              <div
                key={c.id}
                className={styles.coItem}
                onClick={() => navigate(`/seiyuu/${c.id}`)}
              >
                <span className={styles.coName}>{c.name_zh}</span>
                <span className={styles.coCount}>{c.work_count} 部作品</span>
              </div>
            ))}
            {(!data.top_co_stars || data.top_co_stars.length === 0) && (
              <p className={styles.empty}>暂无数据</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
