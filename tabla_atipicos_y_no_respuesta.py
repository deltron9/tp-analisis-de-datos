import pandas as pd
import numpy as np

# 1. Carga y preparación
df = pd.read_csv('datos/eph_microdatos.csv', low_memory=False)
df.columns = df.columns.str.strip().str.upper()

for col in ['AGLOMERADO', 'ESTADO', 'PONDERA', 'CH04', 'CH06', 'NIVEL_ED', 'CAT_OCUP']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({33: 'Partidos del GBA', 32: 'CABA'})
df = df[df['AGLOMERADO'].isin([32, 33])].copy()

# 2. Distribución por Sexo (conteo total de registros válidos)
sexo_map = {1: 'Varones', 2: 'Mujeres'}
df['SEXO_NOM'] = df['CH04'].map(sexo_map)
print("=== REGISTROS POR SEXO (MUESTRA TOTAL) ===")
print(pd.crosstab(df['SEXO_NOM'], df['AGLOMERADO_NOM']))

# 3. Nivel Educativo (Población de 18 años o más, ponderado con PONDERA)
# Códigos INDEC NIVEL_ED: 1=Prim. Inc, 2=Prim. Comp, 3=Sec. Inc, 4=Sec. Comp, 5=Sup. Inc, 6=Sup. Comp, 7=Sin instrucción
ed_map = {
    7: 'Sin instrucción / Primaria incompleta',
    1: 'Sin instrucción / Primaria incompleta',
    2: 'Primaria completa / Secundaria incompleta',
    3: 'Primaria completa / Secundaria incompleta',
    4: 'Secundaria completa',
    5: 'Superior / Universitario incompleto',
    6: 'Superior / Universitario completo'
}
adultos = df[(df['CH06'] >= 18) & (df['NIVEL_ED'].isin(ed_map.keys()))].copy()
adultos['ED_GRUPO'] = adultos['NIVEL_ED'].map(ed_map)

ed_tab = (
    adultos.groupby(['AGLOMERADO_NOM', 'ED_GRUPO'])['PONDERA'].sum()
    .groupby(level=0).apply(lambda x: (x / x.sum()) * 100)
    .unstack(0).round(1)
)
print("\n=== NIVEL EDUCATIVO (% POBLACIÓN 18+ PONDERADA) ===")
print(ed_tab)

# 4. Categoría Ocupacional (Ocupados ESTADO == 1, ponderado con PONDERA)
# Códigos INDEC CAT_OCUP: 1=Patrón, 2=Cuenta propia, 3=Obrero o empleado, 4=Trabajador familiar sin remuneración
cat_map = {
    3: 'Obrero o empleado (asalariado)',
    2: 'Trabajador por cuenta propia',
    1: 'Patrón / Empleador',
    4: 'Trabajador familiar sin remuneración'
}
ocupados = df[(df['ESTADO'] == 1) & (df['CAT_OCUP'].isin(cat_map.keys()))].copy()
ocupados['CAT_NOM'] = ocupados['CAT_OCUP'].map(cat_map)

cat_tab = (
    ocupados.groupby(['AGLOMERADO_NOM', 'CAT_NOM'])['PONDERA'].sum()
    .groupby(level=0).apply(lambda x: (x / x.sum()) * 100)
    .unstack(0).round(1)
)
print("\n=== CATEGORÍA OCUPACIONAL (% OCUPADOS PONDERADO) ===")
print(cat_tab)