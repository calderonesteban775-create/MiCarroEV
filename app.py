import streamlit as st
import pandas as pd
from pipeline import (
    cargar_catalogo, filtrar_vehiculos, recomendar_vehiculos,
    preparar_comparacion, formato_cop
)

st.set_page_config(page_title="Mi Carro EV", page_icon="🚗", layout="wide")
st.title("🚗 Mi Carro EV")
st.caption("Explora, compara y encuentra vehículos eléctricos e híbridos en Colombia.")

for key, value in {
    "pagina": "Necesidades",
    "presupuesto": 150000000,
    "pasajeros": 5,
    "comparar": [],
    "favoritos": [],
    "carga": "No sé",
    "tipo_preferido": "Cualquiera",
    "segmento_preferido": "Cualquiera",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

paginas = ["Necesidades", "Alternativas", "Comparar", "Favoritos"]
pagina = st.radio(
    "Navegación", paginas, horizontal=True,
    index=paginas.index(st.session_state["pagina"])
)
st.session_state["pagina"] = pagina

try:
    catalogo, alertas = cargar_catalogo("datos/vehiculos_ev_hibridos_colombia.xlsx")
except FileNotFoundError:
    st.warning("Falta el Excel de vehículos. Coloca 'vehiculos_ev_hibridos_colombia.xlsx' dentro de la carpeta 'datos' del repositorio de GitHub.")
    st.info("Al agregar la base de datos, se habilitarán los filtros, la comparación y las recomendaciones.")
    st.stop()
except (ValueError, OSError, ImportError) as exc:
    st.error(f"No se pudo cargar el catálogo: {exc}")
    st.stop()

for alerta in alertas:
    st.warning(alerta)

if pagina == "Necesidades":
    st.subheader("Cuéntanos qué necesitas")
    with st.form("necesidades"):
        presupuesto = st.number_input(
            "Presupuesto máximo (COP)", min_value=1_000_000,
            max_value=2_000_000_000, step=5_000_000,
            value=int(st.session_state.presupuesto)
        )
        pasajeros = st.number_input(
            "Número mínimo de pasajeros", min_value=1, max_value=20,
            value=int(st.session_state.pasajeros), step=1
        )
        carga = st.selectbox(
            "¿Tienes dónde cargar un vehículo?",
            ["No sé", "Sí", "No"],
            index=["No sé", "Sí", "No"].index(st.session_state.carga)
        )
        tipo_opciones = ["Cualquiera"] + sorted(catalogo["Tipo"].dropna().unique().tolist())
        tipo_actual = st.session_state.tipo_preferido
        tipo = st.selectbox(
            "Tecnología preferida", tipo_opciones,
            index=tipo_opciones.index(tipo_actual) if tipo_actual in tipo_opciones else 0
        )
        segmento_opciones = ["Cualquiera"] + sorted(catalogo["Segmento_normalizado"].dropna().unique().tolist())
        segmento_actual = st.session_state.segmento_preferido
        segmento = st.selectbox(
            "Carrocería preferida", segmento_opciones,
            index=segmento_opciones.index(segmento_actual) if segmento_actual in segmento_opciones else 0
        )
        enviar = st.form_submit_button("Ver alternativas")

    if enviar:
        st.session_state.update({
            "presupuesto": int(presupuesto),
            "pasajeros": int(pasajeros),
            "carga": carga,
            "tipo_preferido": tipo,
            "segmento_preferido": segmento,
            "pagina": "Alternativas"
        })
        st.rerun()

    st.caption("El sistema utiliza tus respuestas para filtrar y ordenar alternativas. No estima consumos ni autonomía real.")

elif pagina == "Alternativas":
    st.subheader("Alternativas según tus necesidades")
    st.write(
        f"Presupuesto: **{formato_cop(st.session_state.presupuesto)}** · "
        f"Pasajeros mínimos: **{st.session_state.pasajeros}**"
    )

    candidatos = filtrar_vehiculos(
        catalogo, st.session_state.presupuesto, st.session_state.pasajeros
    )
    if candidatos.empty:
        st.info("No hay vehículos que cumplan simultáneamente esos requisitos. Cambia el presupuesto o los pasajeros en Necesidades.")
    else:
        marcas = st.multiselect("Filtrar por marca (opcional)", sorted(candidatos["Marca"].dropna().unique()))
        if marcas:
            candidatos = candidatos[candidatos["Marca"].isin(marcas)]

        sugeridos = recomendar_vehiculos(
            candidatos,
            carga=st.session_state.carga,
            tipo=st.session_state.tipo_preferido,
            segmento=st.session_state.segmento_preferido,
            presupuesto=st.session_state.presupuesto,
            pasajeros=st.session_state.pasajeros
        )

        st.subheader("Tus 5 alternativas mejor puntuadas")
        st.caption(
            "Puntaje multicriterio de 0 a 100. Es un ordenamiento matemático basado "
            "en tus preferencias, no una predicción de compra ni una garantía de desempeño."
        )
        columnas_sugeridas = [
            "Marca", "Modelo / Referencia", "Tipo", "Segmento",
            "Pasajeros", "Precio máximo (COP)", "Puntaje (0-100)",
            "Motivos", "Detalle del puntaje"
        ]
        st.dataframe(
            sugeridos[columnas_sugeridas].head(5),
            hide_index=True, use_container_width=True
        )

        with st.expander("¿Cómo se calcula el puntaje?"):
            st.markdown(
                """
                El modelo aplica primero filtros obligatorios de presupuesto y
                capacidad mínima. Después calcula un puntaje ponderado para ordenar
                los vehículos que sí cumplen esos filtros.

                | Criterio | Peso inicial |
                |---|---:|
                | Precio frente al presupuesto | 35 % |
                | Ajuste de capacidad de pasajeros | 25 % |
                | Tecnología preferida | 20 % |
                | Carrocería preferida | 10 % |
                | Acceso a carga | 10 % |

                Cuando no seleccionas una tecnología o carrocería específica,
                ese criterio se excluye y los demás pesos se reescalan.
                """
            )
            st.latex(
                r"S_i=\frac{\sum_{j=1}^{n} w_j\,s_{ij}}{\sum_{j=1}^{n}w_j}"
            )
            st.caption(
                "Los pesos son una configuración inicial del proyecto y deben "
                "validarse con el equipo y el docente."
            )

        st.subheader("Catálogo que cumple los filtros")
        st.dataframe(
            candidatos[
                ["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros",
                 "Autonomía (km)", "Ciclo", "Precio máximo (COP)"]
            ],
            hide_index=True, use_container_width=True
        )

        opciones = dict(zip(
            candidatos["ID_vehiculo"],
            candidatos["Marca"] + " — " + candidatos["Modelo / Referencia"]
        ))
        seleccion = st.selectbox(
            "Selecciona un vehículo", options=list(opciones),
            format_func=lambda x: opciones[x]
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Agregar o quitar de comparación"):
                ids = st.session_state.comparar
                if seleccion in ids:
                    ids.remove(seleccion)
                elif len(ids) < 3:
                    ids.append(seleccion)
                else:
                    st.warning("Puedes comparar hasta 3 vehículos.")
        with c2:
            if st.button("Agregar o quitar de favoritos"):
                ids = st.session_state.favoritos
                if seleccion in ids:
                    ids.remove(seleccion)
                else:
                    ids.append(seleccion)
        st.caption(
            "Las autonomías de diferentes tecnologías o ciclos no se comparan "
            "directamente en el puntaje porque no son magnitudes homogéneas."
        )

elif pagina == "Comparar":
    st.subheader("Comparar vehículos")
    seleccionados = catalogo[catalogo["ID_vehiculo"].isin(st.session_state.comparar)]
    if seleccionados.empty:
        st.info("Selecciona vehículos desde Alternativas.")
    else:
        st.dataframe(preparar_comparacion(seleccionados), use_container_width=True)
        st.warning(
            "La autonomía conserva su ciclo original; según el vehículo puede "
            "representar autonomía eléctrica o total. No se establece un ganador automático."
        )
        if st.button("Vaciar comparación"):
            st.session_state.comparar = []
            st.rerun()

else:
    st.subheader("Mis favoritos")
    seleccionados = catalogo[catalogo["ID_vehiculo"].isin(st.session_state.favoritos)]
    if seleccionados.empty:
        st.info("Todavía no tienes favoritos. Agrégalos desde Alternativas.")
    else:
        st.dataframe(
            seleccionados[
                ["Marca", "Modelo / Referencia", "Tipo", "Segmento",
                 "Pasajeros", "Precio máximo (COP)"]
            ],
            hide_index=True, use_container_width=True
        )
        st.caption("Los favoritos se guardan solamente durante esta sesión.")
        if st.button("Vaciar favoritos"):
            st.session_state.favoritos = []
            st.rerun()

st.divider()
st.caption("Proyecto académico · Precios y fichas técnicas sujetos a verificación · Mi Carro EV")
