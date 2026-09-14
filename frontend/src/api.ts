export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`);
  }
  return res.json();
}

export async function sendJSON<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data as { message?: string }).message || `${res.status}`);
  }
  return data as T;
}

export type Layer = {
  id: number;
  slug: string;
  name: string;
  description: string;
  provider: string;
  default_scheme: string;
  min_z: number;
  max_z: number;
};

export type Issue = {
  id?: number;
  kind: string;
  z: number;
  x: number;
  y: number;
  message: string;
};

export type ScanRun = {
  id: number;
  layer_slug: string;
  scheme: string;
  max_z: number;
  status: string;
  total: number;
  missing: number;
  y_flip: number;
  meta_missing: number;
  created_at: string;
  issues?: Issue[];
};

export type Job = {
  id: number;
  layer_slug: string;
  kind: string;
  status: string;
  result: string;
  created_at: string;
};
