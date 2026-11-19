import pandas as pd

# 1. Reconstrucción mensual IPC-GBA 2016 (anclado en 201612 = 100.0)
vars_2016 = {
    201605: 0.042,
    201606: 0.031,
    201607: 0.020,
    201608: 0.002,
    201609: 0.011,
    201610: 0.024,
    201611: 0.016,
    201612: 0.012,
}

idx_2016 = {201612: 100.0}
for p in [201612, 201611, 201610, 201609, 201608, 201607, 201606, 201605]:
    idx_2016[p - 1] = idx_2016[p] / (1 + vars_2016[p])

df_2016 = pd.DataFrame([
    {"Periodo": k, "Indice_IPC": v}
    for k, v in sorted(idx_2016.items())
])

# 2. Lectura del CSV oficial INDEC (201701 en adelante, Nivel General GBA)
df_csv = pd.read_csv("./datos/serie_ipc_divisiones212016-102026.csv", sep=";", encoding="latin1", decimal=",")
df_gba = df_csv[
    (df_csv["Codigo"] == "0") &
    (df_csv["Region"] == "GBA") &
    (df_csv["Periodo"] >= 201701)
][["Periodo", "Indice_IPC"]].copy()
df_gba["Indice_IPC"] = df_gba["Indice_IPC"].astype(float)

# 3. Unión y agrupación trimestral
ipc_mensual = pd.concat([df_2016, df_gba], ignore_index=True)
ipc_mensual["ANO4"] = ipc_mensual["Periodo"] // 100
ipc_mensual["TRIMESTRE"] = ((ipc_mensual["Periodo"] % 100 - 1) // 3) + 1
ipc_mensual["PERIODO_TRIM"] = ipc_mensual["ANO4"].astype(str) + "-T" + ipc_mensual["TRIMESTRE"].astype(str)

ipc_trim = (
    ipc_mensual.groupby(["ANO4", "TRIMESTRE", "PERIODO_TRIM"], as_index=False)
    .agg(IPC_GBA_TRIM=("Indice_IPC", "mean"), MESES_RELEVADOS=("Periodo", "count"))
)
ipc_trim = ipc_trim[ipc_trim["MESES_RELEVADOS"] == 3].copy()

# 4. Coeficientes deflactores a pesos constantes de 2026-T2 y 2026-T3
ipc_base_2026t2 = ipc_trim.loc[(ipc_trim["ANO4"] == 2026) & (ipc_trim["TRIMESTRE"] == 2), "IPC_GBA_TRIM"].values[0]
ipc_base_2026t3 = ipc_trim.loc[(ipc_trim["ANO4"] == 2026) & (ipc_trim["TRIMESTRE"] == 3), "IPC_GBA_TRIM"].values[0]

ipc_trim["COEF_DEFLACTOR_2026T2"] = (ipc_base_2026t2 / ipc_trim["IPC_GBA_TRIM"]).round(6)
ipc_trim["COEF_DEFLACTOR_2026T3"] = (ipc_base_2026t3 / ipc_trim["IPC_GBA_TRIM"]).round(6)
ipc_trim["IPC_GBA_TRIM"] = ipc_trim["IPC_GBA_TRIM"].round(6)

output_filename = "./datos/ipc_gba_trimestral_2016T2_2026T3.csv"
ipc_trim.drop(columns=["MESES_RELEVADOS"]).to_csv(output_filename, index=False)
print("Generado:", output_filename)