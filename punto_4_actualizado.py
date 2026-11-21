import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import statsmodels.formula.api as smf

from sklearn.model_selection import train_test_split
from sklearn.metrics import (r2_score, mean_squared_error, mean_absolute_error )

# CONFIGURACIÓN GENERAL

os.makedirs("graficos", exist_ok=True)

DIRECTORIO_GRAFICOS = os.path.join("graficos", "analisis_multivariado_complemento", "05_regresion_e_imputacion" )

os.makedirs(DIRECTORIO_GRAFICOS, exist_ok=True)

RUTA_GRAFICO = os.path.join(DIRECTORIO_GRAFICOS, "07_regresion_e_imputacion.png" )

sns.set_theme(style="whitegrid")

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1200)
pd.options.display.float_format = "{:,.2f}".format

AGLOMERADOS = { 32: "CABA", 33: "Gran Buenos Aires" }

CATEGORIAS_IMPUTABLES = [1, 2, 3]

VARIABLES_MODELO = [ "CH06", "HORAS_SEM", "SEXO_NOM", "ED_GRUPO", "AGLOMERADO_NOM", "CAT_NOM", "CALIF_NOM", "RAMA_2D" ]

# 1. CARGA Y HOMOLOGACIÓN DE VARIABLES

df = pd.read_csv("datos/eph_microdatos.csv", low_memory=False )

df.columns = df.columns.str.strip().str.upper()

columnas_numericas = [
    "AGLOMERADO", "ANO4", "TRIMESTRE", "ESTADO",
    "PONDERA", "PONDIIO", "CH04", "CH06",
    "NIVEL_ED", "CAT_OCUP", "P21", "P21_REAL", "PP3E_TOT"
]

for columna in columnas_numericas:
    if columna in df.columns:
        df[columna] = pd.to_numeric(df[columna], errors="coerce" )

columnas_requeridas = [
    "AGLOMERADO", "ESTADO", "PONDERA", "PONDIIO",
    "CH04", "CH06", "NIVEL_ED", "CAT_OCUP",
    "P21", "P21_REAL", "PP3E_TOT", "PP04D_COD", "PP04B_COD"
]

faltantes = [
    col
    for col in columnas_requeridas
    if col not in df.columns
]

if faltantes:
    raise ValueError(
        f"Faltan columnas necesarias en eph_microdatos.csv: {faltantes}"
    )

df = df[
    df["AGLOMERADO"].isin(AGLOMERADOS)
].copy()

df["AGLOMERADO_NOM"] = df["AGLOMERADO"].map(
    AGLOMERADOS
)

ed_map = {
    1: "1. Sin estudios / Prim. inc.",
    7: "1. Sin estudios / Prim. inc.",
    2: "2. Prim. comp. / Sec. inc.",
    3: "2. Prim. comp. / Sec. inc.",
    4: "3. Secundaria completa",
    5: "4. Superior / Univ. inc.",
    6: "5. Superior / Univ. comp."
}

df["ED_GRUPO"] = df["NIVEL_ED"].map(ed_map)

cat_map = {
    1: "Patrón / Empleador",
    2: "Trabajador por cuenta propia",
    3: "Obrero o empleado (asalariado)",
    4: "Trabajador familiar sin remuneración"
}

df["CAT_NOM"] = df["CAT_OCUP"].map(cat_map)

df["SEXO_NOM"] = df["CH04"].map({
    1: "Varones",
    2: "Mujeres"
})

# Calificación ocupacional: último dígito de PP04D_COD.

calif_str = (df["PP04D_COD"] .astype("string") .str.replace(r"\.0$", "", regex=True) .str.zfill(5) )

df["CALIF_COD"] = pd.to_numeric( calif_str.str[-1], errors="coerce" )

df["CALIF_NOM"] = df["CALIF_COD"].map({
    1: "Profesional",
    2: "Técnica",
    3: "Operativa",
    4: "No calificada"
}).fillna("Otra / Sin especificar")

# Rama de actividad: primeros dos dígitos de PP04B_COD.
rama_str = (df["PP04B_COD"] .astype("string") .str.replace(r"\.0$", "", regex=True) .str.zfill(4))
df["RAMA_2D"] = rama_str.str[:2]
df.loc[df["PP04B_COD"].isna(), "RAMA_2D" ] = "00"

# 2. UNIVERSO DE OCUPADOS Y CLASIFICACIÓN DE INGRESOS

df_ocupados = df[ df["ESTADO"] == 1 ].copy()

# La clasificación se realiza sobre P21,
# que conserva los códigos originales.
# P21_REAL mantiene esos códigos especiales.

df_ocupados["ESTADO_INGRESO"] = np.select(
    [ df_ocupados["P21"] == -9, df_ocupados["P21"] == 0, df_ocupados["P21"] > 0 ],
    [ "No respuesta (-9)", "No corresponde (0)", "Ingreso positivo" ],
    default="Valor faltante / inválido"
)

df_ocupados["no_resp_ingreso"] = (df_ocupados["P21"] == -9 )
df_ocupados["no_corresponde"] = (df_ocupados["P21"] == 0 )

# Horas semanales válidas:
# se excluyen valores no plausibles.

df_ocupados["HORAS_SEM"] = df_ocupados[
    "PP3E_TOT"
].where((df_ocupados["PP3E_TOT"] > 0) & (df_ocupados["PP3E_TOT"] <= 120), np.nan )

print("\n" + "=" * 85)
print("1. CLASIFICACIÓN DE INGRESOS EN EL UNIVERSO DE OCUPADOS")
print("=" * 85)

tabla_estado = pd.crosstab(df_ocupados["AGLOMERADO_NOM"], df_ocupados["ESTADO_INGRESO"], margins=True )

print(tabla_estado)

# 3. CONSTRUCCIÓN DE LA MUESTRA PARA EL MODELO

# Se utilizan exclusivamente ingresos positivos declarados.
# Los casos -9 son candidatos a imputación.
# Los casos 0 no corresponden a la secuencia y no se imputan.

# DIAGNÓSTICO DE HORAS SEMANALES

print("\n" + "=" * 85)
print("DIAGNÓSTICO DE HORAS SEMANALES (PP3E_TOT)")
print("=" * 85)

horas = pd.to_numeric(df_ocupados.loc[ df_ocupados["P21"] > 0, "PP3E_TOT" ], errors="coerce" )

sin_dato = horas.isna()
cero = horas.eq(0)
negativas = horas.lt(0)
validas = horas.between(1, 120)
superiores = horas.gt(120)

clasificados = (sin_dato | cero | negativas | validas | superiores )

otros = ~clasificados

print(f"Sin dato: {sin_dato.sum():,}")
print(f"Igual a cero: {cero.sum():,}")
print(f"Negativas: {negativas.sum():,}")
print(f"Válidas (1 a 120): {validas.sum():,}")
print(f"Superiores a 120: {superiores.sum():,}")
print(f"Otros valores: {otros.sum():,}")
print(f"Total analizado: {len(horas):,}")
print(f"Total excluido por horas: " f"{len(horas) - validas.sum():,}" )

# DIAGNÓSTICO SECUENCIAL DE EXCLUSIONES
condiciones_diagnostico = {
    "Ingreso P21 positivo": df_ocupados["P21"] > 0,
    "Ingreso real positivo": df_ocupados["P21_REAL"] > 0,
    "PONDIIO positivo": df_ocupados["PONDIIO"] > 0,
    "Horas semanales válidas": df_ocupados["HORAS_SEM"].notna(),
    "Edad disponible": df_ocupados["CH06"].notna(),
    "Nivel educativo disponible": df_ocupados["ED_GRUPO"].notna(),
    "Categoría ocupacional disponible": df_ocupados["CAT_NOM"].notna(),
    "Sexo disponible": df_ocupados["SEXO_NOM"].notna(),
    "Aglomerado disponible": df_ocupados["AGLOMERADO_NOM"].notna(),
    "Calificación disponible": df_ocupados["CALIF_NOM"].notna(),
    "Rama disponible": df_ocupados["RAMA_2D"].notna()
}

mascara_acumulada = pd.Series(True, index=df_ocupados.index )

print("\n" + "=" * 85)
print("DIAGNÓSTICO DE EXCLUSIONES DE LA MUESTRA")
print("=" * 85)
print(f"Ocupados totales: {len(df_ocupados):,}")
print("Ocupados con ingreso positivo: " f"{(df_ocupados['P21'] > 0).sum():,}" )
print("\nDesglose secuencial:")

for nombre, condicion in condiciones_diagnostico.items():
    mascara_anterior = mascara_acumulada.copy()
    mascara_acumulada &= condicion
    excluidos = ( mascara_anterior & ~condicion).sum()
    print(f"{nombre}: " f"{mascara_acumulada.sum():,} acumulados | " f"{excluidos:,} excluidos en este filtro")

cond_validos = (
    (df_ocupados["P21"] > 0) & (df_ocupados["P21_REAL"] > 0)
    & (df_ocupados["PONDIIO"] > 0) & (df_ocupados["HORAS_SEM"].notna())
    & (df_ocupados["CH06"].notna()) & (df_ocupados["ED_GRUPO"].notna())
    & (df_ocupados["CAT_NOM"].notna()) & (df_ocupados["SEXO_NOM"].notna())
    & (df_ocupados["AGLOMERADO_NOM"].notna()) & (df_ocupados["CALIF_NOM"].notna())
    & (df_ocupados["RAMA_2D"].notna())
)

df_validos = df_ocupados.loc[ cond_validos ].copy()

if len(df_validos) < 100:
    raise ValueError("La cantidad de observaciones válidas es insuficiente " "para estimar el modelo." )

print(f"\nObservaciones antes del recorte P99,5: " f"{len(df_validos):,}" )

# Recorte del 0,5 % superior para reducir
# la influencia de valores extremos.
limite_sup = df_validos[ "P21_REAL" ].quantile(0.995)
cantidad_antes_recorte = len(df_validos)
df_validos = df_validos[ df_validos["P21_REAL"] <= limite_sup ].copy()
cantidad_despues_recorte = len(df_validos)
cantidad_excluida_recorte = ( cantidad_antes_recorte - cantidad_despues_recorte )

print(f"Umbral superior P99,5: ${limite_sup:,.2f}")
print( f"Observaciones después del recorte P99,5: " f"{cantidad_despues_recorte:,}" )
print( f"Observaciones excluidas por P99,5: " f"{cantidad_excluida_recorte:,}" )

if df_validos.empty:
    raise ValueError("No quedaron observaciones para estimar el modelo.")

# 4. REGRESIÓN SOBRE LA VARIABLE ORIGINAL EN PESOS REALES

# La variable dependiente es P21_REAL,
# sin transformación logarítmica.

formula = (
    "P21_REAL ~ CH06 + I(CH06**2) + HORAS_SEM + "
    "C(SEXO_NOM) + C(ED_GRUPO) + C(AGLOMERADO_NOM) + "
    "C(CAT_NOM) + C(CALIF_NOM) + C(RAMA_2D)"
)

train_split, test_split = train_test_split(df_validos, test_size=0.20, random_state=42 )

# Se identifican las categorías presentes en entrenamiento.
# Los casos de prueba con categorías desconocidas no pueden
# utilizarse para predecir con este modelo.

columnas_categoricas = ["SEXO_NOM", "ED_GRUPO", "AGLOMERADO_NOM", "CAT_NOM", "CALIF_NOM", "RAMA_2D" ]

cantidad_test_antes_filtro = len(test_split)

for columna in columnas_categoricas:
    categorias_train = (train_split[columna] .dropna() .unique() )
    test_split = test_split[ test_split[columna].isin(categorias_train) ].copy()

cantidad_test_excluida = ( cantidad_test_antes_filtro - len(test_split) )

if test_split.empty:
    raise ValueError("El conjunto de prueba quedó vacío luego de " "filtrar categorías." )

print("\n" + "=" * 85)
print("DIAGNÓSTICO DEL CONJUNTO DE ENTRENAMIENTO Y PRUEBA")
print("=" * 85)

print(f"Entrenamiento: {len(train_split):,}")
print(f"Prueba antes del filtro: {cantidad_test_antes_filtro:,}")
print(f"Prueba después del filtro: {len(test_split):,}")
print(f"Casos de prueba excluidos: {cantidad_test_excluida:,}")

# 4.1 MODELO OLS DE ENTRENAMIENTO

modelo_ols_train = smf.ols(formula=formula, data=train_split ).fit()
pred_test_ols = modelo_ols_train.predict( test_split )
r2_test_ols = r2_score( test_split["P21_REAL"], pred_test_ols )
rmse_test_ols = np.sqrt( mean_squared_error(test_split["P21_REAL"], pred_test_ols) )
mae_test_ols = mean_absolute_error(test_split["P21_REAL"], pred_test_ols )

# 4.2 MODELO WLS DE ENTRENAMIENTO

# WLS utiliza PONDIIO como ponderador.
# La validación ponderada debe realizarse con sus predicciones.

modelo_wls_train = smf.wls(formula=formula, data=train_split, weights=train_split["PONDIIO"]).fit()

pred_test_wls = modelo_wls_train.predict(test_split)

# 4.3 FUNCIONES DE MÉTRICAS PONDERADAS

def weighted_r2(y_real, y_pred, weights):

    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    weights = np.asarray(weights, dtype=float)

    mask = (np.isfinite(y_real) & np.isfinite(y_pred) & np.isfinite(weights) & (weights > 0) )

    y_real = y_real[mask]
    y_pred = y_pred[mask]
    weights = weights[mask]

    if len(y_real) == 0:
        return np.nan

    media_ponderada = np.average( y_real, weights=weights)
    suma_error = np.sum( weights * (y_real - y_pred) ** 2)
    suma_total = np.sum( weights * (y_real - media_ponderada) ** 2)

    if suma_total == 0:
        return np.nan

    return 1 - suma_error / suma_total


def weighted_rmse(y_real, y_pred, weights):
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    weights = np.asarray(weights, dtype=float)

    mask = (np.isfinite(y_real) & np.isfinite(y_pred) & np.isfinite(weights) & (weights > 0))

    y_real = y_real[mask]
    y_pred = y_pred[mask]
    weights = weights[mask]

    if len(y_real) == 0:
        return np.nan

    return np.sqrt(
        np.average(
            (y_real - y_pred) ** 2,
            weights=weights
        )
    )


def weighted_mae(y_real, y_pred, weights):
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    weights = np.asarray(weights, dtype=float)

    mask = (np.isfinite(y_real) & np.isfinite(y_pred) & np.isfinite(weights) & (weights > 0) )

    y_real = y_real[mask]
    y_pred = y_pred[mask]
    weights = weights[mask]

    if len(y_real) == 0:
        return np.nan

    return np.average( np.abs(y_real - y_pred), weights=weights )

# 4.4 MÉTRICAS PONDERADAS DEL MODELO WLS

# IMPORTANTE:
# Se utilizan las predicciones WLS, no las predicciones OLS.
r2_test_ponderado = weighted_r2( test_split["P21_REAL"], pred_test_wls, test_split["PONDIIO"])
rmse_test_ponderado = weighted_rmse( test_split["P21_REAL"], pred_test_wls, test_split["PONDIIO"])
mae_test_ponderado = weighted_mae( test_split["P21_REAL"], pred_test_wls, test_split["PONDIIO"])

# 4.5 MODELOS FINALES SOBRE TODA LA MUESTRA VÁLIDA

modelo_ols = smf.ols( formula=formula, data=df_validos).fit()
modelo_wls = smf.wls( formula=formula, data=df_validos, weights=df_validos["PONDIIO"]).fit()

# 4.6 RESULTADOS DE LA REGRESIÓN

print("\n" + "=" * 85)
print("2. EVALUACIÓN DEL MODELO DE REGRESIÓN SOBRE INGRESOS REALES")
print("=" * 85)

print(f"Observaciones válidas: {int(modelo_ols.nobs):,}")
print(f"Observaciones entrenamiento: {len(train_split):,}")
print(f"Observaciones prueba: {len(test_split):,}")
print(f"Observaciones prueba excluidas: {cantidad_test_excluida:,}")
print(f"Umbral superior P99,5: ${limite_sup:,.2f}")

print("\n--- MODELO OLS ---")
print( f"R² OLS (muestra completa): " f"{modelo_ols.rsquared:.4f}" )
print( f"R² ajustado OLS:           " f"{modelo_ols.rsquared_adj:.4f}" )
print( f"R² OLS (test):             " f"{r2_test_ols:.4f}" )
print( f"RMSE OLS (test):           " f"${rmse_test_ols:,.2f}" )
print( f"MAE OLS (test):            " f"${mae_test_ols:,.2f}" )

print("\n--- MODELO WLS ---")
print( f"R² WLS (muestra completa): " f"{modelo_wls.rsquared:.4f}" )
print( f"R² ajustado WLS:           " f"{modelo_wls.rsquared_adj:.4f}" )

print("\n--- VALIDACIÓN WLS PONDERADA POR PONDIIO ---")
print( f"R² ponderado (test):       " f"{r2_test_ponderado:.4f}" )
print( f"RMSE ponderado (test):     " f"${rmse_test_ponderado:,.2f}" )
print( f"MAE ponderado (test):      " f"${mae_test_ponderado:,.2f}" )

print("\n--- ESTADÍSTICOS DEL MODELO OLS ---")
print(f"Estadístico F OLS:         {modelo_ols.fvalue:.2f}")
print(f"p-valor F OLS:             {modelo_ols.f_pvalue:.2e}")


# 4.7 TABLA DE COEFICIENTES

print("\n--- COEFICIENTES ---")

tabla_coef = pd.DataFrame({
    "Coef_OLS": modelo_ols.params,
    "Coef_WLS": modelo_wls.params,
    "Error_Std_OLS": modelo_ols.bse,
    "t_stat_OLS": modelo_ols.tvalues,
    "p_valor_OLS": modelo_ols.pvalues
})

print(tabla_coef.to_string())

# 5. IMPUTACIÓN DE NO RESPUESTA

# Se imputan exclusivamente los casos con P21 = -9.
# Se excluye la categoría 4 (trabajador familiar sin remuneración).
# Los casos con P21 = 0 no se imputan.

cond_imputar = (
    (df_ocupados["P21"] == -9)
    & (df_ocupados["CAT_OCUP"].isin(CATEGORIAS_IMPUTABLES)) & (df_ocupados["HORAS_SEM"].notna())
    & (df_ocupados["CH06"].notna()) & (df_ocupados["ED_GRUPO"].notna())
    & (df_ocupados["CAT_NOM"].notna()) & (df_ocupados["SEXO_NOM"].notna())
    & (df_ocupados["AGLOMERADO_NOM"].notna()) & (df_ocupados["CALIF_NOM"].notna())
    & (df_ocupados["RAMA_2D"].notna())
)

df_imputar = df_ocupados.loc[ cond_imputar ].copy()

# El modelo no puede predecir categorías ausentes
# en su entrenamiento.

for columna in columnas_categoricas:
    categorias_modelo = ( df_validos[columna] .dropna() .unique())
    df_imputar = df_imputar[ df_imputar[columna].isin(categorias_modelo) ].copy()


if not df_imputar.empty:
    predicciones = modelo_wls.predict( df_imputar)
    df_imputar["P21_IMPUTADO"] = np.maximum( predicciones, 0)
else:
    df_imputar["P21_IMPUTADO"] = pd.Series(dtype=float, index=df_imputar.index)


# Consolidación:
# - Ingresos positivos: se conservan.
# - Cero: se conserva como no correspondiente.
# - -9: se reemplaza únicamente cuando pudo imputarse.
df_ocupados["P21_CONSOLIDADO"] = ( df_ocupados["P21_REAL"].copy() )
df_ocupados.loc[ df_ocupados["P21"] == -9, "P21_CONSOLIDADO" ] = np.nan
df_ocupados.loc[ df_imputar.index, "P21_CONSOLIDADO" ] = df_imputar["P21_IMPUTADO"]

# 5.1 COBERTURA DE IMPUTACIÓN

print("\n" + "=" * 85)
print("3. COBERTURA DE IMPUTACIÓN SOBRE EL UNIVERSO DE OCUPADOS")
print("=" * 85)

for aglo in ["CABA", "Gran Buenos Aires"]:
    sub_o = df_ocupados[ df_ocupados["AGLOMERADO_NOM"] == aglo ]
    sub_i = df_imputar[ df_imputar["AGLOMERADO_NOM"] == aglo ]
    total_ocupados = len(sub_o)
    total_no_respuesta = ( sub_o["P21"] == -9 ).sum()
    total_no_corresponde = ( sub_o["P21"] == 0 ).sum()
    total_imputados = len(sub_i)
    cobertura = ( total_imputados / total_no_respuesta * 100 if total_no_respuesta > 0 else 0 )

    print(
        f"{aglo}: {total_ocupados:,} ocupados | "  f"{total_no_respuesta:,} no respuesta (-9) | "
        f"{total_no_corresponde:,} no corresponde (0) | "  f"{total_imputados:,} imputados "
        f"({cobertura:.1f}% de los -9)"
    )

# 6. CUANTILES PONDERADOS Y COMPARACIÓN DISTRIBUCIONAL

def weighted_quantiles(values, quantiles, sample_weight):

    values = np.asarray(values, dtype=float )
    quantiles = np.asarray(quantiles, dtype=float )
    sample_weight = np.asarray(sample_weight, dtype=float )
    mask = ( np.isfinite(values) & np.isfinite(sample_weight) & (sample_weight > 0) )

    values = values[mask]
    sample_weight = sample_weight[mask]

    if len(values) == 0:
        return np.full(len(quantiles), np.nan)

    if np.any( (quantiles < 0) | (quantiles > 1)):
        raise ValueError("Los cuantiles deben estar entre 0 y 1.")

    sorter = np.argsort(values)

    values = values[sorter]
    sample_weight = sample_weight[sorter]

    peso_total = sample_weight.sum()

    posiciones = ( np.cumsum(sample_weight) - 0.5 * sample_weight) / peso_total

    return np.interp( quantiles, posiciones, values, left=values[0], right=values[-1] )

def resumen_ponderado(grupo, columna_valor, columna_peso):
    """ Calcula estadísticas ponderadas usando  un único ponderador por escenario. """
    peso = grupo[columna_peso]
    mascara = ((grupo[columna_valor] > 0) & np.isfinite(grupo[columna_valor]) & (peso > 0) & np.isfinite(peso) )
    valores = grupo.loc[ mascara, columna_valor ]
    pesos = peso.loc[ mascara ]

    if len(valores) == 0:

        return pd.Series({ "Media_Pond": np.nan, "Q1": np.nan, "Mediana_Q2": np.nan, "Q3": np.nan, "Observaciones": 0 })

    media = np.average(valores, weights=pesos )

    q1, q2, q3 = weighted_quantiles(valores, [0.25, 0.50, 0.75], pesos )

    return pd.Series({
        "Media_Pond": media,
        "Q1": q1,
        "Mediana_Q2": q2,
        "Q3": q3,
        "Observaciones": len(valores)
    })


# Se excluyen los ceros porque no corresponden
# a la secuencia de ingresos.
# Los no respondentes no imputados permanecen como NaN.
# Escenario 1: ingresos declarados con PONDIIO.
# Escenario 2: ingresos declarados + imputados con PONDERA.
# No se combinan PONDIIO y PONDERA dentro
# de una misma distribución.

comp_antes = (df_ocupados .groupby("AGLOMERADO_NOM")
    .apply( resumen_ponderado, columna_valor="P21_REAL", columna_peso="PONDIIO" )
)

comp_despues = (df_ocupados .groupby("AGLOMERADO_NOM")
    .apply( resumen_ponderado, columna_valor="P21_CONSOLIDADO", columna_peso="PONDERA" )
)

comparativa = pd.concat(
    {
        "Sin imputar (PONDIIO)": comp_antes,
        "Con imputación (PONDERA)": comp_despues
    },
    axis=1
).reindex([
    "CABA",
    "Gran Buenos Aires"
])

print("\n" + "=" * 85)
print("4. COMPARACIÓN DISTRIBUCIONAL POR AGLOMERADO")
print("=" * 85)
print("Sin imputar: ingresos declarados ponderados con PONDIIO." )
print("Con imputación: ingresos declarados e imputados ""ponderados con PONDERA." )
print("Los resultados usan ponderadores distintos ""y deben interpretarse como escenarios alternativos." )
print(comparativa.T.to_string())

# 7. GRÁFICO DE AJUSTE Y DISTRIBUCIÓN DE INGRESOS
colores_ref = { "CABA": "#D8DB00", "Gran Buenos Aires": "#0077ff" }
fig, axes = plt.subplots( 1, 2, figsize=(14, 5) )

# PANEL A: VALIDACIÓN WLS SOBRE EL CONJUNTO DE PRUEBA

# Se utiliza test_split, que no participó del entrenamiento.
# Las predicciones corresponden a modelo_wls_train.

muestra = test_split.sample( min(5000, len(test_split)), random_state=42 ).copy()
pred_muestra = modelo_wls_train.predict( muestra )
observado_millones = ( muestra["P21_REAL"] / 1e6 )
predicho_millones = ( pred_muestra / 1e6 )
axes[0].scatter( observado_millones, predicho_millones, alpha=0.22, s=14, color="#0077ff" )
minimo = min( observado_millones.min(), predicho_millones.min() )
maximo = max( observado_millones.max(), predicho_millones.max() )

axes[0].plot( [minimo, maximo], [minimo, maximo], color="#D32F2F", linestyle="--", linewidth=2, label="Ajuste ideal (y = x)" )
axes[0].set_title( f"Validación WLS (R² ponderado = {r2_test_ponderado:.3f})", fontsize=11, fontweight="bold", loc="left", pad=10 )
axes[0].set_xlabel( "Ingreso real observado (millones de pesos)", fontsize=9.5, fontweight="bold" )
axes[0].set_ylabel( "Ingreso real predicho (millones de pesos)", fontsize=9.5, fontweight="bold" )
axes[0].yaxis.grid( True, linestyle=":", color="gray", alpha=0.5 )
axes[0].xaxis.grid(False)
axes[0].spines["top"].set_visible(False)
axes[0].spines["right"].set_visible(False)
axes[0].legend( frameon=True, fontsize=9 )

# PANEL B: DISTRIBUCIÓN DE INGRESOS DECLARADOS E IMPUTADOS

ingresos_declarados = df_ocupados.loc[
    df_ocupados["P21"] > 0,
    "P21_REAL"
].dropna()

ingresos_imputados = (
    df_imputar["P21_IMPUTADO"].dropna()
)

if len(ingresos_declarados) > 1:

    sns.kdeplot(
        ingresos_declarados / 1e6, label="Declarados (original)",
        color="#0077ff", linewidth=2.2,
        clip=(0, limite_sup / 1e6), ax=axes[1]
    )

if len(ingresos_imputados) > 1:

    sns.kdeplot(
        ingresos_imputados / 1e6,
        label="Imputados (modelo WLS)", color="#9FA300",
        linewidth=2.4, linestyle="--",
        clip=(0, limite_sup / 1e6), ax=axes[1]
    )

axes[1].set_title("Distribución: declarados vs. imputados", fontsize=11, fontweight="bold", loc="left", pad=10 )
axes[1].set_xlabel("Ingreso real en millones de pesos", fontsize=9.5, fontweight="bold" )
axes[1].set_ylabel("Densidad", fontsize=9.5, fontweight="bold" )
axes[1].xaxis.set_major_formatter(ticker.FuncFormatter(lambda val, pos: f"${val:,.1f}M".replace(".", ",")) )
axes[1].yaxis.grid( True, linestyle=":", color="gray", alpha=0.5 )
axes[1].xaxis.grid(False)
axes[1].spines["top"].set_visible(False)
axes[1].spines["right"].set_visible(False)
axes[1].legend( frameon=True, fontsize=9)

plt.suptitle(
    "Modelo de regresión e imputación de no respuesta en ocupados (2016–2026)",
    fontsize=12.5, fontweight="bold", y=1.02
)

plt.tight_layout()
plt.savefig(RUTA_GRAFICO, dpi=300, bbox_inches="tight" )
plt.show()

# 8. RESUMEN FINAL
print("\n" + "=" * 85)
print("ANÁLISIS DEL PUNTO 4 FINALIZADO")
print("=" * 85)
print( f"R² OLS (muestra completa): " f"{modelo_ols.rsquared:.4f}")
print( f"R² WLS (muestra completa): " f"{modelo_wls.rsquared:.4f}")
print( f"R² OLS (test): " f"{r2_test_ols:.4f}")
print( f"R² ponderado WLS (test): " f"{r2_test_ponderado:.4f}")
print( f"RMSE ponderado WLS (test): " f"${rmse_test_ponderado:,.2f}")
print( f"MAE ponderado WLS (test): " f"${mae_test_ponderado:,.2f}")
print( f"Observaciones imputadas: " f"{len(df_imputar):,}")
print( f"Gráfico generado: {RUTA_GRAFICO}")