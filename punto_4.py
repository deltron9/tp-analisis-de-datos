import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import statsmodels.formula.api as smf
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, root_mean_squared_error

# Configuraciones generales y estilo unificado con el repositorio
os.makedirs("graficos", exist_ok=True)
sns.set_theme(style="whitegrid")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.options.display.float_format = '{:,.2f}'.format

# -------------------------------------------------------------------------
# 1. CARGA Y HOMOLOGACIÓN DE VARIABLES (Alineado con scripts 1, 2 y 3)
# -------------------------------------------------------------------------
df = pd.read_csv('datos/eph_microdatos.csv', low_memory=False)
df.columns = df.columns.str.strip().str.upper()

cols_num = ['AGLOMERADO', 'ANO4', 'TRIMESTRE', 'ESTADO', 'PONDERA', 'PONDIIO',
            'CH04', 'CH06', 'NIVEL_ED', 'CAT_OCUP', 'P21_REAL', 'PP3E_TOT']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Filtrar CABA (32) y Gran Buenos Aires (33)
df = df[df['AGLOMERADO'].isin([32, 33])].copy()
df['AGLOMERADO_NOM'] = df['AGLOMERADO'].map({32: 'CABA', 33: 'Gran Buenos Aires'})

# Mismos grupos educativos usados en el informe y script 3
ed_map = {
    7: '1. Sin estudios / Prim. inc.',
    1: '1. Sin estudios / Prim. inc.',
    2: '2. Prim. comp. / Sec. inc.',
    3: '2. Prim. comp. / Sec. inc.',
    4: '3. Secundaria completa',
    5: '4. Superior / Univ. inc.',
    6: '5. Superior / Univ. comp.'
}
df['ED_GRUPO'] = df['NIVEL_ED'].map(ed_map)

# Misma categoría ocupacional usada en el informe
cat_map = {
    3: 'Obrero o empleado (asalariado)',
    2: 'Trabajador por cuenta propia',
    1: 'Patrón / Empleador',
    4: 'Trabajador familiar sin remuneración'
}
df['CAT_NOM'] = df['CAT_OCUP'].map(cat_map)
df['SEXO_NOM'] = df['CH04'].map({1: 'Varones', 2: 'Mujeres'})

# Calificación del puesto (último dígito de PP04D_COD, idéntico a script 3)
calif_str = df['PP04D_COD'].dropna().astype(int).astype(str).str.zfill(5).str[-1].astype(int)
df.loc[calif_str.index, 'CALIF_COD'] = calif_str
df['CALIF_NOM'] = df['CALIF_COD'].map({
    1: 'Profesional',
    2: 'Técnica',
    3: 'Operativa',
    4: 'No calificada'
}).fillna('Otra / Sin especificar')

# Rama de actividad (primeros 2 dígitos de PP04B_COD)
if 'PP04B_COD' in df.columns:
    cod_str = df['PP04B_COD'].fillna(0).astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
    df['RAMA_2D'] = cod_str.str[:2]
else:
    df['RAMA_2D'] = '00'

# -------------------------------------------------------------------------
# 2. UNIVERSO DE OCUPADOS (ESTADO == 1) Y DETECCIÓN DE NO RESPUESTA
# -------------------------------------------------------------------------
# Mismo universo exacto que 2_atipicos_y_no_respuesta.py (146.628 ocupados totales)
df_ocupados = df[df['ESTADO'] == 1].copy()

df_ocupados['no_resp_ingreso'] = (df_ocupados['P21_REAL'] <= 0) | (df_ocupados['P21_REAL'].isna())
df_ocupados['HORAS_SEM'] = df_ocupados['PP3E_TOT'].where(
    (df_ocupados['PP3E_TOT'] > 0) & (df_ocupados['PP3E_TOT'] <= 120), np.nan
)

# Conjunto válido para entrenamiento (ocupados con ingreso > 0 y covariables completas)
cond_validos = (
    (~df_ocupados['no_resp_ingreso']) &
    (df_ocupados['P21_REAL'] > 0) &
    (df_ocupados['HORAS_SEM'].notna()) &
    (df_ocupados['CH06'].notna()) &
    (df_ocupados['ED_GRUPO'].notna()) &
    (df_ocupados['CAT_NOM'].notna()) &
    (df_ocupados['SEXO_NOM'].notna()) &
    (df_ocupados['PONDIIO'] > 0)
)
df_validos = df_ocupados[cond_validos].copy()

# Recorte del 0,5% superior extremo solo para estabilizar el ajuste lineal
limite_sup = df_validos['P21_REAL'].quantile(0.995)
df_validos = df_validos[df_validos['P21_REAL'] <= limite_sup].copy()
df_validos['LOG_P21'] = np.log(df_validos['P21_REAL'])

# -------------------------------------------------------------------------
# 3. VALIDACIÓN CRUZADA (TRAIN 80% / TEST 20%) Y MODELOS OLS / WLS (PONDIIO)
# -------------------------------------------------------------------------
formula = (
    "LOG_P21 ~ CH06 + I(CH06**2) + HORAS_SEM + "
    "C(SEXO_NOM) + C(ED_GRUPO) + C(AGLOMERADO_NOM) + "
    "C(CAT_NOM) + C(CALIF_NOM) + C(RAMA_2D)"
)

train_split, test_split = train_test_split(df_validos, test_size=0.20, random_state=42)
for col_cat in ['RAMA_2D', 'CALIF_NOM', 'ED_GRUPO', 'CAT_NOM']:
    test_split = test_split[test_split[col_cat].isin(train_split[col_cat].unique())]

modelo_val = smf.ols(formula=formula, data=train_split).fit()
pred_test = modelo_val.predict(test_split)
r2_test = r2_score(test_split['LOG_P21'], pred_test)
rmse_test = root_mean_squared_error(test_split['LOG_P21'], pred_test)

# Modelos finales: OLS y WLS ponderado con PONDIIO (ponderador oficial de P21)
modelo_ols = smf.ols(formula=formula, data=df_validos).fit()
modelo_wls = smf.wls(formula=formula, data=df_validos, weights=df_validos['PONDIIO']).fit()

print("=========================================================================")
print("1. EVALUACIÓN Y ROBUSTEZ DEL MODELO DE REGRESIÓN (OLS vs WLS - PONDIIO)")
print("=========================================================================")
print(f"Observaciones válidas de entrenamiento: {int(modelo_ols.nobs):,}")
print(f"R² OLS (Muestra completa):              {modelo_ols.rsquared:.4f}  ({'CUMPLE (> 0.30)' if modelo_ols.rsquared > 0.30 else 'NO CUMPLE'})")
print(f"R² Ajustado OLS:                        {modelo_ols.rsquared_adj:.4f}")
print(f"R² Test (Validación 20% out-of-sample): {r2_test:.4f}  (RMSE Log: {rmse_test:.4f})")
print(f"R² WLS (Ponderado por PONDIIO):         {modelo_wls.rsquared:.4f}")
print(f"Estadístico F (OLS):                    {modelo_ols.fvalue:.2f} (p-valor = {modelo_ols.f_pvalue:.2e})")
print("-------------------------------------------------------------------------")

tabla_coef = pd.DataFrame({
    'Coef_OLS': modelo_ols.params,
    'Coef_WLS': modelo_wls.params,
    'Error_Std': modelo_ols.bse,
    't_stat': modelo_ols.tvalues,
    'p_valor': modelo_ols.pvalues
})
print(tabla_coef[~tabla_coef.index.str.contains('RAMA_2D')])

# -------------------------------------------------------------------------
# 4. IMPUTACIÓN DE NO RESPUESTA (EXCLUYENDO TRABAJADOR FAMILIAR SIN REM.)
# -------------------------------------------------------------------------
cond_imputar = (
    (df_ocupados['no_resp_ingreso']) &
    (df_ocupados['CAT_OCUP'].isin([1, 2, 3])) &
    (df_ocupados['HORAS_SEM'].notna()) &
    (df_ocupados['CH06'].notna()) &
    (df_ocupados['ED_GRUPO'].isin(df_validos['ED_GRUPO'].unique())) &
    (df_ocupados['CAT_NOM'].isin(df_validos['CAT_NOM'].unique())) &
    (df_ocupados['SEXO_NOM'].isin(df_validos['SEXO_NOM'].unique())) &
    (df_ocupados['AGLOMERADO_NOM'].isin(df_validos['AGLOMERADO_NOM'].unique())) &
    (df_ocupados['RAMA_2D'].isin(df_validos['RAMA_2D'].unique())) &
    (df_ocupados['CALIF_NOM'].isin(df_validos['CALIF_NOM'].unique()))
)

df_imputar = df_ocupados[cond_imputar].copy()

# Re-transformación insesgada (Factor de Duan)
pred_log = modelo_ols.predict(df_imputar)
factor_duan = np.mean(np.exp(modelo_ols.resid))
df_imputar['P21_IMPUTADO'] = np.exp(pred_log) * factor_duan

df_ocupados['P21_CONSOLIDADO'] = df_ocupados['P21_REAL'].where(~df_ocupados['no_resp_ingreso'], np.nan)
df_ocupados.loc[df_imputar.index, 'P21_CONSOLIDADO'] = df_imputar['P21_IMPUTADO']

print("\n=========================================================================")
print("2. COBERTURA DE IMPUTACIÓN SOBRE EL UNIVERSO TOTAL DE OCUPADOS")
print("=========================================================================")
for aglo in ['CABA', 'Gran Buenos Aires']:
    sub_o = df_ocupados[df_ocupados['AGLOMERADO_NOM'] == aglo]
    sub_i = df_imputar[df_imputar['AGLOMERADO_NOM'] == aglo]
    tot = len(sub_o)
    sin_resp = sub_o['no_resp_ingreso'].sum()
    imp = len(sub_i)
    print(f"{aglo}: {tot:,} ocupados | {sin_resp:,} sin ingreso positivo | {imp:,} imputados ({(imp/sin_resp)*100:.1f}%)")

# -------------------------------------------------------------------------
# 5. COMPARACIÓN PONDERADA POR PONDIIO (ANTES VS. DESPUÉS DE IMPUTAR)
# -------------------------------------------------------------------------
def weighted_quantiles(values, quantiles, sample_weight):
    sorter = np.argsort(values)
    values = np.asarray(values)[sorter]
    sample_weight = np.asarray(sample_weight)[sorter]
    wq = (np.cumsum(sample_weight) - 0.5 * sample_weight) / np.sum(sample_weight)
    return np.interp(quantiles, wq, values)

def resumen_pondiio(g, col_val):
    # Para datos originales usamos PONDIIO; para imputados sin PONDIIO (>0), respaldamos con PONDERA
    peso = g['PONDIIO'].where(g['PONDIIO'] > 0, g['PONDERA'])
    mask = (g[col_val] > 0) & (peso > 0)
    g_val = g[mask]
    w_val = peso[mask]
    media = np.average(g_val[col_val], weights=w_val)
    q1, q2, q3 = weighted_quantiles(g_val[col_val], [0.25, 0.50, 0.75], w_val)
    return pd.Series({'Media_Pond': media, 'Q1': q1, 'Mediana_Q2': q2, 'Q3': q3})

comp_antes = df_ocupados.groupby('AGLOMERADO_NOM').apply(resumen_pondiio, col_val='P21_REAL', include_groups=False)
comp_despues = df_ocupados.groupby('AGLOMERADO_NOM').apply(resumen_pondiio, col_val='P21_CONSOLIDADO', include_groups=False)

comparativa = pd.concat({
    '1_Sin_Imputar (Declarados)': comp_antes.loc[['CABA', 'Gran Buenos Aires']],
    '2_Con_Imputacion (Consolidado)': comp_despues.loc[['CABA', 'Gran Buenos Aires']]
}, axis=1)

print("\n=========================================================================")
print("3. IMPACTO DISTRIBUCIONAL PONDERADO (PONDIIO) POR AGLOMERADO")
print("=========================================================================")
print(comparativa.T)

# -------------------------------------------------------------------------
# 6. FIGURA 7: VISUALIZACIÓN Y EXPORTACIÓN (Misma estética del repositorio)
# -------------------------------------------------------------------------
colores_ref = {'CABA': "#D8DB00", 'Gran Buenos Aires': "#0077ff"}
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))

# Panel A: Ajuste Observado vs Predicho
muestra = df_validos.sample(min(5000, len(df_validos)), random_state=42)
axes[0].scatter(
    muestra['LOG_P21'],
    modelo_ols.predict(muestra),
    alpha=0.22,
    s=14,
    color='#0077ff'
)
lims = [muestra['LOG_P21'].min(), muestra['LOG_P21'].max()]
axes[0].plot(lims, lims, color='#D32F2F', linestyle='--', linewidth=2, label='Ajuste Ideal (y = x)')
axes[0].set_title(f"Bondad de Ajuste OLS (R² = {modelo_ols.rsquared:.3f} | Test = {r2_test:.3f})",
                fontsize=11, fontweight='bold', loc='left', pad=10)
axes[0].set_xlabel("Log(P21_REAL Observado)", fontsize=9.5, fontweight='bold')
axes[0].set_ylabel("Log(P21_REAL Predicho)", fontsize=9.5, fontweight='bold')
axes[0].yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
axes[0].xaxis.grid(False)
axes[0].spines['top'].set_visible(False)
axes[0].spines['right'].set_visible(False)
axes[0].legend(frameon=True, fontsize=9)

# Panel B: Densidad de Ingresos Declarados vs Imputados
sns.kdeplot(
    df_ocupados[~df_ocupados['no_resp_ingreso']]['P21_REAL'] / 1e6,
    label='Declarados (Original)',
    color='#0077ff',
    linewidth=2.2,
    clip=(0, limite_sup / 1e6),
    ax=axes[1]
)
sns.kdeplot(
    df_imputar['P21_IMPUTADO'] / 1e6,
    label='Imputados (Modelo OLS)',
    color='#9FA300',
    linewidth=2.4,
    linestyle='--',
    clip=(0, limite_sup / 1e6),
    ax=axes[1]
)
axes[1].set_title("Distribución: Declarados vs. Imputados", fontsize=11, fontweight='bold', loc='left', pad=10)
axes[1].set_xlabel("Ingreso real en millones de pesos", fontsize=9.5, fontweight='bold')
axes[1].set_ylabel("Densidad", fontsize=9.5, fontweight='bold')
axes[1].xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
axes[1].yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
axes[1].xaxis.grid(False)
axes[1].spines['top'].set_visible(False)
axes[1].spines['right'].set_visible(False)
axes[1].legend(frameon=True, fontsize=9)

fig.suptitle("Modelo de Regresión Lineal e Imputación de No Respuesta en Ocupados (2016 - 2026)",
            fontsize=12.5, fontweight='bold', y=0.97)
fig.text(0.01, 0.01, "Fuente: Elaboración propia en base a EPH-INDEC e IPC-GBA.",
        fontsize=8.5, color='#555555')

plt.tight_layout(rect=[0, 0.04, 1, 0.92])
plt.savefig('graficos/07_regresion_e_imputacion.png', dpi=300, bbox_inches='tight')
plt.show()

# -------------------------------------------------------------------------
# 7. FIGURA 7B: EVOLUCIÓN TRIMESTRAL PONDERADA (TODOS LOS TRIMESTRES)
# -------------------------------------------------------------------------
df_ocupados['PERIODO'] = df_ocupados['ANO4'].astype(int).astype(str) + '-T' + df_ocupados['TRIMESTRE'].astype(int).astype(str)

rows_trim = []
for (ano, trim, per, aglo), g in df_ocupados.groupby(['ANO4', 'TRIMESTRE', 'PERIODO', 'AGLOMERADO_NOM']):
    # Sin imputar (solo declarados con PONDIIO)
    g_decl = g[(~g['no_resp_ingreso']) & (g['P21_REAL'] > 0) & (g['PONDIIO'] > 0)]
    med_decl = weighted_quantiles(g_decl['P21_REAL'], [0.50], g_decl['PONDIIO'])[0] / 1e6 if len(g_decl) > 0 else np.nan
    
    # Con imputación (consolidado usando PONDIIO o PONDERA como respaldo)
    peso_cons = g['PONDIIO'].where(g['PONDIIO'] > 0, g['PONDERA'])
    mask_cons = (g['P21_CONSOLIDADO'] > 0) & (peso_cons > 0)
    g_cons = g[mask_cons]
    med_cons = weighted_quantiles(g_cons['P21_CONSOLIDADO'], [0.50], peso_cons[mask_cons])[0] / 1e6 if len(g_cons) > 0 else np.nan
    
    rows_trim.append({
        'ANO4': int(ano),
        'TRIMESTRE': int(trim),
        'PERIODO': per,
        'AGLOMERADO_NOM': aglo,
        'Mediana_Declarados': med_decl,
        'Mediana_Consolidado': med_cons
    })

df_trim_imp = pd.DataFrame(rows_trim).sort_values(['ANO4', 'TRIMESTRE'])

# 2 filas x 1 columna para dar ancho completo a todos los trimestres
fig7b, axes7b = plt.subplots(2, 1, figsize=(14.5, 8.2), sharex=True, sharey=True)

for i, aglo in enumerate(['CABA', 'Gran Buenos Aires']):
    sub = df_trim_imp[df_trim_imp['AGLOMERADO_NOM'] == aglo].reset_index(drop=True)
    ax = axes7b[i]
    
    ax.plot(sub.index, sub['Mediana_Declarados'], marker='o', markersize=4, linewidth=2.0,
            color='#0077ff', label='Sin imputar (Solo declarados)')
    ax.plot(sub.index, sub['Mediana_Consolidado'], marker='s', markersize=3.8, linewidth=2.0,
            linestyle='--', color='#9FA300', label='Con imputación (Consolidado)')
    
    # Mostrar TODOS los trimestres en el eje X
    ax.set_xticks(sub.index)
    ax.set_xticklabels(sub['PERIODO'], rotation=60, ha='right', fontsize=7.8)
    ax.tick_params(axis='x', labelbottom=True)
    
    ax.set_title(f"{aglo}", fontsize=11.5, fontweight='bold', loc='left', pad=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f'${val:,.1f}M'.replace('.', ',')))
    ax.set_ylabel("Mediana ingreso real\n(en millones)", fontsize=9.5, fontweight='bold')
    ax.yaxis.grid(True, linestyle=':', color='gray', alpha=0.5)
    ax.xaxis.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=True, fontsize=9)

fig7b.suptitle("Evolución trimestral de la mediana salarial real: Declarados vs. Base Imputada (2016-T2 a 2026-T2)",
            fontsize=13, fontweight='bold', y=0.98)
fig7b.text(0.01, 0.01, "Fuente: Elaboración propia en base a EPH-INDEC e IPC-GBA. Ponderado por PONDIIO (y PONDERA en imputados).",
        fontsize=8.5, color='#555555')

# Reservar espacio arriba para suptitle y abajo para la fuente
plt.tight_layout(rect=[0, 0.03, 1, 0.94])
plt.savefig('graficos/07b_evolucion_trimestral_imputacion.png', dpi=300, bbox_inches='tight')
plt.show()