import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import SeiyuuPage from "./pages/SeiyuuPage";
import WorkPage from "./pages/WorkPage";
import GraphPage from "./pages/GraphPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/seiyuu/:id" element={<SeiyuuPage />} />
        <Route path="/work/:id" element={<WorkPage />} />
        <Route path="/graph" element={<GraphPage />} />
      </Routes>
    </Layout>
  );
}
