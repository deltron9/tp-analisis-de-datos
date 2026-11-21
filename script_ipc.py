import os
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

RUTA_IPC_ORIGINAL = "datos/serie_ipc_divisiones212016-102026.csv"
RUTA_IPC_SALIDA = "datos/ipc_gba_trimestral_2016T2_2026T3.csv"

os.makedirs("datos", exist_ok=True)

# Variación mensual oficial del IPC-GBA durante 2016.
# Se utiliza para reconstruir los índices anteriores a diciembre.
VARIACIONES_2016 = {
    201605: 0.042,
    201606: 0.031,
    201607: 0.020,
    201608: 0.002,
    201609: 0.011,
    201610: 0.024,
    201611: 0.016,
    201612: 0.012,
}

# ============================================================
# 1. RECONSTRUCCIÓN DEL IPC-GBA DE 2016
# ============================================================

# Base oficial: diciembre de 2016 = 100.
indices_2016 = {201612: 100.0}

# Reconstrucción retrospectiva mediante las variaciones mensuales.
for periodo in sorted(VARIACIONES_2016, reverse=True):
    indice_actual = indices_2016[periodo]
    variacion = VARIACIONES_2016[periodo]
    indices_2016[periodo - 1] = indice_actual / (1 + variacion)

df_2016 = pd.DataFrame([
    {"Periodo": periodo, "Indice_IPC": indice}
    for periodo, indice in sorted(indices_2016.items())
])

# ============================================================
# 2. LECTURA DE LA SERIE OFICIAL DEL INDEC
# ============================================================

if not os.path.exists(RUTA_IPC_ORIGINAL):
    raise FileNotFoundError(
        f"No se encontró el archivo: {RUTA_IPC_ORIGINAL}"
    )

df_csv = pd.read_csv(
    RUTA_IPC_ORIGINAL,
    sep=";",
    encoding="latin1",
    decimal=","
)

df_gba = df_csv[
    (df_csv["Codigo"].astype(str).str.strip() == "0") &
    (df_csv["Region"].astype(str).str.strip() == "GBA") &
    (pd.to_numeric(df_csv["Periodo"], errors="coerce") >= 201701)
][["Periodo", "Indice_IPC"]].copy()

df_gba["Periodo"] = pd.to_numeric(
    df_gba["Periodo"], errors="coerce"
).astype(int)

df_gba["Indice_IPC"] = pd.to_numeric(
    df_gba["Indice_IPC"], errors="coerce"
)

if df_gba.empty:
    raise ValueError("No se encontraron registros del IPC-GBA Nivel General.")

if df_gba["Indice_IPC"].isna().any():
    raise ValueError("Hay índices IPC oficiales que no pudieron convertirse a números.")

# ============================================================
# 3. UNIFICACIÓN DE LA SERIE MENSUAL
# ============================================================

ipc_mensual = pd.concat(
    [df_2016, df_gba],
    ignore_index=True
)

ipc_mensual = ipc_mensual.sort_values("Periodo").reset_index(drop=True)

if ipc_mensual["Periodo"].duplicated().any():
    duplicados = ipc_mensual.loc[
        ipc_mensual["Periodo"].duplicated(keep=False), "Periodo"
    ].tolist()
    raise ValueError(f"Hay períodos mensuales duplicados: {duplicados}")

# Verificar continuidad mensual.
periodos_esperados = pd.period_range(
    start="2016-04",
    end=pd.Period(
        str(ipc_mensual["Periodo"].max() // 100) + "-" +
        str(ipc_mensual["Periodo"].max() % 100).zfill(2),
        freq="M"
    ),
    freq="M"
)

periodos_esperados = [
    periodo.year * 100 + periodo.month
    for periodo in periodos_esperados
]

periodos_existentes = set(ipc_mensual["Periodo"].tolist())
periodos_faltantes = sorted(set(periodos_esperados) - periodos_existentes)

if periodos_faltantes:
    raise ValueError(
        f"Faltan meses en la serie IPC: {periodos_faltantes}"
    )

# Comprobar anclaje oficial.
indice_dic_2016 = ipc_mensual.loc[
    ipc_mensual["Periodo"] == 201612, "Indice_IPC"
]

if indice_dic_2016.empty or abs(indice_dic_2016.iloc[0] - 100.0) > 0.0001:
    raise ValueError("El empalme no conserva diciembre de 2016 = 100.")

# ============================================================
# 4. AGRUPACIÓN TRIMESTRAL
# ============================================================

ipc_mensual["ANO4"] = ipc_mensual["Periodo"] // 100
ipc_mensual["TRIMESTRE"] = (
    (ipc_mensual["Periodo"] % 100 - 1) // 3
) + 1

ipc_mensual["PERIODO_TRIM"] = (
    ipc_mensual["ANO4"].astype(str) +
    "-T" +
    ipc_mensual["TRIMESTRE"].astype(str)
)

ipc_trim = (
    ipc_mensual
    .groupby(
        ["ANO4", "TRIMESTRE", "PERIODO_TRIM"],
        as_index=False
    )
    .agg(
        IPC_GBA_TRIM=("Indice_IPC", "mean"),
        MESES_RELEVADOS=("Periodo", "count")
    )
)

# Conservar solamente trimestres con los tres meses disponibles.
ipc_trim = ipc_trim[
    ipc_trim["MESES_RELEVADOS"] == 3
].copy()

ipc_trim = ipc_trim.sort_values(
    ["ANO4", "TRIMESTRE"]
).reset_index(drop=True)

if len(ipc_trim) != 42:
    raise ValueError(
        f"Se esperaban 42 trimestres completos y se obtuvieron {len(ipc_trim)}."
    )

if ipc_trim.iloc[0]["PERIODO_TRIM"] != "2016-T2":
    raise ValueError("El primer trimestre de la serie no es 2016-T2.")

if ipc_trim.iloc[-1]["PERIODO_TRIM"] != "2026-T3":
    raise ValueError("El último trimestre de la serie no es 2026-T3.")

# ============================================================
# 5. COEFICIENTES DE DEFLACTACIÓN
# ============================================================

def obtener_indice_base(anio, trimestre):
    resultado = ipc_trim.loc[
        (ipc_trim["ANO4"] == anio) &
        (ipc_trim["TRIMESTRE"] == trimestre),
        "IPC_GBA_TRIM"
    ]

    if resultado.empty:
        raise ValueError(
            f"No existe el IPC para {anio}-T{trimestre}."
        )

    return resultado.iloc[0]


ipc_base_2026t2 = obtener_indice_base(2026, 2)
ipc_base_2026t3 = obtener_indice_base(2026, 3)

ipc_trim["COEF_DEFLACTOR_2026T2"] = (
    ipc_base_2026t2 / ipc_trim["IPC_GBA_TRIM"]
).round(6)

ipc_trim["COEF_DEFLACTOR_2026T3"] = (
    ipc_base_2026t3 / ipc_trim["IPC_GBA_TRIM"]
).round(6)

ipc_trim["IPC_GBA_TRIM"] = ipc_trim["IPC_GBA_TRIM"].round(6)

# ============================================================
# 6. EXPORTACIÓN Y RESUMEN
# ============================================================

ipc_salida = ipc_trim.drop(
    columns=["MESES_RELEVADOS"]
)

ipc_salida.to_csv(
    RUTA_IPC_SALIDA,
    index=False
)

print("\nIPC-GBA TRIMESTRAL GENERADO CORRECTAMENTE")
print("Archivo:", RUTA_IPC_SALIDA)
print("Cantidad de trimestres:", len(ipc_salida))
print("Primer trimestre:", ipc_salida.iloc[0]["PERIODO_TRIM"])
print("Último trimestre:", ipc_salida.iloc[-1]["PERIODO_TRIM"])

print("\nÍndices base:")
print(f"2026-T2: {ipc_base_2026t2:.6f}")
print(f"2026-T3: {ipc_base_2026t3:.6f}")

print("\nPrimeros registros:")
print(ipc_salida.head(3).to_string(index=False))

print("\nÚltimos registros:")
print(ipc_salida.tail(3).to_string(index=False))