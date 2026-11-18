# Verificación API ↔ PostgreSQL/PostGIS

- Fecha: 2026-11-17 22:39
- Python 3.12.10 · Windows
- PostgreSQL 18.7 on x86_64-windows · PostGIS 3.7
- API: http://127.0.0.1:8000

| # | Prueba | Endpoint | HTTP | ms | Resultado API | Resultado SQL directo | ¿Coincide? |
|---|--------|----------|------|----|---------------|-----------------------|-----------|
| 1 | Municipios en /salud | `/salud` | 200 application/json | 55 | 42 | 42 | ✅ |
| 2 | Veredas en /salud | `/salud` | 200 application/json | 21 | 2019 | 2019 | ✅ |
| 3 | F1 · nº de municipios (FeatureCollection) | `/municipios` | 200 application/json | 641 | 42 | 42 | ✅ |
| 4 | F1 · Σ n_veredas de los features | `/municipios` | 200 application/json | 678 | 2019 | 2019 | ✅ |
| 5 | F2 · área geodésica Popayán (km²) | `/municipios/19001` | 200 application/json | 52 | 479.244 | 479.2442364985285 | ✅ |
| 6 | F2 · búsqueda 'el cane' (ids) | `/veredas/buscar?q=el%20cane` | 200 application/json | 40 | [1, 209, 613] | [1, 209, 613] | ✅ |
| 7 | F3 · veredas ≤ 3 km del punto (ids) | `/espacial/cerca?lon=-76.606&lat=2.444&radio_m=3000` | 200 application/json | 102 | [3, 4, 5, 13, 1585, 1933] | [3, 4, 5, 13, 1585, 1933] | ✅ |
| 8 | F3 · municipio que contiene el punto | `/espacial/punto?lon=-76.606&lat=2.444` | 200 application/json | 17 | 19001 | 19001 | ✅ |
| 9 | F4 · veredas Timbío 100–500 ha | `/veredas?municipio=19807&area_min_ha=100&area_max_` | 200 application/json | 270 | 41 | 41 | ✅ |
| 10 | F4 · veredas fuera de su municipio | `/calidad/inconsistencias` | 200 application/json | 1274 | 17 | 17 | ✅ |

**Resultado global: todas las comparaciones coinciden**

Las respuestas completas (con geometrías resumidas) están en `docs/evidencias/api/`.
