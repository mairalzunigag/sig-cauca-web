// Mapa Leaflet y capas. Aquí se representan los GeoJSON que entrega la API.

const mapa = L.map("mapa", { zoomControl: true }).setView([2.35, -76.8], 8);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "© OpenStreetMap · Datos: DANE / IGAC / POT municipales",
}).addTo(mapa);
L.control.scale({ metric: true, imperial: false }).addTo(mapa);

// Capas temáticas (cada una se alimenta desde un endpoint distinto)
const capas = {
  departamento: L.geoJSON(null, { style: { color: "#0a4d42", weight: 3, fill: false }, interactive: false }).addTo(mapa),
  municipios: L.geoJSON(null).addTo(mapa),
  veredas: L.geoJSON(null).addTo(mapa),
  espacial: L.layerGroup().addTo(mapa),
  calidad: L.geoJSON(null).addTo(mapa),
};

// ---- Coropleta por número de veredas ------------------------------------
const CLASES = [
  { min: 0,  color: "#d8efe9" }, { min: 20, color: "#a5d8cb" },
  { min: 40, color: "#5fb8a5" }, { min: 60, color: "#2a8d7a" },
  { min: 80, color: "#0b5d4f" },
];
const colorPorVeredas = (n) => [...CLASES].reverse().find((c) => n >= c.min).color;

function estiloMunicipio(f) {
  return { color: "#1f5f54", weight: 1, fillColor: colorPorVeredas(f.properties.n_veredas), fillOpacity: 0.6 };
}

const leyenda = L.control({ position: "bottomright" });
leyenda.onAdd = () => {
  const d = L.DomUtil.create("div", "leyenda");
  d.innerHTML = "<b>Veredas por municipio</b><br>" + CLASES.map((c, i) =>
    `<i style="background:${c.color}"></i>${c.min}${CLASES[i + 1] ? "–" + (CLASES[i + 1].min - 1) : "+"}`
  ).join("<br>");
  return d;
};
leyenda.addTo(mapa);

// ---- Dibujo de resultados ------------------------------------------------
const ESTILO_VEREDA = { color: "#b9770e", weight: 1.5, fillColor: "#f0b429", fillOpacity: 0.45 };
const ESTILO_CALIDAD = { color: "#a93226", weight: 2, fillColor: "#e74c3c", fillOpacity: 0.5 };

function popupVereda(p) {
  return `<div class="popup"><h4>${esc(p.nombre_vereda)}</h4>
    <p>${esc(p.nombre_municipio || p.municipio_declarado || "")}</p>
    ${p.area_ha != null ? `<p>Área: ${esc(p.area_ha)} ha</p>` : ""}
    ${p.nombre_fuente ? `<p>Fuente: ${esc(p.nombre_fuente)}</p>` : ""}
    ${p.distancia_m != null ? `<p>Distancia: ${esc(p.distancia_m)} m</p>` : ""}
    <button data-vereda="${esc(p.id_vereda)}">Ver ficha</button></div>`;
}

function dibujarVeredas(capa, fc, estilo) {
  capa.clearLayers();
  capa.addData(fc);
  capa.setStyle(estilo);
  capa.eachLayer((l) => l.bindPopup(() => popupVereda(l.feature.properties)));
  if (capa.getLayers().length) mapa.fitBounds(capa.getBounds(), { padding: [30, 30], maxZoom: 13 });
}

function ajustarA(fc) {
  const b = L.geoJSON(fc).getBounds();
  if (b.isValid()) mapa.fitBounds(b, { padding: [30, 30], maxZoom: 14 });
}
