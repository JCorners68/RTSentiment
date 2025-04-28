import pandas as pd
import glob
import os
from pathlib import Path

def deduplicate_parquet(input_path, output_path=None, columns=None, keep='first'):
    """
    Deduplicate a parquet file or directory of parquet files.
    
    Parameters:
    -----------
    input_path : str
        Path to a parquet file or directory containing parquet files
    output_path : str, optional
        Path to save deduplicated file(s). If None, will overwrite original.
    columns : list, optional
        Columns to consider for duplication. If None, uses all columns.
    keep : {'first', 'last', False}, default 'first'
        Which duplicates to keep:
        - 'first': Keep first occurrence of duplicates
        - 'last': Keep last occurrence of duplicates
        - False: Drop all duplicates
    
    Returns:
    --------
    int: Number of duplicate rows removed
    """
    print(f"Starting deduplication process...")
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path if output_path else 'Same as input (overwrite)'}")
    
    total_dups_removed = 0
    
    # Handle single file case
    if os.path.isfile(input_path):
        print(f"Reading parquet file: {input_path}")
        df = pd.read_parquet(input_path)
        original_len = len(df)
        print(f"Original dataframe has {original_len} rows")
        
        df = df.drop_duplicates(subset=columns, keep=keep)
        dups_removed = original_len - len(df)
        print(f"Found and removed {dups_removed} duplicate rows")
        
        save_path = output_path if output_path else input_path
        print(f"Saving deduplicated data to: {save_path}")
        df.to_parquet(save_path, index=False)
        print(f"Deduplication complete. New dataframe has {len(df)} rows")
        
        return dups_removed
    
    # Handle directory case
    elif os.path.isdir(input_path):
        if output_path and not os.path.exists(output_path):
            os.makedirs(output_path)
            
        parquet_files = glob.glob(os.path.join(input_path, "*.parquet"))
        print(f"Found {len(parquet_files)} parquet files in directory")
        
        for file in parquet_files:
            print(f"Processing file: {file}")
            df = pd.read_parquet(file)
            original_len = len(df)
            df = df.drop_duplicates(subset=columns, keep=keep)
            file_dups_removed = original_len - len(df)
            total_dups_removed += file_dups_removed
            
            if output_path:
                filename = os.path.basename(file)
                save_path = os.path.join(output_path, filename)
            else:
                save_path = file
                
            df.to_parquet(save_path, index=False)
            
            print(f"Processed {file}: Removed {file_dups_removed} duplicates")
            
        return total_dups_removed
    
    else:
        print(f"ERROR: Input path {input_path} is not a valid file or directory")
        raise ValueError(f"Input path {input_path} is not a valid file or directory")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deduplicate parquet files")
    parser.add_argument("input_path", help="Path to parquet file or directory of parquet files")
    parser.add_argument("--output_path", help="Output path for deduplicated files")
    parser.add_argument("--columns", nargs="+", help="Columns to consider for duplication")
    parser.add_argument("--keep", choices=['first', 'last', 'none'], default='first',
                       help="Which duplicates to keep: first, last, or none")
    
    args = parser.parse_args()
    
    # Fix for positional arguments
    if len(args.input_path.split()) > 1:
        input_parts = args.input_path.split()
        args.input_path = input_parts[0]
        if not args.output_path and len(input_parts) > 1:
            args.output_path = input_parts[1]
    
    print("Arguments:")
    print(f"  Input path: {args.input_path}")
    print(f"  Output path: {args.output_path}")
    print(f"  Columns: {args.columns}")
    print(f"  Keep: {args.keep}")
    
    keep_value = False if args.keep == 'none' else args.keep
    
    try:
        dups_removed = deduplicate_parquet(args.input_path, args.output_path, args.columns, keep_value)
        print(f"Total duplicates removed: {dups_removed}")
        print("Deduplication completed successfully!")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()