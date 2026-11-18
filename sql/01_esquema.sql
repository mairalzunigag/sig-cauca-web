-- =====================================================================
-- SIG Web del Cauca - Esquema de la geodatabase (PostgreSQL + PostGIS)
-- Ejecutar conectado a la base de datos del proyecto (ver README).
-- Sistema de referencia de almacenamiento: EPSG:4326 (WGS 84).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;   -- búsqueda sin tildes

DROP TABLE IF EXISTS vereda       CASCADE;
DROP TABLE IF EXISTS fuente_limite CASCADE;
DROP TABLE IF EXISTS municipio    CASCADE;
DROP TABLE IF EXISTS departamento CASCADE;

-- 1) Departamento (1 registro: Cauca) ---------------------------------
CREATE TABLE departamento (
    cod_departamento     VARCHAR(2)   PRIMARY KEY,
    nombre_departamento  VARCHAR(100) NOT NULL,
    area_oficial_km2     NUMERIC(12,3),
    norma                VARCHAR(250),
    geom                 geometry(MultiPolygon, 4326) NOT NULL
);

-- 2) Municipio (42 registros) ----------------------------------------
CREATE TABLE municipio (
    cod_municipio        VARCHAR(5)   PRIMARY KEY,            -- código DIVIPOLA
    nombre_municipio     VARCHAR(250) NOT NULL,
    cod_departamento     VARCHAR(2)   NOT NULL
                         REFERENCES departamento (cod_departamento),
    area_oficial_km2     NUMERIC(12,3),                       -- atributo MpArea de la fuente
    altitud_msnm         INTEGER,                             -- altitud de la cabecera
    norma_creacion       VARCHAR(250),
    geom                 geometry(MultiPolygon, 4326) NOT NULL,
    CONSTRAINT ck_municipio_cod CHECK (cod_municipio ~ '^[0-9]{5}$'),
    CONSTRAINT ck_municipio_dpto CHECK (left(cod_municipio, 2) = cod_departamento)
);

-- 3) Fuente del límite veredal (catálogo, 18 registros) ---------------
--    Cada vereda proviene de una fuente distinta (POT, IGAC, DANE, ...).
CREATE TABLE fuente_limite (
    id_fuente            SERIAL       PRIMARY KEY,
    nombre_fuente        VARCHAR(100) NOT NULL UNIQUE
);

-- 4) Vereda (2019 registros) -----------------------------------------
--    codigo_ver NO es único en la fuente (hay códigos repetidos para
--    veredas con partes separadas), por eso se usa clave sustituta.
CREATE TABLE vereda (
    id_vereda            SERIAL       PRIMARY KEY,
    codigo_ver           VARCHAR(8)   NOT NULL,
    nombre_vereda        VARCHAR(100) NOT NULL,
    cod_municipio        VARCHAR(5)   NOT NULL
                         REFERENCES municipio (cod_municipio),
    id_fuente            INTEGER      NOT NULL
                         REFERENCES fuente_limite (id_fuente),
    vigencia             VARCHAR(4),                          -- año o 'INDF' (indefinido)
    tiene_centro_poblado BOOLEAN      NOT NULL DEFAULT FALSE,
    observacion          TEXT,
    area_ha_fuente       NUMERIC(14,3),                       -- AREA_HA de la fuente
    geom                 geometry(MultiPolygon, 4326) NOT NULL
);

-- Índices -------------------------------------------------------------
CREATE INDEX idx_departamento_geom ON departamento USING GIST (geom);
CREATE INDEX idx_municipio_geom    ON municipio    USING GIST (geom);
CREATE INDEX idx_vereda_geom       ON vereda       USING GIST (geom);
-- Índice sobre la versión geography: lo usan ST_DWithin / ST_Distance
-- cuando la consulta se hace en metros (ver endpoint /espacial/cerca).
CREATE INDEX idx_vereda_geog       ON vereda       USING GIST ((geom::geography));
CREATE INDEX idx_vereda_municipio  ON vereda (cod_municipio);
CREATE INDEX idx_vereda_fuente     ON vereda (id_fuente);
CREATE INDEX idx_vereda_nombre     ON vereda (nombre_vereda);
