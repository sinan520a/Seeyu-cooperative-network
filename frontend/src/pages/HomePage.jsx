import { useNavigate } from "react-router-dom";
import SearchBar from "../components/SearchBar";
import styles from "./HomePage.module.css";

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className={styles.hero}>
      <h1 className={styles.title}>
        探索<span className={styles.highlight}>声优</span>的共演世界
      </h1>
      <p className={styles.desc}>
        通过交互式网络图，发现声优之间的合作关系，追踪他们共同出演的作品。
      </p>
      <div className={styles.searchRow}>
        <SearchBar
          type="seiyuu"
          placeholder="输入声优名，如 花泽香菜、神谷浩史..."
          onSelect={(s) => navigate(`/seiyuu/${s.id}`)}
        />
      </div>
      <div className={styles.links}>
        <a href="/graph">打开关系图工具</a>
      </div>
    </div>
  );
}
