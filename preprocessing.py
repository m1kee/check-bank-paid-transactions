import pandas as pd
import sys
import os
import config  # Imports our config.py file
from utils import safe_to_datetime, safe_to_int

def process_raw_file(input_path: str, output_path: str) -> bool:
    """
    Reads a raw bank XLS file, cleans it, and saves it
    as a processed XLSX file.

    Returns True if successful, False if failed.
    """
    print(f"[Processing]: Reading raw file: {input_path}")
    
    try:
        df = pd.read_excel(
            input_path,
            header=None,
            skiprows=config.ROWS_TO_SKIP,
            engine='xlrd'
        )
    except FileNotFoundError:
        print(f"Error: Input file not found: '{input_path}'", file=sys.stderr)
        return False
    except ImportError:
        print("Error: 'xlrd' library missing. Please install with: pip install xlrd", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error while reading the Excel file: {e}", file=sys.stderr)
        return False

    print("File read. Transforming data...")

    try:
        # 1. Validate that we have enough columns
        max_index = max(config.RAW_COLUMN_INDICES)
        if df.shape[1] <= max_index:
            print(f"Error: File only has {df.shape[1]} columns, {max_index + 1} are needed.", file=sys.stderr)
            return False

        # 2. Select columns
        clean_df = df.iloc[:, config.RAW_COLUMN_INDICES]

        # 3. Rename columns
        clean_df.columns = config.CLEAN_COLUMN_NAMES

        # 4. Clean data (drop rows with no Date)
        clean_df = clean_df.dropna(subset=['Date'])

        # 5. Transform data types using utils
        clean_df['Date'] = safe_to_datetime(clean_df['Date'])
        clean_df['Amount ($)'] = safe_to_int(clean_df['Amount ($)'])
        
        # 6. Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 7. Save the clean file
        clean_df.to_excel(output_path, index=False, engine='openpyxl')
        
        print(f"[Success]: Clean file saved to: {output_path}")
        print(f"Total movements processed: {len(clean_df)}")
        return True

    except Exception as e:
        print(f"An error occurred during transformation: {e}", file=sys.stderr)
        return False