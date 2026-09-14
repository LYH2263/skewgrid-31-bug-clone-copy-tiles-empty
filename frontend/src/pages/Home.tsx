import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJSON, type Layer, type ScanRun } from "../api";

export default function Home() {
  const [layers, setLayers] = useState<Layer[]>([]);
  const [scans, setScans] = useState<ScanRun[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([getJSON<Layer[]>("/api/layers"), getJSON<ScanRun[]>("/api/scans")])
      .then(([l, s]) => {
        setLayers(l);
        setScans(s.slice(0, 5));
      })
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="page">
      <h1>图层选择</h1>
      <p className="lead">底栏导航。有问题的层左侧橙色条；干净层蓝色。直接进地图扫缺口 / y 翻转。</p>
      {err && <p className="err">{err}</p>}
      <div className="layer-strip">
        {layers.map((l) => {
          const problem = /demo|flip|gap|bad/i.test(l.slug + l.description);
          return (
            <Link key={l.slug} className={`layer-chip ${problem ? "problem" : ""}`} to={`/layers/${l.slug}/map`}>
              <div>
                <strong>{l.name}</strong>
                <div className="mono">{l.slug}</div>
                <p className="lead" style={{ margin: "6px 0 0" }}>
                  {l.description}
                </p>
              </div>
              <span>打开地图 →</span>
            </Link>
          );
        })}
      </div>
      <h2>最近扫描</h2>
      {scans.length === 0 && <p className="lead">还没有扫描记录。</p>}
      <ul>
        {scans.map((s) => (
          <li key={s.id}>
            <Link to={`/scans/${s.id}`}>
              #{s.id} {s.layer_slug} · {s.total} 个问题
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
