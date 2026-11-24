from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import statsmodels.formula.api as smf
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

SEMILLA = 7 

BASE_DIR = Path(__file__).resolve().parent
DIR_GRAFICOS = BASE_DIR / "graficos"
DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

df = pd.read_csv(BASE_DIR / "datos" / "eph_microdatos.csv", low_memory=False)
df.columns = df.columns.str.strip().str.upper()

#filtrar universo de ocupados
occ = df[(df["ESTADO"] == 1) & (df["AGLOMERADO"].isin([32, 33]))].copy()
occ["AGLOMERADO_NOM"] = occ["AGLOMERADO"].map({32: "CABA", 33: "Gran Buenos Aires"})


#horas trabajadas semanales
occ["HORAS_RAW"] = pd.to_numeric(
    occ["PP3E_TOT"].astype(str).str.replace(",", "."), errors="coerce" #limpieza de comas
)
occ.loc[(occ["HORAS_RAW"] <= 0) | (occ["HORAS_RAW"] >= 999), "HORAS_RAW"] = np.nan
occ["HORAS_MISSING"] = occ["HORAS_RAW"].isna().astype(int)
occ["HORAS"] = occ["HORAS_RAW"].fillna(
    occ.groupby(["CAT_OCUP", "CH04"])["HORAS_RAW"].transform("median")
)
#respaldo: si algun grupo no tuviera ninguna hora valida, se usa la mediana general para no perder la observación en el ajuste.
occ["HORAS"] = occ["HORAS"].fillna(occ["HORAS_RAW"].median())
occ["HORAS2"] = occ["HORAS"] ** 2

#edad y edad al cuadrado
occ["EDAD"] = pd.to_numeric(occ["CH06"], errors="coerce")
occ["EDAD2"] = occ["EDAD"] ** 2

#calificacion ocupacional (último dígito de PP04D_COD)
# 1 = profesional
# 2 = tecnica
# 3 = operativa
# 4 = no calificada
# 9 = sin dato
cod_cal = occ["PP04D_COD"].dropna().astype(int).astype(str).str.zfill(5).str[-1].astype(int)
occ["CALIF"] = 9
occ.loc[cod_cal.index, "CALIF"] = cod_cal
occ.loc[~occ["CALIF"].isin([1, 2, 3, 4]), "CALIF"] = 9

#rama de actividad economica (2 primeros digitos de PP04B_COD)
def map_rama_caes(cod):
    if 10 <= cod <= 33:
        return "Industria"
    elif cod == 40:
        return "Construccion"
    elif 45 <= cod <= 48:
        return "Comercio"
    elif 49 <= cod <= 53:
        return "Transporte"
    elif 55 <= cod <= 56:
        return "Hoteleria_Gastron"
    elif 62 <= cod <= 82:
        return "Serv_Prof_Fin_Inf"
    elif cod == 84:
        return "Adm_Publica"
    elif 85 <= cod <= 88:
        return "Ensenanza_Salud"
    elif 97 <= cod <= 98:
        return "Serv_Domestico"
    return "Otros"

rama_2d = occ["PP04B_COD"].dropna().astype(int).astype(str).str.zfill(4).str[:2].astype(int)
occ["RAMA"] = "Otros"
occ.loc[rama_2d.index, "RAMA"] = rama_2d.map(map_rama_caes)

#tamaño del establecimiento (PP04C agrupado)
def agrupar_tamano(v):
    if v == 0:
        return "No_corresp"
    elif 1 <= v <= 5:
        return "1_a_5"
    elif 6 <= v <= 9:
        return "6_a_100"
    elif v in [10, 11, 12]:
        return "Mas_de_100"
    return "Ns_Nr"

occ["TAM_ESTAB"] = occ["PP04C"].apply(agrupar_tamano)

#funciones auxiliares
def calcular_piso(base):
    """Piso positivo para las predicciones: percentil 1 de los ingresos
    observados, por aglomerado. Evita imputar ingresos negativos o nulos a
    ocupados que cobran."""
    return base.groupby("AGLOMERADO")["P21_REAL"].quantile(0.01)


def predecir_con_piso(modelo, datos, piso):
    """Predice y lleva al piso las predicciones menores. Devuelve (pred, al_piso)."""
    pred = modelo.predict(datos)
    piso_fila = datos.loc[pred.index, "AGLOMERADO"].map(piso)
    al_piso = pred < piso_fila
    return np.maximum(pred, piso_fila), al_piso


def mediana_ponderada(valores, pesos):
    """Mediana ponderada con la misma interpolación que el análisis multivariado."""
    valores = np.asarray(valores, dtype=float)
    pesos = np.asarray(pesos, dtype=float)
    orden = np.argsort(valores)
    valores, pesos = valores[orden], pesos[orden]
    acum = np.cumsum(pesos)
    pos = (acum - 0.5 * pesos) / acum[-1]
    return float(np.interp(0.5, pos, valores))


#estimacion del modelo WLS (ponderado por PONDIIO) para imputar la no respuesta
train_pool = occ[(occ["P21_REAL"] > 0) & (occ["PONDIIO"] > 0)].copy()
no_resp = occ[(occ["P21_REAL"] < 0) | (occ["P21_REAL"].isna())].copy()

#division estratificada 80% entrenamiento / 20% evaluación
estrato = train_pool["AGLOMERADO"].astype(str) + "_" + train_pool["ANO4"].astype(str)
df_train, df_test = train_test_split(
    train_pool, test_size=0.20, random_state=SEMILLA, stratify=estrato
)

formula = (
    "P21_REAL ~ HORAS + HORAS2 + HORAS_MISSING + EDAD + EDAD2 + "
    "C(CH04) + C(NIVEL_ED) + C(CAT_OCUP) + C(CALIF) * C(AGLOMERADO) + "
    "C(RAMA) + C(TAM_ESTAB) + C(ANO4) + C(TRIMESTRE)"
)

#ajuste por minimos cuadrados ponderados (WLS con PONDIIO)
modelo_wls = smf.wls(formula, data=df_train, weights=df_train["PONDIIO"]).fit()

# evaluacion: el piso se calcula solo con entrenamiento para no usar info del test
piso_train = calcular_piso(df_train)
pred_train, _ = predecir_con_piso(modelo_wls, df_train, piso_train)
pred_test, _ = predecir_con_piso(modelo_wls, df_test, piso_train)

y_train = df_train.loc[pred_train.index, "P21_REAL"]
y_test = df_test.loc[pred_test.index, "P21_REAL"]
w_train = df_train.loc[pred_train.index, "PONDIIO"]
w_test = df_test.loc[pred_test.index, "PONDIIO"]

#r2 en ambas bases (ponderado por PONDIIO y sin ponderar) para entrenamiento y evaluacion
r2_train_pond = modelo_wls.rsquared
r2_adj_train = modelo_wls.rsquared_adj
r2_train_simple = r2_score(y_train, pred_train)
r2_test_simple = r2_score(y_test, pred_test)
r2_test_pond = r2_score(y_test, pred_test, sample_weight=w_test)
mae_test = mean_absolute_error(y_test, pred_test)
rmse_test = np.sqrt(mean_squared_error(y_test, pred_test))

#imputacion de la no respuesta

#reentrenamiento con el 100% de respondentes validos para maxima precision
modelo_final = smf.wls(formula, data=train_pool, weights=train_pool["PONDIIO"]).fit()
piso_final = calcular_piso(train_pool)

no_resp_remun = no_resp[no_resp["CAT_OCUP"].isin([1.0, 2.0, 3.0])].copy()
no_resp_tfsr = no_resp[no_resp["CAT_OCUP"] == 4.0].copy()

pred_imp, al_piso = predecir_con_piso(modelo_final, no_resp_remun, piso_final)
sin_prediccion = no_resp_remun.index.difference(pred_imp.index)
if len(sin_prediccion) > 0:
    print(f"{len(sin_prediccion)} no respondentes sin predicción (variables faltantes).")

occ["P21_IMPUTADO"] = occ["P21_REAL"]
occ["IMPUTADO"] = False
occ.loc[pred_imp.index, "P21_IMPUTADO"] = pred_imp
occ.loc[pred_imp.index, "IMPUTADO"] = True
occ.loc[no_resp_tfsr.index, "P21_IMPUTADO"] = 0.0   # trabajadores familiares sin remuneracion

# comparacion: oficial (respondentes con PONDIIO) vs base imputada (todos con PONDERA)
resumen_imp = []
for aglo, nom in [(32, "CABA"), (33, "Gran Buenos Aires")]:
    obs = occ[(occ["AGLOMERADO"] == aglo) & (occ["P21_REAL"] > 0) & (occ["PONDIIO"] > 0)]
    idx_imp = occ.index[(occ["AGLOMERADO"] == aglo) & occ["IMPUTADO"]]
    imp = occ.loc[obs.index.union(idx_imp)]
    imp = imp[imp["PONDERA"] > 0]

    media_oficial = np.average(obs["P21_REAL"], weights=obs["PONDIIO"])
    media_imputada = np.average(imp["P21_IMPUTADO"], weights=imp["PONDERA"])
    mediana_oficial = mediana_ponderada(obs["P21_REAL"], obs["PONDIIO"])
    mediana_imputada = mediana_ponderada(imp["P21_IMPUTADO"], imp["PONDERA"])

    resumen_imp.append({
        "Aglomerado": nom,
        "Casos_Observados": len(obs),
        "Casos_Imputados": len(idx_imp),
        "Casos_Imputados_al_Piso": int(al_piso.loc[idx_imp].sum()),
        "Media_Oficial_PONDIIO": round(media_oficial, 0),
        "Media_Con_Imputacion_PONDERA": round(media_imputada, 0),
        "Diferencia_Media_Pct": round((media_imputada / media_oficial - 1) * 100, 2),
        "Mediana_Oficial_PONDIIO": round(mediana_oficial, 0),
        "Mediana_Con_Imputacion_PONDERA": round(mediana_imputada, 0),
        "Diferencia_Mediana_Pct": round((mediana_imputada / mediana_oficial - 1) * 100, 2),
    })

df_res_imp = pd.DataFrame(resumen_imp)
residuos_test = y_test - pred_test

#grafico observado vs predicho
fig1, ax1 = plt.subplots(figsize=(8.8, 5.2))
ax1.scatter(
    y_test / 1e6, pred_test / 1e6,
    alpha=0.18, s=14, color="#0077ff", edgecolors="none"
)
ax1.plot([0, 6], [0, 6], color="#D32F2F", linestyle="--", linewidth=1.8, label="Predicción perfecta (y = x)")
ax1.set_xlim(0, 6)
ax1.set_ylim(0, 4.5)
ax1.set_title(
    f"Evaluación del modelo WLS: Observado vs. Predicho en Test ($R^2 = {r2_test_simple:.3f}$)",
    fontsize=11.5, fontweight="bold", loc="left", pad=12
)
ax1.set_xlabel("Ingreso real observado en millones (2026-T2)", fontsize=9.5, fontweight="bold")
ax1.set_ylabel("Ingreso real predicho en millones (2026-T2)", fontsize=9.5, fontweight="bold")
ax1.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"${v:.1f}M".replace(".", ",")))
ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"${v:.1f}M".replace(".", ",")))
ax1.xaxis.grid(True, linestyle=":", color="gray", alpha=0.35)
ax1.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5)
ax1.legend(loc="upper left", frameon=True, fontsize=9)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "10_observado_vs_predicho.png", dpi=300, bbox_inches="tight")
plt.close(fig1)

#grafico residuos vs predichos
fig2, ax2 = plt.subplots(figsize=(8.8, 5.2))
ax2.scatter(
    pred_test / 1e6, residuos_test / 1e6,
    alpha=0.18, s=14, color="#9FA300", edgecolors="none"
)
ax2.axhline(0, color="#D32F2F", linestyle="--", linewidth=1.8, label="Residuo nulo (e = 0)")
ax2.set_xlim(0, 4.2)
ax2.set_ylim(-3.0, 5.0)
ax2.set_title(
    "Diagnóstico del modelo WLS: Residuos vs. Valores Predichos (Test)",
    fontsize=11.5, fontweight="bold", loc="left", pad=12
)
ax2.set_xlabel("Ingreso real predicho en millones (2026-T2)", fontsize=9.5, fontweight="bold")
ax2.set_ylabel("Residuo (Observado - Predicho) en millones", fontsize=9.5, fontweight="bold")
ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"${v:.1f}M".replace(".", ",")))
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"${v:.1f}M".replace(".", ",")))
ax2.xaxis.grid(True, linestyle=":", color="gray", alpha=0.35)
ax2.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5)
ax2.legend(loc="upper right", frameon=True, fontsize=9)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "11_residuos_vs_predichos.png", dpi=300, bbox_inches="tight")
plt.close(fig2)