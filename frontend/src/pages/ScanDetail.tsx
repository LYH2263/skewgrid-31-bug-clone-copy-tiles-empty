import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJSON, type ScanRun } from "../api";

export default function ScanDetail() {
  const { id } = useParams();
  const [run, setRun] = useState<ScanRun | null>(null);
  useEffect(() => {
    if (!id) return;
    getJSON<ScanRun>(`/api/scans/${id}`).then(setRun);
  }, [id]);
  if (!run) return <div className="page">加载中…</div>;
  return (
    <div className="page">
      <h1>
        扫描 #{run.id} · {run.layer_slug}
      </h1>
      <p className="lead">
        {run.total} 个问题（缺口 {run.missing} / 错层 {run.y_flip}）
      </p>
      <table>
        <thead>
          <tr>
            <th>类型</th>
            <th>z/x/y</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          {(run.issues || []).map((i, idx) => (
            <tr key={idx}>
              <td>{i.kind}</td>
              <td className="mono">
                <Link
                  to={`/layers/${run.layer_slug}/inspect?z=${i.z}&x=${i.x}&y=${i.y}`}
                >
                  {i.z}/{i.x}/{i.y}
                </Link>
              </td>
              <td>{i.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
