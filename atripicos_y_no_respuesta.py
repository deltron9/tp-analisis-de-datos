import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

os.makedirs("graficos", exist_ok=True)
sns.set_theme(style="whitegrid")

# -------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN DE DATOS
# -------------------------------------------------------------------------
df = pd.read_csv('datos/eph_microdatos.csv', low_memory=False)
df.columns = df.columns.str.strip().str.upper()

df['AGLOMERADO'] = pd.to_numeric(df['AGLOMERADO'], errors='coerce')
df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({33: 'Gran Buenos Aires', 32: 'CABA'})
df_filtrado = df[df['AGLOMERADO'].isin([33, 32])].copy()

col_ingreso = 'P21_REAL' if 'P21_REAL' in df_filtrado.columns else 'P47T_REAL'
df_filtrado[col_ingreso] = pd.to_numeric(df_filtrado[col_ingreso], errors='coerce')
df_filtrado['ESTADO'] = pd.to_numeric(df_filtrado['ESTADO'], errors='coerce')

# -------------------------------------------------------------------------
# 2. CÁLCULO DE NO RESPUESTA Y ATÍPICOS EN INGRESOS
# -------------------------------------------------------------------------
es_ocupado = (df_filtrado['ESTADO'] == 1)
df_filtrado['no_resp_ingreso'] = es_ocupado & (
    (df_filtrado[col_ingreso] == -9) | (df_filtrado[col_ingreso] == 0) | (df_filtrado[col_ingreso].isna())
)

def detectar_outliers_iqr(serie):
    validos = serie[serie > 0].dropna()
    if len(validos) == 0:
        return pd.Series(False, index=serie.index)
    Q1 = validos.quantile(0.25)
    Q3 = validos.quantile(0.75)
    IQR = Q3 - Q1
    return serie > (Q3 + 1.5 * IQR)

df_filtrado['atipico_ingreso'] = df_filtrado.groupby('AGLOMERADO_NOM')[col_ingreso].transform(detectar_outliers_iqr)

resumen = df_filtrado.groupby('AGLOMERADO_NOM').agg(
    no_resp_ingreso=('no_resp_ingreso', 'sum'),
    atipicos_ingreso=('atipico_ingreso', 'sum')
).reset_index()

# -------------------------------------------------------------------------
# 3. GENERACIÓN Y EXPORTACIÓN DE LA FIGURA 1
# -------------------------------------------------------------------------
resumen_melt = resumen.melt(
    id_vars='AGLOMERADO_NOM',
    var_name='Metrica',
    value_name='Cantidad_Casos'
)

nombres_metricas = {
    'no_resp_ingreso': 'No Respuesta en Ingresos',
    'atipicos_ingreso': 'Valores Atípicos Superiores'
}
resumen_melt['Metrica'] = resumen_melt['Metrica'].map(nombres_metricas)

fig, ax = plt.subplots(figsize=(8.5, 5.2))
colores_ref = {'Gran Buenos Aires': "#0077ff", 'CABA': "#D8DB00"}

sns.barplot(
    data=resumen_melt,
    x='Metrica',
    y='Cantidad_Casos',
    hue='AGLOMERADO_NOM',
    palette=colores_ref,
    edgecolor='black',
    linewidth=1.2,
    width=0.55,
    ax=ax
)

ax.set_axisbelow(True)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax.xaxis.grid(False)

ax.set_ylabel("Cantidad de Registros (Casos)", fontsize=11, fontweight='bold')
ax.set_xlabel("", fontsize=10)
ax.tick_params(axis='x', labelsize=10)
ax.set_ylim(0, resumen_melt['Cantidad_Casos'].max() * 1.15)
ax.legend(title="", loc='upper right', frameon=True, fontsize=10)

for p in ax.patches:
    height = int(p.get_height())
    if height > 0:
        ax.annotate(
            f'{height:,}'.replace(',', '.'),
            (p.get_x() + p.get_width() / 2., height),
            ha='center', va='bottom',
            fontsize=10, fontweight='bold',
            xytext=(0, 5), textcoords='offset points'
        )

plt.title("No respuesta y Valores Atípicos en Ingresos", fontsize=13, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.savefig('graficos/01_no_respuesta_y_atipicos.png', dpi=300, bbox_inches='tight')
plt.show()