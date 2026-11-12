"""Pipeline analítico de Mi Carro EV.

Método: filtros obligatorios + modelo multicriterio aditivo (ponderado).
No es un modelo predictivo entrenado: ordena alternativas según las preferencias
declaradas por el usuario y las variables disponibles en el catálogo.
"""
from pathlib import Path
import pandas as pd

COLUMNAS = [
    "Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros",
    "Autonomía (km)", "Ciclo", "Batería (kWh)", "Potencia (hp)",
    "Precio máximo (COP)", "Notas"
]
NUMERICAS = [
    "Pasajeros", "Autonomía (km)", "Batería (kWh)",
    "Potencia (hp)", "Precio máximo (COP)"
]

# Pesos iniciales del modelo. Deben validarse con el equipo/profesor.
PESOS = {
    "Precio": 0.35,
    "Capacidad": 0.25,
    "Tecnología": 0.20,
    "Carrocería": 0.10,
    "Acceso a carga": 0.10,
}

TIPOS_CON_CARGA_EXTERNA = {"BEV", "PHEV", "EREV", "REEV", "EREV/BEV"}
TIPOS_SIN_CARGA_EXTERNA_HABITUAL = {"HEV", "MHEV", "MHEV/HEV"}


def normalizar_segmento(segmento):
    """Agrupa etiquetas conocidas sin reemplazar la etiqueta original."""
    if pd.isna(segmento):
        return "No disponible"
    s = str(segmento).strip().lower()
    for prefijo, nombre in [
        ("suv", "SUV"), ("sedán", "Sedán"), ("sedan", "Sedán"),
        ("hatchback", "Hatchback"), ("pickup", "Pickup"),
        ("pick-up", "Pickup"), ("crossover", "Crossover")
    ]:
        if s.startswith(prefijo):
            return nombre
    return str(segmento).strip()


def cargar_catalogo(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(str(ruta))
    df = pd.read_excel(ruta, sheet_name="BD", engine="openpyxl")
    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    df = df.copy()
    avisos = []
    duplicados = int(df.duplicated().sum())
    if duplicados:
        avisos.append(f"Se detectaron {duplicados} filas duplicadas completas. Revisa la base.")

    for col in NUMERICAS:
        originales = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        invalidos = int(originales - df[col].notna().sum())
        if invalidos:
            avisos.append(f"{col}: {invalidos} valores no numéricos se trataron como desconocidos.")

    for col in ["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Ciclo", "Notas"]:
        df[col] = df[col].astype("string").str.strip()

    for col in NUMERICAS:
        no_validos = df[col].notna() & (df[col] <= 0)
        if no_validos.any():
            avisos.append(
                f"{col}: {int(no_validos.sum())} valores menores o iguales a cero "
                "se trataron como no disponibles."
            )
            df.loc[no_validos, col] = float("nan")

    df["Segmento_normalizado"] = df["Segmento"].map(normalizar_segmento)
    df["ID_vehiculo"] = [f"v-{i}" for i in range(len(df))]

    if df["Precio máximo (COP)"].isna().any():
        avisos.append("Hay precios desconocidos: no se incluirán en el filtro estricto de presupuesto.")
    if df["Pasajeros"].isna().any():
        avisos.append("Hay capacidades desconocidas: no se incluirán en el filtro estricto de pasajeros.")
    avisos.append(
        "Los precios y datos técnicos provienen del archivo suministrado; "
        "su vigencia y disponibilidad en Colombia no están verificadas por esta aplicación."
    )
    return df, avisos


def filtrar_vehiculos(df, presupuesto, pasajeros):
    """Filtros obligatorios: precio conocido dentro del presupuesto y capacidad suficiente."""
    return df.loc[
        df["Precio máximo (COP)"].notna()
        & (df["Precio máximo (COP)"] <= presupuesto)
        & df["Pasajeros"].notna()
        & (df["Pasajeros"] >= pasajeros)
    ].copy()


def _puntaje_precio(precio, presupuesto):
    if pd.isna(precio) or presupuesto <= 0:
        return None
    # Cuanto menor sea el precio respecto al presupuesto, mayor será el puntaje.
    return max(0.0, min(100.0, 100.0 * (1 - float(precio) / float(presupuesto))))


def _puntaje_capacidad(capacidad, pasajeros_requeridos):
    if pd.isna(capacidad) or pasajeros_requeridos <= 0:
        return None
    # Premia que la capacidad se ajuste a la necesidad; no premia plazas sobrantes.
    return max(0.0, min(100.0, 100.0 * pasajeros_requeridos / float(capacidad)))


def _puntaje_carga(tipo_vehiculo, acceso_carga):
    tipo_vehiculo = str(tipo_vehiculo).strip().upper()
    if acceso_carga == "No sé":
        return 50.0
    if acceso_carga == "Sí":
        if tipo_vehiculo in TIPOS_CON_CARGA_EXTERNA:
            return 100.0
        if tipo_vehiculo in TIPOS_SIN_CARGA_EXTERNA_HABITUAL:
            return 40.0
        return 50.0
    if acceso_carga == "No":
        if tipo_vehiculo in TIPOS_SIN_CARGA_EXTERNA_HABITUAL:
            return 100.0
        if tipo_vehiculo in TIPOS_CON_CARGA_EXTERNA:
            return 20.0
        return 50.0
    return 50.0


def recomendar_vehiculos(
    df,
    carga="No sé",
    tipo="Cualquiera",
    segmento="Cualquiera",
    presupuesto=None,
    pasajeros=1,
):
    """Calcula puntajes de 0 a 100 y ordena las alternativas de forma explicable.

    Los criterios no solicitados por el usuario se excluyen y los pesos restantes
    se reescalan automáticamente. No se usa autonomía porque los ciclos y el
    significado de la autonomía no son homogéneos en el catálogo.
    """
    resultado = df.copy()
    if resultado.empty:
        resultado["Puntaje (0-100)"] = pd.Series(dtype=float)
        resultado["Motivos"] = pd.Series(dtype="string")
        resultado["Detalle del puntaje"] = pd.Series(dtype="string")
        return resultado

    # Si la función se usa directamente sin presupuesto, se toma el mayor precio
    # disponible como referencia; en la app se entrega el presupuesto del usuario.
    if presupuesto is None:
        precios = pd.to_numeric(resultado["Precio máximo (COP)"], errors="coerce").dropna()
        presupuesto = float(precios.max()) if not precios.empty else 1.0

    criterios_activos = {
        "Precio": PESOS["Precio"],
        "Capacidad": PESOS["Capacidad"],
        "Acceso a carga": PESOS["Acceso a carga"],
    }
    if tipo != "Cualquiera":
        criterios_activos["Tecnología"] = PESOS["Tecnología"]
    if segmento != "Cualquiera":
        criterios_activos["Carrocería"] = PESOS["Carrocería"]

    suma_pesos = sum(criterios_activos.values())
    filas_puntaje, filas_motivos, filas_detalle = [], [], []

    for _, r in resultado.iterrows():
        valores = {
            "Precio": _puntaje_precio(r["Precio máximo (COP)"], presupuesto),
            "Capacidad": _puntaje_capacidad(r["Pasajeros"], pasajeros),
            "Acceso a carga": _puntaje_carga(r["Tipo"], carga),
        }
        if "Tecnología" in criterios_activos:
            valores["Tecnología"] = (
                100.0 if str(r["Tipo"]).strip() == tipo else 0.0
            )
        if "Carrocería" in criterios_activos:
            valores["Carrocería"] = (
                100.0 if str(r["Segmento_normalizado"]).strip() == segmento else 0.0
            )

        numerador = 0.0
        denominador = 0.0
        detalle = []
        motivos = []

        for criterio, peso in criterios_activos.items():
            valor = valores.get(criterio)
            if valor is None or pd.isna(valor):
                continue
            numerador += peso * valor
            denominador += peso
            detalle.append(f"{criterio}: {valor:.0f}/100")
            if criterio == "Precio":
                motivos.append("Precio más favorable frente al presupuesto" if valor >= 50
                               else "Consume una proporción alta del presupuesto")
            elif criterio == "Capacidad":
                motivos.append("Capacidad ajustada al número de pasajeros")
            elif criterio == "Tecnología" and valor == 100:
                motivos.append("Coincide con la tecnología preferida")
            elif criterio == "Carrocería" and valor == 100:
                motivos.append("Coincide con la carrocería preferida")
            elif criterio == "Acceso a carga":
                if valor == 100:
                    motivos.append("La tecnología es compatible con tu respuesta sobre carga")
                elif valor < 50:
                    motivos.append("Revisa la necesidad de carga externa de esta tecnología")

        puntaje = numerador / denominador if denominador else 0.0
        filas_puntaje.append(round(puntaje, 1))
        filas_motivos.append("; ".join(motivos))
        filas_detalle.append(" · ".join(detalle))

    resultado["Puntaje (0-100)"] = filas_puntaje
    resultado["Motivos"] = filas_motivos
    resultado["Detalle del puntaje"] = filas_detalle
    return resultado.sort_values(
        ["Puntaje (0-100)", "Precio máximo (COP)"],
        ascending=[False, True]
    )


def preparar_comparacion(df):
    columnas = [
        "Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros",
        "Autonomía (km)", "Ciclo", "Batería (kWh)", "Potencia (hp)",
        "Precio máximo (COP)"
    ]
    t = df[columnas].copy()
    t["Precio máximo (COP)"] = t["Precio máximo (COP)"].map(
        lambda x: formato_cop(x) if pd.notna(x) else "No disponible"
    )
    return t.set_index("Modelo / Referencia").T.fillna("No disponible")


def formato_cop(valor):
    return "${:,.0f} COP".format(valor).replace(",", ".")
