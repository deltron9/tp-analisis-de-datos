import os
import pandas as pd

CARPETA_DATOS = "datos"
os.makedirs(CARPETA_DATOS, exist_ok=True)
os.environ["PYEPH_CACHE_DIR"] = os.path.abspath(CARPETA_DATOS)

import pyeph

AGLOMERADOS_ESTUDIO = [33, 8]  # Gran Buenos Aires (33) y Mar del Plata (8)
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
            
            #descarga de la base individual desde pyeph
            df_t = pyeph.obtener(
                data="eph", 
                ano=anio, 
                periodo=trimestre, 
                tipo_base="individual"
            )
            
            if df_t is not None and not df_t.empty:
                #estandarizado de nombres de columnas a mayúsculas
                df_t.columns = [c.upper() for c in df_t.columns]
                
                #conversion de la columna de aglomerado a numérica
                df_t['AGLOMERADO'] = pd.to_numeric(df_t['AGLOMERADO'], errors='coerce')
                
                #filtrar solo GBA y MDP
                df_filtrado = df_t[df_t['AGLOMERADO'].isin(AGLOMERADOS_ESTUDIO)].copy()
                
                if not df_filtrado.empty:
                    df_filtrado['ANO4'] = anio
                    df_filtrado['TRIMESTRE'] = trimestre
                    
                    #se agrega al listado en memoria
                    dfs_lista.append(df_filtrado)
                    print(f"LISTO CAPO: ({len(df_filtrado)} filas agregadas)")
                else:
                    print("Sin registros para los aglomerados 33 y 8")
            else:
                print("DataFrame vacio")
                
        except Exception as e:
            print(f"No publicado o No disponible ({e})")

#AGRUPACION FINAL EN UN SOLO ARCHIVO CSV
if dfs_lista:
    print("\n--------------------------------------------------")
    print("Fuuuuuu sion! Haaa!")
    df_consolidado = pd.concat(dfs_lista, ignore_index=True)
    
    #variables principales
    cols_interes = [
        'ANO4', 'TRIMESTRE', 'AGLOMERADO', 'ESTADO', 'PONDERA', 
        'P21', 'ITF', 'IPCF', 'CH04', 'CH06'
    ]
    cols_existentes = [c for c in cols_interes if c in df_consolidado.columns]
    df_final = df_consolidado[cols_existentes]
    
    archivo_salida = os.path.join(CARPETA_DATOS, "eph_microdatos.csv")
    df_final.to_csv(archivo_salida, index=False)
    
    print(f"\nTodos los trimestres se agruparon en: '{archivo_salida}'")
    print("\nFilas unificadas por aglomerado:")
    print(df_final['AGLOMERADO'].value_counts().rename({33: 'Gran Buenos Aires', 8: 'Mar del Plata'}))
else:
    print("\nNo se pudieron descargar trimestres")