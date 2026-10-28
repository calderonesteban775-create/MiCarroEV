import streamlit as st
import pandas as pd
from pipeline import cargar_catalogo, filtrar_vehiculos, recomendar_vehiculos, preparar_comparacion, formato_cop

st.set_page_config(page_title="Mi Carro EV", page_icon="🚗", layout="wide")
st.title("🚗 Mi Carro EV")
st.caption("Explora, compara y encuentra vehículos eléctricos e híbridos en Colombia.")

for key, value in {"pagina": "Necesidades", "presupuesto": 150000000, "pasajeros": 5, "comparar": [], "favoritos": []}.items():
    if key not in st.session_state:
        st.session_state[key] = value

paginas = ["Necesidades", "Alternativas", "Comparar", "Favoritos"]
pagina = st.radio("Navegación", paginas, horizontal=True, key="pagina")

try:
    catalogo, alertas = cargar_catalogo("datos/vehiculos_ev_hibridos_colombia.xlsx")
except FileNotFoundError:
    st.warning("Falta el Excel de vehículos. Coloca 'vehiculos_ev_hibridos_colombia.xlsx' dentro de la carpeta 'datos' del repositorio de GitHub.")
    st.info("La aplicación ya está desplegada. Al agregar la base de datos, se habilitarán los filtros, la comparación y las recomendaciones.")
    st.stop()
except (ValueError, OSError, ImportError) as exc:
    st.error(f"No se pudo cargar el catálogo: {exc}")
    st.stop()

for alerta in alertas:
    st.warning(alerta)

if pagina == "Necesidades":
    st.subheader("Cuéntanos qué necesitas")
    with st.form("necesidades"):
        presupuesto = st.number_input("Presupuesto máximo (COP)", min_value=1_000_000, max_value=2_000_000_000, step=5_000_000, value=st.session_state.presupuesto)
        pasajeros = st.number_input("Número mínimo de pasajeros", min_value=1, max_value=20, value=st.session_state.pasajeros, step=1)
        carga = st.selectbox("¿Tienes dónde cargar un vehículo?", ["No sé", "Sí", "No"])
        tipo = st.selectbox("Tecnología preferida", ["Cualquiera"] + sorted(catalogo["Tipo"].dropna().unique().tolist()))
        segmento = st.selectbox("Carrocería preferida", ["Cualquiera"] + sorted(catalogo["Segmento_normalizado"].dropna().unique().tolist()))
        enviar = st.form_submit_button("Ver alternativas")
    if enviar:
        st.session_state.update({"presupuesto": int(presupuesto), "pasajeros": int(pasajeros), "carga": carga, "tipo_preferido": tipo, "segmento_preferido": segmento, "pagina": "Alternativas"})
        st.rerun()
    st.caption("Las recomendaciones son orientativas. No estimamos consumos ni autonomía real sin datos verificables.")

elif pagina == "Alternativas":
    st.subheader("Alternativas según tus necesidades")
    st.write(f"Presupuesto: **{formato_cop(st.session_state.presupuesto)}** · Pasajeros mínimos: **{st.session_state.pasajeros}**")
    candidatos = filtrar_vehiculos(catalogo, st.session_state.presupuesto, st.session_state.pasajeros)
    if candidatos.empty:
        st.info("No hay vehículos que cumplan simultáneamente esos requisitos. Cambia el presupuesto o los pasajeros en Necesidades.")
    else:
        marcas = st.multiselect("Filtrar por marca (opcional)", sorted(candidatos["Marca"].unique()))
        if marcas:
            candidatos = candidatos[candidatos["Marca"].isin(marcas)]
        sugeridos = recomendar_vehiculos(candidatos, st.session_state.get("carga", "No sé"), st.session_state.get("tipo_preferido", "Cualquiera"), st.session_state.get("segmento_preferido", "Cualquiera"))
        st.caption("Orden orientativo basado en preferencias explícitas; no es una predicción de compra ni una evaluación del costo total de propiedad.")
        st.dataframe(sugeridos[["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros", "Precio máximo (COP)", "Motivos"]].head(5), hide_index=True, use_container_width=True)
        st.subheader("Catálogo filtrado")
        st.dataframe(candidatos[["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros", "Autonomía (km)", "Ciclo", "Precio máximo (COP)"]], hide_index=True, use_container_width=True)
        opciones = dict(zip(candidatos["ID_vehiculo"], candidatos["Marca"] + " — " + candidatos["Modelo / Referencia"]))
        seleccion = st.selectbox("Selecciona un vehículo", options=list(opciones), format_func=lambda x: opciones[x])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Agregar o quitar de comparación"):
                ids = st.session_state.comparar
                if seleccion in ids: ids.remove(seleccion)
                elif len(ids) < 3: ids.append(seleccion)
                else: st.warning("Puedes comparar hasta 3 vehículos.")
        with c2:
            if st.button("Agregar o quitar de favoritos"):
                ids = st.session_state.favoritos
                if seleccion in ids: ids.remove(seleccion)
                else: ids.append(seleccion)
        st.caption("Las autonomías de diferentes tecnologías o ciclos no se deben comparar directamente.")

elif pagina == "Comparar":
    st.subheader("Comparar vehículos")
    seleccionados = catalogo[catalogo["ID_vehiculo"].isin(st.session_state.comparar)]
    if seleccionados.empty: st.info("Selecciona vehículos desde Alternativas.")
    else:
        st.dataframe(preparar_comparacion(seleccionados), use_container_width=True)
        st.warning("Autonomía: conserva el ciclo original; los valores pueden representar autonomía eléctrica o total según el vehículo. No se establece un ganador automático.")
        if st.button("Vaciar comparación"):
            st.session_state.comparar = []
            st.rerun()

else:
    st.subheader("Mis favoritos")
    seleccionados = catalogo[catalogo["ID_vehiculo"].isin(st.session_state.favoritos)]
    if seleccionados.empty: st.info("Todavía no tienes favoritos. Agrégalos desde Alternativas.")
    else:
        st.dataframe(seleccionados[["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Precio máximo (COP)"]], hide_index=True, use_container_width=True)
        st.caption("Los favoritos se guardan solamente durante esta sesión.")
        if st.button("Vaciar favoritos"):
            st.session_state.favoritos = []
            st.rerun()

st.divider()
st.caption("Proyecto académico · Precios y fichas técnicas sujetos a verificación · Mi Carro EV")
