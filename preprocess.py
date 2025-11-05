import pandas as pd
import sys

# --- Configuración ---

# ¡IMPORTANTE! 
# Actualicé el nombre del archivo de entrada para que coincida con tu error.
ARCHIVO_ENTRADA = "pre-process-data/2025-11-pre-process.xls"

# Nombre del archivo de salida (limpio y en formato Excel)
ARCHIVO_SALIDA = "movimientos_transformados.xlsx"

# 1. Columnas a extraer (basado en el análisis de los archivos)
# Índices (0-based): Fecha(B=1), Tarjeta(C=2), Descripción(E=4), 
#                     Ciudad(G=6), Cuotas1(H=7), Cuotas2(I=8), Monto(K=10)
COLUMNAS_INDICES = [1, 2, 4, 6, 7, 8, 10]

# 2. Nombres de las columnas en el archivo final
COLUMNAS_NUEVAS = [
    "Fecha",
    "Tipo de Tarjeta ", # Mantenemos el espacio para que coincida
    "Descripción",
    "Ciudad",
    "Cuotas",
    "Cuotas",
    "Monto ($)"
]

# 3. Número de filas a saltar al inicio
FILAS_A_SALTAR = 18

# --- Lógica del Script ---

print(f"Iniciando transformación de '{ARCHIVO_ENTRADA}'...")

try:
    # --- CAMBIO PRINCIPAL ---
    # Usamos read_excel en lugar de read_csv, ya que es un archivo .xls
    # El motor 'xlrd' es necesario para archivos .xls
    df = pd.read_excel(
        ARCHIVO_ENTRADA,
        header=None,           # El archivo no tiene un encabezado útil
        skiprows=FILAS_A_SALTAR, # Saltamos la metadata y el encabezado
        engine='xlrd'          # Especificamos el motor para .xls
    )
    print("Archivo Excel (.xls) leído exitosamente.")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo de entrada: '{ARCHIVO_ENTRADA}'")
    print("Por favor, asegúrate de que el script esté en la carpeta correcta.")
    sys.exit()
except ImportError:
    print("Error: Falta la librería 'xlrd'.")
    print("Por favor, instálala usando: pip install xlrd")
    sys.exit()
except Exception as e:
    print(f"Error inesperado al leer el archivo Excel: {e}")
    sys.exit()


try:
    # --- Verificación de Columnas ---
    max_index_requerido = max(COLUMNAS_INDICES) # El índice más alto es 10
    num_cols_leidas = df.shape[1] # Cuántas columnas leyó pandas

    if num_cols_leidas <= max_index_requerido:
        print("-" * 30)
        print(f"Error: El script esperaba encontrar al menos {max_index_requerido + 1} columnas, pero solo se leyeron {num_cols_leidas}.")
        print("Esto puede pasar si el formato del archivo del banco ha cambiado.")
        print("-" * 30)
        sys.exit()
    
    # 1. Seleccionar las columnas por su índice (posición)
    df = df.iloc[:, COLUMNAS_INDICES]

    # 2. Asignar los nombres de columna correctos
    df.columns = COLUMNAS_NUEVAS

    # 3. Limpieza de datos: Eliminar filas donde 'Fecha' esté vacío 
    # (En Excel, esto es 'NaT' o 'NaN')
    df = df.dropna(subset=['Fecha'])

    # 4. Transformar 'Fecha' (Excel a veces las lee como objetos datetime)
    # Nos aseguramos de que sean texto en formato YYYY-MM-DD o DD/MM/YYYY
    # Si la columna 'Fecha' ya es un objeto datetime:
    if pd.api.types.is_datetime64_any_dtype(df['Fecha']):
        df['Fecha'] = df['Fecha'].dt.strftime('%d/%m/%Y')
    # Si es un objeto (texto), lo dejamos tal cual.
        
    # 5. Transformar 'Monto ($)'
    df['Monto ($)'] = pd.to_numeric(df['Monto ($)'], errors='coerce').fillna(0).astype(int)

    # 6. Guardar en formato Excel (XLSX)
    df.to_excel(ARCHIVO_SALIDA, index=False, engine='openpyxl')

    print("-" * 30)
    print(f"¡Transformación completa!")
    print(f"Archivo de salida guardado como: {ARCHIVO_SALIDA}")
    print(f"Total de movimientos procesados: {len(df)}")

except Exception as e:
    print(f"\nOcurrió un error durante la transformación o guardado:")
    print(e)