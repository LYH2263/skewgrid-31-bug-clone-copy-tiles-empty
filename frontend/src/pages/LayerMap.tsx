import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MapContainer, Rectangle, TileLayer, useMapEvents } from "react-leaflet";
import { getJSON, sendJSON, type Issue, type Layer, type ScanRun } from "../api";
import { tileBounds } from "../geo";

function ClickCatch({ onPick }: { onPick: (z: number, x: number, y: number) => void }) {
  useMapEvents({
    click(e) {
      const z = e.target.getZoom();
      const n = 2 ** z;
      const x = Math.floor(((e.latlng.lng + 180) / 360) * n);
      const latRad = (e.latlng.lat * Math.PI) / 180;
      const y = Math.floor(
        ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n
      );
      onPick(z, x, y);
    },
  });
  return null;
}

export default function LayerMap() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [layer, setLayer] = useState<Layer | null>(null);
  const [scheme, setScheme] = useState<"xyz" | "tms">("xyz");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!slug) return;
    getJSON<Layer>(`/api/layers/${slug}`).then((l) => {
      setLayer(l);
      setScheme((l.default_scheme as "xyz" | "tms") || "xyz");
    });
    sendJSON<ScanRun>(`/api/layers/${slug}/scans`, "POST", { scheme: "xyz", max_z: 3 })
      .then((run) => setIssues(run.issues || []))
      .catch((e) => setErr(String(e)));
  }, [slug]);

  const overlays = useMemo(
    () =>
      issues.map((i) => ({
        issue: i,
        bounds: tileBounds(i.z, i.x, i.y),
        color: i.kind === "missing" ? "#c45c26" : "#2a6f97",
      })),
    [issues]
  );

  if (!slug) return null;

  return (
    <div className="map-page">
      <aside className="side">
        <h1>{layer?.name || slug}</h1>
        <p className="lead">{layer?.description}</p>
        <div className="row">
          <Link to={`/layers/${slug}/coverage`}>覆盖率</Link>
          <Link to={`/layers/${slug}/upstream`}>上游</Link>
          <Link to="/scans">扫描历史</Link>
        </div>
        <div className="row">
          <select value={scheme} onChange={(e) => setScheme(e.target.value as "xyz" | "tms")}>
            <option value="xyz">XYZ</option>
            <option value="tms">TMS</option>
          </select>
        </div>
        {err && <p className="err">{err}</p>}
        {issues.map((i) => (
          <div
            key={`${i.kind}-${i.z}-${i.x}-${i.y}`}
            className={`issue ${i.kind}`}
            onClick={() => navigate(`/layers/${slug}/inspect?z=${i.z}&x=${i.x}&y=${i.y}`)}
          >
            <strong>
              {i.kind} · z{i.z}/{i.x}/{i.y}
            </strong>
            <div>{i.message}</div>
          </div>
        ))}
      </aside>
      <div className="map">
        <MapContainer
          center={[20, 0]}
          zoom={2}
          minZoom={0}
          maxZoom={layer?.max_z ?? 3}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url={`/tiles/${slug}/${scheme}/{z}/{x}/{y}.png`} tileSize={256} noWrap />
          <ClickCatch
            onPick={(z, x, y) => navigate(`/layers/${slug}/inspect?z=${z}&x=${x}&y=${y}`)}
          />
          {overlays.map((o) => (
            <Rectangle
              key={`${o.issue.kind}-${o.issue.z}-${o.issue.x}-${o.issue.y}`}
              bounds={o.bounds}
              pathOptions={{ color: o.color, weight: 2, fillOpacity: 0.15 }}
            />
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
