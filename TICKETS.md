# Plan de tickets — Mi Carro EV

Los tickets están preparados como plan de construcción. **No se marcan como completados sin probar la app publicada con el Excel real.**

| Ticket | Objetivo | Depende de | Estado |
|---|---|---|---|
| T-01 | Repositorio y despliegue «Hola Mundo» | — | Pendiente de despliegue |
| T-02 | Navegación Necesidades → Alternativas → Comparar → Favoritos | T-01 | Implementado, pendiente de pruebas |
| T-03 | Cargar Excel, validar datos y normalizar segmento sin modelo ML inexistente | T-01 | Implementado, pendiente del Excel |
| T-04 | Formulario de presupuesto y pasajeros | T-02 | Implementado, pendiente de pruebas |
| T-05 | Guardar necesidades y navegar | T-04 | Implementado, pendiente de pruebas |
| T-06 | Catálogo con filtros obligatorios | T-03, T-05 | Implementado, pendiente del Excel |
| T-07 | Mostrar datos faltantes sin inventarlos | T-06 | Implementación parcial; validar en UI |
| T-08 | Añadir o quitar vehículos de comparación | T-06 | Implementado, pendiente de pruebas |
| T-09 | Comparación de atributos y unidades | T-08 | Implementado, pendiente de pruebas |
| T-10 | Favoritos de sesión | T-06 | Implementado, pendiente de pruebas |
| T-11 (propuesto) | Ampliar cuestionario de uso y preferencias | T-05 | Parcial |
| T-12 (propuesto) | Recomendador explicable validado | T-03, T-11 | Prototipo de reglas; pendiente de validación |
| T-13 (propuesto) | Explicar ventajas, desventajas y limitaciones | T-12 | Parcial |

## Cambios frente al T-03 original
El plan original exigía `vehiculos.csv` y `modelo.joblib`. No se han proporcionado ni CSV ni modelo entrenado, por lo que este prototipo usa el Excel real y reglas documentadas. Si el profesor exige un modelo ML, este ticket debe revisarse con él.

## Pruebas de aceptación
- Desplegar desde GitHub en Streamlit Community Cloud.
- Subir Excel real con hoja `BD` y columnas esperadas.
- Confirmar filtros de presupuesto y pasajeros.
- Seleccionar y deseleccionar vehículos para comparar y favoritos.
- Verificar que la autonomía se muestra con su ciclo y no se comparan ciclos distintos como equivalentes.
- Probar desde el celular.
