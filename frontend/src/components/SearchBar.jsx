import { useState, useRef, useEffect } from "react";
import { searchSeiyuu, searchWorks } from "../api/client";
import styles from "./SearchBar.module.css";

export default function SearchBar({ type = "seiyuu", placeholder, onSelect, compact }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);
  const timer = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleChange(e) {
    const v = e.target.value;
    setQ(v);
    if (timer.current) clearTimeout(timer.current);
    if (v.trim().length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    timer.current = setTimeout(async () => {
      try {
        const fn = type === "seiyuu" ? searchSeiyuu : searchWorks;
        const data = await fn({ q: v, size: 8 });
        setResults(data.items || []);
        setOpen(true);
      } catch {
        setResults([]);
      }
      setLoading(false);
    }, 250);
  }

  function select(item) {
    setOpen(false);
    setQ("");
    setResults([]);
    if (onSelect) onSelect(item);
  }

  const label = type === "seiyuu" ? "name_zh" : "title_zh";
  const sub = type === "seiyuu" ? "agency" : "studio";

  return (
    <div className={`${styles.wrap} ${compact ? styles.compact : ""}`} ref={ref}>
      <input
        className={styles.input}
        value={q}
        onChange={handleChange}
        placeholder={placeholder || (type === "seiyuu" ? "搜索声优..." : "搜索作品...")}
      />
      {loading && <span className={styles.spinner} />}
      {open && results.length > 0 && (
        <ul className={styles.dropdown}>
          {results.map((r) => (
            <li key={r.id} onClick={() => select(r)}>
              <span className={styles.label}>{r[label]}</span>
              <span className={styles.sub}>{r[sub]}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
