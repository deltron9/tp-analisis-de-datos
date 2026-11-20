
# Bitácora de cambios — TP Análisis de Datos EPH

## 1. Objetivo

Registrar las modificaciones, correcciones y decisiones técnicas realizadas durante el desarrollo del trabajo práctico de Introducción al Análisis de Datos.

El objetivo es mantener la trazabilidad de los cambios, documentar sus fundamentos y evitar modificaciones repetidas o contradictorias entre los integrantes del grupo.

## 2. Criterios de registro

Cada modificación relevante deberá documentarse indicando:

- **Fecha:** cuándo se realizó.
- **Archivo:** archivo afectado.
- **Motivo:** problema detectado o necesidad del cambio.
- **Modificación:** qué se cambió.
- **Justificación:** fundamento técnico o metodológico.
- **Validación:** pruebas realizadas y resultados obtenidos.
- **Estado:** pendiente, implementado o validado.
- **Commit:** identificador del commit, si corresponde.

Un cambio no debe considerarse validado únicamente porque el código haya sido modificado. También debe ejecutarse y revisarse su resultado.

## 3. Contexto del proyecto

- **Fuente de datos:** Encuesta Permanente de Hogares (EPH).
- **Período de análisis:** 2016–2026.
- **Aglomerados:** CABA (32) y Partidos del GBA (33).
- **Frecuencia temporal:** trimestral para los gráficos de evolución.
- **Rama de trabajo:** `eze-punto-1-2`.
- **Rama principal grupal:** `main`.

Consideraciones temporales:
- 2016 comienza en el segundo trimestre (T2).
- 2026 finaliza en el segundo trimestre (T2).
- Los años 2016 y 2026 son períodos parciales.

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

**Validación:**

El usuario ejecutó el script sin errores.

**Estado:** Implementado y ejecutado.

**Commit:** `e9c0a49` — `update: complemento punto 2 con series trimestrales`.

---

### 20/11/2026 — Revisión del análisis multivariado principal

**Archivo:** `3_analisis_multivariado.py`

**Motivo:**

Revisar la adaptación trimestral realizada por otro integrante y detectar posibles problemas antes de incorporarla definitivamente.

**Correcciones pendientes:**

1. Corregir los intervalos de edad de la figura 05e para evitar incluir menores de 15 años y excluir edades superiores a 100.
2. Corregir el filtrado de datos del boxplot de la figura 05e para mantener alineados los ingresos y los grupos etarios.
3. Robustecer la función `weighted_quantiles`, contemplando valores nulos, infinitos, pesos inválidos y grupos vacíos.
4. Revisar el cálculo de las medias móviles de cuatro trimestres. Actualmente se utiliza `min_periods=2`, lo que permite calcular valores con menos de cuatro observaciones.
5. Verificar que las medias móviles contemplen trimestres consecutivos y no solamente cuatro observaciones disponibles.

**Estado:** Revisión realizada. Correcciones pendientes de implementación y validación.

## 5. Pendientes generales

- [ ] Corregir y validar la figura 05e del análisis multivariado.
- [ ] Robustecer las funciones de cuantiles ponderados.
- [ ] Revisar el cálculo de medias móviles trimestrales.
- [ ] Ejecutar nuevamente `3_analisis_multivariado.py`.
- [ ] Inspeccionar visualmente los gráficos generados.
- [ ] Revisar el script del punto 4 y sus métricas.
- [ ] Verificar las fuentes y los cálculos utilizados para deflactar ingresos.
- [ ] Revisar la consistencia metodológica entre los distintos scripts.
- [ ] Mantener sincronizada la rama de trabajo sin integrar cambios a `main` hasta acordarlo con el grupo.

## 6. Historial de actualizaciones

Este documento deberá actualizarse cada vez que se realice una modificación relevante en los scripts, gráficos, tablas, cálculos o criterios metodológicos del proyecto.

Cada entrada debe diferenciar claramente entre cambios implementados, cambios ejecutados y cambios efectivamente validados.
