# TiendaNova S.A.S. — Caso de uso de BI

Guía 11: análisis de la caída en ventas. Caso académico con datos sintéticos de noviembre de 2024 a octubre de 2026.

## Contenido
- `index.html`: dashboard interactivo con Chart.js incorporado. Abrir en el navegador.
- `scripts/`: scripts Python para generación, ETL y análisis.
- `requirements.txt`: dependencias de Python.

## Ejecución del análisis
Desde la raíz del repositorio:

```bash
python -m pip install -r requirements.txt
cd scripts
python gen_data.py
python etl_kpi.py
python analysis.py
```

`gen_data.py` regenera los CSV sintéticos. Los archivos Excel, Word y las evidencias forman parte del paquete de entrega original.

## Dashboard
El archivo `index.html` funciona de forma local. Para publicar con GitHub Pages, seleccionar la rama `main` y la carpeta `/ (root)` en Settings > Pages.

Los datos son simulados con fines académicos. Se conservan los avisos de licencia de las bibliotecas incluidas.
