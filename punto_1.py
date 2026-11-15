import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

# -------------------------------------------------------------------------
# 1. CARGA Y LIMPIEZA DE DATOS
# -------------------------------------------------------------------------
ruta_csv = 'datos/eph_microdatos.csv'
df = pd.read_csv(ruta_csv)
df.columns = df.columns.str.strip().str.upper()

# Asegurar que AGLOMERADO sea numérico entero
df['AGLOMERADO'] = pd.to_numeric(df['AGLOMERADO'], errors='coerce')

# -------------------------------------------------------------------------
# 2. DEFINIR AGLOMERADOS (33: Partidos del GBA | 32: CABA)
# -------------------------------------------------------------------------
AGLO_1_COD, AGLO_1_NOM = 33, 'Gran Buenos Aires'
AGLO_2_COD, AGLO_2_NOM = 32, 'CABA'

df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({AGLO_1_COD: AGLO_1_NOM, AGLO_2_COD: AGLO_2_NOM})
df_filtrado = df[df['AGLOMERADO'].isin([AGLO_1_COD, AGLO_2_COD])].copy()

print("=== CANTIDAD DE REGISTROS POR AGLOMERADO EN EL CSV ===")
print(df_filtrado['AGLOMERADO_NOM'].value_counts(dropna=False))

# -------------------------------------------------------------------------
# 3. ASIGNACIÓN DE VARIABLE DE INGRESO (P47T_REAL / P47T / P21)
# -------------------------------------------------------------------------
if 'P47T_REAL' in df_filtrado.columns:
    col_ingreso = 'P47T_REAL'
elif 'P47T' in df_filtrado.columns:
    df_filtrado['P47T_REAL'] = df_filtrado['P47T']
    col_ingreso = 'P47T_REAL'
elif 'P21' in df_filtrado.columns:
    if df_filtrado['P21'].dtype == object:
        df_filtrado['P21'] = df_filtrado['P21'].str.replace(',', '.').astype(float)
    df_filtrado['P47T_REAL'] = df_filtrado['P21']
    col_ingreso = 'P47T_REAL'
else:
    raise KeyError("No se encontró variable de ingreso válida.")

# -------------------------------------------------------------------------
# 4. CÁLCULO DE NO RESPUESTA Y ATÍPICOS (IQR)
# -------------------------------------------------------------------------
df_filtrado['no_resp_edad'] = (df_filtrado['CH06'] == -9) | (df_filtrado['CH06'].isna())
df_filtrado['no_resp_ingreso'] = (df_filtrado['P47T_REAL'] == -9) | (df_filtrado['P47T_REAL'] == 0) | (df_filtrado['P47T_REAL'].isna())

def detectar_outliers_iqr(serie):
    validos = serie[serie > 0]
    if len(validos) == 0:
        return pd.Series(False, index=serie.index)
    Q1 = validos.quantile(0.25)
    Q3 = validos.quantile(0.75)
    IQR = Q3 - Q1
    return serie > (Q3 + 1.5 * IQR)

df_filtrado['atipico_ingreso'] = df_filtrado.groupby('AGLOMERADO_NOM')['P47T_REAL'].transform(detectar_outliers_iqr)
df_filtrado['atipico_edad'] = df_filtrado.groupby('AGLOMERADO_NOM')['CH06'].transform(detectar_outliers_iqr)

resumen_univariado = df_filtrado.groupby('AGLOMERADO_NOM').agg(
    no_resp_edad=('no_resp_edad', 'sum'),
    no_resp_ingreso=('no_resp_ingreso', 'sum'),
    atipicos_edad=('atipico_edad', 'sum'),
    atipicos_ingreso=('atipico_ingreso', 'sum')
).reset_index()

print("\n=== RESUMEN UNIVARIADO DE CALIDAD DE DATOS ===")
print(resumen_univariado)

# -------------------------------------------------------------------------
# 5. GRÁFICO AGRUPADO (Estilo Informe de Referencia)
# -------------------------------------------------------------------------
resumen_melt = resumen_univariado.melt(
    id_vars='AGLOMERADO_NOM', 
    var_name='Metrica', 
    value_name='Cantidad_Casos'
)

nombres_metricas = {
    'no_resp_edad': 'No Resp. Edad\n(CH06)',
    'no_resp_ingreso': 'No Resp. Ingreso\n(P47T / P21)',
    'atipicos_edad': 'Atípicos Edad\n(CH06)',
    'atipicos_ingreso': 'Atípicos Ingreso\n(P47T_REAL)'
}
resumen_melt['Metrica'] = resumen_melt['Metrica'].map(nombres_metricas)

orden_categorias = [
    'No Resp. Edad\n(CH06)', 
    'No Resp. Ingreso\n(P47T / P21)', 
    'Atípicos Edad\n(CH06)', 
    'Atípicos Ingreso\n(P47T_REAL)'
]

fig, ax = plt.subplots(figsize=(10, 6))

# Paleta actualizada para GBA (33) y CABA (32)
colores_ref = {'Gran Buenos Aires': '#ff8c00', 'CABA': '#4b0082'}

sns.barplot(
    data=resumen_melt, 
    x='Metrica', 
    y='Cantidad_Casos', 
    hue='AGLOMERADO_NOM', 
    order=orden_categorias,
    palette=colores_ref,
    edgecolor='black',
    linewidth=1.2,
    ax=ax
)

ax.set_axisbelow(True)
ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax.xaxis.grid(False)

ax.set_ylabel("Cantidad de Registros (Casos)", fontsize=11, fontweight='bold')
ax.set_xlabel("", fontsize=10)
ax.tick_params(axis='x', labelsize=9.5)
ax.legend(title="", loc='upper left', frameon=True)

for p in ax.patches:
    height = int(p.get_height())
    if height >= 0:
        ax.annotate(
            f'{height}',
            (p.get_x() + p.get_width() / 2., height),
            ha='center', va='bottom', 
            fontsize=9, fontweight='bold',
            xytext=(0, 4), textcoords='offset points'
        )

plt.title("1.2. No respuesta y Atípicos (GBA vs CABA)", fontsize=14, fontweight='bold', loc='left', pad=15)
plt.tight_layout()
plt.show()