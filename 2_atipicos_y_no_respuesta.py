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