from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx

app = FastAPI()

API_KEY = "c1509a9d90f6ae1f2cb351c1eec8ad64" 
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

TEMPLATES_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

from fastapi import Query

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("busqueda.html", {"request": request})    
    
@app.get("/clima", response_class=HTMLResponse)
async def get_weather(request: Request, city: str):
    parametros = {
        "q": city,  
        "appid": API_KEY,
        "units": "metric"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BASE_URL, params=parametros)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Error contacting weather API")
        if response.status_code == 200:
            data = response.json()
            datos_clima = {
                "ciudad": data["name"],   
                "temperatura": data["main"]["temp"],
                "descripcion": data["weather"][0]["description"],
                "humedad": data["main"]["humidity"],
                "velocidad-viento": data["wind"]["speed"]
            }
            return templates.TemplateResponse("resultado.html", {"request": request, "clima": datos_clima})
        else:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")