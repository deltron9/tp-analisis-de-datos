import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter

# Configuraciones de visualización en consola (sin recortar años ni usar notación científica)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.options.display.float_format = '{:,.2f}'.format

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Formateador de moneda para los ejes de los gráficos ($1.200.000)
formato_pesos = FuncFormatter(lambda y, _: f'${int(y):,}'.replace(',', '.'))

# -------------------------------------------------------------------------
# 1. CARGA DE DATOS Y SELECCIÓN DE AGLOMERADOS (33: GBA | 32: CABA)
# -------------------------------------------------------------------------
ruta_csv = 'datos/eph_microdatos.csv'
df = pd.read_csv(ruta_csv)
df.columns = df.columns.str.strip().str.upper()

# Asegurar formato numérico en la variable de ingreso real
df['P21_REAL'] = pd.to_numeric(df['P21_REAL'], errors='coerce')

AGLO_1_COD, AGLO_1_NOM = 33, 'Gran Buenos Aires'
AGLO_2_COD, AGLO_2_NOM = 32, 'CABA'

df = df[df['AGLOMERADO'].isin([AGLO_1_COD, AGLO_2_COD])].copy()
df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({AGLO_1_COD: AGLO_1_NOM, AGLO_2_COD: AGLO_2_NOM})

# -------------------------------------------------------------------------
# 2. EVOLUCIÓN HISTÓRICA DE TASAS DEL MERCADO LABORAL (Con PONDERA)
# -------------------------------------------------------------------------
df_laboral = df[df['ESTADO'].isin([1, 2, 3])].copy()

tasas = df_laboral.groupby(['ANO4', 'AGLOMERADO_NOM']).apply(
    lambda g: pd.Series({
        'poblacion_total': g['PONDERA'].sum(),
        'ocupados': g.loc[g['ESTADO'] == 1, 'PONDERA'].sum(),
        'desocupados': g.loc[g['ESTADO'] == 2, 'PONDERA'].sum()
    })
).reset_index()

tasas['pea'] = tasas['ocupados'] + tasas['desocupados']
tasas['tasa_actividad'] = (tasas['pea'] / tasas['poblacion_total']) * 100
tasas['tasa_empleo'] = (tasas['ocupados'] / tasas['poblacion_total']) * 100
tasas['tasa_desocupacion'] = (tasas['desocupados'] / tasas['pea']) * 100

print("=========================================================================")
print("1. EVOLUCIÓN HISTÓRICA DE TASAS DEL MERCADO LABORAL (2016-2026)")
print("=========================================================================")
print(tasas[['ANO4', 'AGLOMERADO_NOM', 'tasa_actividad', 'tasa_empleo', 'tasa_desocupacion']])

# -------------------------------------------------------------------------
# 3. MEDIDAS DE TENDENCIA CENTRAL Y POSICIÓN EN TÉRMINOS REALES (P21_REAL)
# -------------------------------------------------------------------------
ocupados_ingreso = df[(df['ESTADO'] == 1) & (df['P21_REAL'] > 0)].copy()

def calcular_medidas_posicion(g):
    return pd.Series({
        'Media_Real': np.average(g['P21_REAL'], weights=g['PONDERA']),
        'Q1_Real': g['P21_REAL'].quantile(0.25),
        'Mediana_Q2_Real': g['P21_REAL'].quantile(0.50),
        'Q3_Real': g['P21_REAL'].quantile(0.75)
    })

medidas_ingreso = ocupados_ingreso.groupby(['ANO4', 'AGLOMERADO_NOM', 'CH04']).apply(calcular_medidas_posicion).reset_index()
medidas_ingreso['CH04'] = medidas_ingreso['CH04'].map({1: 'Hombre', 2: 'Mujer'})

print("\n=========================================================================")
print("2. MEDIDAS DE TENDENCIA CENTRAL Y POSICIÓN DEL INGRESO REAL SEGÚN SEXO")
print("=========================================================================")
print(medidas_ingreso)

# -------------------------------------------------------------------------
# 4. EVOLUCIÓN DEL INGRESO REAL POR RANGOS ETARIOS (CH06)
# -------------------------------------------------------------------------
bins = [0, 29, 49, 100]
labels = ['15-29 años', '30-49 años', '50+ años']
ocupados_ingreso['GRUPO_EDAD'] = pd.cut(ocupados_ingreso['CH06'], bins=bins, labels=labels)

ingreso_edad = ocupados_ingreso.groupby(['ANO4', 'AGLOMERADO_NOM', 'GRUPO_EDAD'], observed=False).apply(
    lambda g: np.average(g['P21_REAL'], weights=g['PONDERA']) if len(g) > 0 else np.nan
).reset_index(name='Ingreso_Real_Medio')

print("\n=========================================================================")
print("3. INGRESO REAL MEDIO PONDERADO POR GRUPO ETARIO")
print("=========================================================================")
print(ingreso_edad)

# -------------------------------------------------------------------------
# 5. EVOLUCIÓN DEL INGRESO REAL POR NIVEL EDUCATIVO (NIVEL_ED)
# -------------------------------------------------------------------------
mapa_educacion = {
    1: 'Primario Incompleto',
    2: 'Primario Completo',
    3: 'Secundario Incompleto',
    4: 'Secundario Completo',
    5: 'Superior/Univ. Incompleto',
    6: 'Superior/Univ. Completo',
    7: 'Sin Instrucción'
}
ocupados_ingreso['NIVEL_ED_NOM'] = ocupados_ingreso['NIVEL_ED'].map(mapa_educacion)

ingreso_educacion = ocupados_ingreso.groupby(['ANO4', 'AGLOMERADO_NOM', 'NIVEL_ED_NOM']).apply(
    lambda g: np.average(g['P21_REAL'], weights=g['PONDERA']) if len(g) > 0 else np.nan
).reset_index(name='Ingreso_Real_Medio')

print("\n=========================================================================")
print("4. INGRESO REAL MEDIO PONDERADO POR NIVEL EDUCATIVO")
print("=========================================================================")
print(ingreso_educacion.dropna())

# -------------------------------------------------------------------------
# 6. VISUALIZACIÓN GRÁFICA (EN PESOS CONSTANTES / REALES)
# -------------------------------------------------------------------------
colores_aglo = {'Gran Buenos Aires': '#ff8c00', 'CABA': '#4b0082'}

# FIGURA 1: Tasas del mercado laboral
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

sns.lineplot(data=tasas, x='ANO4', y='tasa_actividad', hue='AGLOMERADO_NOM', palette=colores_aglo, marker='o', linewidth=2.5, ax=axes[0])
axes[0].set_title("Tasa de Actividad (%)", fontweight='bold')
axes[0].set_ylabel("Porcentaje (%)")
axes[0].set_xlabel("Año")

sns.lineplot(data=tasas, x='ANO4', y='tasa_empleo', hue='AGLOMERADO_NOM', palette=colores_aglo, marker='s', linewidth=2.5, ax=axes[1])
axes[1].set_title("Tasa de Empleo (%)", fontweight='bold')
axes[1].set_ylabel("Porcentaje (%)")
axes[1].set_xlabel("Año")

sns.lineplot(data=tasas, x='ANO4', y='tasa_desocupacion', hue='AGLOMERADO_NOM', palette=colores_aglo, marker='^', linewidth=2.5, ax=axes[2])
axes[2].set_title("Tasa de Desocupación (%)", fontweight='bold')
axes[2].set_ylabel("Porcentaje (%)")
axes[2].set_xlabel("Año")

plt.suptitle("Evolución de Indicadores del Mercado Laboral: GBA vs CABA (2016-2026)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

# FIGURA 2: Ingreso Real Medio por Grupo Etario
fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)

for i, aglo in enumerate([AGLO_1_NOM, AGLO_2_NOM]):
    datos_aglo = ingreso_edad[ingreso_edad['AGLOMERADO_NOM'] == aglo]
    sns.lineplot(data=datos_aglo, x='ANO4', y='Ingreso_Real_Medio', hue='GRUPO_EDAD', marker='o', linewidth=2.5, ax=axes[i])
    axes[i].set_title(f"Ingreso Real por Grupo Etario - {aglo}", fontweight='bold')
    axes[i].set_xlabel("Año")
    axes[i].set_ylabel("Ingreso Real (Pesos Constantes)")
    axes[i].yaxis.set_major_formatter(formato_pesos)
    axes[i].legend(title="Grupo Etario", loc='upper right')

plt.suptitle("Evolución del Ingreso Real según Edad (Deflactado por CBT)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

# FIGURA 3: Ingreso Real Medio por Nivel Educativo
fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

niveles_principales = [
    'Primario Completo', 
    'Secundario Incompleto', 
    'Secundario Completo', 
    'Superior/Univ. Incompleto', 
    'Superior/Univ. Completo'
]
datos_edu_plot = ingreso_educacion[ingreso_educacion['NIVEL_ED_NOM'].isin(niveles_principales)]

for i, aglo in enumerate([AGLO_1_NOM, AGLO_2_NOM]):
    datos_aglo = datos_edu_plot[datos_edu_plot['AGLOMERADO_NOM'] == aglo]
    sns.lineplot(
        data=datos_aglo, 
        x='ANO4', 
        y='Ingreso_Real_Medio', 
        hue='NIVEL_ED_NOM', 
        hue_order=niveles_principales,
        marker='o', 
        linewidth=2.2, 
        ax=axes[i]
    )
    axes[i].set_title(f"Ingreso Real por Nivel Educativo - {aglo}", fontweight='bold')
    axes[i].set_xlabel("Año")
    axes[i].set_ylabel("Ingreso Real (Pesos Constantes)")
    axes[i].yaxis.set_major_formatter(formato_pesos)
    axes[i].legend(title="Nivel Educativo", loc='upper right', fontsize=8.5)

plt.suptitle("Evolución del Ingreso Real según Nivel Educativo (Deflactado por CBT)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()