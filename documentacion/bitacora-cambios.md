# Bitácora de cambios — TP Análisis de Datos EPH

## 1. Objetivo

Registrar las modificaciones, correcciones y decisiones técnicas realizadas durante el desarrollo del trabajo práctico de Introducción al Análisis de Datos.

El objetivo es mantener la trazabilidad de los cambios, documentar sus fundamentos y evitar modificaciones repetidas o contradictorias entre los integrantes del grupo.

## 2. Criterios de registro

Cada modificación relevante deberá documentarse indicando:

- **Fecha:** cuándo se realizó.
- **Archivo:** archivo afectado.
- **Motivo:** problema detectado o necesidad del cambio.
- **Modificaciones:** qué se cambió.
- **Justificación:** fundamento técnico o metodológico.
- **Validación:** pruebas realizadas y resultados obtenidos.
- **Estado:** pendiente, implementado, ejecutado o validado.
- **Commit:** identificador del commit, si corresponde.

Un cambio no debe considerarse validado únicamente porque el código haya sido modificado. También debe ejecutarse y revisarse su resultado.

Se diferenciará entre validación técnica (ejecución correcta y generación de archivos) e inspección visual o metodológica de los resultados.

## 3. Contexto del proyecto

- **Fuente de datos:** Encuesta Permanente de Hogares (EPH).
- **Período de análisis:** 2016–2026.
- **Aglomerados:** CABA (`AGLOMERADO = 32`) y Partidos del Gran Buenos Aires (`AGLOMERADO = 33`).
- **Frecuencia temporal:** trimestral para los gráficos de evolución.
- **Rama de trabajo:** `eze-punto-1-2`.
- **Rama principal grupal:** `main`.

Consideraciones temporales:

- 2016 comienza en el segundo trimestre (T2).
- 2026 finaliza en el segundo trimestre (T2) para los microdatos EPH disponibles en el proyecto.
- El período analizado comprende 41 trimestres.
- Los años 2016 y 2026 son períodos parciales.

**Indicación del profesor:** los gráficos de líneas que representen evolución temporal deben utilizar frecuencia trimestral y no anual. Las tablas anuales pueden conservarse como resúmenes.

## 4. Registro de cambios

### 20/11/2026 — Adaptación trimestral del complemento multivariado

**Archivo:** `3b_multivariado_complemento.py`

**Motivo:**

Adaptar los gráficos de evolución temporal a frecuencia trimestral, siguiendo la indicación del profesor.

**Modificaciones:**

- Incorporación de los períodos trimestrales desde 2016-T2 hasta 2026-T2.
- Incorporación de la evolución trimestral de media y mediana de ingresos.
- Adaptación de las tasas por sexo, edad y nivel educativo.
- Adaptación de la evolución de ingresos por nivel educativo y edad.
- Conservación de las tablas anuales como resúmenes.
- Incorporación de una tabla de ingresos trimestrales.
- Exportación de resultados a archivos CSV.

**Validación anterior a la actualización del IPC:**

El script fue ejecutado sin errores y generó resultados para los 41 trimestres.

**Estado:** Implementado y ejecutado sobre la base anterior. Pendiente volver a ejecutar y validar los resultados con la base actualizada.

**Commit:** `e9c0a49` — `update: complemento punto 2 con series trimestrales`.

---

### 20/11/2026 — Revisión y adaptación del análisis multivariado principal

**Archivo:** `3_analisis_multivariado.py`

**Motivo:**

Revisar la adaptación trimestral del análisis multivariado y corregir aspectos relacionados con el tratamiento de datos, los intervalos de edad y el cálculo de indicadores temporales.

**Modificaciones:**

- Adaptación de las series de tasas de actividad, empleo y desocupación a frecuencia trimestral.
- Incorporación de la evolución trimestral de ingresos mediante cuantiles.
- Incorporación de la evolución de ingresos y brecha por sexo.
- Implementación de medias móviles estrictas de cuatro trimestres (`min_periods=4`).
- Incorporación de una grilla temporal completa para los 41 trimestres.
- Robustecimiento de la función `weighted_quantiles`, contemplando valores nulos, infinitos, ponderadores inválidos y grupos sin observaciones válidas.
- Corrección del filtrado y alineación de ingresos y grupos etarios en el boxplot.
- Revisión del correlograma y de las categorías de calificación utilizadas.

**Gráficos previstos:**

- `03a_tasa_actividad_trimestral.png`
- `03b_tasa_empleo_trimestral.png`
- `03c_tasa_desocupacion_trimestral.png`
- `04_evolucion_ingresos_trimestral.png`
- `05a_ingreso_nivel_educativo.png`
- `05b_ingreso_calificacion.png`
- `05c_evolucion_sexo_trimestral.png`
- `05d_boxplot_edad.png`
- `06_correlograma.png`

**Validación anterior a la actualización del IPC:**

El usuario ejecutó el script con Python 3.12.15 utilizando `MPLBACKEND=Agg`.

La ejecución finalizó correctamente y confirmó:

- Período analizado: 2016-T2 a 2026-T2.
- Cantidad de trimestres: 41.
- Aglomerados: CABA y Gran Buenos Aires.
- Generación de los nueve gráficos en `graficos/analisis_multivariado/`.

Los avisos relacionados con `FigureCanvasAgg` no impidieron guardar los gráficos.

**Estado:** Implementado y ejecutado sobre la base anterior. Pendiente volver a ejecutar y validar con la nueva base deflactada.

**Commit:** Pendiente.

---

### 20/11/2026 — Organización de gráficos del análisis univariado

**Archivo:** `2_atipicos_y_no_respuesta.py`

**Motivo:**

Organizar los gráficos generados por el análisis de valores atípicos y no respuesta en subdirectorios temáticos.

**Modificaciones:**

- Creación automática de `graficos/calidad_datos/`.
- Creación automática de `graficos/distribucion_ingresos/`.
- Reubicación de la figura 01 en `graficos/calidad_datos/01_no_respuesta_y_atipicos.png`.
- Reubicación de la figura 02 en `graficos/distribucion_ingresos/02_distribucion_ingresos_boxplot.png`.
- Conservación de los cálculos, filtros, métricas, etiquetas y criterios estadísticos originales.

**Validación anterior a la actualización del IPC:**

El usuario ejecutó el script con Python 3.12.15 utilizando `MPLBACKEND=Agg`.

Se confirmó la generación de ambos archivos y de los resúmenes de calidad de datos y métricas del boxplot.

**Estado:** Organización implementada y ejecutada sobre la base anterior. Pendiente volver a ejecutar con la base actualizada y revisar los resultados.

**Commit:** Pendiente.

---

### 20/11/2026 — Organización de gráficos del análisis multivariado principal

**Archivo:** `3_analisis_multivariado.py`

**Motivo:**

Organizar los gráficos generados por el análisis multivariado principal en subdirectorios temáticos.

**Modificaciones:**

- Gráficos de evolución de tasas en `graficos/analisis_multivariado/01_evolucion_tasas/`.
- Evolución de ingresos en `graficos/analisis_multivariado/02_evolucion_ingresos/`.
- Ingresos por características en `graficos/analisis_multivariado/03_ingresos_por_caracteristicas/`.
- Distribución por edad en `graficos/analisis_multivariado/04_distribucion_por_edad/`.
- Correlograma en `graficos/analisis_multivariado/05_correlaciones/`.
- Creación automática de los directorios de salida.

Se conservaron los nueve gráficos y sus nombres originales.

**Validación anterior a la actualización del IPC:**

El usuario ejecutó nuevamente el script con Python 3.12.15 utilizando `MPLBACKEND=Agg`.

La ejecución finalizó correctamente y confirmó la generación de los nueve gráficos en `graficos/analisis_multivariado/`.

**Estado:** Organización implementada y ejecutada. Pendiente regenerar los gráficos con la nueva base y realizar inspección visual.

**Commit:** Pendiente.

---

### 20/11/2026 — Organización de gráficos del análisis multivariado complementario

**Archivo:** `3b_multivariado_complemento.py`

**Motivo:**

Organizar los gráficos del análisis multivariado complementario en subdirectorios temáticos.

**Modificaciones:**

- Comparación de medidas de ingresos en `graficos/analisis_multivariado_complemento/01_medidas_ingresos/`.
- Tasas por características en `graficos/analisis_multivariado_complemento/02_tasas_por_caracteristicas/`.
- Ingresos por características en `graficos/analisis_multivariado_complemento/03_ingresos_por_caracteristicas/`.
- Ingresos por actividad económica en `graficos/analisis_multivariado_complemento/04_ingresos_por_actividad/`.
- Creación automática de los directorios de salida.
- Conservación de los siete gráficos y sus nombres originales.
- Conservación de las tablas CSV en `tablas/`.

**Validación anterior a la actualización del IPC:**

El usuario ejecutó el script con Python 3.12.15 utilizando `MPLBACKEND=Agg`.

La ejecución finalizó correctamente y confirmó:

- Período analizado: 2016-T2 a 2026-T2.
- Cantidad de trimestres: 41.
- Aglomerados: CABA y Gran Buenos Aires.
- Generación de los siete gráficos.
- Generación de las tablas CSV.

**Estado:** Organización implementada y ejecutada sobre la base anterior. Pendiente volver a ejecutar y validar con la base actualizada.

**Commit:** Pendiente.

---

### 20/11/2026 — Actualización del análisis de regresión e imputación de ingresos

**Archivo anterior:** `punto_4.py` (eliminado).

**Archivo de reemplazo:** `punto_4_actualizado.py`.

**Motivo:**

Actualizar el análisis del punto 4 para evaluar la relación entre los ingresos reales y distintas características sociodemográficas y laborales. Incorporar un procedimiento de imputación para los ingresos identificados como no respuesta y comparar las distribuciones con y sin imputación.

**Modificaciones:**

- Reemplazo de `punto_4.py` por `punto_4_actualizado.py`.
- Utilización de `P21_REAL` como variable dependiente.
- Incorporación de variables explicativas relacionadas con edad, sexo, educación, aglomerado, categoría ocupacional, calificación y rama de actividad.
- Incorporación de regresión OLS y regresión ponderada WLS.
- División de la muestra en entrenamiento y prueba.
- Cálculo de R², R² ajustado, RMSE y MAE.
- Incorporación de métricas ponderadas para la evaluación del modelo.
- Aplicación de un recorte del 0,5 % superior mediante el percentil 99,5.
- Diagnóstico de horas semanales trabajadas mediante `PP3E_TOT`.
- Incorporación de un procedimiento de imputación para registros con `P21 = -9`.
- Exclusión de la imputación para los registros con ingreso cero y para la categoría de trabajador familiar sin remuneración.
- Comparación de distribuciones ponderadas sin imputar y con imputación.
- Uso de `PONDIIO` para ingresos declarados y `PONDERA` para el escenario con imputación.

**Criterios de selección de la muestra:**

La muestra de regresión se construye progresivamente a partir de los ocupados de CABA y Gran Buenos Aires. Se requieren:

- Ingreso nominal positivo (`P21 > 0`).
- Ingreso real positivo (`P21_REAL > 0`).
- Ponderador de ingresos positivo (`PONDIIO > 0`).
- Horas semanales entre 1 y 120.
- Edad, nivel educativo, categoría ocupacional, sexo, aglomerado, calificación y rama de actividad disponibles.

Posteriormente, se excluyen las observaciones que superan el umbral P99,5 de ingresos reales.

**Justificación metodológica:**

El valor `-9` se trata como no respuesta, mientras que el valor cero se conserva diferenciado y no se imputa.

El ponderador `PONDIIO` se utiliza para los ingresos declarados. Para el escenario que incorpora los valores imputados se utiliza `PONDERA` en todos los registros de ese escenario, evitando combinar ambos ponderadores dentro de una misma distribución.

La comparación entre escenarios debe interpretarse con cautela porque utilizan ponderadores diferentes.

**Resultados anteriores a la actualización del IPC:**

Los resultados numéricos de selección de muestra, regresión, imputación y distribución que se habían registrado en versiones anteriores de esta bitácora corresponden a la base anterior.

Dado que la variable dependiente `P21_REAL` fue recalculada con la nueva serie de IPC, esos resultados ya no deben utilizarse como resultados definitivos. Se deberán regenerar las métricas, las tasas de imputación y las distribuciones con la nueva base.

**Gráfico previsto:**

`graficos/analisis_multivariado_complemento/05_regresion_e_imputacion/07_regresion_e_imputacion.png`

**Validación anterior a la actualización del IPC:**

El usuario ejecutó `punto_4_actualizado.py` con Python 3.12.15.

La ejecución anterior confirmó el funcionamiento técnico del diagnóstico de horas, selección de muestra, recorte P99,5, modelos OLS y WLS, métricas ponderadas, imputación y generación del gráfico.

Se corrigió la ubicación del PNG para que quedara dentro del subdirectorio específico.

**Estado:** Script implementado y ejecutado sobre la base anterior. Los resultados numéricos deben recalcularse con la base actualizada. Pendiente inspección visual y revisión metodológica final.

**Commit:** Pendiente.

---

### 20/11/2026 — Reconstrucción y consolidación de la serie IPC-GBA

**Archivos:**

- `script_ipc.py`
- `datos/serie_ipc_divisiones212016-102026.csv` (fuente de datos existente).
- `datos/ipc_gba_trimestral_2016T2_2026T3.csv` (archivo generado).

**Motivo:**

Actualizar el procedimiento de deflactación de ingresos de la EPH, incorporando una serie mensual continua y una serie trimestral de IPC-GBA para el período de análisis.

La serie oficial disponible utilizada en el proyecto comienza en diciembre de 2016. Para completar el período desde abril de 2016 se reconstruyeron los índices anteriores utilizando las variaciones mensuales disponibles.

**Modificaciones:**

- Lectura de la serie IPC-GBA de nivel general.
- Reconstrucción de los índices mensuales de abril a noviembre de 2016, tomando diciembre de 2016 como base 100.
- Incorporación de validaciones de continuidad temporal.
- Verificación de períodos duplicados, valores nulos e índices no positivos.
- Construcción de índices trimestrales a partir de los índices mensuales.
- Cálculo de coeficientes de deflactación con base 2026-T2 y 2026-T3.
- Exportación de la serie trimestral a CSV.

**Justificación:**

La reconstrucción permite disponer de una serie continua para los trimestres utilizados en el análisis. La utilización de una base de precios común permite expresar los ingresos de distintos períodos en una misma escala monetaria.

**Validación:**

El procedimiento fue ejecutado y se verificó:

- Serie mensual desde abril de 2016 hasta octubre de 2026.
- Diciembre de 2016 establecido como índice 100.
- Serie trimestral de 42 períodos, desde 2016-T2 hasta 2026-T3.
- Ausencia de períodos trimestrales duplicados.
- Ausencia de índices trimestrales nulos o no positivos.
- Coeficientes de deflactación calculados para las bases 2026-T2 y 2026-T3.

El archivo trimestral contiene las columnas:

- `ANO4`
- `TRIMESTRE`
- `PERIODO_TRIM`
- `IPC_GBA_TRIM`
- `COEF_DEFLACTOR_2026T2`
- `COEF_DEFLACTOR_2026T3`

**Estado:** Implementado, ejecutado y validado técnicamente.

**Commit:** `92fe315` — incluido junto con la consolidación de microdatos.

---

### 20/11/2026 — Actualización de la consolidación de microdatos EPH

**Archivo:** `1_carga_y_consolidacion_de_datos.py`

**Archivo de salida:** `datos/eph_microdatos.csv`

**Motivo:**

Actualizar la consolidación de microdatos EPH para incorporar la nueva serie trimestral IPC-GBA y recalcular los ingresos reales de todos los períodos.

**Modificaciones:**

- Procesamiento de los 41 trimestres esperados, desde 2016-T2 hasta 2026-T2.
- Incorporación de validaciones de períodos, columnas obligatorias, aglomerados y variables requeridas.
- Lectura y validación de la serie trimestral IPC.
- Verificación de valores nulos, duplicados, finitos y positivos.
- Unión de los microdatos con la serie trimestral mediante una relación `many_to_one`.
- Utilización de 2026-T2 como período base de precios.
- Deflactación de `P47T`, `P21`, `ITF` e `IPCF`.
- Generación de las variables reales correspondientes: `P47T_REAL`, `P21_REAL`, `ITF_REAL` e `IPCF_REAL`.
- Conservación de valores no positivos sin transformarlos en ingresos válidos.
- Verificación de la relación entre ingresos nominales, ingresos reales y coeficientes IPC.
- Selección de 23 columnas para el archivo consolidado.
- Escritura atómica mediante archivo temporal y reemplazo final, evitando dejar una base incompleta si ocurre un error durante el procesamiento.

**Justificación:**

La actualización permite que los ingresos de los distintos trimestres sean comparables en términos de poder adquisitivo, utilizando una base de precios común.

Se mantienen separados los ingresos nominales y reales para conservar la información original y permitir distintos análisis.

**Validación:**

El usuario ejecutó `1_carga_y_consolidacion_de_datos.py` sin errores.

La ejecución confirmó:

- 41 de 41 períodos procesados.
- Uso de la caché local de PyEPH.
- 330.003 registros consolidados.
- 259.300 registros de Gran Buenos Aires.
- 70.703 registros de CABA.
- 41 períodos IPC validados.
- IPC base 2026-T2: 11.580,684633.
- Coeficientes de deflactación verificados.
- Archivo final generado con 23 columnas.

El archivo `datos/eph_microdatos.csv` tiene un tamaño aproximado de 37 MB.

**Estado:** Implementado, ejecutado y validado técnicamente.

**Commit:** `92fe315` — `feat: consolidar microdatos EPH con IPC trimestral`.

---

### 20/11/2026 — Confirmación del primer commit de actualización IPC

**Rama:** `eze-punto-1-2`

**Commit:** `92fe315` — `feat: consolidar microdatos EPH con IPC trimestral`.

**Archivos incluidos:**

- `1_carga_y_consolidacion_de_datos.py`
- `script_ipc.py`
- `datos/ipc_gba_trimestral_2016T2_2026T3.csv`

**Validación Git:**

Se ejecutaron `git diff --cached --check`, `git diff --cached --stat` y `git diff --cached --name-status` antes del commit.

Se confirmó que únicamente los tres archivos previstos estaban preparados para confirmar.

El commit se creó correctamente. Los restantes cambios locales continuaron sin confirmar.

**Estado:** Commit creado localmente. Pendiente realizar push y acordar la integración con el grupo.

## 5. Criterios metodológicos que deben mantenerse

- Tasas calculadas utilizando `PONDERA`.
- Ingresos declarados calculados utilizando `PONDIIO`.
- Tasas por sexo sobre población total.
- Tasas por edad sobre población de 15 años y más.
- Tasas por nivel educativo sobre población de 25 años y más.
- Ingresos reales ajustados por inflación.
- Evoluciones temporales representadas por trimestre.
- Los años 2016 y 2026 deben identificarse como períodos parciales.
- Los boxplots y la detección de valores atípicos se realizan sin ponderar, salvo que se decida y justifique otra metodología.
- El valor `P21 = -9` se considera no respuesta, sujeto a verificación contra el diccionario oficial.
- El valor `P21 = 0` se mantiene diferenciado de la no respuesta y no se imputa.
- Para el escenario de ingresos declarados se utiliza `PONDIIO`.
- Para el escenario con imputación se utiliza `PONDERA` en todos los registros de ese escenario.
- Las comparaciones entre escenarios con ponderadores diferentes deben interpretarse con cautela.
- En el punto 4, la muestra de regresión se limita a ocupados con ingresos positivos, horas semanales válidas y covariables disponibles.
- El recorte P99,5 debe documentarse al interpretar los resultados del modelo.
- La serie IPC utilizada para la deflactación es IPC-GBA.
- La base de precios de los ingresos reales es 2026-T2.
- La serie trimestral llega hasta 2026-T3, pero los microdatos EPH consolidados llegan hasta 2026-T2.

## 6. Organización actual de los gráficos

```text
graficos/
├── analisis_multivariado/
│   ├── 01_evolucion_tasas/
│   ├── 02_evolucion_ingresos/
│   ├── 03_ingresos_por_caracteristicas/
│   ├── 04_distribucion_por_edad/
│   └── 05_correlaciones/
│
├── analisis_multivariado_complemento/
│   ├── 01_medidas_ingresos/
│   ├── 02_tasas_por_caracteristicas/
│   ├── 03_ingresos_por_caracteristicas/
│   ├── 04_ingresos_por_actividad/
│   └── 05_regresion_e_imputacion/
│
├── calidad_datos/
│
└── distribucion_ingresos/
```

Los gráficos se guardan en subdirectorios temáticos y no directamente en la raíz de `graficos/`.

La estructura y los archivos de salida deberán verificarse nuevamente después de ejecutar los scripts con la base actualizada.

## 7. Estado actual de los archivos y cambios pendientes

### Cambios confirmados en el commit `92fe315`

- `1_carga_y_consolidacion_de_datos.py`: actualización del proceso de consolidación y deflactación.
- `script_ipc.py`: reconstrucción y validación de la serie IPC.
- `datos/ipc_gba_trimestral_2016T2_2026T3.csv`: serie IPC trimestral generada.

### Cambios locales todavía no confirmados

- `2_atipicos_y_no_respuesta.py`: organización de gráficos y análisis que debe volver a ejecutarse con la base actualizada.
- `3_analisis_multivariado.py`: análisis trimestral y organización de gráficos; requiere regenerar resultados.
- `3b_multivariado_complemento.py`: análisis complementario y organización de gráficos; requiere regenerar resultados.
- `datos/eph_microdatos.csv`: nueva base consolidada de aproximadamente 37 MB. No está incluida en el commit.
- `documentacion/bitacora-cambios.md`: documento que registra los cambios y su estado.
- `punto_4_actualizado.py`: reemplazo del script anterior, pendiente de regenerar resultados con la base actualizada.
- Directorios de gráficos reorganizados y archivos PNG generados.

### Archivos que no deben incorporarse al próximo commit sin una decisión expresa

- `3_analisis_multivariado_companero.py`: copia de referencia del script de un compañero; no forma parte del trabajo propio.
- `datos/eph_microdatos_antes_ipc.csv`: respaldo de la base anterior; no debe incorporarse como dato de análisis vigente.
- `datos/eph_microdatos.csv`: decidir con el grupo si se versiona en Git o si cada integrante la genera localmente mediante el script de consolidación.

## 8. Pendientes generales

### Prioridad 1 — Regeneración de resultados

- [ ] Ejecutar `2_atipicos_y_no_respuesta.py` sobre la nueva base.
- [ ] Ejecutar `3_analisis_multivariado.py` sobre la nueva base.
- [ ] Ejecutar `3b_multivariado_complemento.py` sobre la nueva base.
- [ ] Ejecutar `punto_4_actualizado.py` sobre la nueva base.
- [ ] Verificar que todos los gráficos y tablas se generen en las rutas previstas.
- [ ] Actualizar las cifras y conclusiones de esta bitácora con los resultados nuevos.

### Prioridad 2 — Revisión de resultados

- [ ] Inspeccionar visualmente los dos gráficos del análisis de calidad de datos.
- [ ] Inspeccionar visualmente los nueve gráficos del análisis multivariado principal.
- [ ] Inspeccionar visualmente los siete gráficos del análisis multivariado complementario.
- [ ] Inspeccionar visualmente el gráfico de regresión e imputación del punto 4, verificando ambos paneles.
- [ ] Revisar la codificación de no respuesta, especialmente el valor `-9`, contra el diccionario oficial de la EPH.
- [ ] Revisar el filtro de edad y la interpretación de la figura `05d_boxplot_edad.png`.
- [ ] Revisar el comportamiento de las medias móviles de cuatro trimestres.
- [ ] Verificar la definición y aplicación de cuantiles ponderados.
- [ ] Revisar el mapeo de ramas de actividad según la clasificación CAES.
- [ ] Revisar la interpretación de los resultados del punto 4 y las limitaciones de la muestra seleccionada.
- [ ] Revisar la comparabilidad entre los escenarios sin imputar y con imputación, considerando que utilizan ponderadores diferentes.

### Prioridad 3 — Revisión metodológica de la deflactación

- [ ] Verificar las fuentes del IPC y los factores de deflactación, especialmente las variaciones mensuales de 2016.
- [ ] Documentar el uso de IPC-GBA como aproximación para deflactar ingresos de CABA, si se mantiene esa decisión.
- [ ] Considerar que la EPH pregunta por ingresos del mes anterior y que el uso del IPC trimestral promedio puede introducir diferencias temporales.
- [ ] Revisar la consistencia metodológica entre los distintos scripts.
- [ ] Confirmar que las variables nominales y reales se utilicen correctamente en cada análisis.

### Prioridad 4 — Git e integración grupal

- [ ] Revisar los cambios locales de Git antes de preparar cada commit.
- [ ] Excluir los archivos de referencia y respaldos que no formen parte del trabajo propio.
- [ ] Acordar con el grupo si `datos/eph_microdatos.csv` debe versionarse o generarse localmente.
- [ ] Preparar commits separados y descriptivos para los análisis y gráficos actualizados.
- [ ] Realizar push de la rama `eze-punto-1-2` cuando los cambios estén revisados.
- [ ] Mantener la rama separada de `main` hasta que el grupo acuerde su integración.

## 9. Historial de actualizaciones

Este documento deberá actualizarse cada vez que se realice una modificación relevante en los scripts, gráficos, tablas, cálculos o criterios metodológicos del proyecto.

Cada entrada debe diferenciar claramente entre cambios implementados, cambios ejecutados y cambios efectivamente validados.

Los resultados anteriores a la actualización de la base IPC no deben presentarse como definitivos cuando dependan de variables de ingresos reales recalculadas.

Los commits deberán registrarse únicamente cuando los cambios correspondientes hayan sido confirmados en Git.

La rama `eze-punto-1-2` se mantiene separada de `main` hasta que el grupo acuerde su integración.