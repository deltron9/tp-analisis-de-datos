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

cols_num = ['AGLOMERADO', 'ANO4', 'TRIMESTRE', 'ESTADO', 'PONDERA', 'PONDIIO', 'CH04', 'CH06', 'NIVEL_ED', 'P21_REAL', 'PP3E_TOT']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

df = df[df['AGLOMERADO'].isin([32, 33])].copy()
df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({32: 'CABA', 33: 'Gran Buenos Aires'})

colores_ref = {'CABA': "#D8DB00", 'Gran Buenos Aires': "#0077ff"}
colores_linea = {'CABA': "#9FA300", 'Gran Buenos Aires': "#0077ff"}

def weighted_quantiles(values, quantiles, sample_weight):
    sorter = np.argsort(values)
    values = np.asarray(values)[sorter]
    sample_weight = np.asarray(sample_weight)[sorter]
    wq = (np.cumsum(sample_weight) - 0.5 * sample_weight) / np.sum(sample_weight)
    return np.interp(quantiles, wq, values)

# -------------------------------------------------------------------------
# 2. FIGURAS 3A, 3B y 3C: EVOLUCIÓN ANUAL DE TASAS POR SEPARADO (CON PONDERA)
# -------------------------------------------------------------------------
tasas_anual = []
for (ano, nom), g in df.groupby(['ANO4', 'AGLOMERADO_NOM']):
    pob = g['PONDERA'].sum()
    ocup = g[g['ESTADO'] == 1]['PONDERA'].sum()
    desoc = g[g['ESTADO'] == 2]['PONDERA'].sum()
    pea = ocup + desoc
    tasas_anual.append({
        'ANO4': int(ano),
        'AGLOMERADO_NOM': nom,
        'Tasa_Actividad': (pea / pob) * 100,
        'Tasa_Empleo': (ocup / pob) * 100,
        'Tasa_Desocupacion': (desoc / pea) * 100
    })
df_tasas = pd.DataFrame(tasas_anual).sort_values('ANO4')

configs_tasas = [
    ('Tasa_Actividad', 'Evolución anual de la Tasa de Actividad en CABA y Gran Buenos Aires',
     'Tasa de Actividad', 'o', (38, 60), '03a_tasa_actividad.png', 'lower right', (2020, 41.3), (2020.4, 41.8)),
    ('Tasa_Empleo', 'Evolución anual de la Tasa de Empleo en CABA y Gran Buenos Aires',
     'Tasa de Empleo', 's', (34, 56), '03b_tasa_empleo.png', 'lower right', (2020, 35.6), (2020.4, 36.2)),
    ('Tasa_Desocupacion', 'Evolución anual de la Tasa de Desocupación en CABA y Gran Buenos Aires',
     'Tasa de Desocupación', '^', (3, 15), '03c_tasa_desocupacion.png', 'upper right', (2020, 13.7), (2020.4, 13.4),)
]

for col, titulo, ylabel, marker, ylims, archivo, loc_leg, xy_pt, xy_txt in configs_tasas:
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for nom in ['CABA', 'Gran Buenos Aires']:
        sub = df_tasas[df_tasas['AGLOMERADO_NOM'] == nom]
        ax.plot(sub['ANO4'], sub[col], marker=marker, markersize=6, linewidth=2.3,
                color=colores_linea[nom], label=nom)
    
    ax.axvline(2020, color='#D32F2F', linestyle='--', linewidth=1.1, alpha=0.75)
    
    ax.set_title(titulo, fontsize=11.5, fontweight='bold', loc='left', pad=12)
    ax.set_ylabel(ylabel, fontsize=10, fontweight='bold')
    ax.set_xlabel("")
    ax.set_ylim(ylims)
    ax.set_xticks(range(2016, 2027))
    ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
    ax.xaxis.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc=loc_leg, frameon=True, fontsize=9.5)
    
    plt.tight_layout()
    plt.savefig(f'graficos/{archivo}', dpi=300, bbox_inches='tight')
    plt.show()

# -------------------------------------------------------------------------
# 3. FIGURA 4: EVOLUCIÓN ANUAL DE MEDIANA Y CUARTILES Q1-Q3 (CON PONDIIO)
# -------------------------------------------------------------------------
ocup_pos = df[(df['ESTADO'] == 1) & (df['P21_REAL'] > 0)].copy()

ing_anual = []
for (ano, nom), g in ocup_pos.groupby(['ANO4', 'AGLOMERADO_NOM']):
    q25, q50, q75 = weighted_quantiles(g['P21_REAL'], [0.25, 0.50, 0.75], g['PONDIIO'])
    ing_anual.append({'ANO4': int(ano), 'AGLOMERADO_NOM': nom, 'Q25': q25, 'Mediana': q50, 'Q75': q75})
df_ing = pd.DataFrame(ing_anual).sort_values('ANO4')

fig4, ax4 = plt.subplots(figsize=(10.2, 4.8))

for nom in ['CABA', 'Gran Buenos Aires']:
    sub = df_ing[df_ing['AGLOMERADO_NOM'] == nom]
    ax4.plot(sub['ANO4'], sub['Mediana'] / 1e6, marker='o', markersize=5.5, linewidth=2.4,
             color=colores_linea[nom], label=f'{nom} - Mediana (Q2)')
    ax4.fill_between(sub['ANO4'], sub['Q25'] / 1e6, sub['Q75'] / 1e6,
                     color=colores_ref[nom], alpha=0.18, label=f'{nom} - Rango Q1 - Q3')

ax4.axvline(2024, color='#555555', linestyle='--', linewidth=1, alpha=0.7)

ax4.set_xticks(range(2016, 2027))
ax4.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax4.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax4.xaxis.grid(False)
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.set_ylabel("Ingreso real en millones de pesos", fontsize=10, fontweight='bold')
ax4.set_ylim(0.25, 2.45)
ax4.legend(loc='upper right', ncol=2, frameon=True, fontsize=8.8)

plt.title("Evolución anual de la mediana y medidas de posición (Q1 - Q3) del ingreso real (2016 - 2026)",
          fontsize=12, fontweight='bold', loc='left', pad=12)
plt.tight_layout()
plt.savefig('graficos/04_evolucion_ingresos.png', dpi=300, bbox_inches='tight')
plt.show()

calif_str = ocup_pos['PP04D_COD'].dropna().astype(int).astype(str).str.zfill(5).str[-1].astype(int)
ocup_pos.loc[calif_str.index, 'CALIF_COD'] = calif_str
ocup_pos['CALIF_NOM'] = ocup_pos['CALIF_COD'].map({1: 'Profesional', 2: 'Técnica', 3: 'Operativa', 4: 'No calificada'})

niv_map_short = {
    1: 'Primaria incompleta/\nSin estudios', 7: 'Primaria incompleta/\nSin estudios',
    2: 'Primaria completa/\nSecundaria incompleta', 3: 'Primaria completa/\nSecundaria incompleta',
    4: 'Secundaria\ncompleta', 5: 'Superior/Universitario\nincompleto', 6: 'Superior/Universitario\ncompleto'
}
ocup_pos['NIVEL_SHORT'] = ocup_pos['NIVEL_ED'].map(niv_map_short)

# -------------------------------------------------------------------------
# FIGURA 5A: INGRESO MEDIANO SEGÚN NIVEL EDUCATIVO
# -------------------------------------------------------------------------
orden_niv = [
    'Primaria incompleta/\nSin estudios',
    'Primaria completa/\nSecundaria incompleta',
    'Secundaria\ncompleta',
    'Superior/Universitario\nincompleto',
    'Superior/Universitario\ncompleto'
]
rows_niv = []
for nom in ['CABA', 'Gran Buenos Aires']:
    sub = ocup_pos[(ocup_pos['AGLOMERADO_NOM'] == nom) & (ocup_pos['NIVEL_SHORT'].notna())]
    for niv in orden_niv:
        g = sub[sub['NIVEL_SHORT'] == niv]
        med = weighted_quantiles(g['P21_REAL'], [0.5], g['PONDIIO'])[0] / 1e6
        rows_niv.append({'Aglomerado': nom, 'Nivel': niv, 'Mediana': med})
df_niv = pd.DataFrame(rows_niv)

fig5a, ax5_a = plt.subplots(figsize=(8.6, 4.6))
sns.barplot(data=df_niv, x='Nivel', y='Mediana', hue='Aglomerado',
            hue_order=['CABA', 'Gran Buenos Aires'], palette=colores_ref,
            edgecolor='black', linewidth=1, ax=ax5_a)
ax5_a.set_title("Ingreso real mediano ponderado según nivel educativo", fontsize=11.5, fontweight='bold', loc='left', pad=12)
ax5_a.set_xlabel("")
ax5_a.set_ylabel("Mediana ingreso real", fontsize=9.5, fontweight='bold')
ax5_a.set_ylim(0, 2.0)
ax5_a.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax5_a.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax5_a.xaxis.grid(False)
ax5_a.spines['top'].set_visible(False)
ax5_a.spines['right'].set_visible(False)
ax5_a.tick_params(axis='x', labelsize=8.5)
ax5_a.legend(title="", loc='upper left', frameon=True, fontsize=9)

for p in ax5_a.patches:
    h = p.get_height()
    if h > 0:
        ax5_a.annotate(f'${h:.2f}M'.replace('.', ','), (p.get_x() + p.get_width()/2., h),
                       ha='center', va='bottom', fontsize=8.2, fontweight='bold', xytext=(0, 3), textcoords='offset points')

plt.tight_layout()
plt.savefig('graficos/05a_ingreso_nivel_educativo.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# FIGURA 5B: INGRESO MEDIANO SEGÚN CALIFICACIÓN DEL PUESTO (PP04D_COD)
# -------------------------------------------------------------------------
orden_cal = ['No calificada', 'Operativa', 'Técnica', 'Profesional']
rows_cal = []
for nom in ['CABA', 'Gran Buenos Aires']:
    sub = ocup_pos[(ocup_pos['AGLOMERADO_NOM'] == nom) & (ocup_pos['CALIF_NOM'].notna())]
    for cal in orden_cal:
        g = sub[sub['CALIF_NOM'] == cal]
        med = weighted_quantiles(g['P21_REAL'], [0.5], g['PONDIIO'])[0] / 1e6
        rows_cal.append({'Aglomerado': nom, 'Calificacion': cal, 'Mediana': med})
df_cal = pd.DataFrame(rows_cal)

fig5b, ax5_b = plt.subplots(figsize=(8.6, 4.6))
sns.barplot(data=df_cal, x='Calificacion', y='Mediana', hue='Aglomerado',
            hue_order=['CABA', 'Gran Buenos Aires'], palette=colores_ref,
            edgecolor='black', linewidth=1, ax=ax5_b)
ax5_b.set_title("Ingreso real mediano ponderado según calificación del puesto", fontsize=11.5, fontweight='bold', loc='left', pad=12)
ax5_b.set_xlabel("")
ax5_b.set_ylabel("Mediana ingreso real", fontsize=9.5, fontweight='bold')
ax5_b.set_ylim(0, 2.35)
ax5_b.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax5_b.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax5_b.xaxis.grid(False)
ax5_b.spines['top'].set_visible(False)
ax5_b.spines['right'].set_visible(False)
ax5_b.legend(title="", loc='upper left', frameon=True, fontsize=9)

for p in ax5_b.patches:
    h = p.get_height()
    if h > 0:
        ax5_b.annotate(f'${h:.2f}M'.replace('.', ','), (p.get_x() + p.get_width()/2., h),
                       ha='center', va='bottom', fontsize=8.2, fontweight='bold', xytext=(0, 3), textcoords='offset points')

plt.tight_layout()
plt.savefig('graficos/05b_ingreso_calificacion.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# FIGURA 5C: EVOLUCIÓN ANUAL DE INGRESO MEDIANO Y BRECHA POR SEXO (CH04)
# -------------------------------------------------------------------------
ocup_sx = ocup_pos[ocup_pos['CH04'].isin([1, 2])].copy()
ocup_sx['SEXO_NOM'] = ocup_sx['CH04'].map({1: 'Varones', 2: 'Mujeres'})

rows_sx = []
for (ano, aglo, sx), g in ocup_sx.groupby(['ANO4', 'AGLOMERADO_NOM', 'SEXO_NOM']):
    med = weighted_quantiles(g['P21_REAL'], [0.5], g['PONDIIO'])[0]
    rows_sx.append({'ANO4': int(ano), 'Aglomerado': aglo, 'Sexo': sx, 'Mediana': med})

df_sx_anual = pd.DataFrame(rows_sx)
piv_sx = df_sx_anual.pivot(index=['ANO4', 'Aglomerado'], columns='Sexo', values='Mediana').reset_index()
piv_sx['Brecha_%'] = ((piv_sx['Varones'] - piv_sx['Mujeres']) / piv_sx['Varones']) * 100

fig5c, axes_sx = plt.subplots(1, 2, figsize=(13.5, 4.8), sharey=True)

for i, aglo in enumerate(['CABA', 'Gran Buenos Aires']):
    sub = piv_sx[piv_sx['Aglomerado'] == aglo].sort_values('ANO4')
    ax = axes_sx[i]
    
    l1 = ax.plot(sub['ANO4'], sub['Varones'] / 1e6, marker='o', markersize=5.5, linewidth=2.3,
                 color='#0077ff', label='Varones (Mediana)')
    l2 = ax.plot(sub['ANO4'], sub['Mujeres'] / 1e6, marker='s', markersize=5.5, linewidth=2.3,
                 color='#9FA300', label='Mujeres (Mediana)')
    
    ax.set_title(f"{aglo}", fontsize=11.5, fontweight='bold', loc='left', pad=10)
    ax.set_xticks(range(2016, 2027))
    ax.tick_params(axis='x', rotation=25, labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
    ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
    ax.xaxis.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if i == 0:
        ax.set_ylabel("Mediana ingreso real", fontsize=9.5, fontweight='bold')
    
    ax_b = ax.twinx()
    l3 = ax_b.plot(sub['ANO4'], sub['Brecha_%'], marker='d', markersize=4.8, linewidth=1.6,
                   linestyle='--', color='#D32F2F', alpha=0.85, label='Brecha salarial')
    ax_b.set_ylim(0, 48)
    ax_b.grid(False)
    ax_b.spines['top'].set_visible(False)
    if i == 1:
        ax_b.set_ylabel("Brecha salarial", fontsize=9.5, fontweight='bold', color='#D32F2F')
    else:
        ax_b.set_yticklabels([])
    
    if i == 0:
        lineas = l1 + l2 + l3
        etiquetas = [l.get_label() for l in lineas]
        ax.legend(lineas, etiquetas, loc='upper right', frameon=True, fontsize=8.5)

plt.suptitle("Evolución de la mediana del ingreso real y brecha salarial por sexo",
             fontsize=12.5, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('graficos/05c_evolucion_sexo.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# FIGURA 5D: BOXPLOT DE INGRESO REAL SEGÚN GRUPO ETARIO (CH06)
# -------------------------------------------------------------------------
bins = [0, 29, 49, 100]
labels_ed = ['15 a 29 años\n(Jóvenes)', '30 a 49 años\n(Adultos)', '+50 años\n(Mayores)']
ocup_pos['GRUPO_EDAD'] = pd.cut(ocup_pos['CH06'], bins=bins, labels=labels_ed)

fig5d, ax5_d = plt.subplots(figsize=(8.6, 4.6))
sns.boxplot(
    data=ocup_pos.dropna(subset=['GRUPO_EDAD']),
    x='GRUPO_EDAD',
    y=ocup_pos['P21_REAL'] / 1e6,
    hue='AGLOMERADO_NOM',
    hue_order=['CABA', 'Gran Buenos Aires'],
    palette=colores_ref,
    showfliers=True,
    flierprops={"marker": "o", "markersize": 2.5, "alpha": 0.4},
    width=0.55,
    linewidth=1.2,
    ax=ax5_d
)

ax5_d.set_title("Distribución del ingreso real según grupo etario", fontsize=11.5, fontweight='bold', loc='left', pad=12)
ax5_d.set_xlabel("")
ax5_d.set_ylabel("Ingreso real", fontsize=9.5, fontweight='bold')
ax5_d.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax5_d.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax5_d.xaxis.grid(False)
ax5_d.spines['top'].set_visible(False)
ax5_d.spines['right'].set_visible(False)
ax5_d.legend(title="", loc='upper left', frameon=True, fontsize=9)
ax5_d.set_ylim(0, 4.5)

plt.tight_layout()
plt.savefig('graficos/05d_boxplot_edad.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# FIGURA 5E: INGRESO MEDIANO SEGÚN RAMA DE ACTIVIDAD ECONÓMICA (PP04B_COD)
# -------------------------------------------------------------------------
# Agrupamiento oficial CAES-Mercosur (primeros 2 dígitos de PP04B_COD)
def mapear_rama_caes(cod):
    if pd.isna(cod):
        return np.nan
    s = str(cod).replace('.0', '').strip().zfill(4)
    d2 = int(s[:2]) if s[:2].isdigit() else 0
    if 10 <= d2 <= 33:
        return 'Industria\nmanufacturera'
    elif 41 <= d2 <= 43:
        return 'Construcción'
    elif 45 <= d2 <= 47:
        return 'Comercio'
    elif 49 <= d2 <= 53:
        return 'Transporte y\nalmacenamiento'
    elif 55 <= d2 <= 56:
        return 'Hotelería y\ngastronomía'
    elif 58 <= d2 <= 66:
        return 'Info., comun. y\nfinanzas'
    elif 68 <= d2 <= 82:
        return 'Serv. prof., inm.\ny admin.'
    elif d2 == 84:
        return 'Administración\npública'
    elif 85 <= d2 <= 88:
        return 'Enseñanza y\nsalud'
    elif 97 <= d2 <= 98:
        return 'Servicio\ndoméstico'
    return np.nan

ocup_pos['RAMA_NOM'] = ocup_pos['PP04B_COD'].apply(mapear_rama_caes)

# Seleccionar las 7 ramas con mayor volumen de ocupados para una comparación limpia
top_ramas = ocup_pos['RAMA_NOM'].value_counts().nlargest(7).index.tolist()
rows_rama = []
for nom in ['CABA', 'Gran Buenos Aires']:
    sub = ocup_pos[(ocup_pos['AGLOMERADO_NOM'] == nom) & (ocup_pos['RAMA_NOM'].isin(top_ramas))]
    for rama in top_ramas:
        g = sub[sub['RAMA_NOM'] == rama]
        if len(g) > 0:
            med = weighted_quantiles(g['P21_REAL'], [0.5], g['PONDIIO'])[0] / 1e6
            rows_rama.append({'Aglomerado': nom, 'Rama': rama, 'Mediana': med})

df_rama = pd.DataFrame(rows_rama)
orden_rama = (
    df_rama[df_rama['Aglomerado'] == 'CABA']
    .sort_values('Mediana', ascending=True)['Rama']
    .tolist()
)

fig5e, ax5_e = plt.subplots(figsize=(9.5, 5.2))
sns.barplot(
    data=df_rama, y='Rama', x='Mediana', hue='Aglomerado',
    order=orden_rama, hue_order=['CABA', 'Gran Buenos Aires'],
    palette=colores_ref, edgecolor='black', linewidth=1, ax=ax5_e
)
ax5_e.set_title("Ingreso real mediano ponderado según rama de actividad económica (PP04B_COD)",
                fontsize=11.5, fontweight='bold', loc='left', pad=12)
ax5_e.set_ylabel("")
ax5_e.set_xlabel("Mediana ingreso real (pesos constantes 2026-T2)", fontsize=9.5, fontweight='bold')
ax5_e.set_xlim(0, 2.35)
ax5_e.xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
ax5_e.xaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
ax5_e.yaxis.grid(False)
ax5_e.spines['top'].set_visible(False)
ax5_e.spines['right'].set_visible(False)
ax5_e.legend(title="", loc='lower right', frameon=True, fontsize=9)

for p in ax5_e.patches:
    w = p.get_width()
    if w > 0:
        ax5_e.annotate(f'${w:.2f}M'.replace('.', ','), (w, p.get_y() + p.get_height()/2.),
                    ha='left', va='center', fontsize=8.2, fontweight='bold', xytext=(4, 0), textcoords='offset points')

fig5e.text(0.01, -0.02, "Fuente: Elaboración propia en base a microdatos EPH - INDEC (2016-T2 a 2026-T2). Ponderado por PONDIIO.",
        fontsize=8, color='#555555')
plt.tight_layout()
plt.savefig('graficos/05e_ingreso_rama.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# TABLAS COMPLEMENTARIAS: TASAS LABORALES DESAGREGADAS Y EVOLUCIÓN HISTÓRICA
# -------------------------------------------------------------------------
os.makedirs("tablas", exist_ok=True)

def calcular_tasas_grupo(df_base, cols_grupo):
    res = []
    for keys, g in df_base.groupby(cols_grupo, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        pob = g['PONDERA'].sum()
        ocup = g[g['ESTADO'] == 1]['PONDERA'].sum()
        desoc = g[g['ESTADO'] == 2]['PONDERA'].sum()
        pea = ocup + desoc
        fila = dict(zip(cols_grupo, keys))
        fila.update({
            'Tasa_Actividad_%': round((pea / pob) * 100, 1) if pob > 0 else np.nan,
            'Tasa_Empleo_%': round((ocup / pob) * 100, 1) if pob > 0 else np.nan,
            'Tasa_Desocupacion_%': round((desoc / pea) * 100, 1) if pea > 0 else np.nan
        })
        res.append(fila)
    return pd.DataFrame(res)

# Preparar dimensiones sociodemográficas sobre la población total
df_dem = df.copy()
df_dem['SEXO_NOM'] = df_dem['CH04'].map({1: 'Varones', 2: 'Mujeres'})
df_dem['GRUPO_EDAD'] = pd.cut(df_dem['CH06'], bins=[13, 29, 49, 100],
                            labels=['14 a 29 años', '30 a 49 años', '+50 años'])
df_dem['NIVEL_SHORT'] = df_dem['NIVEL_ED'].map(niv_map_short).str.replace('\n', ' ')

tasas_sexo = calcular_tasas_grupo(df_dem.dropna(subset=['SEXO_NOM']), ['AGLOMERADO_NOM', 'SEXO_NOM'])
tasas_edad = calcular_tasas_grupo(df_dem.dropna(subset=['GRUPO_EDAD']), ['AGLOMERADO_NOM', 'GRUPO_EDAD'])
tasas_edu = calcular_tasas_grupo(df_dem[df_dem['CH06'] >= 18].dropna(subset=['NIVEL_SHORT']), ['AGLOMERADO_NOM', 'NIVEL_SHORT'])

# Exportar tablas resumen para respaldar la redacción del informe
df_tasas.round(2).to_csv('tablas/evolucion_tasas_anual.csv', index=False)
df_ing.round(2).to_csv('tablas/evolucion_ingresos_cuartiles.csv', index=False)
tasas_sexo.to_csv('tablas/tasas_por_sexo.csv', index=False)
tasas_edad.to_csv('tablas/tasas_por_edad.csv', index=False)
tasas_edu.to_csv('tablas/tasas_por_educacion.csv', index=False)

print("\n=== TASAS LABORALES DESAGREGADAS (PONDERADAS POR PONDERA) ===")
print("\n-- Por Sexo --\n", tasas_sexo.to_string(index=False))
print("\n-- Por Grupo Etario (14+) --\n", tasas_edad.to_string(index=False))
print("\n-- Por Nivel Educativo (18+) --\n", tasas_edu.to_string(index=False))

# -------------------------------------------------------------------------
# 5. FIGURA 6: CORRELOGRAMA DE SPEARMAN
# -------------------------------------------------------------------------
corr_df = ocup_pos[['P21_REAL', 'NIVEL_ED', 'CALIF_COD', 'PP3E_TOT', 'CH06']].copy()
corr_df['NIVEL_ORD'] = corr_df['NIVEL_ED'].replace({7: 0})
corr_df['CALIF_ORD'] = 5 - corr_df['CALIF_COD']
corr_df.loc[(corr_df['PP3E_TOT'] <= 0) | (corr_df['PP3E_TOT'] > 120), 'PP3E_TOT'] = np.nan

cols_corr = ['P21_REAL', 'NIVEL_ORD', 'CALIF_ORD', 'PP3E_TOT', 'CH06']
corr_plot = corr_df[cols_corr].rename(columns={
    'P21_REAL': 'Ingreso Real\n(P21_REAL)',
    'NIVEL_ORD': 'Nivel Educativo\n(NIVEL_ED)',
    'CALIF_ORD': 'Calificación\n(PP04D_COD)',
    'PP3E_TOT': 'Horas Trabajadas\n(PP3E_TOT)',
    'CH06': 'Edad\n(CH06)'
}).corr(method='spearman')

fig6, ax6 = plt.subplots(figsize=(6.8, 5.0))
sns.heatmap(corr_plot, annot=True, fmt=".2f", cmap="YlGnBu", vmin=-0.2, vmax=1.0,
            linewidths=1, linecolor='white', cbar_kws={"shrink": 0.8}, ax=ax6,
            annot_kws={"size": 10, "weight": "bold"})
ax6.set_title("Matriz de correlación de Spearman entre variables clave de los ocupados",
              fontsize=11.5, fontweight='bold', loc='left', pad=12)
plt.xticks(rotation=20, ha='right', fontsize=9)
plt.yticks(rotation=0, fontsize=9)
plt.tight_layout()
plt.savefig('graficos/06_correlograma.png', dpi=300, bbox_inches='tight')
plt.show()