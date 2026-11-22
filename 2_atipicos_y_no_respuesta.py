import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.container import BarContainer
import seaborn as sns

os.makedirs("graficos", exist_ok=True)
sns.set_theme(style="whitegrid")

# -------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN DE DATOS
# -------------------------------------------------------------------------
df = pd.read_csv('datos/eph_microdatos.csv', low_memory=False)
df.columns = df.columns.str.strip().str.upper()

df['AGLOMERADO'] = pd.to_numeric(df['AGLOMERADO'], errors='coerce')
df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({32: 'CABA', 33: 'Gran Buenos Aires'})
df_filtrado = df[df['AGLOMERADO'].isin([32, 33])].copy()

col_ingreso = 'P21_REAL' if 'P21_REAL' in df_filtrado.columns else 'P47T_REAL'
df_filtrado[col_ingreso] = pd.to_numeric(df_filtrado[col_ingreso], errors='coerce')
df_filtrado['ESTADO'] = pd.to_numeric(df_filtrado['ESTADO'], errors='coerce')

# Universo: únicamente ocupados (ESTADO == 1)
ocupados = df_filtrado[df_filtrado['ESTADO'] == 1].copy()

orden_aglo = ['CABA', 'Gran Buenos Aires']
colores_ref = {'CABA': "#D8DB00", 'Gran Buenos Aires': "#0077ff"}

# -------------------------------------------------------------------------
# 2. NO RESPUESTA, INGRESO CERO Y ATÍPICOS (SOBRE OCUPADOS)
# -------------------------------------------------------------------------
# No respuesta: código negativo (-9) o dato faltante. Ingreso cero: == 0.
# Se separan porque son fenómenos distintos y solo la no respuesta se imputa.
ocupados['no_resp_ingreso'] = (ocupados[col_ingreso] < 0) | ocupados[col_ingreso].isna()
ocupados['ingreso_cero'] = ocupados[col_ingreso] == 0


def detectar_outliers_iqr(serie):
    """Atípico superior: ingreso > Q3 + 1,5*IQR (cuartiles sobre ingresos > 0)."""
    validos = serie[serie > 0].dropna()
    if len(validos) == 0:
        return pd.Series(False, index=serie.index)
    Q1 = validos.quantile(0.25)
    Q3 = validos.quantile(0.75)
    IQR = Q3 - Q1
    return serie > (Q3 + 1.5 * IQR)


ocupados['atipico_ingreso'] = ocupados.groupby('AGLOMERADO_NOM')[col_ingreso].transform(detectar_outliers_iqr)

resumen = ocupados.groupby('AGLOMERADO_NOM').agg(
    total_ocupados=('ESTADO', 'count'),
    no_resp_casos=('no_resp_ingreso', 'sum'),
    cero_casos=('ingreso_cero', 'sum'),
    atipicos_casos=('atipico_ingreso', 'sum')
)
for k in ['no_resp', 'cero', 'atipicos']:
    resumen[f'{k}_pct'] = resumen[f'{k}_casos'] / resumen['total_ocupados'] * 100
resumen = resumen.loc[orden_aglo].reset_index()

print("=== RESUMEN DE CALIDAD DE DATOS (OCUPADOS) ===")
print(resumen.round(2).to_string(index=False))

# -------------------------------------------------------------------------
# 3. FIGURA 1: BARRAS DE CALIDAD DE DATOS (% Y CASOS SOBRE OCUPADOS)
# -------------------------------------------------------------------------
etiquetas = {
    'no_resp': 'No respuesta',
    'cero': 'Ingreso cero',
    'atipicos': 'Valores atípicos'
}
orden_metricas = list(etiquetas.values())

filas = []
for _, r in resumen.iterrows():
    for k, etq in etiquetas.items():
        filas.append({
            'AGLOMERADO_NOM': r['AGLOMERADO_NOM'],
            'Metrica': etq,
            'Porcentaje': r[f'{k}_pct'],
            'Casos': r[f'{k}_casos']
        })
df_fig1 = pd.DataFrame(filas)

fig1, ax1 = plt.subplots(figsize=(9.4, 5.2))

sns.barplot(
    data=df_fig1,
    x='Metrica',
    y='Porcentaje',
    order=orden_metricas,
    hue='AGLOMERADO_NOM',
    hue_order=orden_aglo,
    palette=colores_ref,
    edgecolor='black',
    linewidth=1.1,
    width=0.6,
    errorbar=None,
    ax=ax1
)

ax1.set_axisbelow(True)
ax1.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax1.xaxis.grid(False)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

ax1.set_ylabel("Porcentaje sobre el total de ocupados", fontsize=10.5, fontweight='bold')
ax1.set_xlabel("")
ax1.set_ylim(0, df_fig1['Porcentaje'].max() * 1.22)

# Etiquetas: porcentaje + casos entre paréntesis (un contenedor por aglomerado)
contenedores = [c for c in ax1.containers if isinstance(c, BarContainer)]
for cont, aglo in zip(contenedores, orden_aglo):
    sub = df_fig1[df_fig1['AGLOMERADO_NOM'] == aglo].set_index('Metrica').loc[orden_metricas]
    for barra, (_, fila) in zip(cont, sub.iterrows()):
        h = barra.get_height()
        if h > 0:
            pct_txt = f"{h:.1f}%".replace('.', ',')
            casos_txt = f"({int(fila['Casos']):,})".replace(',', '.')
            ax1.annotate(
                f"{pct_txt}\n{casos_txt}",
                (barra.get_x() + barra.get_width() / 2., h),
                ha='center', va='bottom',
                fontsize=9.5, fontweight='bold',
                xytext=(0, 4), textcoords='offset points'
            )

# Leyenda con n calculado desde los datos
n_ocup = resumen.set_index('AGLOMERADO_NOM')['total_ocupados']
fmt_n = lambda x: f"{int(x):,}".replace(',', '.')
handles, _ = ax1.get_legend_handles_labels()
ax1.legend(
    handles,
    [f"CABA (n = {fmt_n(n_ocup['CABA'])} ocupados)",
     f"Gran Buenos Aires (n = {fmt_n(n_ocup['Gran Buenos Aires'])} ocupados)"],
    title="", loc='upper right', frameon=True, fontsize=9.5
)

plt.title("Incidencia de no respuesta, ingreso cero y valores atípicos en ingresos (2016 - 2026)",
          fontsize=12, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.savefig('graficos/01_no_respuesta_y_atipicos.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# 4. FIGURA 2: BOXPLOT DE DISTRIBUCIÓN DE INGRESOS REALES (INGRESO > 0)
# -------------------------------------------------------------------------
validos = ocupados[ocupados[col_ingreso] > 0].copy()
validos['INGRESO_MILLONES'] = validos[col_ingreso] / 1e6

data_caba = validos[validos['AGLOMERADO_NOM'] == 'CABA']['INGRESO_MILLONES']
data_gba = validos[validos['AGLOMERADO_NOM'] == 'Gran Buenos Aires']['INGRESO_MILLONES']


def metricas(s):
    """Devuelve mediana, IQR y umbral de atípico superior (Q3 + 1,5*IQR)."""
    q1, q2, q3 = s.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    return q2, iqr, q3 + 1.5 * iqr


m_caba = metricas(data_caba)
m_gba = metricas(data_gba)

fig2, ax2 = plt.subplots(figsize=(8.6, 5.2))

bp = ax2.boxplot(
    [data_caba, data_gba],
    patch_artist=True,
    widths=0.34,
    flierprops=dict(marker='o', markerfacecolor='#666666', markeredgecolor='none', markersize=3.2, alpha=0.4),
    medianprops=dict(color='#D32F2F', linewidth=2.2),
    boxprops=dict(linewidth=1.1, edgecolor='black'),
    whiskerprops=dict(linewidth=1.1, color='black'),
    capprops=dict(linewidth=1.1, color='black')
)

ax2.set_xticks([1, 2])
ax2.set_xticklabels([
    f'CABA\n(n = {len(data_caba):,} válidos)'.replace(',', '.'),
    f'Gran Buenos Aires\n(n = {len(data_gba):,} válidos)'.replace(',', '.')
], fontsize=10, fontweight='bold')

for patch, color in zip(bp['boxes'], [colores_ref['CABA'], colores_ref['Gran Buenos Aires']]):
    patch.set_facecolor(color)
    patch.set_alpha(0.85)

# Límite del eje Y calculado a partir de los umbrales (no fijo)
ax2.set_ylim(0, max(m_caba[2], m_gba[2]) * 1.6)
ax2.set_xlim(0.5, 2.5)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax2.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax2.xaxis.grid(False)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.set_ylabel("Ingreso real en millones de pesos", fontsize=10.5, fontweight='bold')

# Cuadro de métricas calculado desde los datos
fm = lambda x: f"${x:,.2f}M".replace('.', ',')
texto_resumen = (
    "Métricas clave (sin ponderar)\n"
    "──────────────────────────────\n"
    "■ CABA:\n"
    f"   • Mediana (Q2): {fm(m_caba[0])}\n"
    f"   • Rango IQR: {fm(m_caba[1])}\n"
    f"   • Umbral atípico: {fm(m_caba[2])}\n\n"
    "■ Gran Buenos Aires:\n"
    f"   • Mediana (Q2): {fm(m_gba[0])}\n"
    f"   • Rango IQR: {fm(m_gba[1])}\n"
    f"   • Umbral atípico: {fm(m_gba[2])}"
)

ax2.text(
    1.03, 0.52, texto_resumen,
    transform=ax2.transAxes,
    fontsize=9,
    va='center', ha='left',
    color='#1A1A1A',
    bbox=dict(boxstyle='round,pad=0.6', facecolor='#F8F9FA', edgecolor='#CCCCCC', linewidth=1)
)

print("\n=== MÉTRICAS DEL BOXPLOT (millones de pesos reales, sin ponderar) ===")
print(f"CABA: mediana={m_caba[0]:.3f} | IQR={m_caba[1]:.3f} | umbral={m_caba[2]:.3f}")
print(f"GBA:  mediana={m_gba[0]:.3f} | IQR={m_gba[1]:.3f} | umbral={m_gba[2]:.3f}")

plt.title("Distribución univariada del ingreso real de la ocupación principal (2016 - 2026)",
          fontsize=12, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.savefig('graficos/02_distribucion_ingresos_boxplot.png', dpi=300, bbox_inches='tight')
plt.show()