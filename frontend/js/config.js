// Dirección base de la API FastAPI.
// - Si el visor se abre desde la propia API (http://127.0.0.1:8000/), se usa la misma origen.
// - Si se abre desde otro servidor estático (p. ej. python -m http.server 5500), apunta al puerto 8000.
const API_BASE = (location.port === "8000") ? "" : "http://127.0.0.1:8000";
