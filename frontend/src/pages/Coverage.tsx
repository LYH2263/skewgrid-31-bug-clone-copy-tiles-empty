import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJSON } from "../api";

type Grid = {
  z: number;
  n: number;
  counts: Record<string, number>;
  cells: { x: number; y: number; status: string }[][];
};

export default function Coverage() {
  const { slug } = useParams();
  const [z, setZ] = useState(2);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!slug) return;
    getJSON<Grid>(`/api/layers/${slug}/coverage?z=${z}`)
      .then(setGrid)
      .catch((e) => setErr(String(e)));
  }, [slug, z]);

  return (
    <div className="page">
      <h1>覆盖率 · {slug}</h1>
      <p className="lead">每个格子是一块瓦。橙=缺口，蓝=y 轴写反，米白=正常。</p>
      {err && <p className="err">{err}</p>}
      <div className="row">
        <span>zoom</span>
        <select value={z} onChange={(e) => setZ(Number(e.target.value))}>
          {[0, 1, 2, 3].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <Link to={`/layers/${slug}/map`}>回地图</Link>
      </div>
      {grid && (
        <>
          <p className="lead">{JSON.stringify(grid.counts)}</p>
          <div
            className="coverage"
            style={{ gridTemplateColumns: `repeat(${grid.n}, 18px)` }}
          >
            {grid.cells.flat().map((c) => (
              <Link
                key={`${c.x}-${c.y}`}
                to={`/layers/${slug}/inspect?z=${z}&x=${c.x}&y=${c.y}`}
                className={`cell ${c.status}`}
                title={`${c.status} ${c.x}/${c.y}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
