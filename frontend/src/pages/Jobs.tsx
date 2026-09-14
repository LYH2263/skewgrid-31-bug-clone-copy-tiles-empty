import { useEffect, useState } from "react";
import { getJSON, sendJSON, type Job, type Layer } from "../api";

export default function Jobs() {
  const [layers, setLayers] = useState<Layer[]>([]);
  const [slug, setSlug] = useState("demo-grid");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [msg, setMsg] = useState("");

  function load() {
    getJSON<Job[]>("/api/jobs").then(setJobs);
  }

  useEffect(() => {
    getJSON<Layer[]>("/api/layers").then((rows) => {
      setLayers(rows);
      if (rows[0]) setSlug(rows[0].slug);
    });
    load();
  }, []);

  async function run(kind: string, payload: Record<string, unknown> = {}) {
    setMsg("");
    try {
      const job = await sendJSON<Job>(`/api/layers/${slug}/jobs`, "POST", { kind, payload });
      setMsg(`${job.kind} → ${job.status}: ${job.result}`);
      load();
    } catch (e) {
      setMsg(String(e));
      load();
    }
  }

  return (
    <div className="page">
      <h1>任务</h1>
      <p className="lead">
        prerender / repair_all / export_geojson 已实现。export_mbtiles 故意 501，留给 0-1 模块。
      </p>
      <div className="row">
        <select value={slug} onChange={(e) => setSlug(e.target.value)}>
          {layers.map((l) => (
            <option key={l.slug} value={l.slug}>
              {l.slug}
            </option>
          ))}
        </select>
        <button onClick={() => run("prerender", { z: 3 })}>预渲染 z=3</button>
        <button onClick={() => run("repair_all")}>按最近扫描全部修复</button>
        <button onClick={() => run("export_geojson")}>导出 GeoJSON</button>
        <button onClick={() => run("export_mbtiles")}>导出 MBTiles（未实现）</button>
      </div>
      {msg && <p className="lead">{msg}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>图层</th>
            <th>类型</th>
            <th>状态</th>
            <th>结果</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.id}</td>
              <td>{j.layer_slug}</td>
              <td>{j.kind}</td>
              <td>{j.status}</td>
              <td>{j.result}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
