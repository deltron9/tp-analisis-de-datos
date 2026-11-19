import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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

# Filtramos únicamente el universo de ocupados (ESTADO == 1)
ocupados = df_filtrado[df_filtrado['ESTADO'] == 1].copy()

# -------------------------------------------------------------------------
# 2. CÁLCULO DE NO RESPUESTA Y ATÍPICOS (SOBRE OCUPADOS)
# -------------------------------------------------------------------------
# No respuesta (-9), ingreso cero (<= 0) o NaN
ocupados['no_resp_ingreso'] = (ocupados[col_ingreso] <= 0) | (ocupados[col_ingreso].isna())

def detectar_outliers_iqr(serie):
    validos = serie[serie > 0].dropna()
    if len(validos) == 0:
        return pd.Series(False, index=serie.index)
    Q1 = validos.quantile(0.25)
    Q3 = validos.quantile(0.75)
    IQR = Q3 - Q1
    return serie > (Q3 + 1.5 * IQR)

ocupados['atipico_ingreso'] = ocupados.groupby('AGLOMERADO_NOM')[col_ingreso].transform(detectar_outliers_iqr)

# Resumen con conteos y porcentajes sobre el total de ocupados
resumen = ocupados.groupby('AGLOMERADO_NOM').agg(
    total_ocupados=('ESTADO', 'count'),
    no_resp_casos=('no_resp_ingreso', 'sum'),
    no_resp_pct=('no_resp_ingreso', lambda x: x.mean() * 100),
    atipicos_casos=('atipico_ingreso', 'sum'),
    atipicos_pct=('atipico_ingreso', lambda x: x.mean() * 100)
).reset_index()

colores_ref = {'CABA': "#D8DB00", 'Gran Buenos Aires': "#0077ff"}
orden_aglo = ['CABA', 'Gran Buenos Aires']

# -------------------------------------------------------------------------
# 3. FIGURA 1: BARRAS DE CALIDAD DE DATOS (% Y CASOS SOBRE OCUPADOS)
# -------------------------------------------------------------------------
df_fig1 = pd.DataFrame({
    'AGLOMERADO_NOM': list(resumen['AGLOMERADO_NOM']) * 2,
    'Metrica': ['No respuesta / Ingreso cero'] * len(resumen) +
               ['Valores atípicos superiores'] * len(resumen),
    'Porcentaje': list(resumen['no_resp_pct']) + list(resumen['atipicos_pct']),
    'Casos': list(resumen['no_resp_casos']) + list(resumen['atipicos_casos'])
})

fig1, ax1 = plt.subplots(figsize=(8.2, 5.0))

sns.barplot(
    data=df_fig1,
    x='Metrica',
    y='Porcentaje',
    hue='AGLOMERADO_NOM',
    hue_order=orden_aglo,
    palette=colores_ref,
    edgecolor='black',
    linewidth=1.1,
    width=0.55,
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

casos_ordenados = [
    df_fig1[(df_fig1['Metrica'].str.startswith('No respuesta')) & (df_fig1['AGLOMERADO_NOM'] == 'CABA')]['Casos'].values[0],
    df_fig1[(df_fig1['Metrica'].str.startswith('Valores atípicos')) & (df_fig1['AGLOMERADO_NOM'] == 'CABA')]['Casos'].values[0],
    df_fig1[(df_fig1['Metrica'].str.startswith('No respuesta')) & (df_fig1['AGLOMERADO_NOM'] == 'Gran Buenos Aires')]['Casos'].values[0],
    df_fig1[(df_fig1['Metrica'].str.startswith('Valores atípicos')) & (df_fig1['AGLOMERADO_NOM'] == 'Gran Buenos Aires')]['Casos'].values[0],
]

for p, casos in zip(ax1.patches, casos_ordenados):
    h = p.get_height()
    if h > 0:
        pct_txt = f"{h:.1f}%".replace('.', ',')
        casos_txt = f"({int(casos):,})".replace(',', '.')
        ax1.annotate(
            f"{pct_txt}\n{casos_txt}",
            (p.get_x() + p.get_width() / 2., h),
            ha='center', va='bottom',
            fontsize=9.5, fontweight='bold',
            xytext=(0, 4), textcoords='offset points'
        )

n_caba_tot = int(resumen.loc[resumen['AGLOMERADO_NOM'] == 'CABA', 'total_ocupados'].values[0])
n_gba_tot = int(resumen.loc[resumen['AGLOMERADO_NOM'] == 'Gran Buenos Aires', 'total_ocupados'].values[0])

handles, _ = ax1.get_legend_handles_labels()
ax1.legend(
    handles,
    [f"CABA (n = {n_caba_tot:,} ocupados)".replace(',', '.'),
     f"Gran Buenos Aires (n = {n_gba_tot:,} ocupados)".replace(',', '.')],
    title="", loc='upper right', frameon=True, fontsize=9.5
)

plt.title("Incidencia de no respuesta y valores atípicos en ingresos (2016 - 2026)",
          fontsize=12, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.savefig('graficos/01_no_respuesta_y_atipicos.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# 4. FIGURA 2: BOXPLOT DE DISTRIBUCIÓN DE INGRESOS REALES (P21_REAL > 0)
# -------------------------------------------------------------------------
validos = ocupados[ocupados[col_ingreso] > 0].copy()
validos['INGRESO_MILLONES'] = validos[col_ingreso] / 1e6

data_caba = validos[validos['AGLOMERADO_NOM'] == 'CABA']['INGRESO_MILLONES']
data_gba = validos[validos['AGLOMERADO_NOM'] == 'Gran Buenos Aires']['INGRESO_MILLONES']

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

ax2.set_xticklabels([
    f'CABA\n(n = {len(data_caba):,} válidos)'.replace(',', '.'),
    f'Gran Buenos Aires\n(n = {len(data_gba):,} válidos)'.replace(',', '.')
], fontsize=10, fontweight='bold')

for patch, color in zip(bp['boxes'], [colores_ref['CABA'], colores_ref['Gran Buenos Aires']]):
    patch.set_facecolor(color)
    patch.set_alpha(0.85)

ax2.set_ylim(0, 6.2)
ax2.set_xlim(0.5, 2.5)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax2.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax2.xaxis.grid(False)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.set_ylabel("Ingreso real en millones de pesos (2026-T2)", fontsize=10.5, fontweight='bold')

# Cálculo dinámico de métricas clave
q1_caba, q2_caba, q3_caba = data_caba.quantile([0.25, 0.50, 0.75])
iqr_caba = q3_caba - q1_caba
umb_caba = q3_caba + 1.5 * iqr_caba

q1_gba, q2_gba, q3_gba = data_gba.quantile([0.25, 0.50, 0.75])
iqr_gba = q3_gba - q1_gba
umb_gba = q3_gba + 1.5 * iqr_gba

texto_resumen = (
    "Métricas clave (sin ponderar)\n"
    "──────────────────────────────\n"
    "■ CABA:\n"
    f"   • Mediana (Q2): ${q2_caba:.2f}M\n".replace('.', ',') +
    f"   • Rango IQR: ${iqr_caba:.2f}M\n".replace('.', ',') +
    f"   • Umbral atípico: ${umb_caba:.2f}M\n\n".replace('.', ',') +
    "■ Gran Buenos Aires:\n"
    f"   • Mediana (Q2): ${q2_gba:.2f}M\n".replace('.', ',') +
    f"   • Rango IQR: ${iqr_gba:.2f}M\n".replace('.', ',') +
    f"   • Umbral atípico: ${umb_gba:.2f}M".replace('.', ',')
)

ax2.text(
    1.03, 0.52, texto_resumen,
    transform=ax2.transAxes,
    fontsize=9,
    va='center', ha='left',
    color='#1A1A1A',
    bbox=dict(boxstyle='round,pad=0.6', facecolor='#F8F9FA', edgecolor='#CCCCCC', linewidth=1)
)

plt.title("Distribución univariada del ingreso real de la ocupación principal (2016 - 2026)",
          fontsize=12, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.savefig('graficos/02_distribucion_ingresos_boxplot.png', dpi=300, bbox_inches='tight')
plt.show()