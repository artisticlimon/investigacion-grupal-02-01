#Aplicación FastAPI para obtener y mostrar el clima de una ciudad utilizando Redis como caché.

#Cargar los paquetes necesarios
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
import valkey
import json
import time
import asyncio

app = FastAPI() # Crear instancia de la aplicación FastAPI

# Configurar valkey cliente y almacenarlo 
valkey_client = valkey.Valkey(host='localhost', port=6379, db=0, decode_responses=True)
app.state.valkey_client = valkey_client

# Configuración de la API de clima, con el API key y URL base
API_KEY = "c1509a9d90f6ae1f2cb351c1eec8ad64" 
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

#Plantillas html
TEMPLATES_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Enseñar página de búsqueda
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("busqueda.html", {"request": request})    

# Obtener clima de una ciudad, usando Redis
@app.get("/clima", response_class=HTMLResponse)
async def get_weather(request: Request, city: str):
    parametros = {"q": city, "appid": API_KEY, "units": "metric"}  #Parámetros para la solicitud de la API
    t_start = time.perf_counter()

    # Intentar obtener del cache valkey
    cached = None
    try:
        t0 = time.perf_counter() # Tiempo inicial para medir tiempo de obtención desde caché
        try:
            cached = await asyncio.wait_for( # Obtener valor desde valkey con timeout, si está disponible, y que cada 5 minutos se elimine
                asyncio.to_thread(app.state.valkey_client.get, city),
                timeout=0.5
            )
            t1 = time.perf_counter() # Tiempo final para medir tiempo de obtención desde caché
            print(f"[cache] get {city} took {t1-t0:.3f}s") # Imprimir tiempo tomado para obtener desde caché
        except Exception:
            t1 = time.perf_counter()
            print(f"[cache] get {city} failed/timed out after {t1-t0:.3f}s") # Imprimir si la obtención desde caché falló o se agotó el tiempo
            cached = None # Si falla la obtención, establecer cached como None
        if isinstance(cached, (bytes, bytearray)):
            cached = cached.decode() # Decodificar bytes a string si es necesario
    except Exception:
        cached = None

    if cached:
        try:
            valor = json.loads(cached) # Cargar datos JSON desde el caché
        except Exception:
            valor = None # Si falla la carga, establecer valor como None
        if valor:
            datos_clima = {
                "ciudad": valor.get("name"),
                "temperatura": valor.get("main", {}).get("temp"),
                "descripcion": valor.get("weather", [{}])[0].get("description"),
                "humedad": valor.get("main", {}).get("humidity"),
                "velocidad_viento": valor.get("wind", {}).get("speed"),
            } # Extraer datos relevantes del valor cargado
            duracion = f"{(time.perf_counter() - t_start):.6f}s" # Calcular duración total de la operación
            return templates.TemplateResponse(
                "resultado.html", 
                {"request": request, "clima": datos_clima, "duracion": duracion, "fuente": "cache"} # Enseñar resultado desde caché, con duración y fuente
            )

    # --- Consultar API ---
    async with httpx.AsyncClient() as client:
        try:  # Si no está en caché, hacer solicitud a la API de clima
            response = await client.get(BASE_URL, params=parametros) # Hacer solicitud GET a la API de clima
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="No se puede conectar al servicio de clima") # Si no se puede conectar, imprimir mensaje de error

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada") # Si la ciudad no se encuentra, imprimir mensaje de error

        valor = response.json() # Obtener datos JSON de la respuesta

        
        try:
            t0 = time.perf_counter()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(lambda: app.state.valkey_client.set(city, json.dumps(valor), ex=300)),
                    timeout=0.5
                ) # Almacenar datos en valkey con tiempo de expiración de 5 minutos y timeout
                t1 = time.perf_counter()
                print(f"[cache] set {city} took {t1-t0:.3f}s")  # Imprimir tiempo tomado para almacenar en caché
            except Exception:
                t1 = time.perf_counter()
                print(f"[cache] set {city} failed/timed out after {t1-t0:.3f}s") # Imprimir si el almacenamiento en caché falló o se agotó el tiempo, y en cuánto tiempo
        except Exception:
            print("[cache] set failed") # Imprimir si hubo un error general al almacenar en caché
            pass

        datos_clima = { # Extraer datos relevantes del valor obtenido de la API o el caché
            "ciudad": valor.get("name"),
            "temperatura": valor.get("main", {}).get("temp"),
            "descripcion": valor.get("weather", [{}])[0].get("description"),
            "humedad": valor.get("main", {}).get("humidity"),
            "velocidad_viento": valor.get("wind", {}).get("speed"),
        }
    duracion = f"{(time.perf_counter() - t_start):.6f}s"  # Calcular duración total de la operación
    return templates.TemplateResponse(
        "resultado.html", 
        {"request": request, "clima": datos_clima, "duracion": duracion, "fuente": "api"} # Enseñar resultado desde la API, con fuente del API y duración
    )
    