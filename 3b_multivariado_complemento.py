import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

os.makedirs("graficos", exist_ok=True)
os.makedirs("tablas", exist_ok=True)
sns.set_theme(style="whitegrid")

ORDEN_AGLO = ['CABA', 'Gran Buenos Aires']
COLORES_AGLO = {'CABA': "#9FA300", 'Gran Buenos Aires': "#0077ff"}
COLORES_GRUPO = ['#0077ff', '#9FA300', '#D32F2F', '#6A1B9A', '#EF6C00']
MIN_N = 30  # mínimo de casos sin ponderar para mostrar una celda de ingresos

# -------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN (ingresos ya deflactados por IPC en P21_REAL)
# -------------------------------------------------------------------------
df = pd.read_csv('datos/eph_microdatos.csv', low_memory=False)
df.columns = df.columns.str.strip().str.upper()

for col in ['AGLOMERADO', 'ANO4', 'TRIMESTRE', 'ESTADO', 'PONDERA', 'PONDIIO',
            'CH04', 'CH06', 'NIVEL_ED', 'P21_REAL', 'PP04B_COD']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df = df[df['AGLOMERADO'].isin([32, 33])].copy()
df['AGLO'] = df['AGLOMERADO'].map({32: 'CABA', 33: 'Gran Buenos Aires'})

# Años con menos de 4 trimestres (se marcan con círculos vacíos en los gráficos)
trim_por_ano = df.groupby('ANO4')['TRIMESTRE'].nunique()
ANOS_PARCIALES = [int(a) for a in trim_por_ano[trim_por_ano < 4].index]
ANOS_COMPLETOS = [int(a) for a in trim_por_ano[trim_por_ano == 4].index]
ANO_INI, ANO_FIN = min(ANOS_COMPLETOS), max(ANOS_COMPLETOS)
NOTA_PARCIALES = (f"Círculos vacíos: año con relevamiento parcial ({', '.join(map(str, ANOS_PARCIALES))}); "
                  "no es estrictamente comparable por estacionalidad.")

# Variables de agrupamiento
df['SEXO'] = df['CH04'].map({1: 'Varones', 2: 'Mujeres'})
ORDEN_SEXO = ['Varones', 'Mujeres']

df['GRUPO_EDAD'] = pd.cut(df['CH06'], bins=[14, 29, 49, 120],
                          labels=['15 a 29 años', '30 a 49 años', '50 años y más'])
ORDEN_EDAD = ['15 a 29 años', '30 a 49 años', '50 años y más']

niv_map = {
    1: 'Hasta primaria incompleta', 7: 'Hasta primaria incompleta',
    2: 'Primaria completa / Sec. incompleta', 3: 'Primaria completa / Sec. incompleta',
    4: 'Secundaria completa',
    5: 'Superior / Univ. incompleto',
    6: 'Superior / Univ. completo'
}
df['NIVEL'] = df['NIVEL_ED'].map(niv_map)
ORDEN_NIVEL = ['Hasta primaria incompleta', 'Primaria completa / Sec. incompleta',
               'Secundaria completa', 'Superior / Univ. incompleto', 'Superior / Univ. completo']

# Rama de actividad: PP04B_COD es la clase CAES-Mercosur 1.0 (4 dígitos);
# los 2 primeros dígitos son la división. Se agrupa en sectores amplios.
SECTORES = [
    ('Industria manufacturera', range(10, 34)),
    ('Construcción', [40]),
    ('Comercio', [45, 48]),
    ('Transporte y almacenamiento', range(49, 54)),
    ('Hotelería y gastronomía', [55, 56]),
    ('Información y comunicaciones', range(58, 64)),
    ('Finanzas, seguros e inmobiliarias', [64, 65, 66, 68]),
    ('Servicios profesionales y administrativos', range(69, 83)),
    ('Administración pública', [84]),
    ('Enseñanza', [85]),
    ('Salud y servicios sociales', range(86, 89)),
    ('Arte, recreación y otros servicios', range(90, 97)),
    ('Servicio doméstico', [97, 98]),
    ('Agro, minería y suministros', list(range(1, 10)) + list(range(35, 40))),
]
DIV_A_SECTOR = {d: nombre for nombre, divs in SECTORES for d in divs}


def sector_caes(cod):
    if pd.isna(cod):
        return np.nan
    return DIV_A_SECTOR.get(int(cod) // 100, 'Sin especificar')


df['SECTOR'] = df['PP04B_COD'].apply(sector_caes)

# Ocupados con ingreso válido (para medidas de ingreso, con PONDIIO)
ocup = df[(df['ESTADO'] == 1) & (df['P21_REAL'] > 0)].copy()


# -------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES
# -------------------------------------------------------------------------
def weighted_quantiles(values, quantiles, sample_weight):
    values = np.asarray(values, dtype=float)
    sample_weight = np.asarray(sample_weight, dtype=float)
    sorter = np.argsort(values)
    values, sample_weight = values[sorter], sample_weight[sorter]
    wq = (np.cumsum(sample_weight) - 0.5 * sample_weight) / np.sum(sample_weight)
    return np.interp(quantiles, wq, values)


fmt_millones = ticker.FuncFormatter(lambda v, p: f'${v:,.1f}M'.replace('.', ','))


def estilo(ax):
    ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
    ax.xaxis.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xticks(range(2016, 2027))
    ax.tick_params(axis='x', rotation=45, labelsize=8)


def linea(ax, sub, y, color, label, marker='o', ls='-'):
    """Línea anual; los años parciales se marcan con círculo vacío."""
    ax.plot(sub['ANO4'], sub[y], marker=marker, ms=5, lw=2.1, color=color, ls=ls, label=label)
    p = sub[sub['ANO4'].isin(ANOS_PARCIALES)]
    if len(p):
        ax.plot(p['ANO4'], p[y], marker=marker, ms=5.5, mfc='white', mec=color, mew=1.5, ls='none')


def guardar(fig, archivo):
    fig.text(0.01, -0.02, NOTA_PARCIALES, fontsize=8.2, color='#555555')
    fig.savefig(f'graficos/{archivo}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  guardado: graficos/{archivo}")


# -------------------------------------------------------------------------
# 3. TABLA 1 Y FIGURA 7: MEDIDAS DE TENDENCIA CENTRAL Y POSICIÓN (PONDIIO)
# -------------------------------------------------------------------------
print("=== TABLA 1: INGRESO REAL (media, mediana, Q1, Q3) ===")
filas = []
for (ano, aglo), g in ocup.groupby(['ANO4', 'AGLO']):
    q1, q2, q3 = weighted_quantiles(g['P21_REAL'], [0.25, 0.5, 0.75], g['PONDIIO'])
    filas.append({
        'Año': int(ano), 'Aglomerado': aglo, 'Casos (sin ponderar)': len(g),
        'Media': np.average(g['P21_REAL'], weights=g['PONDIIO']),
        'Q1': q1, 'Mediana': q2, 'Q3': q3,
        'Año parcial': int(ano) in ANOS_PARCIALES
    })
tabla_ing = pd.DataFrame(filas)
tabla_ing['Media/Mediana'] = (tabla_ing['Media'] / tabla_ing['Mediana']).round(2)
for c in ['Media', 'Q1', 'Mediana', 'Q3']:
    tabla_ing[c] = tabla_ing[c].round(0)
tabla_ing.to_csv('tablas/tabla_ingresos_anual.csv', index=False, encoding='utf-8-sig')
print(tabla_ing.to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
for ax, aglo in zip(axes, ORDEN_AGLO):
    sub = tabla_ing[tabla_ing['Aglomerado'] == aglo].sort_values('Año').rename(columns={'Año': 'ANO4'})
    sub = sub.assign(Media_M=sub['Media'] / 1e6, Mediana_M=sub['Mediana'] / 1e6)
    linea(ax, sub, 'Media_M', COLORES_AGLO[aglo], 'Media ponderada', marker='o')
    linea(ax, sub, 'Mediana_M', COLORES_AGLO[aglo], 'Mediana ponderada', marker='s', ls='--')
    ax.set_title(aglo, fontsize=11.5, fontweight='bold', loc='left')
    ax.yaxis.set_major_formatter(fmt_millones)
    estilo(ax)
    ax.legend(loc='upper left', frameon=True, fontsize=9)
axes[0].set_ylabel("Ingreso real (ocupación principal)", fontsize=10, fontweight='bold')
fig.suptitle("Media vs. mediana del ingreso real, ocupados con ingreso válido (PONDIIO)",
             fontsize=12.5, fontweight='bold', y=1.02)
plt.tight_layout()
guardar(fig, '07_media_vs_mediana.png')


# -------------------------------------------------------------------------
# 4. FIGURAS 8A-8C: TASAS DEL MERCADO LABORAL SEGÚN SEXO, EDAD Y NIVEL EDUCATIVO
# -------------------------------------------------------------------------
def tasas_por(base, grupo):
    filas = []
    for (ano, aglo, g), d in base.groupby(['ANO4', 'AGLO', grupo], observed=True):
        pob = d['PONDERA'].sum()
        ocu = d.loc[d['ESTADO'] == 1, 'PONDERA'].sum()
        des = d.loc[d['ESTADO'] == 2, 'PONDERA'].sum()
        pea = ocu + des
        filas.append({
            'ANO4': int(ano), 'AGLO': aglo, grupo: g,
            'Actividad': pea / pob * 100,
            'Empleo': ocu / pob * 100,
            'Desocupación': des / pea * 100 if pea > 0 else np.nan
        })
    return pd.DataFrame(filas)


def graficar_tasas(tasas, grupo, orden, titulo, archivo):
    metricas = [('Actividad', 'Tasa de actividad (%)'),
                ('Empleo', 'Tasa de empleo (%)'),
                ('Desocupación', 'Tasa de desocupación (%)')]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.4), sharex=True)
    for i, aglo in enumerate(ORDEN_AGLO):
        for j, (col, etiqueta) in enumerate(metricas):
            ax = axes[i, j]
            for k, nivel in enumerate(orden):
                sub = tasas[(tasas['AGLO'] == aglo) & (tasas[grupo] == nivel)].sort_values('ANO4')
                if len(sub):
                    linea(ax, sub, col, COLORES_GRUPO[k], nivel)
            ax.set_title(f"{etiqueta} - {aglo}", fontsize=10, fontweight='bold', loc='left')
            estilo(ax)
    axes[0, 0].legend(loc='best', frameon=True, fontsize=8)
    fig.suptitle(titulo, fontsize=12.5, fontweight='bold', y=1.01)
    plt.tight_layout()
    guardar(fig, archivo)


print("\n=== TASAS SEGÚN SEXO, EDAD Y NIVEL EDUCATIVO ===")
# Sexo: población total de cada sexo (mismo criterio que las tasas generales)
t_sexo = tasas_por(df[df['SEXO'].notna()], 'SEXO')
graficar_tasas(t_sexo, 'SEXO', ORDEN_SEXO,
               "Tasas de actividad, empleo y desocupación según sexo (población total)",
               '08a_tasas_sexo.png')
t_sexo.round(2).to_csv('tablas/tasas_por_sexo.csv', index=False, encoding='utf-8-sig')

# Edad: población de 15 años y más dentro de cada grupo
t_edad = tasas_por(df[df['GRUPO_EDAD'].notna()], 'GRUPO_EDAD')
graficar_tasas(t_edad, 'GRUPO_EDAD', ORDEN_EDAD,
               "Tasas de actividad, empleo y desocupación según grupo de edad (15 años y más)",
               '08b_tasas_edad.png')
t_edad.round(2).to_csv('tablas/tasas_por_edad.csv', index=False, encoding='utf-8-sig')

# Nivel educativo: población de 25 años y más (edad en que se completa el ciclo educativo típico)
t_nivel = tasas_por(df[(df['CH06'] >= 25) & df['NIVEL'].notna()], 'NIVEL')
graficar_tasas(t_nivel, 'NIVEL', ORDEN_NIVEL,
               "Tasas de actividad, empleo y desocupación según nivel educativo (25 años y más)",
               '08c_tasas_nivel_educativo.png')
t_nivel.round(2).to_csv('tablas/tasas_por_nivel_educativo.csv', index=False, encoding='utf-8-sig')


# -------------------------------------------------------------------------
# 5. FIGURAS 9A-9B: EVOLUCIÓN DEL INGRESO REAL MEDIANO SEGÚN NIVEL EDUCATIVO Y EDAD
# -------------------------------------------------------------------------
def mediana_anual_por(base, grupo):
    filas = []
    for (ano, aglo, g), d in base.groupby(['ANO4', 'AGLO', grupo], observed=True):
        if len(d) < MIN_N:
            continue
        med = weighted_quantiles(d['P21_REAL'], [0.5], d['PONDIIO'])[0]
        filas.append({'ANO4': int(ano), 'AGLO': aglo, grupo: g, 'Mediana_M': med / 1e6, 'Casos': len(d)})
    return pd.DataFrame(filas)


def graficar_ingreso_grupo(med, grupo, orden, titulo, archivo):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, aglo in zip(axes, ORDEN_AGLO):
        for k, nivel in enumerate(orden):
            sub = med[(med['AGLO'] == aglo) & (med[grupo] == nivel)].sort_values('ANO4')
            if len(sub):
                linea(ax, sub, 'Mediana_M', COLORES_GRUPO[k], nivel)
        ax.set_title(aglo, fontsize=11.5, fontweight='bold', loc='left')
        ax.yaxis.set_major_formatter(fmt_millones)
        estilo(ax)
    axes[0].set_ylabel("Mediana del ingreso real", fontsize=10, fontweight='bold')
    axes[0].legend(loc='upper left', frameon=True, fontsize=8.5)
    fig.suptitle(titulo, fontsize=12.5, fontweight='bold', y=1.02)
    plt.tight_layout()
    guardar(fig, archivo)


print("\n=== EVOLUCIÓN DEL INGRESO MEDIANO ===")
m_nivel = mediana_anual_por(ocup[ocup['NIVEL'].notna()], 'NIVEL')
graficar_ingreso_grupo(m_nivel, 'NIVEL', ORDEN_NIVEL,
                       "Evolución del ingreso real mediano según nivel educativo",
                       '09a_evolucion_ingreso_nivel.png')
m_nivel.round(4).to_csv('tablas/mediana_ingreso_por_nivel.csv', index=False, encoding='utf-8-sig')

m_edad = mediana_anual_por(ocup[ocup['GRUPO_EDAD'].notna()], 'GRUPO_EDAD')
graficar_ingreso_grupo(m_edad, 'GRUPO_EDAD', ORDEN_EDAD,
                       "Evolución del ingreso real mediano según grupo de edad",
                       '09b_evolucion_ingreso_edad.png')
m_edad.round(4).to_csv('tablas/mediana_ingreso_por_edad.csv', index=False, encoding='utf-8-sig')


# -------------------------------------------------------------------------
# 6. RAMA DE ACTIVIDAD (PP04B_COD): TABLA 2 Y FIGURA 10
# -------------------------------------------------------------------------
print("\n=== RAMA DE ACTIVIDAD (PP04B_COD -> sector CAES) ===")
ocu_all = df[(df['ESTADO'] == 1) & df['SECTOR'].notna()].copy()


def participacion(base):
    t = base.groupby(['AGLO', 'SECTOR'])['PONDERA'].sum()
    return (t / t.groupby(level=0).transform('sum') * 100)


p_ini = participacion(ocu_all[ocu_all['ANO4'] == ANO_INI]).unstack(0)
p_fin = participacion(ocu_all[ocu_all['ANO4'] == ANO_FIN]).unstack(0)

ing_sector = []
for (aglo, sec), g in ocup[ocup['SECTOR'].notna()].groupby(['AGLO', 'SECTOR']):
    if len(g) >= MIN_N:
        ing_sector.append({'AGLO': aglo, 'SECTOR': sec,
                           'Mediana': weighted_quantiles(g['P21_REAL'], [0.5], g['PONDIIO'])[0],
                           'Casos': len(g)})
ing_sector = pd.DataFrame(ing_sector)
med_sector = ing_sector.pivot(index='SECTOR', columns='AGLO', values='Mediana')

tabla_sector = pd.DataFrame(index=sorted(set(p_ini.index) | set(p_fin.index)))
for aglo in ORDEN_AGLO:
    tabla_sector[f'% ocupados {aglo} {ANO_INI}'] = p_ini.get(aglo)
    tabla_sector[f'% ocupados {aglo} {ANO_FIN}'] = p_fin.get(aglo)
    tabla_sector[f'Mediana ingreso real {aglo} ({int(df["ANO4"].min())}-{int(df["ANO4"].max())})'] = \
        med_sector.get(aglo)
tabla_sector = tabla_sector.round(1)
tabla_sector.index.name = 'Sector (CAES)'
tabla_sector.to_csv('tablas/tabla_sectores.csv', encoding='utf-8-sig')
print(tabla_sector.to_string())

orden_sector = (med_sector[ORDEN_AGLO].mean(axis=1).sort_values(ascending=True).index.tolist())
fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
for ax, aglo in zip(axes, ORDEN_AGLO):
    vals = med_sector[aglo].reindex(orden_sector) / 1e6
    barras = ax.barh(orden_sector, vals.fillna(0), color=COLORES_AGLO[aglo], edgecolor='black', linewidth=0.9)
    for b, v in zip(barras, vals):
        if pd.notna(v):
            ax.text(v, b.get_y() + b.get_height() / 2, f" ${v:.2f}M".replace('.', ','),
                    va='center', fontsize=8.2, fontweight='bold')
    ax.set_title(aglo, fontsize=11.5, fontweight='bold', loc='left')
    ax.xaxis.set_major_formatter(fmt_millones)
    ax.xaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
    ax.yaxis.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, np.nanmax(med_sector[ORDEN_AGLO].values) / 1e6 * 1.2)
fig.suptitle("Ingreso real mediano según rama de actividad (PP04B_COD), todo el período",
             fontsize=12.5, fontweight='bold', y=1.0)
plt.tight_layout()
fig.savefig('graficos/10_ingreso_rama_actividad.png', dpi=300, bbox_inches='tight')
plt.close(fig)
print("  guardado: graficos/10_ingreso_rama_actividad.png")

print("\nListo. Gráficos en 'graficos/' y tablas CSV en 'tablas/'.")