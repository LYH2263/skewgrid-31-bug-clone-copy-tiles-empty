import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJSON, type ScanRun } from "../api";

export default function Scans() {
  const [rows, setRows] = useState<ScanRun[]>([]);
  useEffect(() => {
    getJSON<ScanRun[]>("/api/scans").then(setRows);
  }, []);
  return (
    <div className="page">
      <h1>扫描历史</h1>
      <p className="lead">每次扫描落库。可对照多次结果看出修瓦有没有把计数打下来。</p>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>图层</th>
            <th>总数</th>
            <th>缺口</th>
            <th>错层</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id}>
              <td>
                <Link to={`/scans/${s.id}`}>#{s.id}</Link>
              </td>
              <td>{s.layer_slug}</td>
              <td>{s.total}</td>
              <td>{s.missing}</td>
              <td>{s.y_flip}</td>
              <td className="mono">{s.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
