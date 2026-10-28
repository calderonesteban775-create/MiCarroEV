# Mi Carro EV 🚗
Aplicación académica para explorar, filtrar y comparar vehículos eléctricos e híbridos del mercado colombiano.

## Puesta en marcha
1. Crea un repositorio de GitHub y sube **el contenido** de este ZIP a la raíz.
2. Agrega el archivo real `datos/vehiculos_ev_hibridos_colombia.xlsx` (hoja `BD`). **No se incluye en el ZIP porque no ha sido suministrado.**
3. En Streamlit Community Cloud crea una app conectada al repositorio, rama `main`, archivo principal `app.py`.
4. La app puede publicarse sin Excel, pero solo habilita sus funcionalidades de catálogo cuando el Excel esté presente.

## Desarrollo local (opcional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Alcance
Filtro obligatorio por precio máximo y pasajeros; preferencias sencillas de tecnología, carrocería y carga; comparación y favoritos durante la sesión. La recomendación es un ordenamiento basado en reglas, **no machine learning**. No se inventan autonomías ni conversiones de ciclos. Precios y disponibilidad requieren verificación.

## Estructura
- `app.py`: interfaz Streamlit.
- `pipeline.py`: lectura, auditoría básica, normalización conservadora, filtrado y ordenamiento explicable.
- `datos/`: ubicación del Excel real.
- `docs/funcionalidades.md`: alcance y comportamiento de las pantallas.
- `TICKETS.md`: plan de trabajo y criterios de aceptación.

**Advertencia:** el proyecto es un prototipo académico. No sustituye la verificación comercial y técnica antes de comprar un vehículo.
