from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
import redis
import json
import asyncio

app = FastAPI()

# Conexión a Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
app.state.redis_client = redis_client

API_KEY = "e398b09460852caba2296b2d5915e79e" 
BASE_URL = "http://api.openweathermap.org/data/3.0/weather"

TEMPLATES_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("busqueda.html", {"request": request})    
    
@app.get("/clima", response_class=HTMLResponse)
async def get_weather(request: Request, city: str):
    parametros = {"q": city, "appid": API_KEY, "units": "metric"}

    # Intentar obtener de cache Redis
    cached = None
    try:
        import time
        t0 = time.perf_counter()
        try:
            cached = await asyncio.wait_for(
                asyncio.to_thread(app.state.redis_client.get, city), timeout=0.5
            )
            t1 = time.perf_counter()
            print(f"[cache] get {city} took {t1-t0:.3f}s")
        except Exception:
            t1 = time.perf_counter()
            print(f"[cache] get {city} failed/timed out after {t1-t0:.3f}s")
            cached = None
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
            return templates.TemplateResponse("resultado.html", {"request": request, "clima": datos_clima})

    # Si no está en cache, consultar OpenWeather
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BASE_URL, params=parametros)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="No se puede conectar al servicio de clima")

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")

        valor = response.json()

        # Guardar en cache Redis con TTL 300s (5 minutos)
        try:
            t0 = time.perf_counter()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(lambda: app.state.redis_client.set(city, json.dumps(valor), ex=300)),
                    timeout=0.5
                )
                t1 = time.perf_counter()
                print(f"[cache] set {city} took {t1-t0:.3f}s")
            except Exception:
                t1 = time.perf_counter()
                print(f"[cache] set {city} failed/timed out after {t1-t0:.3f}s")
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
        return templates.TemplateResponse("resultado.html", {"request": request, "clima": datos_clima})

    