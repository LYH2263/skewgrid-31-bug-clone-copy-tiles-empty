import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getJSON, sendJSON } from "../api";

export default function Inspect() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const z = Number(params.get("z") || 0);
  const x = Number(params.get("x") || 0);
  const y = Number(params.get("y") || 0);
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState("");

  function load() {
    if (!slug) return;
    getJSON<Record<string, unknown>>(`/api/layers/${slug}/tile?z=${z}&x=${x}&y=${y}`)
      .then(setInfo)
      .catch((e) => setErr(String(e)));
  }

  useEffect(() => {
    load();
  }, [slug, z, x, y]);

  async function repair() {
    if (!slug) return;
    await sendJSON(`/api/layers/${slug}/repair?z=${z}&x=${x}&y=${y}`, "POST");
    load();
  }

  return (
    <div className="page">
      <h1>
        瓦片检查 · {slug} · z{z}/{x}/{y}
      </h1>
      <div className="row">
        <Link to={`/layers/${slug}/map`}>地图</Link>
        <Link to={`/layers/${slug}/coverage`}>覆盖率</Link>
        <button onClick={repair}>写回正确瓦片</button>
      </div>
      {err && <p className="err">{err}</p>}
      {info && (
        <img
          alt="tile"
          width={256}
          height={256}
          src={`/tiles/${slug}/xyz/${z}/${x}/${y}.png`}
          style={{ border: "1px solid #cbbba0", imageRendering: "pixelated" }}
        />
      )}
      <pre className="info">{JSON.stringify(info, null, 2)}</pre>
    </div>
  );
}
