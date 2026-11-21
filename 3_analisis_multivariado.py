
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

# -------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CARGA DE DATOS
# -------------------------------------------------------------------------

DIR_BASE = "graficos/analisis_multivariado"

DIR_TASAS = os.path.join(DIR_BASE, "01_evolucion_tasas")
DIR_INGRESOS = os.path.join(DIR_BASE, "02_evolucion_ingresos")
DIR_CARACTERISTICAS = os.path.join(DIR_BASE, "03_ingresos_por_caracteristicas")
DIR_EDAD = os.path.join(DIR_BASE, "04_distribucion_por_edad")
DIR_CORRELACIONES = os.path.join(DIR_BASE, "05_correlaciones")

for directorio in [
    DIR_TASAS,
    DIR_INGRESOS,
    DIR_CARACTERISTICAS,
    DIR_EDAD,
    DIR_CORRELACIONES
]:
    os.makedirs(directorio, exist_ok=True)

sns.set_theme(style="whitegrid")

df = pd.read_csv("datos/eph_microdatos.csv", low_memory=False)
df.columns = df.columns.str.strip().str.upper()

cols_num = [
    "AGLOMERADO", "ANO4", "TRIMESTRE", "ESTADO",
    "PONDERA", "PONDIIO", "CH04", "CH06",
    "NIVEL_ED", "P21_REAL", "PP3E_TOT", "PP04D_COD"
]

for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df[df["AGLOMERADO"].isin([32, 33])].copy()
df = df[df["TRIMESTRE"].isin([1, 2, 3, 4])].copy()
df = df[df["ANO4"].notna()].copy()

df["ANO4"] = df["ANO4"].astype(int)
df["TRIMESTRE"] = df["TRIMESTRE"].astype(int)

df["AGLOMERADO_NOM"] = df["AGLOMERADO"].map({
    32: "CABA",
    33: "Gran Buenos Aires"
})

colores_ref = {
    "CABA": "#D8DB00",
    "Gran Buenos Aires": "#0077ff"
}

colores_linea = {
    "CABA": "#9FA300",
    "Gran Buenos Aires": "#0077ff"
}

# Identificador temporal trimestral.
df["PERIODO"] = (
    df["ANO4"].astype(str)
    + "-T"
    + df["TRIMESTRE"].astype(str)
)

df["PERIODO_ORD"] = df["ANO4"] * 10 + df["TRIMESTRE"]

# Se determina correctamente el primer y último trimestre disponible.
primera_fila = df.sort_values(
    ["ANO4", "TRIMESTRE"]
).iloc[0]

ultima_fila = df.sort_values(
    ["ANO4", "TRIMESTRE"]
).iloc[-1]

periodos = pd.period_range(
    start=pd.Period(
        f"{int(primera_fila['ANO4'])}Q{int(primera_fila['TRIMESTRE'])}",
        freq="Q-DEC"
    ),
    end=pd.Period(
        f"{int(ultima_fila['ANO4'])}Q{int(ultima_fila['TRIMESTRE'])}",
        freq="Q-DEC"
    ),
    freq="Q-DEC"
)

tabla_periodos = pd.DataFrame({
    "PERIODO": [f"{p.year}-T{p.quarter}" for p in periodos],
    "ANO4": [p.year for p in periodos],
    "TRIMESTRE": [p.quarter for p in periodos],
    "IDX_T": range(len(periodos))
})

mapa_periodos = dict(
    zip(tabla_periodos["PERIODO"], tabla_periodos["IDX_T"])
)

df["IDX_T"] = df["PERIODO"].map(mapa_periodos)

eje_x = tabla_periodos["IDX_T"].to_numpy()
etiquetas_x = tabla_periodos["PERIODO"].to_numpy()

# Mostrar una etiqueta cada cuatro trimestres.
ticks_x = eje_x[::4]
labels_x = etiquetas_x[::4]


# -------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES
# -------------------------------------------------------------------------

def weighted_quantiles(values, quantiles, sample_weight):
    """
    Calcula cuantiles ponderados.

    Descarta valores y ponderadores inválidos.
    Devuelve NaN cuando no existen observaciones válidas.
    """

    values = np.asarray(values, dtype=float)
    sample_weight = np.asarray(sample_weight, dtype=float)
    quantiles = np.asarray(quantiles, dtype=float)

    if len(values) != len(sample_weight):
        raise ValueError(
            "Los valores y los ponderadores deben tener igual longitud."
        )

    validos = (
        np.isfinite(values)
        & np.isfinite(sample_weight)
        & (sample_weight > 0)
    )

    values = values[validos]
    sample_weight = sample_weight[validos]

    if len(values) == 0 or sample_weight.sum() <= 0:
        return np.full(len(quantiles), np.nan)

    if np.any((quantiles < 0) | (quantiles > 1)):
        raise ValueError("Los cuantiles deben estar entre 0 y 1.")

    sorter = np.argsort(values)

    values = values[sorter]
    sample_weight = sample_weight[sorter]

    pesos_acumulados = np.cumsum(sample_weight)

    posiciones = (
        pesos_acumulados - 0.5 * sample_weight
    ) / pesos_acumulados[-1]

    return np.interp(
        quantiles,
        posiciones,
        values,
        left=values[0],
        right=values[-1]
    )


def media_movil_4t(datos, columna):
    """
    Calcula una media móvil estricta de cuatro trimestres.

    Reindexa la serie sobre todos los períodos para impedir
    que una observación saltee un trimestre faltante.
    """

    serie = (
        datos.set_index("IDX_T")[columna]
        .reindex(eje_x)
    )

    return serie.rolling(
        window=4,
        min_periods=4
    ).mean()


def configurar_eje_temporal(ax):
    """Configura el eje X para mostrar los trimestres disponibles."""

    ax.set_xticks(ticks_x)
    ax.set_xticklabels(
        labels_x,
        rotation=45,
        ha="right",
        fontsize=8
    )

    ax.set_xlabel("Trimestre", fontsize=9.5)
    ax.xaxis.grid(False)
    ax.yaxis.grid(
        True,
        linestyle=":",
        color="gray",
        alpha=0.5
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def agregar_referencia_2020(ax):
    """Marca el segundo trimestre de 2020 como referencia temporal."""

    if "2020-T2" in mapa_periodos:
        ax.axvline(
            mapa_periodos["2020-T2"],
            color="#D32F2F",
            linestyle="--",
            linewidth=1.1,
            alpha=0.75,
            label="2020-T2"
        )


# -------------------------------------------------------------------------
# 3. FIGURAS 03A, 03B Y 03C: EVOLUCIÓN TRIMESTRAL DE TASAS
# -------------------------------------------------------------------------

tasas_trimestrales = []

for (ano, trimestre, nom), g in df.groupby(
    ["ANO4", "TRIMESTRE", "AGLOMERADO_NOM"]
):

    g = g[
        np.isfinite(g["PONDERA"])
        & (g["PONDERA"] > 0)
    ]

    poblacion = g["PONDERA"].sum()

    ocupados = g.loc[
        g["ESTADO"] == 1,
        "PONDERA"
    ].sum()

    desocupados = g.loc[
        g["ESTADO"] == 2,
        "PONDERA"
    ].sum()

    pea = ocupados + desocupados

    tasa_actividad = (
        pea / poblacion * 100
        if poblacion > 0 else np.nan
    )

    tasa_empleo = (
        ocupados / poblacion * 100
        if poblacion > 0 else np.nan
    )

    tasa_desocupacion = (
        desocupados / pea * 100
        if pea > 0 else np.nan
    )

    periodo = f"{ano}-T{trimestre}"

    tasas_trimestrales.append({
        "ANO4": ano,
        "TRIMESTRE": trimestre,
        "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo],
        "AGLOMERADO_NOM": nom,
        "Tasa_Actividad": tasa_actividad,
        "Tasa_Empleo": tasa_empleo,
        "Tasa_Desocupacion": tasa_desocupacion
    })

df_tasas = pd.DataFrame(tasas_trimestrales)

configs_tasas = [
    (
        "Tasa_Actividad",
        "Evolución trimestral de la Tasa de Actividad",
        "Tasa de Actividad (%)",
        "o",
        "03a_tasa_actividad_trimestral.png"
    ),
    (
        "Tasa_Empleo",
        "Evolución trimestral de la Tasa de Empleo",
        "Tasa de Empleo (%)",
        "s",
        "03b_tasa_empleo_trimestral.png"
    ),
    (
        "Tasa_Desocupacion",
        "Evolución trimestral de la Tasa de Desocupación",
        "Tasa de Desocupación (%)",
        "^",
        "03c_tasa_desocupacion_trimestral.png"
    )
]

for col, titulo, ylabel, marker, archivo in configs_tasas:

    fig, ax = plt.subplots(figsize=(11.5, 5))

    for nom in ["CABA", "Gran Buenos Aires"]:

        sub = (
            df_tasas[
                df_tasas["AGLOMERADO_NOM"] == nom
            ]
            .sort_values("IDX_T")
        )

        # Valores trimestrales observados.
        ax.plot(
            sub["IDX_T"],
            sub[col],
            marker=marker,
            markersize=3.5,
            linewidth=1.2,
            alpha=0.45,
            color=colores_linea[nom],
            label=f"{nom} - Trimestral"
        )

        # Media móvil estricta de cuatro trimestres.
        mm4 = media_movil_4t(sub, col)

        ax.plot(
            eje_x,
            mm4,
            linewidth=2.5,
            color=colores_linea[nom],
            label=f"{nom} - Media móvil 4T"
        )

    agregar_referencia_2020(ax)

    ax.set_title(
        titulo,
        fontsize=12,
        fontweight="bold",
        loc="left",
        pad=12
    )

    ax.set_ylabel(
        ylabel,
        fontsize=10,
        fontweight="bold"
    )

    configurar_eje_temporal(ax)

    ax.legend(
        loc="best",
        frameon=True,
        fontsize=8.5
    )

    plt.tight_layout()
    plt.savefig(
        os.path.join(DIR_TASAS, archivo),
        dpi=300,
        bbox_inches="tight"
    )
    plt.show()


# -------------------------------------------------------------------------
# 4. FIGURA 04: EVOLUCIÓN TRIMESTRAL DE INGRESOS REALES
# -------------------------------------------------------------------------

ocup_pos = df[
    (df["ESTADO"] == 1)
    & (df["P21_REAL"] > 0)
    & (df["PONDIIO"] > 0)
    & np.isfinite(df["P21_REAL"])
    & np.isfinite(df["PONDIIO"])
].copy()

ing_trimestral = []

for (ano, trimestre, nom), g in ocup_pos.groupby(
    ["ANO4", "TRIMESTRE", "AGLOMERADO_NOM"]
):

    q25, q50, q75 = weighted_quantiles(
        g["P21_REAL"],
        [0.25, 0.50, 0.75],
        g["PONDIIO"]
    )

    periodo = f"{ano}-T{trimestre}"

    ing_trimestral.append({
        "ANO4": ano,
        "TRIMESTRE": trimestre,
        "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo],
        "AGLOMERADO_NOM": nom,
        "Q25": q25,
        "Mediana": q50,
        "Q75": q75
    })

df_ing = pd.DataFrame(ing_trimestral)

fig4, ax4 = plt.subplots(figsize=(11.5, 5.2))

for nom in ["CABA", "Gran Buenos Aires"]:

    sub = (
        df_ing[
            df_ing["AGLOMERADO_NOM"] == nom
        ]
        .sort_values("IDX_T")
    )

    # Serie trimestral de la mediana.
    ax4.plot(
        sub["IDX_T"],
        sub["Mediana"] / 1e6,
        marker="o",
        markersize=3.5,
        linewidth=1.2,
        alpha=0.5,
        color=colores_linea[nom],
        label=f"{nom} - Mediana trimestral"
    )

    # Rango intercuartílico.
    ax4.fill_between(
        sub["IDX_T"],
        sub["Q25"] / 1e6,
        sub["Q75"] / 1e6,
        color=colores_ref[nom],
        alpha=0.18,
        label=f"{nom} - Rango Q1-Q3"
    )

    # Media móvil de cuatro trimestres de la mediana.
    mm4 = media_movil_4t(sub, "Mediana")

    ax4.plot(
        eje_x,
        mm4 / 1e6,
        linewidth=2.5,
        color=colores_linea[nom],
        label=f"{nom} - Media móvil 4T"
    )

agregar_referencia_2020(ax4)

ax4.set_title(
    "Evolución trimestral de la mediana y los cuartiles del ingreso real",
    fontsize=12,
    fontweight="bold",
    loc="left",
    pad=12
)

ax4.set_ylabel(
    "Ingreso real en millones de pesos",
    fontsize=10,
    fontweight="bold"
)

ax4.yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda val, pos: f"${val:,.1f}M".replace(".", ",")
    )
)

configurar_eje_temporal(ax4)

ax4.legend(
    loc="best",
    ncol=2,
    frameon=True,
    fontsize=8
)

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_INGRESOS, "04_evolucion_ingresos_trimestral.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 5. PREPARACIÓN DE VARIABLES PARA ANÁLISIS COMPLEMENTARIOS
# -------------------------------------------------------------------------

# Calificación del puesto a partir de PP04D_COD.
if "PP04D_COD" in ocup_pos.columns:

    codigos_calificacion = (
        ocup_pos["PP04D_COD"]
        .dropna()
        .astype(int)
        .astype(str)
        .str.zfill(5)
        .str[-1]
        .astype(int)
    )

    ocup_pos["CALIF_COD"] = np.nan

    ocup_pos.loc[
        codigos_calificacion.index,
        "CALIF_COD"
    ] = codigos_calificacion

else:
    ocup_pos["CALIF_COD"] = np.nan

# Solo se consideran las cuatro categorías válidas.
ocup_pos.loc[
    ~ocup_pos["CALIF_COD"].isin([1, 2, 3, 4]),
    "CALIF_COD"
] = np.nan

ocup_pos["CALIF_NOM"] = ocup_pos["CALIF_COD"].map({
    1: "Profesional",
    2: "Técnica",
    3: "Operativa",
    4: "No calificada"
})

niv_map_short = {
    1: "Primaria incompleta/\nSin estudios",
    7: "Primaria incompleta/\nSin estudios",
    2: "Primaria completa/\nSecundaria incompleta",
    3: "Primaria completa/\nSecundaria incompleta",
    4: "Secundaria\ncompleta",
    5: "Superior/Universitario\nincompleto",
    6: "Superior/Universitario\ncompleto"
}

ocup_pos["NIVEL_SHORT"] = ocup_pos["NIVEL_ED"].map(
    niv_map_short
)


# -------------------------------------------------------------------------
# 6. FIGURA 05A: INGRESO MEDIANO SEGÚN NIVEL EDUCATIVO
# -------------------------------------------------------------------------

orden_niv = [
    "Primaria incompleta/\nSin estudios",
    "Primaria completa/\nSecundaria incompleta",
    "Secundaria\ncompleta",
    "Superior/Universitario\nincompleto",
    "Superior/Universitario\ncompleto"
]

rows_niv = []

for nom in ["CABA", "Gran Buenos Aires"]:

    sub = ocup_pos[
        (ocup_pos["AGLOMERADO_NOM"] == nom)
        & (ocup_pos["NIVEL_SHORT"].notna())
    ]

    for niv in orden_niv:

        g = sub[sub["NIVEL_SHORT"] == niv]

        med = weighted_quantiles(
            g["P21_REAL"],
            [0.5],
            g["PONDIIO"]
        )[0] / 1e6

        rows_niv.append({
            "Aglomerado": nom,
            "Nivel": niv,
            "Mediana": med
        })

df_niv = pd.DataFrame(rows_niv)

fig5a, ax5_a = plt.subplots(figsize=(8.6, 4.6))

sns.barplot(
    data=df_niv,
    x="Nivel",
    y="Mediana",
    hue="Aglomerado",
    hue_order=["CABA", "Gran Buenos Aires"],
    palette=colores_ref,
    edgecolor="black",
    linewidth=1,
    ax=ax5_a
)

ax5_a.set_title(
    "Ingreso real mediano ponderado según nivel educativo",
    fontsize=11.5,
    fontweight="bold",
    loc="left",
    pad=12
)

ax5_a.set_xlabel("")
ax5_a.set_ylabel(
    "Mediana ingreso real",
    fontsize=9.5,
    fontweight="bold"
)

ax5_a.set_ylim(0, 2.0)

ax5_a.yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda val, pos: f"${val:,.1f}M".replace(".", ",")
    )
)

ax5_a.yaxis.grid(
    True,
    linestyle=":",
    color="gray",
    alpha=0.5
)

ax5_a.xaxis.grid(False)
ax5_a.spines["top"].set_visible(False)
ax5_a.spines["right"].set_visible(False)
ax5_a.tick_params(axis="x", labelsize=8.5)

ax5_a.legend(
    title="",
    loc="upper left",
    frameon=True,
    fontsize=9
)

for p in ax5_a.patches:

    h = p.get_height()

    if np.isfinite(h) and h > 0:

        ax5_a.annotate(
            f"${h:.2f}M".replace(".", ","),
            (p.get_x() + p.get_width() / 2., h),
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold",
            xytext=(0, 3),
            textcoords="offset points"
        )

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_CARACTERISTICAS, "05a_ingreso_nivel_educativo.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 7. FIGURA 05B: INGRESO MEDIANO SEGÚN CALIFICACIÓN DEL PUESTO
# -------------------------------------------------------------------------

orden_cal = [
    "No calificada",
    "Operativa",
    "Técnica",
    "Profesional"
]

rows_cal = []

for nom in ["CABA", "Gran Buenos Aires"]:

    sub = ocup_pos[
        (ocup_pos["AGLOMERADO_NOM"] == nom)
        & (ocup_pos["CALIF_NOM"].notna())
    ]

    for cal in orden_cal:

        g = sub[sub["CALIF_NOM"] == cal]

        med = weighted_quantiles(
            g["P21_REAL"],
            [0.5],
            g["PONDIIO"]
        )[0] / 1e6

        rows_cal.append({
            "Aglomerado": nom,
            "Calificacion": cal,
            "Mediana": med
        })

df_cal = pd.DataFrame(rows_cal)

fig5b, ax5_b = plt.subplots(figsize=(8.6, 4.6))

sns.barplot(
    data=df_cal,
    x="Calificacion",
    y="Mediana",
    hue="Aglomerado",
    hue_order=["CABA", "Gran Buenos Aires"],
    palette=colores_ref,
    edgecolor="black",
    linewidth=1,
    ax=ax5_b
)

ax5_b.set_title(
    "Ingreso real mediano ponderado según calificación del puesto",
    fontsize=11.5,
    fontweight="bold",
    loc="left",
    pad=12
)

ax5_b.set_xlabel("")
ax5_b.set_ylabel(
    "Mediana ingreso real",
    fontsize=9.5,
    fontweight="bold"
)

ax5_b.set_ylim(0, 2.35)

ax5_b.yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda val, pos: f"${val:,.1f}M".replace(".", ",")
    )
)

ax5_b.yaxis.grid(
    True,
    linestyle=":",
    color="gray",
    alpha=0.5
)

ax5_b.xaxis.grid(False)
ax5_b.spines["top"].set_visible(False)
ax5_b.spines["right"].set_visible(False)

ax5_b.legend(
    title="",
    loc="upper left",
    frameon=True,
    fontsize=9
)

for p in ax5_b.patches:

    h = p.get_height()

    if np.isfinite(h) and h > 0:

        ax5_b.annotate(
            f"${h:.2f}M".replace(".", ","),
            (p.get_x() + p.get_width() / 2., h),
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold",
            xytext=(0, 3),
            textcoords="offset points"
        )

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_CARACTERISTICAS, "05b_ingreso_calificacion.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 8. FIGURA 05C: EVOLUCIÓN TRIMESTRAL DEL INGRESO POR SEXO Y BRECHA
# -------------------------------------------------------------------------

ocup_sx = ocup_pos[
    ocup_pos["CH04"].isin([1, 2])
].copy()

ocup_sx["SEXO_NOM"] = ocup_sx["CH04"].map({
    1: "Varones",
    2: "Mujeres"
})

rows_sx = []

for (ano, trimestre, aglo, sx), g in ocup_sx.groupby(
    ["ANO4", "TRIMESTRE", "AGLOMERADO_NOM", "SEXO_NOM"]
):

    med = weighted_quantiles(
        g["P21_REAL"],
        [0.5],
        g["PONDIIO"]
    )[0]

    periodo = f"{ano}-T{trimestre}"

    rows_sx.append({
        "ANO4": ano,
        "TRIMESTRE": trimestre,
        "PERIODO": periodo,
        "IDX_T": mapa_periodos[periodo],
        "Aglomerado": aglo,
        "Sexo": sx,
        "Mediana": med
    })

df_sx = pd.DataFrame(rows_sx)

piv_sx = df_sx.pivot_table(
    index=["IDX_T", "PERIODO", "ANO4", "TRIMESTRE", "Aglomerado"],
    columns="Sexo",
    values="Mediana"
).reset_index()

# La brecha se calcula cuando existen ambas medianas.
piv_sx["Brecha_%"] = np.where(
    piv_sx["Varones"] > 0,
    (
        (piv_sx["Varones"] - piv_sx["Mujeres"])
        / piv_sx["Varones"]
    ) * 100,
    np.nan
)

fig5c, axes_sx = plt.subplots(
    1,
    2,
    figsize=(13.5, 5.5),
    sharey=True
)

for i, aglo in enumerate(["CABA", "Gran Buenos Aires"]):

    sub = (
        piv_sx[
            piv_sx["Aglomerado"] == aglo
        ]
        .sort_values("IDX_T")
    )

    ax = axes_sx[i]

    # Medianas trimestrales de varones y mujeres.
    l1 = ax.plot(
        sub["IDX_T"],
        sub["Varones"] / 1e6,
        marker="o",
        markersize=3,
        linewidth=1.2,
        alpha=0.45,
        color="#0077ff",
        label="Varones - Trimestral"
    )

    l2 = ax.plot(
        sub["IDX_T"],
        sub["Mujeres"] / 1e6,
        marker="s",
        markersize=3,
        linewidth=1.2,
        alpha=0.45,
        color="#9FA300",
        label="Mujeres - Trimestral"
    )

    # Medias móviles estrictas de cuatro trimestres.
    mm4_varones = media_movil_4t(sub, "Varones")
    mm4_mujeres = media_movil_4t(sub, "Mujeres")

    l3 = ax.plot(
        eje_x,
        mm4_varones / 1e6,
        linewidth=2.3,
        color="#0077ff",
        label="Varones - Media móvil 4T"
    )

    l4 = ax.plot(
        eje_x,
        mm4_mujeres / 1e6,
        linewidth=2.3,
        color="#9FA300",
        label="Mujeres - Media móvil 4T"
    )

    ax.set_title(
        aglo,
        fontsize=11.5,
        fontweight="bold",
        loc="left",
        pad=10
    )

    configurar_eje_temporal(ax)

    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(
            lambda val, pos: f"${val:,.1f}M".replace(".", ",")
        )
    )

    if i == 0:
        ax.set_ylabel(
            "Mediana del ingreso real",
            fontsize=9.5,
            fontweight="bold"
        )

    # Eje secundario para la brecha salarial.
    ax_b = ax.twinx()

    l5 = ax_b.plot(
        sub["IDX_T"],
        sub["Brecha_%"],
        marker="d",
        markersize=3,
        linewidth=1.3,
        linestyle="--",
        color="#D32F2F",
        alpha=0.8,
        label="Brecha salarial trimestral"
    )

    mm4_brecha = media_movil_4t(sub, "Brecha_%")

    l6 = ax_b.plot(
        eje_x,
        mm4_brecha,
        linewidth=2,
        linestyle=":",
        color="#D32F2F",
        label="Brecha - Media móvil 4T"
    )

    ax_b.set_ylabel(
        "Brecha salarial (%)",
        fontsize=9.5,
        fontweight="bold",
        color="#D32F2F"
    )

    ax_b.tick_params(
        axis="y",
        labelcolor="#D32F2F",
        labelsize=8
    )

    ax_b.grid(False)
    ax_b.spines["top"].set_visible(False)

    agregar_referencia_2020(ax)

    if i == 0:

        lineas = l1 + l2 + l3 + l4 + l5 + l6
        etiquetas = [
            linea.get_label()
            for linea in lineas
        ]

        ax.legend(
            lineas,
            etiquetas,
            loc="upper left",
            frameon=True,
            fontsize=7.5
        )

plt.suptitle(
    "Evolución trimestral del ingreso real y la brecha salarial por sexo",
    fontsize=12.5,
    fontweight="bold",
    y=1.02
)

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_CARACTERISTICAS, "05c_evolucion_sexo_trimestral.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 9. FIGURA 05D: BOXPLOT DE INGRESO REAL SEGÚN GRUPO ETARIO
# -------------------------------------------------------------------------

# Se excluyen menores de 15 años.
# Los intervalos quedan definidos como:
# 15-29, 30-49 y 50 años o más.

bins_edad = [14, 29, 49, np.inf]

labels_ed = [
    "15 a 29 años\n(Jóvenes)",
    "30 a 49 años\n(Adultos)",
    "50 años y más\n(Mayores)"
]

ocup_pos["GRUPO_EDAD"] = pd.cut(
    ocup_pos["CH06"],
    bins=bins_edad,
    labels=labels_ed,
    right=True
)

# Se crea un único DataFrame filtrado para evitar desalineaciones.
plot_edad = ocup_pos.dropna(
    subset=["GRUPO_EDAD", "P21_REAL", "AGLOMERADO_NOM"]
).copy()

plot_edad["INGRESO_M"] = (
    plot_edad["P21_REAL"] / 1e6
)

fig5d, ax5_d = plt.subplots(figsize=(8.6, 4.6))

sns.boxplot(
    data=plot_edad,
    x="GRUPO_EDAD",
    y="INGRESO_M",
    hue="AGLOMERADO_NOM",
    hue_order=["CABA", "Gran Buenos Aires"],
    palette=colores_ref,
    showfliers=True,
    flierprops={
        "marker": "o",
        "markersize": 2.5,
        "alpha": 0.4
    },
    width=0.55,
    linewidth=1.2,
    ax=ax5_d
)

ax5_d.set_title(
    "Distribución del ingreso real según grupo etario",
    fontsize=11.5,
    fontweight="bold",
    loc="left",
    pad=12
)

ax5_d.set_xlabel("")
ax5_d.set_ylabel(
    "Ingreso real en millones de pesos",
    fontsize=9.5,
    fontweight="bold"
)

ax5_d.yaxis.set_major_formatter(
    ticker.FuncFormatter(
        lambda val, pos: f"${val:,.1f}M".replace(".", ",")
    )
)

ax5_d.yaxis.grid(
    True,
    linestyle=":",
    color="gray",
    alpha=0.5
)

ax5_d.xaxis.grid(False)
ax5_d.spines["top"].set_visible(False)
ax5_d.spines["right"].set_visible(False)

ax5_d.legend(
    title="",
    loc="upper left",
    frameon=True,
    fontsize=9
)

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_EDAD, "05d_boxplot_edad.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 10. FIGURA 06: CORRELOGRAMA DE SPEARMAN
# -------------------------------------------------------------------------

corr_df = ocup_pos[
    [
        "P21_REAL",
        "NIVEL_ED",
        "CALIF_COD",
        "PP3E_TOT",
        "CH06"
    ]
].copy()

# Orden educativo.
corr_df["NIVEL_ORD"] = corr_df["NIVEL_ED"].replace({
    7: 0
})

# Se conservan únicamente las cuatro categorías válidas.
# Profesional = 4, Técnica = 3, Operativa = 2,
# No calificada = 1.
corr_df["CALIF_ORD"] = (
    5 - corr_df["CALIF_COD"]
)

corr_df.loc[
    ~corr_df["CALIF_COD"].isin([1, 2, 3, 4]),
    "CALIF_ORD"
] = np.nan

# Se descartan valores inválidos de horas trabajadas.
corr_df.loc[
    (corr_df["PP3E_TOT"] <= 0)
    | (corr_df["PP3E_TOT"] > 120),
    "PP3E_TOT"
] = np.nan

# Se conservan únicamente niveles educativos válidos.
corr_df.loc[
    ~corr_df["NIVEL_ED"].isin([1, 2, 3, 4, 5, 6, 7]),
    "NIVEL_ORD"
] = np.nan

cols_corr = [
    "P21_REAL",
    "NIVEL_ORD",
    "CALIF_ORD",
    "PP3E_TOT",
    "CH06"
]

corr_plot = corr_df[cols_corr].rename(columns={
    "P21_REAL": "Ingreso Real\n(P21_REAL)",
    "NIVEL_ORD": "Nivel Educativo\n(NIVEL_ED)",
    "CALIF_ORD": "Calificación\n(PP04D_COD)",
    "PP3E_TOT": "Horas Trabajadas\n(PP3E_TOT)",
    "CH06": "Edad\n(CH06)"
}).corr(method="spearman")

fig6, ax6 = plt.subplots(figsize=(6.8, 5.0))

sns.heatmap(
    corr_plot,
    annot=True,
    fmt=".2f",
    cmap="YlGnBu",
    vmin=-0.2,
    vmax=1.0,
    linewidths=1,
    linecolor="white",
    cbar_kws={"shrink": 0.8},
    ax=ax6,
    annot_kws={
        "size": 10,
        "weight": "bold"
    }
)

ax6.set_title(
    "Matriz de correlación de Spearman entre variables clave de los ocupados",
    fontsize=11.5,
    fontweight="bold",
    loc="left",
    pad=12
)

plt.xticks(
    rotation=20,
    ha="right",
    fontsize=9
)

plt.yticks(
    rotation=0,
    fontsize=9
)

plt.tight_layout()
plt.savefig(
    os.path.join(DIR_CORRELACIONES, "06_correlograma.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.show()


# -------------------------------------------------------------------------
# 11. RESUMEN DE EJECUCIÓN
# -------------------------------------------------------------------------

print("\n" + "=" * 65)
print("ANÁLISIS MULTIVARIADO FINALIZADO")
print("=" * 65)

print(f"Período analizado: {etiquetas_x[0]} a {etiquetas_x[-1]}")
print(f"Cantidad de trimestres: {len(tabla_periodos)}")
print("Aglomerados: CABA y Gran Buenos Aires")
print(f"Gráficos generados en: {DIR_BASE}/")

print("=" * 65)
