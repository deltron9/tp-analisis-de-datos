from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
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
    "NIVEL_ED", "P21_REAL", "PP04B_COD", "PP04D_COD"
]
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df[df["AGLOMERADO"].isin([32, 33]) & df["TRIMESTRE"].isin([1, 2, 3, 4]) & df["ANO4"].notna()].copy()
df["ANO4"] = df["ANO4"].astype(int)
df["TRIMESTRE"] = df["TRIMESTRE"].astype(int)
df["AGLOMERADO_NOM"] = df["AGLOMERADO"].map({32: "CABA", 33: "Gran Buenos Aires"})
df["PERIODO"] = df["ANO4"].astype(str) + "-T" + df["TRIMESTRE"].astype(str)
df["SEXO_NOM"] = df["CH04"].map({1: "Varones", 2: "Mujeres"})


def clasificar_edad(e):
    if pd.isna(e) or e < 15:
        return np.nan
    elif e <= 29:
        return "15 a 29 años"
    elif e <= 49:
        return "30 a 49 años"
    else:
        return "50 años y más"


df["GRUPO_EDAD"] = df["CH06"].apply(clasificar_edad)

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

colores_linea = {"CABA": "#9FA300", "Gran Buenos Aires": "#0077ff"}

# Ocupados con ingreso positivo (base de los análisis de ingresos)
ocup_pos = df[(df["ESTADO"] == 1) & (df["P21_REAL"] > 0) & (df["PONDIIO"] > 0)
              & np.isfinite(df["P21_REAL"]) & np.isfinite(df["PONDIIO"])].copy()

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


def calcular_tasas(g):
    g = g[np.isfinite(g["PONDERA"]) & (g["PONDERA"] > 0)]
    pob = g["PONDERA"].sum()
    ocup = g.loc[g["ESTADO"] == 1, "PONDERA"].sum()
    desoc = g.loc[g["ESTADO"] == 2, "PONDERA"].sum()
    pea = ocup + desoc
    return {
        "Tasa_Actividad": (pea / pob * 100) if pob > 0 else np.nan,
        "Tasa_Empleo": (ocup / pob * 100) if pob > 0 else np.nan,
        "Tasa_Desocupacion": (desoc / pea * 100) if pea > 0 else np.nan
    }


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


def agregar_linea_divisoria(fig, ax_sup, ax_inf, offset=-0.028):
    fig.canvas.draw()
    pos_sup = ax_sup.get_position()
    pos_inf = ax_inf.get_position()
    y_linea = (pos_sup.y0 + pos_inf.y1) / 2 + offset
    linea = Line2D(
        [0.02, 0.98], [y_linea, y_linea],
        transform=fig.transFigure, color="#000000", linewidth=1.2, linestyle="-"
    )
    fig.add_artist(linea)


# -------------------------------------------------------------------------
# 3. TASA DE ACTIVIDAD TRIMESTRAL Y TABLA GENERAL DE TASAS
# -------------------------------------------------------------------------
tasas_trim = []
for (ano, trimestre, nom), g in df.groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM"]):
    periodo = f"{ano}-T{trimestre}"
    tasas_trim.append({
        "ANO4": ano, "TRIMESTRE": trimestre, "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo], "AGLOMERADO_NOM": nom,
        **calcular_tasas(g)
    })

df_tasas = pd.DataFrame(tasas_trim).sort_values(["AGLOMERADO_NOM", "IDX_T"])
df_tasas.drop(columns=["IDX_T"]).round(2).to_csv(
    DIR_TABLAS / "03_tasas_trimestrales.csv", index=False, sep=";", decimal=","
)

fig, ax = plt.subplots(figsize=(12.2, 4.6))
for nom in ["CABA", "Gran Buenos Aires"]:
    sub = df_tasas[df_tasas["AGLOMERADO_NOM"] == nom].sort_values("IDX_T")
    ax.plot(sub["IDX_T"], sub["Tasa_Actividad"], marker="o", markersize=4.5, linewidth=2.1,
            color=colores_linea[nom], label=nom)
agregar_referencia_2020(ax, label=True)
ax.set_title("Evolución trimestral de la Tasa de Actividad (T2 2016 a T2 2026)",
             fontsize=11.5, fontweight="bold", loc="left", pad=12)
ax.set_ylabel("Tasa de Actividad (%)", fontsize=10, fontweight="bold")
ax.set_ylim((33, 60))
configurar_eje_temporal(ax, mostrar_labels=True)
ax.legend(loc="lower right", ncol=3, frameon=True, fontsize=8.8)
plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "3_1_tasa_actividad_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# 4. DESOCUPACIÓN POR SEXO Y GRUPO ETARIO
# -------------------------------------------------------------------------
filas_seg = []
for seg, col_seg in [("Sexo", "SEXO_NOM"), ("Grupo etario", "GRUPO_EDAD")]:
    for (ano, trimestre, nom, cat), g in df.dropna(subset=[col_seg]).groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", col_seg]):
        periodo = f"{ano}-T{trimestre}"
        filas_seg.append({
            "Segmento": seg, "Categoria": cat, "PERIODO": periodo, "IDX_T": mapa_periodos[periodo],
            "Aglomerado": nom, **calcular_tasas(g)
        })

df_seg = pd.DataFrame(filas_seg).sort_values(["Segmento", "Aglomerado", "Categoria", "IDX_T"])
df_seg.drop(columns=["IDX_T"]).round(2).to_csv(
    DIR_TABLAS / "03b_tasas_sexo_edad.csv", index=False, sep=";", decimal=","
)

estilos_seg = {
    "Sexo": {"Varones": ("#0077ff", "o", "-"), "Mujeres": ("#9FA300", "s", "--")},
    "Grupo etario": {"15 a 29 años": ("#42A5F5", "o", "-"), "30 a 49 años": ("#9FA300", "s", "--"),
                     "50 años y más": ("#0D47A1", "^", "-.")}
}
configs_seg = [
    ("Tasa_Desocupacion", "Tasa de Desocupación", "upper right", "desocupacion")
]

n_fig = 2
for col, nombre, loc_leg, clave in configs_seg:
    for seg, sufijo in [("Sexo", "sexo"), ("Grupo etario", "edad")]:
        fig_s, axes_s = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)
        for i, nom in enumerate(["CABA", "Gran Buenos Aires"]):
            ax = axes_s[i]
            for cat, (c_cat, mk, ls) in estilos_seg[seg].items():
                s_c = df_seg[(df_seg["Segmento"] == seg) & (df_seg["Aglomerado"] == nom)
                             & (df_seg["Categoria"] == cat)].sort_values("IDX_T")
                ax.plot(s_c["IDX_T"], s_c[col], marker=mk, markersize=3.8, linewidth=2.0,
                        linestyle=ls, color=c_cat, label=cat)
            agregar_referencia_2020(ax, label=(i == 1))
            ax.set_title(nom, fontsize=11.5, fontweight="bold", loc="left", pad=10)
            ax.set_ylabel(f"{nombre} (%)", fontsize=9.5, fontweight="bold")
            configurar_eje_temporal(ax, mostrar_labels=True)
            if i == 1:
                ax.legend(loc=loc_leg, ncol=4, frameon=True, fontsize=8.4)
        plt.suptitle(f"Evolución trimestral de la {nombre} según {seg.lower()}",
                     fontsize=12.5, fontweight="bold", y=0.91)
        plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)
        agregar_linea_divisoria(fig_s, axes_s[0], axes_s[1])
        plt.savefig(DIR_GRAFICOS / f"3_{n_fig}_tasa_{clave}_{sufijo}.png", dpi=300, bbox_inches="tight")
        plt.close()
        n_fig += 1

# -------------------------------------------------------------------------
# 5. TENDENCIA CENTRAL (MEDIA/MEDIANA) Y POSICIÓN (Q1-Q3) TRIMESTRAL
# -------------------------------------------------------------------------
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
df_ing.drop(columns=["IDX_T"]).round(2).to_csv(
    DIR_TABLAS / "04_ingresos_trimestrales.csv", index=False, sep=";", decimal=","
)

fig4, axes4 = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)

for i, nom in enumerate(["CABA", "Gran Buenos Aires"]):
    ax = axes4[i]
    sub = df_ing[df_ing["AGLOMERADO_NOM"] == nom].sort_values("IDX_T")
    c_base = colores_linea[nom]
    ax.plot(sub["IDX_T"], sub["Q75"] / 1e6, linestyle="--", linewidth=1.6, color="#455A64", label="Cuartil 3 (Q3)")
    ax.plot(sub["IDX_T"], sub["Media"] / 1e6, linestyle="-.", linewidth=1.9, color="#D32F2F", label="Media ponderada")
    ax.plot(sub["IDX_T"], sub["Mediana"] / 1e6, marker="o", markersize=3.8, linestyle="-", linewidth=2.3, color=c_base, label="Mediana (Q2)")
    ax.plot(sub["IDX_T"], sub["Q25"] / 1e6, linestyle=":", linewidth=1.7, color="#78909C", label="Cuartil 1 (Q1)")
    agregar_referencia_2020(ax, label=True)
    ax.set_title(nom, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_ylabel("Ingreso real en millones (2026-T2)", fontsize=9.5, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax, mostrar_labels=True)
    ax.legend(loc="upper right", ncol=5, frameon=True, fontsize=8.3)

plt.suptitle("Evolución trimestral de los ingresos reales", fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)
agregar_linea_divisoria(fig4, axes4[0], axes4[1])
plt.savefig(DIR_GRAFICOS / "04_evolucion_ingresos_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# 6. DECODIFICACIÓN DE VARIABLES DE CALIFICACIÓN Y RAMA (PP04D_COD y PP04B_COD)
# -------------------------------------------------------------------------
cod_cal = ocup_pos["PP04D_COD"].dropna().astype(int).astype(str).str.zfill(5).str[-1].astype(int)
ocup_pos["CALIF_COD"] = np.nan
ocup_pos.loc[cod_cal.index, "CALIF_COD"] = cod_cal
ocup_pos.loc[~ocup_pos["CALIF_COD"].isin([1, 2, 3, 4]), "CALIF_COD"] = np.nan
ocup_pos["CALIF_NOM"] = ocup_pos["CALIF_COD"].map({1: "Profesional", 2: "Técnica", 3: "Operativa", 4: "No calificada"})

rama_2d = ocup_pos["PP04B_COD"].dropna().astype(int).astype(str).str.zfill(4).str[:2].astype(int)


def map_rama_caes(cod):
    if 10 <= cod <= 33:
        return "Industria manufacturera"
    elif cod == 40:
        return "Construcción"
    elif 45 <= cod <= 48:
        return "Comercio"
    elif 49 <= cod <= 53:
        return "Transporte y almacenamiento"
    elif 55 <= cod <= 56:
        return "Hotelería y gastronomía"
    elif 62 <= cod <= 82:
        return "Servicios prof., finan. e inf."
    elif cod == 84:
        return "Adm. pública y defensa"
    elif 85 <= cod <= 88:
        return "Enseñanza y salud"
    elif 97 <= cod <= 98:
        return "Servicio doméstico"
    else:
        return "Otros servicios y actividades"


ocup_pos.loc[rama_2d.index, "RAMA_NOM"] = rama_2d.map(map_rama_caes)

# -------------------------------------------------------------------------
# 7. EVOLUCIÓN TRIMESTRAL POR NIVEL EDUCATIVO
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
df_niv.drop(columns=["IDX_T"]).round(3).to_csv(
    DIR_TABLAS / "05a_evolucion_educacion_trim.csv", index=False, sep=";", decimal=","
)

fig5a, axes5a = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)
pal_niv = ["#78909C", "#42A5F5", "#9FA300", "#0D47A1"]
orden_nt = ["Hasta Secundaria incompleta", "Secundaria completa", "Superior / Univ. incompleto", "Superior / Univ. completo"]

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

plt.suptitle("Evolución trimestral del ingreso real mediano según Nivel Educativo", fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)
agregar_linea_divisoria(fig5a, axes5a[0], axes5a[1])
plt.savefig(DIR_GRAFICOS / "05a_educacion_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# 8. EVOLUCIÓN TRIMESTRAL POR CALIFICACIÓN DEL PUESTO
# -------------------------------------------------------------------------
rows_cal = []
for (ano, trimestre, aglo, cal), g in ocup_pos.dropna(subset=["CALIF_NOM"]).groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", "CALIF_NOM"]):
    med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0] / 1e6
    periodo = f"{ano}-T{trimestre}"
    rows_cal.append({"PERIODO": periodo, "IDX_T": mapa_periodos[periodo], "Aglomerado": aglo, "Calificacion": cal, "Mediana_M": med})
df_cal = pd.DataFrame(rows_cal).sort_values(["Aglomerado", "Calificacion", "IDX_T"])
df_cal.drop(columns=["IDX_T"]).round(3).to_csv(
    DIR_TABLAS / "05b_evolucion_calificacion_trim.csv", index=False, sep=";", decimal=","
)

fig5b1, axes5b1 = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)
pal_cal = ["#78909C", "#42A5F5", "#9FA300", "#0D47A1"]
orden_cal = ["No calificada", "Operativa", "Técnica", "Profesional"]

for i, aglo in enumerate(["CABA", "Gran Buenos Aires"]):
    ax = axes5b1[i]
    sub = df_cal[df_cal["Aglomerado"] == aglo]
    for cal, col_c in zip(orden_cal, pal_cal):
        s_c = sub[sub["Calificacion"] == cal].sort_values("IDX_T")
        ax.plot(s_c["IDX_T"], s_c["Mediana_M"], marker="o", markersize=3.5, linewidth=1.9, color=col_c, label=cal)
    agregar_referencia_2020(ax, label=(i == 1))
    ax.set_title(aglo, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_ylabel("Mediana ingreso real (2026-T2)", fontsize=9.5, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax, mostrar_labels=True)
    if i == 1:
        ax.legend(loc="upper right", ncol=3, frameon=True, fontsize=8.2)

plt.suptitle("Evolución trimestral del ingreso real mediano según Calificación del Puesto", fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)
agregar_linea_divisoria(fig5b1, axes5b1[0], axes5b1[1])
plt.savefig(DIR_GRAFICOS / "05b_1_calificacion_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# 9. EVOLUCIÓN TRIMESTRAL POR TOP 3 RAMAS DE ACTIVIDAD
# -------------------------------------------------------------------------
def obtener_top3_aglo(aglo):
    return (
        ocup_pos[
            (ocup_pos["AGLOMERADO_NOM"] == aglo)
            & ocup_pos["RAMA_NOM"].notna()
            & (ocup_pos["RAMA_NOM"] != "Otros servicios y actividades")
        ]
        .groupby("RAMA_NOM")["PONDIIO"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )


top3_caba = obtener_top3_aglo("CABA")
top3_gba = obtener_top3_aglo("Gran Buenos Aires")

rows_rama_trim = []
for (ano, trimestre, aglo, rama), g in ocup_pos.dropna(subset=["RAMA_NOM"]).groupby(["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", "RAMA_NOM"]):
    med = weighted_quantiles(g["P21_REAL"], [0.5], g["PONDIIO"])[0] / 1e6
    periodo = f"{ano}-T{trimestre}"
    rows_rama_trim.append({
        "PERIODO": periodo, "IDX_T": mapa_periodos[periodo],
        "Aglomerado": aglo, "Rama": rama, "Mediana_M": med
    })

df_rama_trim = pd.DataFrame(rows_rama_trim).sort_values(["Aglomerado", "Rama", "IDX_T"])
df_rama_trim.drop(columns=["IDX_T"]).round(3).to_csv(
    DIR_TABLAS / "05c_evolucion_ramas_trim.csv", index=False, sep=";", decimal=","
)

fig5c, axes5c = plt.subplots(2, 1, figsize=(13.5, 8.8), sharey=True)
colores_ramas = {
    "Servicios prof., finan. e inf.": "#0D47A1",
    "Enseñanza y salud": "#42A5F5",
    "Comercio": "#9FA300",
    "Industria manufacturera": "#AB00FA"
}

for i, (aglo, ramas_lista) in enumerate([("CABA", top3_caba), ("Gran Buenos Aires", top3_gba)]):
    ax = axes5c[i]
    sub = df_rama_trim[df_rama_trim["Aglomerado"] == aglo]
    for rama in ramas_lista:
        s_r = sub[sub["Rama"] == rama].sort_values("IDX_T")
        ax.plot(
            s_r["IDX_T"], s_r["Mediana_M"],
            marker="o", markersize=3.5, linewidth=1.9,
            color=colores_ramas.get(rama, "#455A64"), label=rama
        )
    agregar_referencia_2020(ax, label=(i == 1))
    ax.set_title(aglo, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_ylabel("Mediana ingreso real (2026-T2)", fontsize=9.5, fontweight="bold")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    configurar_eje_temporal(ax, mostrar_labels=True)
    ax.legend(loc="upper right", ncol=2, frameon=True, fontsize=8.2)

plt.suptitle("Evolución trimestral del ingreso real según principales ramas de actividad", fontsize=12.5, fontweight="bold", y=0.91)
plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.8)
agregar_linea_divisoria(fig5c, axes5c[0], axes5c[1])
plt.savefig(DIR_GRAFICOS / "05c_ramas_trimestral.png", dpi=300, bbox_inches="tight")
plt.close()

conteo_ramas = (
    ocup_pos.dropna(subset=["RAMA_NOM"])
    .groupby(["AGLOMERADO_NOM", "RAMA_NOM"])
    .size()
    .reset_index(name="Casos_n")
)
totales_aglo = conteo_ramas.groupby("AGLOMERADO_NOM")["Casos_n"].transform("sum")
conteo_ramas["Participacion_%"] = (conteo_ramas["Casos_n"] / totales_aglo * 100).round(2)
conteo_ramas = conteo_ramas.sort_values(["AGLOMERADO_NOM", "Casos_n"], ascending=[True, False])
conteo_ramas.to_csv(DIR_TABLAS / "05c_cantidad_casos_ramas.csv", index=False, sep=";", decimal=",")

# -------------------------------------------------------------------------
# GRÁFICO MULTIVARIADO DE 4 VARIABLES: INGRESO x EDAD x SEXO x AGLOMERADO
# -------------------------------------------------------------------------
def clasificar_edad(e):
    if pd.isna(e) or e < 15:
        return np.nan
    elif e <= 29:
        return "15 a 29 años"
    elif e <= 49:
        return "30 a 49 años"
    else:
        return "50 años y más"

ocup_pos["GRUPO_EDAD"] = ocup_pos["CH06"].apply(clasificar_edad)

df_4v = ocup_pos.dropna(subset=["GRUPO_EDAD"]).copy()
df_4v = df_4v[df_4v["CH04"].isin([1, 2])].copy()
df_4v["SEXO_NOM"] = df_4v["CH04"].map({1: "Varones", 2: "Mujeres"})
df_4v["P21_M"] = df_4v["P21_REAL"] / 1e6

# Exportar métricas exactas (Q1, Mediana, Q3 y n) para el texto
resumen_4v = []
for (aglo, gedad, sexo), g in df_4v.groupby(["AGLOMERADO_NOM", "GRUPO_EDAD", "SEXO_NOM"]):
    q25, q50, q75 = weighted_quantiles(g["P21_REAL"], [0.25, 0.50, 0.75], g["PONDIIO"]) / 1e6
    resumen_4v.append({
        "Aglomerado": aglo,
        "Grupo_Edad": gedad,
        "Sexo": sexo,
        "Casos_n": len(g),
        "Q1_M": round(q25, 3),
        "Mediana_M": round(q50, 3),
        "Q3_M": round(q75, 3)
    })

df_res_4v = pd.DataFrame(resumen_4v)
df_res_4v.to_csv(DIR_TABLAS / "07_resumen_edad_sexo_aglo.csv", index=False, sep=";", decimal=",")
print("\n--- RESUMEN EDAD x SEXO x AGLOMERADO ---")
print(df_res_4v.to_string(index=False))

# Gráfico (con outliers superiores visibles y eje Y acotado a $6,2M para no aplastar las cajas)
fig_4v, axes_4v = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
paleta_sexo = {"Varones": "#0077ff", "Mujeres": "#D8DB00"}
orden_edad = ["15 a 29 años", "30 a 49 años", "50 años y más"]

for i, aglo in enumerate(["CABA", "Gran Buenos Aires"]):
    ax = axes_4v[i]
    sub = df_4v[df_4v["AGLOMERADO_NOM"] == aglo]
    sns.boxplot(
        data=sub,
        x="GRUPO_EDAD",
        y="P21_M",
        hue="SEXO_NOM",
        order=orden_edad,
        hue_order=["Varones", "Mujeres"],
        palette=paleta_sexo,
        showfliers=True,
        width=0.55,
        boxprops=dict(edgecolor="#000000", linewidth=1.1),
        medianprops=dict(color="#D32F2F", linewidth=2.0),
        whiskerprops=dict(color="#000000", linewidth=1.1),
        capprops=dict(color="#000000", linewidth=1.1),
        flierprops=dict(
            marker="o",
            markersize=2.4,
            markerfacecolor="#616161",
            markeredgecolor="none",
            alpha=0.35
        ),
        ax=ax
    )
    ax.set_title(aglo, fontsize=11.5, fontweight="bold", loc="left", pad=10)
    ax.set_xlabel("Grupo etario", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Ingreso real en millones (2026-T2)" if i == 0 else "", fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, 6.2)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")))
    ax.xaxis.grid(False)
    ax.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5)
    estilizar_ejes(ax, solo_y=True)

    if i == 0:
        ax.get_legend().remove()
    else:
        ax.legend(title="", frameon=True, loc="upper right", fontsize=9.5)

plt.suptitle("Distribución del ingreso real por grupo etario, sexo y aglomerado",
             fontsize=12.5, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(DIR_GRAFICOS / "07_ingreso_edad_sexo_aglo.png", dpi=300, bbox_inches="tight")
plt.close()

print("Listo: gráficos generados en", DIR_GRAFICOS, "y CSV en", DIR_TABLAS)