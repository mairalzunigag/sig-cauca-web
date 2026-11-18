// Cliente HTTP: único punto por el que el frontend habla con la API (FastAPI).
// Cada petición queda anotada en el "Registro de peticiones HTTP" del panel.

const esc = (v) => String(v ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function registrar(url, estado, ms, ok) {
  const li = document.createElement("li");
  li.className = ok ? "" : "err";
  li.textContent = `GET ${url.replace(API_BASE, "") || url} → ${estado} (${ms} ms)`;
  const log = document.getElementById("log");
  log.prepend(li);
  while (log.children.length > 50) log.lastChild.remove();
}

async function api(ruta, params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v !== null && v !== undefined && v !== false) qs.set(k, v);
  }
  const url = API_BASE + ruta + (qs.toString() ? "?" + qs : "");
  const t0 = performance.now();
  let resp;
  try {
    resp = await fetch(url);
  } catch (e) {
    registrar(url, "sin conexión", Math.round(performance.now() - t0), false);
    throw new Error("No se pudo conectar con la API. ¿Está corriendo uvicorn?");
  }
  registrar(url, resp.status, Math.round(performance.now() - t0), resp.ok);
  if (!resp.ok) {
    const e = await resp.json().catch(() => ({}));
    const det = typeof e.detail === "string" ? e.detail : "solicitud no válida";
    throw new Error(`Error ${resp.status}: ${det}`);
  }
  return resp.json();
}
