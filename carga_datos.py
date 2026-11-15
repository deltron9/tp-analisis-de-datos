import os
import pandas as pd

CARPETA_DATOS = "datos"
os.makedirs(CARPETA_DATOS, exist_ok=True)
os.environ["PYEPH_CACHE_DIR"] = os.path.abspath(CARPETA_DATOS)

import pyeph

AGLOMERADOS_ESTUDIO = [33, 32]  # Gran Buenos Aires (33) y CABA (32)
ANIO_INICIO = 2016
ANIO_FIN = 2026

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
                df_t['AGLOMERADO'] = pd.to_numeric(df_t['AGLOMERADO'], errors='coerce')
                
                # Filtrar solo GBA (33) y CABA (32)
                df_filtrado = df_t[df_t['AGLOMERADO'].isin(AGLOMERADOS_ESTUDIO)].copy()
                
                if not df_filtrado.empty:
                    df_filtrado['ANO4'] = anio
                    df_filtrado['TRIMESTRE'] = trimestre
                    dfs_lista.append(df_filtrado)
                    print(f"LISTO CAPO: ({len(df_filtrado)} filas agregadas)")
                else:
                    print("Sin registros para los aglomerados 33 y 32")
            else:
                print("DataFrame vacio")
                
        except Exception as e:
            print(f"No publicado o No disponible ({e})")

# AGRUPACION FINAL EN UN SOLO ARCHIVO CSV CON DEFLACTACIÓN POR CANASTAS (CBT)
if dfs_lista:
    print("\n--------------------------------------------------")
    print("Fuuuuuu sion! Haaa!")
    df_consolidado = pd.concat(dfs_lista, ignore_index=True)
    
    # 1. Descargar Canastas Básicas (CBT) desde pyeph para deflactar ingresos
    print("Descargando Canastas Básicas (CBT) desde pyeph...")
    df_canastas = pyeph.obtener(data="canastas")
    df_canastas.columns = [c.strip().upper() for c in df_canastas.columns]
    print("Columnas detectadas en canastas:", df_canastas.columns.tolist())
    
    if 'REGION' in df_canastas.columns:
        filtro_gba = df_canastas['REGION'].astype(str).str.upper().isin(['GBA', '1', 'GRAN BUENOS AIRES'])
        if filtro_gba.any():
            df_canastas = df_canastas[filtro_gba].copy()
            
    if 'PERIODO' in df_canastas.columns:
        periodo_str = df_canastas['PERIODO'].astype(str)
        df_canastas['ANO4'] = periodo_str.str.extract(r'(\d{4})').astype(int)
        if periodo_str.str.contains(r'\d{4}[\.\-]\d{1}').any():
            df_canastas['TRIMESTRE'] = periodo_str.str.extract(r'\d{4}[\.\-](\d{1})').astype(int)
        elif 'MES' in df_canastas.columns:
            df_canastas['TRIMESTRE'] = ((pd.to_numeric(df_canastas['MES']) - 1) // 3) + 1
    elif 'ANO4' in df_canastas.columns and 'TRIMESTRE' in df_canastas.columns:
        pass
    elif 'FECHA' in df_canastas.columns:
        fechas = pd.to_datetime(df_canastas['FECHA'])
        df_canastas['ANO4'] = fechas.dt.year
        df_canastas['TRIMESTRE'] = fechas.dt.quarter

    col_cbt = [c for c in df_canastas.columns if 'CBT' in c][0]
    df_canastas[col_cbt] = pd.to_numeric(df_canastas[col_cbt], errors='coerce')

    cbt_trimestral = df_canastas.groupby(['ANO4', 'TRIMESTRE'])[col_cbt].mean().reset_index()
    cbt_trimestral.rename(columns={col_cbt: 'CBT_TRIM'}, inplace=True)
    
    # 2. Unir CBT a los microdatos por Año y Trimestre
    df_consolidado = pd.merge(df_consolidado, cbt_trimestral, on=['ANO4', 'TRIMESTRE'], how='left')
    
    # Verificar si quedó algún trimestre sin CBT
    sin_cbt = df_consolidado[df_consolidado['CBT_TRIM'].isna()][['ANO4', 'TRIMESTRE']].drop_duplicates()
    if not sin_cbt.empty:
        print("\nAVISO - Trimestres sin CBT en pyeph:", sin_cbt.to_dict('records'))
    
    cbt_base = df_consolidado['CBT_TRIM'].max()
    
    # 3. Calcular ingresos en términos reales (deflactados)
    for col_ing in ['P47T', 'P21', 'ITF', 'IPCF']:
        if col_ing in df_consolidado.columns:
            df_consolidado[col_ing] = pd.to_numeric(df_consolidado[col_ing], errors='coerce')
            df_consolidado[f'{col_ing}_REAL'] = df_consolidado[col_ing].where(
                df_consolidado[col_ing] <= 0,
                (df_consolidado[col_ing] / df_consolidado['CBT_TRIM']) * cbt_base
            )

    # 4. Seleccionar columnas a guardar (incluyendo ponderadores de ingreso PONDIIO y PONDII)
    cols_interes = [
        'ANO4', 'TRIMESTRE', 'AGLOMERADO', 'ESTADO', 
        'PONDERA', 'PONDIIO', 'PONDII',
        'CH04', 'CH06', 'NIVEL_ED', 'CAT_OCUP',
        'P47T', 'P47T_REAL', 'P21', 'P21_REAL', 'ITF', 'ITF_REAL', 'IPCF', 'IPCF_REAL',
        'PP04B_COD', 'PP04D_COD', 'PP04C', 'PP3E_TOT'
    ]
    cols_existentes = [c for c in cols_interes if c in df_consolidado.columns]
    df_final = df_consolidado[cols_existentes]
    
    archivo_salida = os.path.join(CARPETA_DATOS, "eph_microdatos.csv")
    df_final.to_csv(archivo_salida, index=False)
    
    print(f"\nTodos los trimestres se agruparon y deflactaron en: '{archivo_salida}'")
    print("\nFilas unificadas por aglomerado:")
    print(df_final['AGLOMERADO'].value_counts().rename({33: 'Gran Buenos Aires', 32: 'CABA'}))
    print("\nColumnas guardadas:", df_final.columns.tolist())
else:
    print("\nNo se pudieron descargar trimestres")