"""F2 (búsqueda/consulta de atributos) y F4 (filtro combinado) sobre veredas."""
from fastapi import APIRouter, HTTPException, Path, Query

from ..db import consultar, consultar_uno, feature_collection

router = APIRouter(tags=["F2/F4 · Veredas"])


@router.get("/veredas/buscar")
def buscar_veredas(
    q: str = Query(min_length=2, max_length=60, description="Texto a buscar en el nombre"),
    limite: int = Query(20, ge=1, le=100),
):
    """F2 · Búsqueda por nombre, sin distinguir mayúsculas ni tildes.

    El texto del usuario se pasa como parámetro (%(patron)s): nunca se concatena.
    """
    sql = """
        SELECT v.id_vereda, v.nombre_vereda, m.nombre_municipio, v.cod_municipio,
               ST_X(ST_PointOnSurface(v.geom)) AS lon,
               ST_Y(ST_PointOnSurface(v.geom)) AS lat
        FROM vereda v
        JOIN municipio m ON m.cod_municipio = v.cod_municipio
        WHERE unaccent(v.nombre_vereda) ILIKE unaccent(%(patron)s)
        ORDER BY (unaccent(v.nombre_vereda) ILIKE unaccent(%(prefijo)s)) DESC,
                 v.nombre_vereda
        LIMIT %(limite)s
    """
    patron = f"%{q}%"
    return consultar(sql, {"patron": patron, "prefijo": f"{q}%", "limite": limite})


@router.get("/veredas/{id_vereda}")
def detalle_vereda(id_vereda: int = Path(ge=1)):
    """F2 · Ficha de una vereda (Feature GeoJSON) con área geodésica en hectáreas."""
    sql = """
        SELECT v.id_vereda, v.codigo_ver, v.nombre_vereda,
               m.nombre_municipio, v.cod_municipio,
               f.nombre_fuente, v.vigencia, v.tiene_centro_poblado, v.observacion,
               v.area_ha_fuente,
               round((ST_Area(v.geom::geography) / 10000.0)::numeric, 2) AS area_geodesica_ha,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(v.geom, 0.0001), 6) AS geometria
        FROM vereda v
        JOIN municipio m     ON m.cod_municipio = v.cod_municipio
        JOIN fuente_limite f ON f.id_fuente = v.id_fuente
        WHERE v.id_vereda = %(id)s
    """
    filas = consultar(sql, {"id": id_vereda})
    if not filas:
        raise HTTPException(404, f"Vereda {id_vereda} no encontrada")
    return feature_collection(filas, id_campo="id_vereda")["features"][0]


@router.get("/municipios/{cod_municipio}/veredas")
def veredas_de_municipio(cod_municipio: str = Path(pattern=r"^\d{5}$")):
    """F1/F2 · Veredas de un municipio (relación 1:N) como GeoJSON."""
    return _filtrar_veredas(municipio=cod_municipio, limite=500)


@router.get("/veredas")
def filtrar_veredas(
    municipio: str | None = Query(None, pattern=r"^\d{5}$"),
    id_fuente: int | None = Query(None, ge=1),
    vigencia: str | None = Query(None, max_length=4),
    area_min_ha: float | None = Query(None, ge=0),
    area_max_ha: float | None = Query(None, ge=0),
    solo_centro_poblado: bool = False,
    limite: int = Query(300, ge=1, le=2100),
):
    """F4 · Filtro combinado (municipio + fuente + vigencia + rango de área).

    Devuelve las veredas como GeoJSON y un resumen estadístico calculado en SQL.
    """
    return _filtrar_veredas(municipio, id_fuente, vigencia, area_min_ha,
                            area_max_ha, solo_centro_poblado, limite)


def _filtrar_veredas(municipio=None, id_fuente=None, vigencia=None, area_min_ha=None,
                     area_max_ha=None, solo_centro_poblado=False, limite=300):
    # Cada filtro es opcional: "(%(x)s::tipo IS NULL OR condición)". Todos los
    # valores van como parámetros; la estructura del SQL no depende del usuario.
    filtros = """
        WHERE (%(mun)s::varchar  IS NULL OR v.cod_municipio = %(mun)s)
          AND (%(fte)s::integer  IS NULL OR v.id_fuente     = %(fte)s)
          AND (%(vig)s::varchar  IS NULL OR v.vigencia      = %(vig)s)
          AND (%(amin)s::numeric IS NULL OR ST_Area(v.geom::geography) / 10000.0 >= %(amin)s)
          AND (%(amax)s::numeric IS NULL OR ST_Area(v.geom::geography) / 10000.0 <= %(amax)s)
          AND (NOT %(cp)s::boolean OR v.tiene_centro_poblado)
    """
    params = {"mun": municipio, "fte": id_fuente, "vig": vigencia, "amin": area_min_ha,
              "amax": area_max_ha, "cp": solo_centro_poblado, "limite": limite}

    sql_features = f"""
        SELECT v.id_vereda, v.nombre_vereda, m.nombre_municipio, f.nombre_fuente,
               v.vigencia, v.tiene_centro_poblado,
               round((ST_Area(v.geom::geography) / 10000.0)::numeric, 2) AS area_ha,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(v.geom, 0.0002), 6) AS geometria
        FROM vereda v
        JOIN municipio m     ON m.cod_municipio = v.cod_municipio
        JOIN fuente_limite f ON f.id_fuente = v.id_fuente
        {filtros}
        ORDER BY v.nombre_vereda
        LIMIT %(limite)s
    """
    sql_resumen = f"""
        SELECT count(*)                                                    AS total,
               round((sum(ST_Area(v.geom::geography)) / 10000.0)::numeric, 1) AS area_total_ha,
               round((avg(ST_Area(v.geom::geography)) / 10000.0)::numeric, 1) AS area_media_ha,
               count(*) FILTER (WHERE v.tiene_centro_poblado)              AS con_centro_poblado
        FROM vereda v
        {filtros}
    """
    resumen = consultar_uno(sql_resumen, params)
    filas = consultar(sql_features, params)
    return feature_collection(
        filas, id_campo="id_vereda",
        extra={"resumen": resumen, "devueltas": len(filas),
               "truncado": resumen["total"] > len(filas)},
    )
