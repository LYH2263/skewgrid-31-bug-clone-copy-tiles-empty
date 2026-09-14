import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJSON, sendJSON, type Layer } from "../api";

function suggestSlug(slug: string) {
  const base = slug.length > 35 ? slug.slice(0, 35) : slug;
  return `${base}-copy`;
}

export default function Layers() {
  const [layers, setLayers] = useState<Layer[]>([]);
  const [err, setErr] = useState("");
  const [cloningFor, setCloningFor] = useState<string | null>(null);
  const [cloneErr, setCloneErr] = useState("");
  const [cloneBusy, setCloneBusy] = useState(false);
  const [cloned, setCloned] = useState<{ slug: string; tiles_copied: number } | null>(null);

  function load() {
    getJSON<Layer[]>("/api/layers").then(setLayers).catch((e) => setErr(String(e)));
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setErr("");
    try {
      await sendJSON("/api/layers", "POST", {
        slug: fd.get("slug"),
        name: fd.get("name"),
        description: fd.get("description"),
        max_z: Number(fd.get("max_z") || 3),
      });
      load();
      e.currentTarget.reset();
    } catch (ex) {
      setErr(String(ex));
    }
  }

  function openClone(layer: Layer) {
    setCloned(null);
    setCloneErr("");
    setCloningFor(cloningFor === layer.slug ? null : layer.slug);
  }

  async function onClone(e: FormEvent<HTMLFormElement>, source: Layer) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const target = String(fd.get("target_slug") || "").trim();
    const name = String(fd.get("name") || "").trim();
    const description = String(fd.get("description") || "").trim();
    setCloneErr("");
    setCloneBusy(true);
    try {
      const result = await sendJSON<Layer & { tiles_copied: number }>(
        `/api/layers/${source.slug}/clone`,
        "POST",
        {
          target_slug: target,
          copy_tiles: fd.get("copy_tiles") === "on",
          ...(name ? { name } : {}),
          ...(description ? { description } : {}),
        }
      );
      setCloningFor(null);
      setCloned({ slug: result.slug, tiles_copied: result.tiles_copied });
      load();
    } catch (ex) {
      setCloneErr(String(ex));
    } finally {
      setCloneBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>图层</h1>
      {err && <p className="err">{err}</p>}
      {cloned && (
        <p className="clone-done">
          克隆完成：<span className="mono">{cloned.slug}</span>
          {cloned.tiles_copied > 0 ? `（已拷贝 ${cloned.tiles_copied} 块瓦）` : "（仅元数据）"}，
          <Link to={`/layers/${cloned.slug}/map`}>进入新图层地图</Link>
          <span> 或 </span>
          <Link to={`/layers/${cloned.slug}/coverage`}>覆盖率核对</Link>
          <button className="link-btn" onClick={() => setCloned(null)}>
            知道了
          </button>
        </p>
      )}
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>slug</th>
            <th>provider</th>
            <th>z</th>
            <th>入口</th>
          </tr>
        </thead>
        <tbody>
          {layers.map((l) => (
            <CloneRows
              key={l.slug}
              layer={l}
              open={cloningFor === l.slug}
              busy={cloneBusy}
              cloneErr={cloneErr}
              onToggle={() => openClone(l)}
              onClone={(e) => onClone(e, l)}
            />
          ))}
        </tbody>
      </table>
      <h2>新建图层</h2>
      <p className="lead">只写元数据，瓦片要去「任务」里跑 prerender，或等 0-1 接上游。</p>
      <form className="form" onSubmit={onCreate}>
        <input name="slug" placeholder="slug，如 city-east" required />
        <input name="name" placeholder="显示名" required />
        <input name="description" placeholder="说明" />
        <input name="max_z" type="number" defaultValue={3} />
        <button type="submit">创建</button>
      </form>
    </div>
  );
}

function CloneRows({
  layer,
  open,
  busy,
  cloneErr,
  onToggle,
  onClone,
}: {
  layer: Layer;
  open: boolean;
  busy: boolean;
  cloneErr: string;
  onToggle: () => void;
  onClone: (e: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <>
      <tr>
        <td>{layer.name}</td>
        <td className="mono">{layer.slug}</td>
        <td>{layer.provider}</td>
        <td>
          {layer.min_z}–{layer.max_z}
        </td>
        <td className="row">
          <Link to={`/layers/${layer.slug}/map`}>地图</Link>
          <Link to={`/layers/${layer.slug}/coverage`}>覆盖率</Link>
          <Link to={`/layers/${layer.slug}/upstream`}>上游</Link>
          <button className="link-btn" onClick={onToggle}>
            {open ? "取消克隆" : "克隆"}
          </button>
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={5}>
            <form className="form clone-form" onSubmit={onClone}>
              <p className="lead">
                复制 <span className="mono">{layer.slug}</span> 的元数据为新图层；扫描与任务历史不会带过去。
              </p>
              <input
                name="target_slug"
                placeholder="新 slug，如 demo-grid-copy"
                defaultValue={suggestSlug(layer.slug)}
                pattern="[a-z0-9-]{2,40}"
                required
              />
              <input name="name" placeholder={`显示名（留空则为「${layer.name} 副本」）`} />
              <input name="description" placeholder="说明（留空则沿用原图层说明）" />
              <label className="row">
                <input type="checkbox" name="copy_tiles" />
                同时拷贝本地金字塔文件（克隆后可直接打开地图核对）
              </label>
              {cloneErr && <p className="err">{cloneErr}</p>}
              <div className="row">
                <button type="submit" disabled={busy}>
                  {busy ? "克隆中…" : "克隆"}
                </button>
              </div>
            </form>
          </td>
        </tr>
      )}
    </>
  );
}
