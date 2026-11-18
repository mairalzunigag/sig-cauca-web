-- =====================================================================
-- Consultas de verificación: se ejecutan DIRECTAMENTE en PostgreSQL
-- (psql o pgAdmin) y sus resultados se contrastan con lo que muestra el visor.
--   psql -h localhost -U postgres -d sig_cauca -f sql/02_verificacion.sql
-- =====================================================================

-- V0. Integridad: conteos y relaciones sin huérfanos
SELECT (SELECT count(*) FROM departamento)  AS departamentos,
       (SELECT count(*) FROM municipio)     AS municipios,
       (SELECT count(*) FROM fuente_limite) AS fuentes,
       (SELECT count(*) FROM vereda)        AS veredas,
       (SELECT count(*) FROM vereda v
         LEFT JOIN municipio m ON m.cod_municipio = v.cod_municipio
        WHERE m.cod_municipio IS NULL)      AS veredas_sin_municipio;

-- V1 (F1). Los mismos 42 municipios y su número de veredas que dibuja el mapa
SELECT m.cod_municipio, m.nombre_municipio, count(v.id_vereda) AS n_veredas
FROM municipio m LEFT JOIN vereda v USING (cod_municipio)
GROUP BY 1, 2 ORDER BY 1;

-- V2 (F2). Detalle de Popayán: ficha del visor (GET /municipios/19001)
SELECT cod_municipio, nombre_municipio, area_oficial_km2,
       round((ST_Area(geom::geography) / 1e6)::numeric, 3)   AS area_geodesica_km2,
       round((ST_Perimeter(geom::geography) / 1e3)::numeric, 3) AS perimetro_km
FROM municipio WHERE cod_municipio = '19001';

-- V3 (F3). Veredas a ≤ 3 km del punto (lon -76.606, lat 2.444)
--          (GET /espacial/cerca?lon=-76.606&lat=2.444&radio_m=3000)
--          Formulación alternativa con ST_Distance en lugar de ST_DWithin.
SELECT v.id_vereda, v.nombre_vereda,
       round(ST_Distance(v.geom::geography,
             ST_SetSRID(ST_MakePoint(-76.606, 2.444), 4326)::geography)::numeric, 1) AS distancia_m
FROM vereda v
WHERE ST_Distance(v.geom::geography,
      ST_SetSRID(ST_MakePoint(-76.606, 2.444), 4326)::geography) <= 3000
ORDER BY distancia_m, nombre_vereda;

-- V4 (F3). ¿Qué municipio contiene ese punto? (GET /espacial/punto)
SELECT cod_municipio, nombre_municipio FROM municipio
WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(-76.606, 2.444), 4326));

-- V5 (F4). Veredas de Timbío con área entre 100 y 500 ha
SELECT count(*) AS total
FROM vereda
WHERE cod_municipio = '19807'
  AND ST_Area(geom::geography) / 10000 BETWEEN 100 AND 500;

-- V6 (F4). Veredas cuyo punto interior cae fuera del municipio declarado
SELECT count(*) AS inconsistentes
FROM vereda v
WHERE NOT EXISTS (
    SELECT 1 FROM municipio m
    WHERE m.cod_municipio = v.cod_municipio
      AND ST_Covers(m.geom, ST_PointOnSurface(v.geom)));

-- V7. Justificación del CRS: la misma área en grados² (sin sentido) y en km²
SELECT round(ST_Area(geom)::numeric, 6)               AS area_en_grados2,
       round((ST_Area(geom::geography)/1e6)::numeric, 2) AS area_en_km2
FROM municipio WHERE cod_municipio = '19001';
