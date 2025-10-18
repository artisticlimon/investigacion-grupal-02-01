from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
import redis
import json
import asyncio
import time

app = FastAPI()  # Instancia FastAPI

# Cliente Redis (Valkey) y almacenarlo en el estado de la app
valkey_client = redis.Redis(host='localhost', port=6379, db=0)
app.state.valkey_client = valkey_client

# API clima
API_KEY = "c1509a9d90f6ae1f2cb351c1eec8ad64"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Plantillas HTML
TEMPLATES_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Página de búsqueda
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("busqueda.html", {"request": request})

# Obtener clima con caché Valkey
@app.get("/clima", response_class=HTMLResponse)
async def get_weather(request: Request, city: str):
    parametros = {"q": city, "appid": API_KEY, "units": "metric"}
    t_start = time.perf_counter()

    # Intentar obtener del caché Valkey
    cached = None
    try:
        t0 = time.perf_counter()
        try:
            cached = await asyncio.to_thread(app.state.valkey_client.get, city)
            t1 = time.perf_counter()
            print(f"[cache] get {city} took {t1-t0:.3f}s")
        except Exception:
            t1 = time.perf_counter()
            print(f"[cache] get {city} failed/timed out after {t1-t0:.3f}s")
            cached = None
        if isinstance(cached, (bytes, bytearray)):
            cached = cached.decode()
    except Exception:
        cached = None

    if cached:
        try:
            valor = json.loads(cached)
        except Exception:
            valor = None
        if valor:
            datos_clima = {
                "ciudad": valor.get("name"),
                "temperatura": valor.get("main", {}).get("temp"),
                "descripcion": valor.get("weather", [{}])[0].get("description"),
                "humedad": valor.get("main", {}).get("humidity"),
                "velocidad_viento": valor.get("wind", {}).get("speed"),
            }
            duracion = f"{(time.perf_counter() - t_start):.6f}s"
            return templates.TemplateResponse("resultado.html", {
                "request": request,
                "clima": datos_clima,
                "duracion": duracion,
                "fuente": "cache"
            })

    # Si no está en caché, pedir a la API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BASE_URL, params=parametros)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="No se puede conectar al servicio de clima")

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")

        valor = response.json()

        # Guardar en caché Valkey (expiración 5 minutos)
        try:
            await asyncio.to_thread(lambda: app.state.valkey_client.set(city, json.dumps(valor), ex=300))
            print(f"[cache] set {city} successful")
        except Exception:
            print("[cache] set failed")
            pass

        datos_clima = {
            "ciudad": valor.get("name"),
            "temperatura": valor.get("main", {}).get("temp"),
            "descripcion": valor.get("weather", [{}])[0].get("description"),
            "humedad": valor.get("main", {}).get("humidity"),
            "velocidad_viento": valor.get("wind", {}).get("speed"),
        }

    duracion = f"{(time.perf_counter() - t_start):.6f}s"
    return templates.TemplateResponse("resultado.html", {
        "request": request,
        "clima": datos_clima,
        "duracion": duracion,
        "fuente": "api"
    })
