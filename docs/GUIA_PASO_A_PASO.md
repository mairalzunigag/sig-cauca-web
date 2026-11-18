# Guía paso a paso (Windows) — de cero a entrega

Tiempo estimado: 1 a 1,5 horas. Hazlo en este orden.

## A. Instalar lo necesario (una sola vez)

1. **PostgreSQL con PostGIS**: descarga el instalador de PostgreSQL 16 para Windows (EDB). Al terminar, abre
   **Application Stack Builder** → Spatial Extensions → **PostGIS 3** → instalar.
   Anota la **contraseña** que pusiste para el usuario `postgres`. Puerto por defecto: 5432. Incluye **pgAdmin 4**.
2. **Python 3.10+** desde python.org. Marca la casilla **"Add Python to PATH"**.
3. **GitHub Desktop** (desktop.github.com) e inicia sesión con tu cuenta de GitHub (créala si no tienes).
4. **Visual Studio Code** (opcional pero cómodo).

## B. Preparar el proyecto

1. Descomprime `sig-cauca-web.zip` (p. ej. en `C:\sig-cauca-web`).
2. Abre **pgAdmin 4** → conéctate → clic derecho en *Databases* → *Create* → *Database…* → nombre: `sig_cauca` → Save.
3. Abre **PowerShell** dentro de la carpeta del proyecto (en el Explorador: clic en la barra de ruta, escribe `powershell`, Enter):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
En el Bloc de notas deja `PGUSER=postgres` y pon en `PGPASSWORD=` tu contraseña de PostgreSQL. Guarda y cierra.

4. Crea las tablas y carga los datos:
```powershell
python scripts\cargar_datos.py --crear-esquema
```
Debe terminar con: `departamento: 1`, `municipio: 42`, `fuente_limite: 18`, `vereda: 2019`, `Carga completa.`
Si falla con "password authentication failed", la contraseña del `.env` está mal.
Si falla con "extension postgis is not available", falta instalar PostGIS (paso A.1).

## C. Ejecutar el visor

```powershell
uvicorn backend.app.main:app --reload
```
Abre en el navegador: **http://127.0.0.1:8000/** (visor) y **http://127.0.0.1:8000/docs** (API).
Deja esta ventana abierta mientras haces las evidencias.

## D. Evidencias (lo que pide el profesor)

1. En **otra** ventana de PowerShell (misma carpeta, con `.venv\Scripts\activate`):
```powershell
python scripts\generar_evidencias.py
```
   Debe decir "todas las comparaciones coinciden". Genera `docs\evidencias\verificacion.md`.
2. Captura de pantalla (tecla Windows + Shift + S) y guarda en `docs\evidencias\capturas\` según
   `LEEME.md` de esa carpeta (8 capturas). Para la captura de pgAdmin: clic derecho en `sig_cauca` →
   *Query Tool* → pega la consulta **V3** de `sql\02_verificacion.sql` → ejecuta (F5) → captura.
   Compara que salgan las mismas 6 veredas que en el visor (punto lon -76.606, lat 2.444, radio 3 km).
3. En el README, bajo la sección 10, agrega las imágenes, por ejemplo: `![Visor F1](docs/evidencias/capturas/01_visor_f1.png)`.
4. Completa en el README la tabla de **Procedencia de los archivos** (entidad y enlace de donde bajaste los datos).

## E. Subir a GitHub

1. GitHub Desktop → *File → Add local repository…* → elige la carpeta → si pregunta, *create a repository*.
   Nombre sugerido: `sig-web-cauca`. **Verifica que NO aparezca `.env` en la lista de cambios** (debe estar ignorado).
2. Escribe un mensaje ("Entrega tarea integradora") → *Commit to main* → *Publish repository*.
   **Desmarca** "Keep this code private" (el repo debe ser público).
3. Abre la URL del repo en una ventana de incógnito para comprobar que se ve el README, las carpetas y que no hay `.env`.

## F. Enviar el correo

- Para: juliangarzonb@uniquindio.edu.co
- Asunto: `Programación para SIG — Tarea integradora — Maira Lucia Zuñiga Gomez`
- Cuerpo: saludo + enlace del repositorio. Fecha límite: **jueves 19 de noviembre, 11:59 p. m.**

## Problemas frecuentes

| Síntoma | Solución |
|---------|----------|
| `uvicorn` no se reconoce | Activa el entorno: `.venv\Scripts\activate` |
| Visor dice "No se pudo conectar con la API" | uvicorn no está corriendo o abriste el HTML con doble clic; usa http://127.0.0.1:8000/ |
| El mapa sale gris sin fondo | Falta internet (el fondo es OpenStreetMap); las capas igual se dibujan |
| `psycopg` no instala | Actualiza pip: `python -m pip install --upgrade pip` |
