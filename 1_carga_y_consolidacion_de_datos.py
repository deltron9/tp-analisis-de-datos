import os
import pandas as pd
import numpy as np

CARPETA_DATOS = "datos"
os.makedirs(CARPETA_DATOS, exist_ok=True)
os.environ["PYEPH_CACHE_DIR"] = os.path.abspath(CARPETA_DATOS)

import pyeph

AGLOMERADOS_ESTUDIO = [33, 32]  # Gran Buenos Aires (33) y CABA (32)
ANIO_INICIO = 2016
ANIO_FIN = 2026
RUTA_IPC = "./datos/ipc_gba_trimestral_2016T2_2026T3.csv"  # Archivo IPC-GBA empalmado (base dic 2016 = 100)

dfs_lista = []

print("=== DESCARGANDO Y CONSOLIDANDO MICRODATOS EPH (EN CARPETA DATOS) ===")

for anio in range(ANIO_INICIO, ANIO_FIN + 1):
    for trimestre in range(1, 5):
        # El trimestre 1 de 2016 no fue publicado por el INDEC
        if anio == 2016 and trimestre == 1:
            continue
            
        try:
            print(f"Obteniendo base {anio}-T{trimestre}...", end=" ")
            
            # Descarga de la base individual desde pyeph
            df_t = pyeph.obtener(
                data="eph", 
                ano=anio, 
                periodo=trimestre, 
                tipo_base="individual"
            )
            
            if df_t is not None and not df_t.empty:
                df_t.columns = [c.strip().upper() for c in df_t.columns]
                df_t["AGLOMERADO"] = pd.to_numeric(df_t["AGLOMERADO"], errors="coerce")
                
                # Filtrar solo GBA (33) y CABA (32)
                df_filtrado = df_t[df_t["AGLOMERADO"].isin(AGLOMERADOS_ESTUDIO)].copy()
                
                if not df_filtrado.empty:
                    df_filtrado["ANO4"] = anio
                    df_filtrado["TRIMESTRE"] = trimestre
                    dfs_lista.append(df_filtrado)
                    print(f"LISTO CAPO: ({len(df_filtrado)} filas agregadas)")
                else:
                    print("Sin registros para los aglomerados 33 y 32")
            else:
                print("DataFrame vacio")
                
        except Exception as e:
            print(f"No publicado o No disponible ({e})")

# AGRUPACION FINAL EN UN SOLO ARCHIVO CSV CON DEFLACTACIÓN POR IPC-GBA
if dfs_lista:
    print("\n--------------------------------------------------")
    print("Fuuuuuu sion! Haaa!")
    df_consolidado = pd.concat(dfs_lista, ignore_index=True)
    
    # 1. Cargar serie trimestral del IPC-GBA empalmado (2016-T2 a 2026-T3)
    print(f"Cargando serie trimestral del IPC-GBA desde '{RUTA_IPC}'...")
    df_ipc = pd.read_csv(RUTA_IPC)
    df_ipc.columns = [c.strip().upper() for c in df_ipc.columns]
    df_ipc["ANO4"] = pd.to_numeric(df_ipc["ANO4"], errors="coerce").astype(int)
    df_ipc["TRIMESTRE"] = pd.to_numeric(df_ipc["TRIMESTRE"], errors="coerce").astype(int)
    
    # 2. Unir IPC-GBA a los microdatos por Año y Trimestre
    df_consolidado = pd.merge(
        df_consolidado,
        df_ipc[["ANO4", "TRIMESTRE", "IPC_GBA_TRIM"]],
        on=["ANO4", "TRIMESTRE"],
        how="left"
    )
    
    # Verificar si quedó algún trimestre sin IPC
    sin_ipc = df_consolidado[df_consolidado["IPC_GBA_TRIM"].isna()][["ANO4", "TRIMESTRE"]].drop_duplicates()
    if not sin_ipc.empty:
        print("\nAVISO - Trimestres sin IPC en el CSV:", sin_ipc.to_dict("records"))
    
    # Base de actualización: último trimestre disponible en la base EPH descargada (ej. 2026-T2)
    ipc_base = df_consolidado["IPC_GBA_TRIM"].max()
    
    # 3. Calcular ingresos en términos reales (deflactados a precios constantes del cierre de la serie)
    # Preserva los valores <= 0 (0 = sin ingreso, -9 = no respuesta) sin alterarlos
    for col_ing in ["P47T", "P21", "ITF", "IPCF"]:
        if col_ing in df_consolidado.columns:
            df_consolidado[col_ing] = pd.to_numeric(df_consolidado[col_ing], errors="coerce")
            df_consolidado[f"{col_ing}_REAL"] = df_consolidado[col_ing].where(
                df_consolidado[col_ing] <= 0,
                (df_consolidado[col_ing] / df_consolidado["IPC_GBA_TRIM"]) * ipc_base
            )

    # 4. Seleccionar columnas a guardar (incluyendo ponderadores de ingreso PONDIIO y PONDII)
    cols_interes = [
        "ANO4", "TRIMESTRE", "AGLOMERADO", "ESTADO", 
        "PONDERA", "PONDIIO", "PONDII",
        "CH04", "CH06", "NIVEL_ED", "CAT_OCUP",
        "P47T", "P47T_REAL", "P21", "P21_REAL", "ITF", "ITF_REAL", "IPCF", "IPCF_REAL",
        "PP04B_COD", "PP04D_COD", "PP04C", "PP3E_TOT"
    ]
    cols_existentes = [c for c in cols_interes if c in df_consolidado.columns]
    df_final = df_consolidado[cols_existentes]
    
    archivo_salida = os.path.join(CARPETA_DATOS, "eph_microdatos.csv")
    df_final.to_csv(archivo_salida, index=False)
    
    print(f"\nTodos los trimestres se agruparon y deflactaron por IPC-GBA en: '{archivo_salida}'")
    print("\nFilas unificadas por aglomerado:")
    print(df_final["AGLOMERADO"].value_counts().rename({33: "Gran Buenos Aires", 32: "CABA"}))
    print("\nColumnas guardadas:", df_final.columns.tolist())
else:
    print("\nNo se pudieron descargar trimestres")