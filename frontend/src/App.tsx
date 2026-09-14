import { Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import Home from "./pages/Home";
import Layers from "./pages/Layers";
import LayerMap from "./pages/LayerMap";
import Coverage from "./pages/Coverage";
import Inspect from "./pages/Inspect";
import Scans from "./pages/Scans";
import ScanDetail from "./pages/ScanDetail";
import Jobs from "./pages/Jobs";
import Settings from "./pages/Settings";
import Upstream from "./pages/Upstream";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/layers" element={<Layers />} />
        <Route path="/layers/:slug/map" element={<LayerMap />} />
        <Route path="/layers/:slug/coverage" element={<Coverage />} />
        <Route path="/layers/:slug/inspect" element={<Inspect />} />
        <Route path="/layers/:slug/upstream" element={<Upstream />} />
        <Route path="/scans" element={<Scans />} />
        <Route path="/scans/:id" element={<ScanDetail />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
