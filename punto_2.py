import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración para mostrar TODAS las filas en la consola (sin recortar años)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# -------------------------------------------------------------------------
# 1. CARGA DE DATOS Y SELECCIÓN DE AGLOMERADOS
# -------------------------------------------------------------------------
ruta_csv = 'datos/eph_microdatos.csv'
df = pd.read_csv(ruta_csv)
df.columns = df.columns.str.strip().str.upper()

# Convertir P21 a flotante por si viene en formato texto
if df['P21'].dtype == object:
    df['P21'] = df['P21'].str.replace(',', '.').astype(float)

AGLO_1_COD, AGLO_1_NOM = 33, 'Gran Buenos Aires'
AGLO_2_COD, AGLO_2_NOM = 8, 'Gran La Plata'

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
# 3. MEDIDAS DE TENDENCIA CENTRAL Y POSICIÓN (Media, Q1, Mediana Q2, Q3)
# -------------------------------------------------------------------------
ocupados_ingreso = df[(df['ESTADO'] == 1) & (df['P21'] > 0)].copy()

def calcular_medidas_posicion(g):
    return pd.Series({
        'Media': np.average(g['P21'], weights=g['PONDERA']),
        'Q1': g['P21'].quantile(0.25),
        'Mediana_Q2': g['P21'].quantile(0.50),
        'Q3': g['P21'].quantile(0.75)
    })

medidas_ingreso = ocupados_ingreso.groupby(['ANO4', 'AGLOMERADO_NOM', 'CH04']).apply(calcular_medidas_posicion).reset_index()
medidas_ingreso['CH04'] = medidas_ingreso['CH04'].map({1: 'Hombre', 2: 'Mujer'})

print("\n=========================================================================")
print("2. MEDIDAS DE TENDENCIA CENTRAL Y POSICIÓN DEL INGRESO SEGÚN SEXO (CH04)")
print("=========================================================================")
print(medidas_ingreso)

# -------------------------------------------------------------------------
# 4. EVOLUCIÓN DEL INGRESO POR RANGOS ETARIOS (CH06)
# -------------------------------------------------------------------------
bins = [0, 29, 49, 100]
labels = ['15-29 años', '30-49 años', '50+ años']
ocupados_ingreso['GRUPO_EDAD'] = pd.cut(ocupados_ingreso['CH06'], bins=bins, labels=labels)

ingreso_edad = ocupados_ingreso.groupby(['ANO4', 'AGLOMERADO_NOM', 'GRUPO_EDAD']).apply(
    lambda g: np.average(g['P21'], weights=g['PONDERA']) if len(g) > 0 else np.nan
).reset_index(name='Ingreso_Medio')

print("\n=========================================================================")
print("3. INGRESO MEDIO PONDERADO POR GRUPO ETARIO")
print("=========================================================================")
print(ingreso_edad)

# -------------------------------------------------------------------------
# 5. VISUALIZACIÓN GRÁFICA
# -------------------------------------------------------------------------
colores = {'Gran Buenos Aires': '#e67e22', 'Gran La Plata': '#4b0082'}

# Figura 1: Tasas del mercado laboral
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

sns.lineplot(data=tasas, x='ANO4', y='tasa_actividad', hue='AGLOMERADO_NOM', palette=colores, marker='o', linewidth=2.5, ax=axes[0])
axes[0].set_title("Tasa de Actividad (%)", fontweight='bold')
axes[0].set_ylabel("Porcentaje (%)")

sns.lineplot(data=tasas, x='ANO4', y='tasa_empleo', hue='AGLOMERADO_NOM', palette=colores, marker='s', linewidth=2.5, ax=axes[1])
axes[1].set_title("Tasa de Empleo (%)", fontweight='bold')

sns.lineplot(data=tasas, x='ANO4', y='tasa_desocupacion', hue='AGLOMERADO_NOM', palette=colores, marker='^', linewidth=2.5, ax=axes[2])
axes[2].set_title("Tasa de Desocupación (%)", fontweight='bold')

plt.suptitle("Evolución de Indicadores del Mercado Laboral (2016-2026)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

# Figura 2: Ingreso Medio por Grupo Etario
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for i, aglo in enumerate([AGLO_1_NOM, AGLO_2_NOM]):
    datos_aglo = ingreso_edad[ingreso_edad['AGLOMERADO_NOM'] == aglo]
    sns.lineplot(data=datos_aglo, x='ANO4', y='Ingreso_Medio', hue='GRUPO_EDAD', marker='o', linewidth=2.5, ax=axes[i])
    axes[i].set_title(f"Ingreso Medio por Grupo Etario - {aglo}", fontweight='bold')
    axes[i].set_xlabel("Año")
    axes[i].set_ylabel("Ingreso Medio ($)")

plt.tight_layout()
plt.show()