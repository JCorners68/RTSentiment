#!/usr/bin/env python3
import os
import shutil
import glob

def move_files(source_dir, target_dir):
    """Move all files from source directory to target directory."""
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Find all parquet files in source directory
    files = glob.glob(f'{source_dir}/*.parquet')
    
    print(f'Found {len(files)} files to move from {source_dir} to {target_dir}')
    
    # Move each file
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        target_path = os.path.join(target_dir, filename)
        
        # Move the file
        shutil.copy2(file_path, target_path)
        
        # Print progress
        if (i+1) % 50 == 0 or i == len(files) - 1:
            print(f'Moved {i+1}/{len(files)} files...')
    
    print(f'Successfully moved all files from {source_dir} to {target_dir}')

if __name__ == '__main__':
    # Directories
    source_dir = '/app/data/output/fixed'
    target_dir = '/app/data/output/real_clean'
    
    move_files(source_dir, target_dir)