import { Link, useLocation } from "react-router-dom";
import styles from "./Layout.module.css";

export default function Layout({ children }) {
  const loc = useLocation();

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={styles.inner}>
          <Link to="/" className={styles.logo}>
            SeiyuuGraph
            <span className={styles.logoSub}>声优共演网络</span>
          </Link>
          <nav className={styles.nav}>
            <Link to="/" className={loc.pathname === "/" ? styles.active : ""}>
              首页
            </Link>
            <Link to="/graph" className={loc.pathname === "/graph" ? styles.active : ""}>
              关系图
            </Link>
          </nav>
        </div>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
