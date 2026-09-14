import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJSON, sendJSON } from "../api";

export default function Upstream() {
  const { slug } = useParams();
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!slug) return;
    getJSON<Record<string, unknown>>(`/api/layers/${slug}/upstream`).then(setInfo);
  }, [slug]);

  async function fetchUp() {
    setMsg("");
    try {
      await sendJSON(`/api/layers/${slug}/upstream/fetch`, "POST", {});
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <div className="page">
      <h1>上游源 · {slug}</h1>
      <p className="lead">
        这是预留的 0-1 模块：实现 <code>app/providers/http_upstream.py</code>，让本页能按模板拉 TMS/XYZ。
      </p>
      <pre className="info">{JSON.stringify(info, null, 2)}</pre>
      <button onClick={fetchUp}>尝试拉取</button>
      {msg && <p className="err">{msg}</p>}
      <p>
        <Link to={`/layers/${slug}/map`}>回地图</Link>
      </p>
    </div>
  );
}
