# Investigación Grupal 1- Gestión de Bases de Datos y Análisis de Información

Este repositorio contiene tres aplicaciones con la misma arquitectura, pero con un gestor de base de datos diferente (Redis, Valkey o KeyDB). El propósito es hacer una comparación entre estos tres softwares de datos NoSQL (específicamente de datos tipo clave-valor).

En cada carpeta hay tres archivos. Los dos archivos HTML corresponden a la UI, que consiste de una página de búsqueda y una página con los resultados. El controlador está en el archivo main.py.

Esta aplicación utiliza FastAPI y OpenWeatherMap.

Para implementar cada aplicación, primero se debe descargar la carpeta que corresponde al software deseado. Hay que asegurarse que estén los tres archivos en la carpeta (dos HTML y uno .py). Es importante asegurarse que se tengan todos los paquetes del main.py descargados, al igual que ``uvicorn`` y el software de base de datos en sí. Luego, se corre esta carpeta desde la terminal y se pasa el siguiente comando: ``uvicorn main:app --reload``. Finalmente, se abre el enlace que aparece en terminal usando CRTL+C.

La página de búsqueda de la aplicación se debe ver así:

 ![](/images/busqueda-ejemplo.png)

y un ejemplo de la página de resultados es la siguiente:

 ![](/images/resultado-ejemplo.png)
