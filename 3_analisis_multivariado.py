from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
import seaborn as sns

# -------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CARGA DE DATOS (41 TRIMESTRES: 2016-T2 A 2026-T2)
# -------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DIR_GRAFICOS = BASE_DIR / "graficos"
DIR_TABLAS = BASE_DIR / "tablas"

DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)
DIR_TABLAS.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

df = pd.read_csv(BASE_DIR / "datos" / "eph_microdatos.csv", low_memory=False)
df.columns = df.columns.str.strip().str.upper()

cols_num = [
    "AGLOMERADO", "ANO4", "TRIMESTRE", "ESTADO",
    "PONDERA", "PONDIIO", "CH04", "CH06",
    "NIVEL_ED", "P21_REAL", "PP3E_TOT", "PP04B_COD", "PP04D_COD"
]
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df[df["AGLOMERADO"].isin([32, 33]) & df["TRIMESTRE"].isin([1, 2, 3, 4]) & df["ANO4"].notna()].copy()
df["ANO4"] = df["ANO4"].astype(int)
df["TRIMESTRE"] = df["TRIMESTRE"].astype(int)
df["AGLOMERADO_NOM"] = df["AGLOMERADO"].map({32: "CABA", 33: "Gran Buenos Aires"})
df["PERIODO"] = df["ANO4"].astype(str) + "-T" + df["TRIMESTRE"].astype(str)

primera = df.sort_values(["ANO4", "TRIMESTRE"]).iloc[0]
ultima = df.sort_values(["ANO4", "TRIMESTRE"]).iloc[-1]

periodos = pd.period_range(
    start=pd.Period(f"{int(primera['ANO4'])}Q{int(primera['TRIMESTRE'])}", freq="Q-DEC"),
    end=pd.Period(f"{int(ultima['ANO4'])}Q{int(ultima['TRIMESTRE'])}", freq="Q-DEC"),
    freq="Q-DEC"
)

tabla_periodos = pd.DataFrame({
    "PERIODO": [f"{p.year}-T{p.quarter}" for p in periodos],
    "ANO4": [p.year for p in periodos],
    "TRIMESTRE": [p.quarter for p in periodos],
    "IDX_T": range(len(periodos))
})

mapa_periodos = dict(zip(tabla_periodos["PERIODO"], tabla_periodos["IDX_T"]))
df["IDX_T"] = df["PERIODO"].map(mapa_periodos)

eje_x = tabla_periodos["IDX_T"].to_numpy()
etiquetas_x = tabla_periodos["PERIODO"].to_numpy()

colores_ref = {"CABA": "#D8DB00", "Gran Buenos Aires": "#0077ff"}
colores_linea = {"CABA": "#9FA300", "Gran Buenos Aires": "#0077ff"}

# -------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES
# -------------------------------------------------------------------------
def weighted_quantiles(values, quantiles, sample_weight):
    values = np.asarray(values, dtype=float)
    sample_weight = np.asarray(sample_weight, dtype=float)
    quantiles = np.asarray(quantiles, dtype=float)
    validos = np.isfinite(values) & np.isfinite(sample_weight) & (sample_weight > 0)
    values, sample_weight = values[validos], sample_weight[validos]
    if len(values) == 0 or sample_weight.sum() <= 0:
        return np.full(len(quantiles), np.nan)
    sorter = np.argsort(values)
    values, sample_weight = values[sorter], sample_weight[sorter]
    pesos_acum = np.cumsum(sample_weight)
    pos = (pesos_acum - 0.5 * sample_weight) / pesos_acum[-1]
    return np.interp(quantiles, pos, values, left=values[0], right=values[-1])

def weighted_mean(values, sample_weight):
    values = np.asarray(values, dtype=float)
    sample_weight = np.asarray(sample_weight, dtype=float)
    validos = np.isfinite(values) & np.isfinite(sample_weight) & (sample_weight > 0)
    return np.average(values[validos], weights=sample_weight[validos]) if validos.sum() > 0 else np.nan

def estilizar_ejes(ax, solo_y=False):
    ax.tick_params(
        axis="y",
        which="major",
        left=True,
        right=False,
        direction="inout",
        length=7,
        width=1.2,
        color="#000000"
    )
    ax.spines["left"].set_color("#000000")
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if solo_y:
        ax.spines["bottom"].set_color("#000000")
        ax.spines["bottom"].set_linewidth(1.0)

def configurar_eje_temporal(ax, mostrar_labels=True):
    ax.set_xticks(eje_x)
    if mostrar_labels:
        ax.set_xticklabels(etiquetas_x, rotation=90, ha="center", fontsize=7.2)
    else:
        ax.set_xticklabels([])
    ax.set_xlim(-0.6, len(eje_x) - 0.4)

    ax.tick_params(
        axis="x",
        which="major",
        bottom=True,
        top=False,
        direction="inout",
        length=7,
        width=1.2,
        color="#000000"
    )
    ax.spines["bottom"].set_color("#000000")
    ax.spines["bottom"].set_linewidth(1.0)

    estilizar_ejes(ax, solo_y=False)

    ax.xaxis.grid(True, linestyle=":", color="gray", alpha=0.25)
    ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5)

def agregar_referencia_2020(ax, label=False):
    if "2020-T1" in mapa_periodos and "2022-T1" in mapa_periodos:
        ax.axvspan(
            mapa_periodos["2020-T1"],
            mapa_periodos["2022-T1"],
            color="#EC1616",
            alpha=0.12,
            zorder=0,
            label="Pandemia COVID-19 (T1 2020 a T1 2022)" if label else None
        )

# -------------------------------------------------------------------------
# GRÁFICOS DE TASAS DE ACTIVIDAD, DESOCUPACIÓN Y EMPLEO: EVOLUCIÓN TRIMESTRAL DE LAS 3 TASAS POR SEPARADO
# -------------------------------------------------------------------------
tasas_trim = []
for (ano, trimestre, nom), g in df.groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM"]):
    g = g[np.isfinite(g["PONDERA"]) & (g["PONDERA"] > 0)]
    pob = g["PONDERA"].sum()
    ocup = g.loc[g["ESTADO"] == 1, "PONDERA"].sum()
    desoc = g.loc[g["ESTADO"] == 2, "PONDERA"].sum()
    pea = ocup + desoc
    periodo = f"{ano}-T{trimestre}"
    tasas_trim.append({
        "ANO4": ano, "TRIMESTRE": trimestre, "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo], "AGLOMERADO_NOM": nom,
        "Tasa_Actividad": (pea / pob * 100) if pob > 0 else np.nan,
        "Tasa_Empleo": (ocup / pob * 100) if pob > 0 else np.nan,
        "Tasa_Desocupacion": (desoc / pea * 100) if pea > 0 else np.nan
    })

df_tasas = pd.DataFrame(tasas_trim).sort_values(["AGLOMERADO_NOM", "IDX_T"])
df_tasas.drop(columns=["IDX_T"]).round(2).to_csv(
    DIR_TABLAS / "03_tasas_trimestrales.csv", index=False, sep=";", decimal=","
)

configs_t = [
    ("Tasa_Actividad", "Evolución trimestral de la Tasa de Actividad (T2 2016 a T2 2026)",
     "Tasa de Actividad (%)", "o", (33, 60), "lower right", "3_1_tasa_actividad_trimestral.png"),
    ("Tasa_Empleo", "Evolución trimestral de la Tasa de Empleo (T2 2016 a T2 2026)",
     "Tasa de Empleo (%)", "s", (28, 56), "lower right", "3_2_tasa_empleo_trimestral.png"),
    ("Tasa_Desocupacion", "Evolución trimestral de la Tasa de Desocupación (T2 2016 a T2 2026)",
     "Tasa de Desocupación (%)", "^", (2, 18), "upper right", "3_3_tasa_desocupacion_trimestral.png")
]

for col, titulo, ylabel, marker, ylims, loc_leg, archivo in configs_t:
    fig, ax = plt.subplots(figsize=(12.2, 4.6))
    for nom in ["CABA", "Gran Buenos Aires"]:
        sub = df_tasas[df_tasas["AGLOMERADO_NOM"] == nom].sort_values("IDX_T")
        ax.plot(sub["IDX_T"], sub[col], marker=marker, markersize=4.5, linewidth=2.1,
                color=colores_linea[nom], label=nom)
    agregar_referencia_2020(ax, label=True)
    ax.set_title(titulo, fontsize=11.5, fontweight="bold", loc="left", pad=12)
    ax.set_ylabel(ylabel, fontsize=10, fontweight="bold")
    ax.set_ylim(ylims)
    configurar_eje_temporal(ax, mostrar_labels=True)
    ax.legend(loc=loc_leg, ncol=3, frameon=True, fontsize=8.8)
    plt.tight_layout()
    plt.savefig(DIR_GRAFICOS / archivo, dpi=300, bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------------------
# FIGURA 4: TENDENCIA CENTRAL (MEDIA/MEDIANA) Y POSICIÓN (Q1-Q3) TRIMESTRAL
# -------------------------------------------------------------------------
ocup_pos = df[(df["ESTADO"] == 1) & (df["P21_REAL"] > 0) & (df["PONDIIO"] > 0)
              & np.isfinite(df["P21_REAL"]) & np.isfinite(df["PONDIIO"])].copy()

ing_trim = []
for (ano, trimestre, nom), g in ocup_pos.groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM"]):
    q25, q50, q75 = weighted_quantiles(g["P21_REAL"], [0.25, 0.50, 0.75], g["PONDIIO"])
    media = weighted_mean(g["P21_REAL"], g["PONDIIO"])
    periodo = f"{ano}-T{trimestre}"
    ing_trim.append({
        "ANO4": ano, "TRIMESTRE": trimestre, "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo], "AGLOMERADO_NOM": nom,
        "Media": media, "Q25": q25, "Mediana": q50, "Q75": q75
    })

df_ing = pd.DataFrame(ing_trim).sort_values(["AGLOMERADO_NOM", "IDX_T"])
df_ing.drop(columns=["IDX_T"]).round(2).to_csv(DIR_TABLAS / "04_ingresos_trimestrales.csv", index=False, sep=";", decimal=",")

fig4, axes4 = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)

for i, nom in enumerate(["CABA", "Gran Buenos Aires"]):
    ax = axes4[i]
    sub = df_ing[df_ing["AGLOMERADO_NOM"] == nom].sort_values("IDX_T")
    c_base = colores_linea[nom]
    ax.plot(sub["IDX_T"], sub["Q75"] / 1e6, linestyle="--", linewidth=1.6, color="#455A64", label="Cuartil 3 (Q3)")
    ax.plot(sub["IDX_T"], sub["Media"] / 1e6, linestyle="-.", linewidth=1.9, color="#D32F2F", label="Media ponderada")
    ax.plot(sub["IDX_T"], sub["Mediana"] / 1e6, marker="o", markersize=3.8, linestyle="-", linewidth=2.3, color=c_base, label="Mediana (Q2)")
    ax.plot(sub["IDX_T"], sub["Q25"] / 1e6, linestyle=":", linewidth=1.7, color="#78909C", label="Cuartil 1 (Q1)")
    agregar_referencia_2020(ax, label=(i == 0))
    ax.set_title(nom, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_ylabel("Ingreso real en millones (2026-T2)", fontsize=9.5, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax, mostrar_labels=True)
    if i == 0:
        ax.legend(loc="upper right", ncol=5, frameon=True, fontsize=8.3)

plt.suptitle("Evolución trimestral de los ingresos reales",
             fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)

# Línea divisoria 
fig4.canvas.draw()
pos_sup = axes4[0].get_position()
pos_inf = axes4[1].get_position()
y_linea = (pos_sup.y0 + pos_inf.y1) / 2 - 0.028

linea_divisoria = Line2D(
    [0.02, 0.98], [y_linea, y_linea],
    transform=fig4.transFigure, color="#000000", linewidth=1.2, linestyle="-"
)
fig4.add_artist(linea_divisoria)

plt.savefig(DIR_GRAFICOS / "04_evolucion_ingresos_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# DECODIFICACIÓN DE VARIABLES DE EDUCACIÓN Y EMPLEO (PP04D_COD y PP04B_COD)
# -------------------------------------------------------------------------
cod_cal = ocup_pos["PP04D_COD"].dropna().astype(int).astype(str).str.zfill(5).str[-1].astype(int)
ocup_pos["CALIF_COD"] = np.nan
ocup_pos.loc[cod_cal.index, "CALIF_COD"] = cod_cal
ocup_pos.loc[~ocup_pos["CALIF_COD"].isin([1, 2, 3, 4]), "CALIF_COD"] = np.nan
ocup_pos["CALIF_NOM"] = ocup_pos["CALIF_COD"].map({1: "Profesional", 2: "Técnica", 3: "Operativa", 4: "No calificada"})

rama_2d = ocup_pos["PP04B_COD"].dropna().astype(int).astype(str).str.zfill(4).str[:2].astype(int)
def map_rama_caes(cod):
    if 10 <= cod <= 33: return "Industria manufacturera"
    elif 41 <= cod <= 43: return "Construcción"
    elif 45 <= cod <= 47: return "Comercio"
    elif 49 <= cod <= 53: return "Transporte y almacenamiento"
    elif 62 <= cod <= 82: return "Servicios prof., finan. e inf."
    elif cod == 84: return "Adm. pública y defensa"
    elif 85 <= cod <= 88: return "Enseñanza y salud"
    elif 97 <= cod <= 98: return "Servicio doméstico"
    else: return "Otros servicios y actividades"
ocup_pos.loc[rama_2d.index, "RAMA_NOM"] = rama_2d.map(map_rama_caes)

# -------------------------------------------------------------------------
# FIGURA 5A: EVOLUCIÓN TRIMESTRAL POR NIVEL EDUCATIVO (APILADA CON LÍNEA DIVISORIA)
# -------------------------------------------------------------------------
niv_evol_map = {
    **dict.fromkeys([1, 2, 3, 7], "Hasta Secundaria incompleta"),
    4: "Secundaria completa",
    5: "Superior / Univ. incompleto",
    6: "Superior / Univ. completo"
}
ocup_pos["NIVEL_EVOL"] = ocup_pos["NIVEL_ED"].map(niv_evol_map)

rows_niv = []
for (ano, trimestre, aglo, niv), g in ocup_pos.dropna(subset=["NIVEL_EVOL"]).groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", "NIVEL_EVOL"]):
    med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0] / 1e6
    periodo = f"{ano}-T{trimestre}"
    rows_niv.append({"PERIODO": periodo, "IDX_T": mapa_periodos[periodo], "Aglomerado": aglo, "Nivel": niv, "Mediana_M": med})
df_niv = pd.DataFrame(rows_niv).sort_values(["Aglomerado", "Nivel", "IDX_T"])
df_niv.drop(columns=["IDX_T"]).round(3).to_csv(DIR_TABLAS / "05a_evolucion_educacion_trim.csv", index=False, sep=";", decimal=",")

fig5a, axes5a = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)
pal_niv = ["#78909C", "#42A5F5", "#9FA300", "#0D47A1"]
orden_nt = [
    "Hasta Secundaria incompleta",
    "Secundaria completa",
    "Superior / Univ. incompleto",
    "Superior / Univ. completo"
]

for i, aglo in enumerate(["CABA", "Gran Buenos Aires"]):
    ax = axes5a[i]
    sub = df_niv[df_niv["Aglomerado"] == aglo]
    for niv, col_n in zip(orden_nt, pal_niv):
        s_n = sub[sub["Nivel"] == niv].sort_values("IDX_T")
        ax.plot(s_n["IDX_T"], s_n["Mediana_M"], marker="o", markersize=3.5, linewidth=1.9, color=col_n, label=niv)
    agregar_referencia_2020(ax, label=(i == 1))
    ax.set_title(aglo, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_ylabel("Mediana ingreso real (2026-T2)", fontsize=9.5, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax, mostrar_labels=True)
    if i == 1:
        ax.legend(loc="upper right", ncol=3, frameon=True, fontsize=8.2)

plt.suptitle("Evolución trimestral del ingreso real mediano según Nivel Educativo",
             fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)

# Línea divisoria continua negra de lado a lado
fig5a.canvas.draw()
pos_sup_5a = axes5a[0].get_position()
pos_inf_5a = axes5a[1].get_position()
y_linea_5a = (pos_sup_5a.y0 + pos_inf_5a.y1) / 2 - 0.028

linea_divisoria_5a = Line2D(
    [0.02, 0.98], [y_linea_5a, y_linea_5a],
    transform=fig5a.transFigure, color="#000000", linewidth=1.2, linestyle="-"
)
fig5a.add_artist(linea_divisoria_5a)

plt.savefig(DIR_GRAFICOS / "05a_educacion_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# FIGURA 5B1: MEDIANA SEGÚN CALIFICACIÓN DEL PUESTO (PP04D_COD) - SEPARADO
# -------------------------------------------------------------------------
rows_cal = []
for nom in ["CABA", "Gran Buenos Aires"]:
    sub = ocup_pos[(ocup_pos["AGLOMERADO_NOM"] == nom) & (ocup_pos["CALIF_NOM"].notna())]
    for cal in ["Profesional", "Técnica", "Operativa", "No calificada"]:
        g = sub[sub["CALIF_NOM"] == cal]
        med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0] / 1e6
        rows_cal.append({"Aglomerado": nom, "Calificacion": cal, "Mediana_M": round(med, 3)})
df_cal = pd.DataFrame(rows_cal)
df_cal.to_csv(DIR_TABLAS / "05b_ingreso_calificacion.csv", index=False, sep=";", decimal=",")

fig5b1, ax5_cal = plt.subplots(figsize=(10.5, 4.6))
sns.barplot(data=df_cal, y="Calificacion", x="Mediana_M", hue="Aglomerado",
            order=["Profesional", "Técnica", "Operativa", "No calificada"],
            hue_order=["CABA", "Gran Buenos Aires"], palette=colores_ref, edgecolor="black", linewidth=0.9, ax=ax5_cal)
ax5_cal.set_title("Mediana del ingreso real según Calificación del Puesto (PP04D_COD)", fontsize=11.5, fontweight="bold", loc="left", pad=12)
ax5_cal.set_ylabel("")
ax5_cal.set_xlabel("Mediana ingreso real en millones (2026-T2)", fontsize=9.5, fontweight="bold")
ax5_cal.set_xlim(0, df_cal["Mediana_M"].max() * 1.18)
ax5_cal.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
estilizar_ejes(ax5_cal, solo_y=True)
ax5_cal.legend(title="", loc="lower right", frameon=True, fontsize=9.0)
for p in ax5_cal.patches:
    w = p.get_width()
    if np.isfinite(w) and w > 0:
        ax5_cal.annotate(f"${w:.2f}M".replace(".", ","), (w, p.get_y() + p.get_height()/2.),
                         ha="left", va="center", fontsize=8.5, fontweight="bold", xytext=(5, 0), textcoords="offset points")

plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "05b_1_empleo_calificacion.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# FIGURA 5B2: MEDIANA SEGÚN RAMA DE ACTIVIDAD (PP04B_COD) - SEPARADO
# -------------------------------------------------------------------------
rows_rama = []
for nom in ["CABA", "Gran Buenos Aires"]:
    sub = ocup_pos[(ocup_pos["AGLOMERADO_NOM"] == nom) & (ocup_pos["RAMA_NOM"].notna())]
    for rama, g in sub.groupby("RAMA_NOM"):
        med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0] / 1e6
        rows_rama.append({"Aglomerado": nom, "Rama": rama, "Mediana_M": round(med, 3)})
df_rama = pd.DataFrame(rows_rama)
orden_rama = df_rama[df_rama["Aglomerado"] == "CABA"].sort_values("Mediana_M", ascending=False)["Rama"].tolist()
df_rama.to_csv(DIR_TABLAS / "05c_ingreso_rama_actividad.csv", index=False, sep=";", decimal=",")

fig5b2, ax5_rama = plt.subplots(figsize=(11.5, 6.2))
sns.barplot(data=df_rama, y="Rama", x="Mediana_M", hue="Aglomerado",
            order=orden_rama, hue_order=["CABA", "Gran Buenos Aires"], palette=colores_ref,
            edgecolor="black", linewidth=0.9, ax=ax5_rama)
ax5_rama.set_title("Mediana del ingreso real según Rama de Actividad (PP04B_COD)", fontsize=11.5, fontweight="bold", loc="left", pad=12)
ax5_rama.set_ylabel("")
ax5_rama.set_xlabel("Mediana ingreso real en millones (2026-T2)", fontsize=9.5, fontweight="bold")
ax5_rama.set_xlim(0, df_rama["Mediana_M"].max() * 1.18)
ax5_rama.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
estilizar_ejes(ax5_rama, solo_y=True)
ax5_rama.legend(title="", loc="lower right", frameon=True, fontsize=9.0)
for p in ax5_rama.patches:
    w = p.get_width()
    if np.isfinite(w) and w > 0:
        ax5_rama.annotate(f"${w:.2f}M".replace(".", ","), (w, p.get_y() + p.get_height()/2.),
                          ha="left", va="center", fontsize=8.2, fontweight="bold", xytext=(5, 0), textcoords="offset points")

plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "05b_2_empleo_rama.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# FIGURA 6: EVOLUCIÓN TRIMESTRAL POR SEXO Y BRECHA SALARIAL (CH04)
# -------------------------------------------------------------------------
ocup_sx = ocup_pos[ocup_pos["CH04"].isin([1, 2])].copy()
ocup_sx["SEXO_NOM"] = ocup_sx["CH04"].map({1: "Varones", 2: "Mujeres"})

rows_sx = []
for (ano, trimestre, aglo, sx), g in ocup_sx.groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", "SEXO_NOM"]):
    med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0]
    periodo = f"{ano}-T{trimestre}"
    rows_sx.append({"ANO4": ano, "TRIMESTRE": trimestre, "PERIODO": periodo,
                    "IDX_T": mapa_periodos[periodo], "Aglomerado": aglo, "Sexo": sx, "Mediana": med})

piv_sx = pd.DataFrame(rows_sx).pivot_table(
    index=["IDX_T", "PERIODO", "ANO4", "TRIMESTRE", "Aglomerado"], columns="Sexo", values="Mediana"
).reset_index().sort_values(["Aglomerado", "IDX_T"])
piv_sx["Brecha_%"] = np.where(piv_sx["Varones"] > 0, ((piv_sx["Varones"] - piv_sx["Mujeres"]) / piv_sx["Varones"]) * 100, np.nan)
piv_sx.drop(columns=["IDX_T"]).round(2).to_csv(DIR_TABLAS / "06_evolucion_sexo_trim.csv", index=False, sep=";", decimal=",")

fig6, axes_sx = plt.subplots(2, 2, figsize=(16.5, 7.6), sharex=True, gridspec_kw={"height_ratios": [2, 1.1]})
for i, aglo in enumerate(["CABA", "Gran Buenos Aires"]):
    sub = piv_sx[piv_sx["Aglomerado"] == aglo].sort_values("IDX_T")
    ax_top = axes_sx[0, i]
    ax_top.plot(sub["IDX_T"], sub["Varones"] / 1e6, marker="o", markersize=3.5, linewidth=2.0, color="#0077ff", label="Varones")
    ax_top.plot(sub["IDX_T"], sub["Mujeres"] / 1e6, marker="s", markersize=3.5, linewidth=2.0, color="#9FA300", label="Mujeres")
    agregar_referencia_2020(ax_top, label=(i == 0))
    ax_top.set_title(aglo, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax_top.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax_top, mostrar_labels=False)
    if i == 0:
        ax_top.set_ylabel("Mediana ingreso real", fontsize=9.5, fontweight="bold")
        ax_top.legend(loc="upper right", frameon=True, fontsize=8.5)

    ax_bot = axes_sx[1, i]
    ax_bot.plot(sub["IDX_T"], sub["Brecha_%"], marker="d", markersize=3.5, linewidth=1.8, color="#D32F2F", label="Brecha salarial (%)")
    ax_bot.set_ylim(0, 48)
    configurar_eje_temporal(ax_bot, mostrar_labels=True)
    if i == 0:
        ax_bot.set_ylabel("Brecha salarial (%)", fontsize=9.5, fontweight="bold", color="#D32F2F")
        ax_bot.legend(loc="upper left", frameon=True, fontsize=8.2)

plt.suptitle("Evolución trimestral del ingreso real mediano y la brecha salarial por sexo (CH04)",
             fontsize=12.5, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "06_evolucion_sexo_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# FIGURA 7: SÍNTESIS MULTIVARIADA (EDAD CH06 + CORRELOGRAMA DE SPEARMAN)
# -------------------------------------------------------------------------
ocup_pos["GRUPO_EDAD"] = pd.cut(ocup_pos["CH06"], bins=[14, 29, 49, np.inf],
                                labels=["15 a 29 años\n(Jóvenes)", "30 a 49 años\n(Adultos)", "50 años y más\n(Mayores)"])
plot_edad = ocup_pos.dropna(subset=["GRUPO_EDAD", "P21_REAL", "AGLOMERADO_NOM"]).copy()
plot_edad["INGRESO_M"] = plot_edad["P21_REAL"] / 1e6

rows_ed = []
for (aglo, ged), g in plot_edad.groupby(["AGLOMERADO_NOM", "GRUPO_EDAD"], observed=True):
    q25, q50, q75 = weighted_quantiles(g["P21_REAL"], [0.25, 0.50, 0.75], g["PONDIIO"])
    rows_ed.append({"Aglomerado": aglo, "Grupo_Edad": ged.replace("\n", " "),
                    "Q25_M": round(q25/1e6, 3), "Mediana_M": round(q50/1e6, 3), "Q75_M": round(q75/1e6, 3)})
pd.DataFrame(rows_ed).to_csv(DIR_TABLAS / "07a_ingresos_grupo_etario.csv", index=False, sep=";", decimal=",")

corr_df = ocup_pos[["P21_REAL", "NIVEL_ED", "CALIF_COD", "PP3E_TOT", "CH06"]].copy()
corr_df["NIVEL_ORD"] = corr_df["NIVEL_ED"].replace({7: 0})
corr_df["CALIF_ORD"] = 5 - corr_df["CALIF_COD"]
corr_df.loc[~corr_df["CALIF_COD"].isin([1, 2, 3, 4]), "CALIF_ORD"] = np.nan
corr_df.loc[(corr_df["PP3E_TOT"] <= 0) | (corr_df["PP3E_TOT"] > 120), "PP3E_TOT"] = np.nan
corr_df.loc[~corr_df["NIVEL_ED"].isin([1, 2, 3, 4, 5, 6, 7]), "NIVEL_ORD"] = np.nan

corr_plot = corr_df[["P21_REAL", "NIVEL_ORD", "CALIF_ORD", "PP3E_TOT", "CH06"]].rename(columns={
    "P21_REAL": "Ingreso Real\n(P21_REAL)",
    "NIVEL_ORD": "Nivel Educativo\n(NIVEL_ED)",
    "CALIF_ORD": "Calificación\n(PP04D_COD)",
    "PP3E_TOT": "Horas Trabajadas\n(PP3E_TOT)",
    "CH06": "Edad\n(CH06)"
}).corr(method="spearman")
corr_plot.to_csv(DIR_TABLAS / "07b_matriz_spearman.csv", sep=";", decimal=",")

fig7, (ax7_l, ax7_r) = plt.subplots(1, 2, figsize=(14.5, 5.0), gridspec_kw={"width_ratios": [1.05, 1.15]})

sns.boxplot(data=plot_edad, x="GRUPO_EDAD", y="INGRESO_M", hue="AGLOMERADO_NOM",
            hue_order=["CABA", "Gran Buenos Aires"], palette=colores_ref,
            showfliers=False, width=0.55, linewidth=1.2, ax=ax7_l)
ax7_l.set_title("Distribución del ingreso real según grupo etario (CH06)", fontsize=11, fontweight="bold", loc="left", pad=10)
ax7_l.set_xlabel("")
ax7_l.set_ylabel("Ingreso real en millones de pesos", fontsize=9.5, fontweight="bold")
ax7_l.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
ax7_l.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5)
estilizar_ejes(ax7_l, solo_y=True)
ax7_l.legend(title="", loc="upper left", frameon=True, fontsize=8.5)

sns.heatmap(corr_plot, annot=True, fmt=".2f", cmap="YlGnBu", vmin=-0.2, vmax=1.0,
            linewidths=1, linecolor="white", cbar_kws={"shrink": 0.8}, ax=ax7_r,
            annot_kws={"size": 9.5, "weight": "bold"})
ax7_r.set_title("Matriz de correlación de Spearman", fontsize=11, fontweight="bold", loc="left", pad=10)
ax7_r.tick_params(axis="x", rotation=20, labelsize=8.5)
ax7_r.tick_params(axis="y", rotation=0, labelsize=8.5)

plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "07_edad_y_correlaciones.png", dpi=300, bbox_inches="tight")
plt.close()

print("Listo: 7 gráficos generados en", DIR_GRAFICOS, "y 7 CSV en", DIR_TABLAS)