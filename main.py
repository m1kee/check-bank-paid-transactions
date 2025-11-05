import sys
import os
import argparse
import datetime  # Import the datetime module
import config    # Import our config to get the archive folder
from preprocessing import process_raw_file
from analysis import analyze_movements

def main():
    """
    Main function that orchestrates the entire workflow of
    pre-processing and analysis.
    """
    print("=============================================")
    print("========= Account Analysis Tool =========")
    print("=============================================\n")
    
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(description="Processes and analyzes bank movement files.")
    
    parser.add_argument(
        "input_file", 
        type=str,
        help="Path to the raw bank XLS/CSV file. (Ex: 'pre-process-data/my_file.xls')"
    )
    
    parser.add_argument(
        "-o", "--output",
        dest="output_prefix",  # Changed from output_file to output_prefix
        type=str,
        help="Optional prefix for the clean output file. (Ex: 'my_report')"
    )
    
    args = parser.parse_args()
    
    # --- NEW NAMING LOGIC ---
    
    # 2. Generate a single, unique timestamp for this run
    # Format: YYYY-MM-DD_HHMMSS (e.g., 2025-11-04_233000)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # 3. Determine the final Output (Cleaned) file path
    input_path = args.input_file
    
    if args.output_prefix:
        # User provided a prefix (e.g., "my_report")
        prefix, _ = os.path.splitext(args.output_prefix) # Remove extension if user adds one
    else:
        # Default prefix
        prefix = "cleaned-movements"
    
    output_filename = f"{prefix}_{timestamp}.xlsx"
    output_path = os.path.join("data", output_filename)

    # 4. Determine the final Archive (Raw) file path
    # We will move the original input file to this new path after processing
    original_base, original_ext = os.path.splitext(os.path.basename(input_path))
    archive_filename = f"movements_{timestamp}{original_ext}" # e.g., movements_..._233000.xls
    archive_path = os.path.join(config.PROCESSED_ARCHIVE_FOLDER, archive_filename)

    # 5. Ensure directories exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(config.PROCESSED_ARCHIVE_FOLDER, exist_ok=True)
    
    print(f"Input file: {input_path}")
    print(f"Clean file will be saved as: {output_path}")
    print(f"Raw file will be archived to: {archive_path}\n")

    # --- END NEW NAMING LOGIC ---

    # 6. Execute the workflow
    
    # --- PART 1: PRE-PROCESSING ---
    success = process_raw_file(input_path, output_path)
    
    if not success:
        print("\nPre-processing failed. Cannot continue with analysis.", file=sys.stderr)
        sys.exit(1)
        
    # --- NEW: Archive Input File ---
    try:
        # Move the original file to the archive folder with its new name
        os.rename(input_path, archive_path)
        print(f"\nSuccessfully archived input file to: {archive_path}")
    except Exception as e:
        print(f"\nWarning: Could not archive input file '{input_path}'. Error: {e}", file=sys.stderr)
        # We don't exit here, as the analysis can still run
        
    # --- PART 2: ANALYSIS ---
    analyze_movements(output_path)
    
    print("\nWorkflow complete.")

if __name__ == "__main__":
    main()