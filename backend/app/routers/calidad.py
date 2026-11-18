"""F4 (complementaria) · Control de calidad espacial de los límites veredales."""
from fastapi import APIRouter

from ..db import consultar, feature_collection

router = APIRouter(prefix="/calidad", tags=["F4 · Calidad espacial"])


@router.get("/inconsistencias")
def veredas_fuera_de_su_municipio():
    """Veredas cuyo punto interior (ST_PointOnSurface) NO cae dentro del municipio
    declarado en sus atributos (cod_municipio). Señala desajustes entre las fuentes
    de las veredas y el límite municipal oficial.

    ST_PointOnSurface garantiza un punto dentro del polígono (el centroide puede
    quedar fuera en polígonos cóncavos).
    """
    sql = """
        SELECT v.id_vereda, v.nombre_vereda,
               md.nombre_municipio AS municipio_declarado,
               mr.nombre_municipio AS municipio_real,
               f.nombre_fuente,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(v.geom, 0.0002), 6) AS geometria
        FROM vereda v
        JOIN municipio md    ON md.cod_municipio = v.cod_municipio
        JOIN fuente_limite f ON f.id_fuente = v.id_fuente
        LEFT JOIN municipio mr
               ON ST_Covers(mr.geom, ST_PointOnSurface(v.geom))
        WHERE mr.cod_municipio IS DISTINCT FROM v.cod_municipio
        ORDER BY md.nombre_municipio, v.nombre_vereda
    """
    filas = consultar(sql)
    return feature_collection(filas, id_campo="id_vereda", extra={"total": len(filas)})


@router.get("/resumen-municipios")
def resumen_por_municipio():
    """Ranking de municipios: número de veredas, área media y % con centro poblado."""
    sql = """
        SELECT m.cod_municipio, m.nombre_municipio,
               count(v.id_vereda)                                              AS n_veredas,
               round((avg(ST_Area(v.geom::geography)) / 10000.0)::numeric, 1)  AS area_media_ha,
               round(100.0 * count(*) FILTER (WHERE v.tiene_centro_poblado)
                     / NULLIF(count(v.id_vereda), 0), 1)                       AS pct_centro_poblado,
               count(DISTINCT v.id_fuente)                                     AS n_fuentes
        FROM municipio m
        LEFT JOIN vereda v ON v.cod_municipio = m.cod_municipio
        GROUP BY m.cod_municipio, m.nombre_municipio
        ORDER BY n_veredas DESC, m.nombre_municipio
    """
    return consultar(sql)
