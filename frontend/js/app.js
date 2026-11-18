// Lógica de la interfaz: eventos del usuario → API → Leaflet.

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 1) => (n == null ? "—" : Number(n).toLocaleString("es-CO", { maximumFractionDigits: d }));

function mostrar(div, html, error = false) {
  div.hidden = false;
  div.classList.toggle("error", error);
  div.innerHTML = html;
}
const dl = (pares) => "<dl>" + pares.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") + "</dl>";

// ---------------------------------------------------------------------------
// Pestañas
// ---------------------------------------------------------------------------
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("activa", x === b));
  document.querySelectorAll(".seccion").forEach((s) => s.classList.toggle("activa", s.id === b.dataset.tab));
}));

// ---------------------------------------------------------------------------
// Inicio: estado de la BD + F1 (departamento y municipios)
// ---------------------------------------------------------------------------
async function iniciar() {
  try {
    const s = await api("/salud");
    const est = $("estado-bd");
    est.className = "estado ok";
    est.textContent = `PostGIS ${s.postgis.split(" ")[0]} · ${s.municipios} municipios · ${s.veredas} veredas`;
  } catch (e) {
    const est = $("estado-bd");
    est.className = "estado error";
    est.textContent = e.message;
    return;
  }
  await cargarMunicipios();
  cargarFiltros();
  cargarRanking();
}

// F1 · GET /departamento y GET /municipios → capas Leaflet
async function cargarMunicipios() {
  const [dep, mun] = await Promise.all([api("/departamento"), api("/municipios")]);
  capas.departamento.addData(dep);
  capas.municipios.addData(mun);
  capas.municipios.setStyle(estiloMunicipio);
  capas.municipios.eachLayer((l) => {
    const p = l.feature.properties;
    l.bindTooltip(p.nombre_municipio, { sticky: true });
    l.bindPopup(`<div class="popup"><h4>${esc(p.nombre_municipio)}</h4>
      <p>Código DIVIPOLA: ${esc(p.cod_municipio)}</p><p>Veredas: ${esc(p.n_veredas)}</p>
      <button data-detalle="${esc(p.cod_municipio)}">Consultar detalle</button>
      <button data-veredas="${esc(p.cod_municipio)}">Ver veredas</button></div>`);
    l.on("mouseover", () => l.setStyle({ weight: 3, fillOpacity: 0.8 }));
    l.on("mouseout", () => capas.municipios.resetStyle(l));
  });
  mapa.fitBounds(capas.departamento.getBounds());
}

// Botones dentro de popups (delegación de eventos)
mapa.on("popupopen", (e) => {
  const el = e.popup.getElement();
  el.querySelectorAll("button[data-detalle]").forEach((b) =>
    b.addEventListener("click", () => detalleMunicipio(b.dataset.detalle, e.popup)));
  el.querySelectorAll("button[data-veredas]").forEach((b) =>
    b.addEventListener("click", () => veredasDeMunicipio(b.dataset.veredas)));
  el.querySelectorAll("button[data-vereda]").forEach((b) =>
    b.addEventListener("click", () => fichaVereda(b.dataset.vereda)));
});

// ---------------------------------------------------------------------------
// F2 · Consulta de atributos
// ---------------------------------------------------------------------------
// GET /municipios/{cod} → área geodésica calculada con ST_Area(geom::geography)
async function detalleMunicipio(cod) {
  activarTab("t-consulta");
  try {
    const m = await api(`/municipios/${cod}`);
    const dif = ((m.area_geodesica_km2 - m.area_oficial_km2) / m.area_oficial_km2) * 100;
    mostrar($("ficha"), `<h3>${esc(m.nombre_municipio)} <small>(${esc(m.cod_municipio)})</small></h3>` + dl([
      ["Departamento", m.nombre_departamento],
      ["Altitud cabecera", `${fmt(m.altitud_msnm, 0)} m s. n. m.`],
      ["Área geodésica (PostGIS)", `${fmt(m.area_geodesica_km2, 2)} km²`],
      ["Área oficial (atributo)", `${fmt(m.area_oficial_km2, 2)} km²`],
      ["Diferencia", `${fmt(dif, 2)} %`],
      ["Perímetro", `${fmt(m.perimetro_km, 1)} km`],
      ["Veredas", m.n_veredas],
      ["Norma de creación", m.norma_creacion || "—"],
    ]) + "<p class='ayuda'>Veredas por fuente: " +
      m.veredas_por_fuente.map((f) => `${esc(f.nombre_fuente)} (${f.n_veredas})`).join(", ") + "</p>");
  } catch (e) { mostrar($("ficha"), esc(e.message), true); }
}

// GET /municipios/{cod}/veredas → capa de veredas
async function veredasDeMunicipio(cod) {
  try {
    const fc = await api(`/municipios/${cod}/veredas`);
    capas.veredas.clearLayers();
    dibujarVeredas(capas.veredas, fc, ESTILO_VEREDA);
  } catch (e) { mostrar($("ficha"), esc(e.message), true); activarTab("t-consulta"); }
}

// GET /veredas/{id} → ficha + polígono
async function fichaVereda(id) {
  activarTab("t-consulta");
  try {
    const f = await api(`/veredas/${id}`);
    const p = f.properties;
    capas.veredas.clearLayers();
    capas.veredas.addData(f);
    capas.veredas.setStyle(ESTILO_VEREDA);
    ajustarA(f);
    mostrar($("ficha"), `<h3>${esc(p.nombre_vereda)}</h3>` + dl([
      ["Municipio", p.nombre_municipio],
      ["Código vereda", p.codigo_ver],
      ["Fuente del límite", p.nombre_fuente],
      ["Vigencia", p.vigencia || "—"],
      ["Centro poblado", p.tiene_centro_poblado ? "Sí" : "No"],
      ["Área geodésica", `${fmt(p.area_geodesica_ha, 1)} ha`],
      ["Área en la fuente", `${fmt(p.area_ha_fuente, 1)} ha`],
      ["Observación", p.observacion || "—"],
    ]));
  } catch (e) { mostrar($("ficha"), esc(e.message), true); }
}

function activarTab(id) {
  document.querySelector(`.tab[data-tab="${id}"]`).click();
}

// GET /veredas/buscar?q=…
$("form-buscar").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const ul = $("resultados-busqueda");
  ul.innerHTML = "";
  try {
    const filas = await api("/veredas/buscar", { q: $("q").value.trim() });
    if (!filas.length) { ul.innerHTML = "<li>Sin resultados</li>"; return; }
    for (const v of filas) {
      const li = document.createElement("li");
      li.innerHTML = `<b>${esc(v.nombre_vereda)}</b><small>${esc(v.nombre_municipio)}</small>`;
      li.addEventListener("click", () => fichaVereda(v.id_vereda));
      ul.appendChild(li);
    }
  } catch (e) { ul.innerHTML = `<li>${esc(e.message)}</li>`; }
});

// ---------------------------------------------------------------------------
// F3 · Consulta espacial (clic en el mapa → PostGIS)
// ---------------------------------------------------------------------------
$("radio").addEventListener("input", () => { $("radio-val").textContent = $("radio").value; });
$("btn-limpiar-espacial").addEventListener("click", () => {
  capas.espacial.clearLayers(); $("res-espacial").hidden = true;
});

const espacialActivo = () => $("t-espacial").classList.contains("activa");

// Los popups de las capas detienen la propagación del clic, así que en modo espacial
// el clic se captura en el contenedor del mapa (fase de captura), antes que las capas.
let _down = null;
mapa.getContainer().addEventListener("mousedown", (ev) => { _down = [ev.clientX, ev.clientY]; }, true);
mapa.getContainer().addEventListener("click", (ev) => {
  if (!espacialActivo() || ev.target.closest(".leaflet-control, .leaflet-popup")) return;
  if (_down && Math.hypot(ev.clientX - _down[0], ev.clientY - _down[1]) > 5) return; // fue un arrastre
  ev.stopPropagation();
  consultaEspacial(mapa.mouseEventToLatLng(ev));
}, true);
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
  mapa.getContainer().style.cursor = (b.dataset.tab === "t-espacial") ? "crosshair" : "";
  if (b.dataset.tab === "t-espacial") mapa.closePopup();
}));

async function consultaEspacial(latlng) {
  const e = { latlng };
  const { lat, lng } = e.latlng;
  const modo = document.querySelector("input[name=modo]:checked").value;
  capas.espacial.clearLayers();
  L.circleMarker(e.latlng, { radius: 6, color: "#7d3c98", fillColor: "#af7ac5", fillOpacity: 1 }).addTo(capas.espacial);
  const div = $("res-espacial");
  try {
    if (modo === "punto") {
      // GET /espacial/punto → ST_Covers
      const r = await api("/espacial/punto", { lon: lng.toFixed(6), lat: lat.toFixed(6) });
      const v = r.veredas.features;
      L.geoJSON(r.veredas, { style: ESTILO_VEREDA }).addTo(capas.espacial);
      mostrar(div, `<h3>Punto ${lat.toFixed(5)}, ${lng.toFixed(5)}</h3>` + dl([
        ["Municipio", r.municipio ? r.municipio.nombre_municipio : "Fuera del Cauca"],
        ["Vereda(s)", v.length ? v.map((f) => f.properties.nombre_vereda).join(", ") : "Ninguna"],
      ]));
    } else {
      // GET /espacial/cerca → ST_DWithin + ST_Distance (metros)
      const radioM = Number($("radio").value) * 1000;
      const r = await api("/espacial/cerca", { lon: lng.toFixed(6), lat: lat.toFixed(6), radio_m: radioM });
      L.circle(e.latlng, { radius: radioM, color: "#7d3c98", weight: 1.5, fillOpacity: 0.05, interactive: false }).addTo(capas.espacial);
      L.geoJSON(r, { style: ESTILO_VEREDA, onEachFeature: (f, l) => l.bindPopup(() => popupVereda(f.properties)) }).addTo(capas.espacial);
      mostrar(div, `<h3>${r.total} veredas a ≤ ${fmt(radioM / 1000, 1)} km</h3><ul class="lista">` +
        r.features.slice(0, 12).map((f) => `<li data-id="${esc(f.properties.id_vereda)}"><b>${esc(f.properties.nombre_vereda)}</b>
          <small>${esc(f.properties.nombre_municipio)} · ${fmt(f.properties.distancia_m, 0)} m</small></li>`).join("") + "</ul>");
      div.querySelectorAll("li[data-id]").forEach((li) => li.addEventListener("click", () => fichaVereda(li.dataset.id)));
    }
  } catch (err) { mostrar(div, esc(err.message), true); }
}

// ---------------------------------------------------------------------------
// F4 · Filtro combinado
// ---------------------------------------------------------------------------
async function cargarFiltros() {
  const [fuentes, vigencias] = await Promise.all([api("/catalogos/fuentes"), api("/catalogos/vigencias")]);
  const mun = capas.municipios.getLayers().map((l) => l.feature.properties)
    .sort((a, b) => a.nombre_municipio.localeCompare(b.nombre_municipio, "es"));
  const llenar = (sel, items) => items.forEach(([v, t]) => sel.add(new Option(t, v)));
  llenar($("f-mun"), mun.map((m) => [m.cod_municipio, m.nombre_municipio]));
  llenar($("f-fte"), fuentes.map((f) => [f.id_fuente, `${f.nombre_fuente} (${f.n_veredas})`]));
  llenar($("f-vig"), vigencias.map((v) => [v.vigencia, `${v.vigencia} (${v.n_veredas})`]));
}

$("form-filtros").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const div = $("res-filtros");
  try {
    const fc = await api("/veredas", {
      municipio: $("f-mun").value, id_fuente: $("f-fte").value, vigencia: $("f-vig").value,
      area_min_ha: $("f-amin").value, area_max_ha: $("f-amax").value,
      solo_centro_poblado: $("f-cp").checked,
    });
    dibujarVeredas(capas.veredas, fc, ESTILO_VEREDA);
    const r = fc.resumen;
    mostrar(div, "<h3>Resultado</h3>" + dl([
      ["Veredas que cumplen", r.total],
      ["Dibujadas", fc.devueltas + (fc.truncado ? " (límite)" : "")],
      ["Área total", `${fmt(r.area_total_ha, 0)} ha`],
      ["Área media", `${fmt(r.area_media_ha, 1)} ha`],
      ["Con centro poblado", r.con_centro_poblado],
    ]));
  } catch (e) { mostrar(div, esc(e.message), true); }
});

$("btn-limpiar-filtros").addEventListener("click", () => {
  $("form-filtros").reset();
  capas.veredas.clearLayers();
  $("res-filtros").hidden = true;
});

// ---------------------------------------------------------------------------
// F4 · Calidad espacial y ranking
// ---------------------------------------------------------------------------
$("btn-calidad").addEventListener("click", async () => {
  const ul = $("lista-calidad");
  ul.innerHTML = "";
  try {
    const fc = await api("/calidad/inconsistencias");
    dibujarVeredas(capas.calidad, fc, ESTILO_CALIDAD);
    ul.innerHTML = `<li><b>${fc.total} veredas fuera de su municipio declarado</b></li>`;
    capas.calidad.eachLayer((l) => {
      const p = l.feature.properties;
      const li = document.createElement("li");
      li.innerHTML = `<b>${esc(p.nombre_vereda)}</b><small>Declarado: ${esc(p.municipio_declarado)} · Real: ${esc(p.municipio_real || "fuera del Cauca")} · ${esc(p.nombre_fuente)}</small>`;
      li.addEventListener("click", () => { mapa.fitBounds(l.getBounds(), { maxZoom: 13 }); l.openPopup(); });
      ul.appendChild(li);
    });
  } catch (e) { ul.innerHTML = `<li>${esc(e.message)}</li>`; }
});

async function cargarRanking() {
  const filas = await api("/calidad/resumen-municipios");
  const tb = document.querySelector("#tabla-ranking tbody");
  tb.innerHTML = filas.map((f) => `<tr data-cod="${esc(f.cod_municipio)}"><td>${esc(f.nombre_municipio)}</td>
    <td>${f.n_veredas}</td><td>${fmt(f.area_media_ha, 0)}</td><td>${fmt(f.pct_centro_poblado, 0)}</td></tr>`).join("");
  tb.querySelectorAll("tr").forEach((tr) => tr.addEventListener("click", () => {
    const l = capas.municipios.getLayers().find((x) => x.feature.id === tr.dataset.cod);
    if (l) { mapa.fitBounds(l.getBounds()); l.openPopup(); }
  }));
}

iniciar();
