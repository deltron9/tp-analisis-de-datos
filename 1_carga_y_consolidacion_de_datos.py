import os
import sys
import tempfile
import numpy as np
import pandas as pd

import pyeph

# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_DATOS = "datos"
os.makedirs(CARPETA_DATOS, exist_ok=True)

AGLOMERADOS_ESTUDIO = [33, 32]

ANIO_INICIO = 2016
TRIMESTRE_INICIO = 2

ANIO_BASE = 2026
TRIMESTRE_BASE = 2
IPC_BASE_ESPERADO = 11580.684633

RUTA_IPC = os.path.join(
    CARPETA_DATOS,
    "ipc_gba_trimestral_2016T2_2026T3.csv"
)

ARCHIVO_SALIDA = os.path.join(
    CARPETA_DATOS,
    "eph_microdatos.csv"
)

# Columnas necesarias para los análisis principales.
COLUMNAS_OBLIGATORIAS = [
    "AGLOMERADO",
    "ESTADO",
    "PONDERA",
    "PONDIIO",
    "CH04",
    "CH06",
    "NIVEL_ED",
    "CAT_OCUP",
    "P21"
]

# Columnas que se conservarán si están disponibles.
COLUMNAS_INTERES = [
    "ANO4", "TRIMESTRE", "AGLOMERADO", "ESTADO",
    "PONDERA", "PONDIIO", "PONDII",
    "CH04", "CH06", "NIVEL_ED", "CAT_OCUP",
    "P47T", "P47T_REAL", "P21", "P21_REAL",
    "ITF", "ITF_REAL", "IPCF", "IPCF_REAL",
    "PP04B_COD", "PP04D_COD", "PP04C", "PP3E_TOT"
]

COLUMNAS_INGRESOS = ["P47T", "P21", "ITF", "IPCF"]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def generar_periodos():
    """Genera los 41 trimestres esperados de la EPH."""

    periodos = []

    for anio in range(ANIO_INICIO, ANIO_BASE + 1):
        trimestre_inicial = (
            TRIMESTRE_INICIO if anio == ANIO_INICIO else 1
        )

        trimestre_final = (
            TRIMESTRE_BASE if anio == ANIO_BASE else 4
        )

        for trimestre in range(trimestre_inicial, trimestre_final + 1):
            periodos.append((anio, trimestre))

    return periodos


def validar_columnas(df, columnas, origen):
    """Comprueba que existan las columnas obligatorias."""

    faltantes = [col for col in columnas if col not in df.columns]

    if faltantes:
        raise ValueError(
            f"Faltan columnas obligatorias en {origen}: {faltantes}"
        )


def cargar_ipc(periodos_esperados):
    """Carga y valida la serie trimestral del IPC-GBA."""

    if not os.path.isfile(RUTA_IPC):
        raise FileNotFoundError(
            f"No se encontró el archivo IPC: {RUTA_IPC}"
        )

    print(f"\nCargando IPC-GBA: {RUTA_IPC}")

    df_ipc = pd.read_csv(RUTA_IPC)
    df_ipc.columns = [col.strip().upper() for col in df_ipc.columns]

    columnas_ipc = ["ANO4", "TRIMESTRE", "IPC_GBA_TRIM"]
    validar_columnas(df_ipc, columnas_ipc, "archivo IPC")

    for col in ["ANO4", "TRIMESTRE", "IPC_GBA_TRIM"]:
        df_ipc[col] = pd.to_numeric(df_ipc[col], errors="coerce")

    if df_ipc[columnas_ipc].isna().any().any():
        raise ValueError(
            "El archivo IPC contiene valores nulos o no numéricos."
        )

    df_ipc["ANO4"] = df_ipc["ANO4"].astype(int)
    df_ipc["TRIMESTRE"] = df_ipc["TRIMESTRE"].astype(int)

    if df_ipc.duplicated(["ANO4", "TRIMESTRE"]).any():
        duplicados = df_ipc.loc[
            df_ipc.duplicated(["ANO4", "TRIMESTRE"], keep=False),
            ["ANO4", "TRIMESTRE"]
        ].drop_duplicates()

        raise ValueError(
            "Hay períodos duplicados en el archivo IPC: "
            f"{duplicados.to_dict('records')}"
        )

    if not np.isfinite(df_ipc["IPC_GBA_TRIM"]).all():
        raise ValueError("El IPC contiene valores no finitos.")

    if (df_ipc["IPC_GBA_TRIM"] <= 0).any():
        raise ValueError("El IPC contiene índices nulos o negativos.")

    periodos_ipc = set(
        zip(df_ipc["ANO4"], df_ipc["TRIMESTRE"])
    )

    faltantes = sorted(set(periodos_esperados) - periodos_ipc)

    if faltantes:
        raise ValueError(
            f"Faltan períodos IPC necesarios: {faltantes}"
        )

    df_ipc = df_ipc[
        df_ipc.apply(
            lambda fila: (
                fila["ANO4"], fila["TRIMESTRE"]
            ) in set(periodos_esperados),
            axis=1
        )
    ].copy()

    fila_base = df_ipc[
        (df_ipc["ANO4"] == ANIO_BASE)
        & (df_ipc["TRIMESTRE"] == TRIMESTRE_BASE)
    ]

    if len(fila_base) != 1:
        raise ValueError(
            "No se encontró exactamente un registro IPC para 2026-T2."
        )

    ipc_base = float(fila_base.iloc[0]["IPC_GBA_TRIM"])

    if not np.isclose(
        ipc_base,
        IPC_BASE_ESPERADO,
        rtol=0,
        atol=0.000001
    ):
        raise ValueError(
            f"IPC base incorrecto. Esperado: {IPC_BASE_ESPERADO}; "
            f"obtenido: {ipc_base}"
        )

    df_ipc = df_ipc[columnas_ipc].copy()

    print(f"Períodos IPC validados: {len(df_ipc)}")
    print(f"IPC base 2026-T2: {ipc_base:.6f}")

    return df_ipc, ipc_base


def guardar_atomico(df, ruta):
    """Escribe un CSV temporal y reemplaza el destino al finalizar."""

    directorio = os.path.dirname(ruta)

    archivo_temporal = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix="eph_microdatos_",
            dir=directorio,
            delete=False
        ) as archivo:
            archivo_temporal = archivo.name
            df.to_csv(archivo, index=False)

        os.replace(archivo_temporal, ruta)

    except Exception:
        if archivo_temporal and os.path.exists(archivo_temporal):
            os.remove(archivo_temporal)

        raise


# ============================================================
# CONSOLIDACIÓN EPH
# ============================================================

def main():
    periodos_esperados = generar_periodos()

    print("=" * 65)
    print("CONSOLIDACIÓN DE MICRODATOS EPH")
    print("=" * 65)
    print(f"Períodos esperados: {len(periodos_esperados)}")
    print(
        f"Desde {periodos_esperados[0][0]}-T{periodos_esperados[0][1]} "
        f"hasta {periodos_esperados[-1][0]}-T{periodos_esperados[-1][1]}"
    )
    print("Aglomerados: GBA (33) y CABA (32)")
    print("La base anterior no se modificará si falla alguna validación.")

    dfs_lista = []
    periodos_obtenidos = []
    errores = []

    for anio, trimestre in periodos_esperados:
        print(f"\nObteniendo base {anio}-T{trimestre}...", end=" ")

        try:
            df_t = pyeph.obtener(
                data="eph",
                ano=anio,
                periodo=trimestre,
                tipo_base="individual"
            )

            if df_t is None or df_t.empty:
                raise ValueError("La base está vacía.")

            df_t.columns = [
                col.strip().upper() for col in df_t.columns
            ]

            if "AGLOMERADO" not in df_t.columns:
                raise ValueError(
                    "La base no contiene la columna AGLOMERADO."
                )

            df_t["AGLOMERADO"] = pd.to_numeric(
                df_t["AGLOMERADO"],
                errors="coerce"
            )

            df_filtrado = df_t[
                df_t["AGLOMERADO"].isin(AGLOMERADOS_ESTUDIO)
            ].copy()

            if df_filtrado.empty:
                raise ValueError(
                    "No hay registros para CABA o GBA."
                )

            df_filtrado["ANO4"] = anio
            df_filtrado["TRIMESTRE"] = trimestre

            dfs_lista.append(df_filtrado)
            periodos_obtenidos.append((anio, trimestre))

            print(f"OK ({len(df_filtrado):,} registros)")

        except Exception as error:
            mensaje = f"{anio}-T{trimestre}: {error}"
            errores.append(mensaje)
            print(f"ERROR ({error})")

    # --------------------------------------------------------
    # VALIDAR COBERTURA TEMPORAL
    # --------------------------------------------------------

    faltantes = sorted(
        set(periodos_esperados) - set(periodos_obtenidos)
    )

    if faltantes:
        print("\nERROR: no se obtuvieron todos los trimestres.")

        for periodo in faltantes:
            print(f"  - {periodo[0]}-T{periodo[1]}")

        if errores:
            print("\nDetalle de errores:")

            for error in errores:
                print(f"  - {error}")

        raise RuntimeError(
            "Consolidación cancelada. No se modificó eph_microdatos.csv."
        )

    if len(dfs_lista) != len(periodos_esperados):
        raise RuntimeError(
            "La cantidad de bases obtenidas no coincide con "
            "los períodos esperados."
        )

    df_consolidado = pd.concat(dfs_lista, ignore_index=True)

    print("\n" + "=" * 65)
    print("VALIDACIÓN DE MICRODATOS")
    print("=" * 65)

    validar_columnas(
        df_consolidado,
        COLUMNAS_OBLIGATORIAS,
        "microdatos EPH"
    )

    df_consolidado["ANO4"] = pd.to_numeric(
        df_consolidado["ANO4"],
        errors="coerce"
    )

    df_consolidado["TRIMESTRE"] = pd.to_numeric(
        df_consolidado["TRIMESTRE"],
        errors="coerce"
    )

    if df_consolidado[["ANO4", "TRIMESTRE"]].isna().any().any():
        raise ValueError(
            "Hay años o trimestres inválidos en los microdatos."
        )

    df_consolidado["ANO4"] = df_consolidado["ANO4"].astype(int)
    df_consolidado["TRIMESTRE"] = (
        df_consolidado["TRIMESTRE"].astype(int)
    )

    periodos_finales = set(
        zip(
            df_consolidado["ANO4"],
            df_consolidado["TRIMESTRE"]
        )
    )

    if periodos_finales != set(periodos_esperados):
        raise ValueError(
            "Los períodos de los microdatos no coinciden "
            "con los 41 trimestres esperados."
        )

    if not df_consolidado["AGLOMERADO"].isin(
        AGLOMERADOS_ESTUDIO
    ).all():
        raise ValueError(
            "Se encontraron aglomerados ajenos al estudio."
        )

    print(f"Filas consolidadas: {len(df_consolidado):,}")
    print(f"Trimestres obtenidos: {len(periodos_finales)}")

    # --------------------------------------------------------
    # CARGAR Y VALIDAR IPC
    # --------------------------------------------------------

    df_ipc, ipc_base = cargar_ipc(periodos_esperados)

    # --------------------------------------------------------
    # UNIR IPC CON MICRODATOS
    # --------------------------------------------------------

    df_consolidado = df_consolidado.merge(
        df_ipc,
        on=["ANO4", "TRIMESTRE"],
        how="left",
        validate="many_to_one"
    )

    if df_consolidado["IPC_GBA_TRIM"].isna().any():
        raise ValueError(
            "Hay registros EPH sin correspondencia con el IPC."
        )

    if (df_consolidado["IPC_GBA_TRIM"] <= 0).any():
        raise ValueError(
            "Se encontraron registros con IPC nulo o negativo."
        )

    # --------------------------------------------------------
    # DEFLACTAR INGRESOS
    # --------------------------------------------------------

    print("\nCalculando ingresos a precios constantes de 2026-T2...")

    for col_ing in COLUMNAS_INGRESOS:
        if col_ing not in df_consolidado.columns:
            raise ValueError(
                f"No se encuentra la variable de ingreso {col_ing}."
            )

        df_consolidado[col_ing] = pd.to_numeric(
            df_consolidado[col_ing],
            errors="coerce"
        )

        df_consolidado[f"{col_ing}_REAL"] = (
            df_consolidado[col_ing].where(
                df_consolidado[col_ing] <= 0,
                (
                    df_consolidado[col_ing]
                    / df_consolidado["IPC_GBA_TRIM"]
                ) * ipc_base
            )
        )

        positivos = df_consolidado[col_ing] > 0

        if not np.isfinite(
            df_consolidado.loc[
                positivos,
                f"{col_ing}_REAL"
            ]
        ).all():
            raise ValueError(
                f"Se generaron valores no finitos en {col_ing}_REAL."
            )

    # --------------------------------------------------------
    # VERIFICAR COEFICIENTES DE DEFLACTACIÓN
    # --------------------------------------------------------

    print("\nVerificando coeficientes de deflactación...")

    coeficientes = (
        ipc_base / df_ipc["IPC_GBA_TRIM"]
    )

    df_coef = df_ipc[
        ["ANO4", "TRIMESTRE"]
    ].copy()

    df_coef["COEF_ESPERADO"] = coeficientes.to_numpy()

    df_consolidado = df_consolidado.merge(
        df_coef,
        on=["ANO4", "TRIMESTRE"],
        how="left",
        validate="many_to_one"
    )

    if df_consolidado["COEF_ESPERADO"].isna().any():
        raise ValueError(
            "No se pudieron asignar todos los coeficientes."
        )

    positivos_p21 = df_consolidado["P21"] > 0

    if positivos_p21.any():
        ratios = (
            df_consolidado.loc[positivos_p21, "P21_REAL"]
            / df_consolidado.loc[positivos_p21, "P21"]
        )

        coef_esperado = df_consolidado.loc[
            positivos_p21,
            "COEF_ESPERADO"
        ]

        if not np.allclose(
            ratios.to_numpy(),
            coef_esperado.to_numpy(),
            rtol=1e-9,
            atol=1e-9
        ):
            raise ValueError(
                "La verificación de P21_REAL/P21 no coincide "
                "con los coeficientes IPC."
            )

    print("Coeficientes verificados correctamente.")

    # --------------------------------------------------------
    # SELECCIONAR COLUMNAS
    # --------------------------------------------------------

    columnas_faltantes = [
        col for col in COLUMNAS_OBLIGATORIAS
        if col not in df_consolidado.columns
    ]

    if columnas_faltantes:
        raise ValueError(
            f"Faltan columnas obligatorias: {columnas_faltantes}"
        )

    cols_existentes = [
        col for col in COLUMNAS_INTERES
        if col in df_consolidado.columns
    ]

    df_final = df_consolidado[cols_existentes].copy()

    if df_final.empty:
        raise ValueError("La base final está vacía.")

    if len(df_final) != len(df_consolidado):
        raise ValueError(
            "La selección de columnas alteró la cantidad de filas."
        )

    # --------------------------------------------------------
    # GUARDADO SEGURO
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("VALIDACIONES SUPERADAS")
    print("=" * 65)

    print(f"Filas finales: {len(df_final):,}")
    print(f"Columnas finales: {len(df_final.columns)}")
    print(f"IPC base: {ipc_base:.6f}")

    print("\nRegistros por aglomerado:")

    print(
        df_final["AGLOMERADO"]
        .value_counts()
        .rename({
            33: "Gran Buenos Aires",
            32: "CABA"
        })
    )

    print("\nColumnas guardadas:")
    print(df_final.columns.tolist())

    guardar_atomico(df_final, ARCHIVO_SALIDA)

    print("\n" + "=" * 65)
    print("CONSOLIDACIÓN FINALIZADA")
    print("=" * 65)
    print(f"Archivo generado: {ARCHIVO_SALIDA}")
    print(f"Registros: {len(df_final):,}")
    print("Base monetaria: precios constantes de 2026-T2.")
    print("El archivo anterior fue reemplazado después de validar todo.")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\n" + "=" * 65)
        print("PROCESO CANCELADO")
        print("=" * 65)
        print(f"Motivo: {error}")
        print(
            "\nNo se generó una nueva base definitiva. "
            "El CSV anterior permanece sin modificaciones."
        )
        sys.exit(1)