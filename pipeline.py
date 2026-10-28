"""Carga, validación y funciones analíticas para Mi Carro EV."""
from pathlib import Path
import pandas as pd

COLUMNAS = ["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros", "Autonomía (km)", "Ciclo", "Batería (kWh)", "Potencia (hp)", "Precio máximo (COP)", "Notas"]
NUMERICAS = ["Pasajeros", "Autonomía (km)", "Batería (kWh)", "Potencia (hp)", "Precio máximo (COP)"]

def normalizar_segmento(segmento):
    """Agrupa solo etiquetas con familia de carrocería explícita; conserva original."""
    s = str(segmento).strip().lower()
    for prefijo, nombre in [("suv", "SUV"), ("sedán", "Sedán"), ("sedan", "Sedán"), ("hatchback", "Hatchback"), ("pickup", "Pickup"), ("pick-up", "Pickup"), ("crossover", "Crossover")]:
        if s.startswith(prefijo): return nombre
    return str(segmento).strip()  # sin suposiciones sobre etiquetas desconocidas

def cargar_catalogo(ruta):
    ruta = Path(ruta)
    if not ruta.exists(): raise FileNotFoundError(str(ruta))
    df = pd.read_excel(ruta, sheet_name="BD", engine="openpyxl")
    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes: raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
    df = df.copy()
    avisos = []
    duplicados = int(df.duplicated().sum())
    if duplicados: avisos.append(f"Se detectaron {duplicados} filas duplicadas completas. Revisa la base.")
    for col in NUMERICAS:
        originales = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        invalidos = int(originales - df[col].notna().sum())
        if invalidos: avisos.append(f"{col}: {invalidos} valores no numéricos se muestran como desconocidos.")
    for col in ["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Ciclo", "Notas"]:
        df[col] = df[col].astype("string").str.strip()
    for col in ["Precio máximo (COP)", "Pasajeros", "Autonomía (km)", "Batería (kWh)", "Potencia (hp)"]:
        negativos = df[col].notna() & (df[col] <= 0)
        if negativos.any():
            avisos.append(f"{col}: {int(negativos.sum())} valores menores o iguales a cero se trataron como no disponibles.")
            df.loc[negativos, col] = float("nan")
    df["Segmento_normalizado"] = df["Segmento"].map(normalizar_segmento)
    df["ID_vehiculo"] = [f"v-{i}" for i in range(len(df))]
    if df["Precio máximo (COP)"].isna().any(): avisos.append("Hay precios desconocidos: no se incluirán en el filtro estricto de presupuesto.")
    if df["Pasajeros"].isna().any(): avisos.append("Hay capacidades desconocidas: no se incluirán en el filtro estricto de pasajeros.")
    avisos.append("Los precios y datos técnicos provienen del archivo suministrado; su vigencia y disponibilidad en Colombia no están verificadas por esta aplicación.")
    return df, avisos

def filtrar_vehiculos(df, presupuesto, pasajeros):
    return df.loc[(df["Precio máximo (COP)"].notna()) & (df["Precio máximo (COP)"] <= presupuesto) & (df["Pasajeros"].notna()) & (df["Pasajeros"] >= pasajeros)].copy()

def recomendar_vehiculos(df, carga="No sé", tipo="Cualquiera", segmento="Cualquiera"):
    """Reglas transparentes; no usa autonomía entre ciclos ni costos sin datos."""
    resultado = df.copy()
    if resultado.empty:
        resultado["Motivos"] = pd.Series(dtype="string")
        return resultado
    puntajes, razones = [], []
    for _, r in resultado.iterrows():
        puntos, motivos = 0, ["Cumple presupuesto y capacidad mínima"]
        if tipo != "Cualquiera" and r["Tipo"] == tipo:
            puntos += 2; motivos.append("Coincide con la tecnología preferida")
        if segmento != "Cualquiera" and r["Segmento_normalizado"] == segmento:
            puntos += 2; motivos.append("Coincide con la carrocería preferida")
        if carga == "No" and r["Tipo"] in ("HEV", "MHEV"):
            puntos += 1; motivos.append("No requiere carga externa habitual")
        if carga == "Sí" and r["Tipo"] == "BEV":
            puntos += 1; motivos.append("Es eléctrico y cuentas con acceso a carga")
        puntajes.append(puntos); razones.append("; ".join(motivos))
    resultado["Puntos_preferencia"] = puntajes
    resultado["Motivos"] = razones
    return resultado.sort_values(["Puntos_preferencia", "Precio máximo (COP)"], ascending=[False, True])

def preparar_comparacion(df):
    columnas = ["Marca", "Modelo / Referencia", "Tipo", "Segmento", "Pasajeros", "Autonomía (km)", "Ciclo", "Batería (kWh)", "Potencia (hp)", "Precio máximo (COP)"]
    t = df[columnas].copy()
    t["Precio máximo (COP)"] = t["Precio máximo (COP)"].map(lambda x: formato_cop(x) if pd.notna(x) else "No disponible")
    return t.set_index("Modelo / Referencia").T.fillna("No disponible")

def formato_cop(valor):
    return "${:,.0f} COP".format(valor).replace(",", ".")
