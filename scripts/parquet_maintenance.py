#!/usr/bin/env python3
"""
Parquet maintenance utilities for RTSentiment.

This script provides maintenance operations for Parquet files, including:
1. Data retention policies
2. File compaction and optimization
3. Validation and repair
4. Backup and recovery
5. Scheduled maintenance tasks

It can be run directly or as a scheduled task, and supports various
command-line options for different maintenance operations.
"""

import argparse
import glob
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("parquet_maintenance.log")
    ]
)
logger = logging.getLogger("parquet_maintenance")


class ParquetMaintenance:
    """
    Utility class for Parquet file maintenance operations.
    """
    
    def __init__(self, 
                 data_dir: str = None, 
                 backup_dir: str = None, 
                 max_age_days: int = 365,
                 compression: str = 'snappy',
                 row_group_size: int = 100000):
        """
        Initialize the maintenance utility.
        
        Args:
            data_dir: Directory containing Parquet files
            backup_dir: Directory for backups
            max_age_days: Maximum age for data retention in days
            compression: Compression codec for optimized files
            row_group_size: Row group size for optimized files
        """
        # Set default data directory if not provided
        if data_dir is None:
            self.data_dir = os.path.join(os.getcwd(), "data", "output")
        else:
            self.data_dir = data_dir
            
        # Set default backup directory if not provided
        if backup_dir is None:
            self.backup_dir = os.path.join(os.getcwd(), "data", "backup")
        else:
            self.backup_dir = backup_dir
            
        # Create directories if they don't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Set parameters
        self.max_age_days = max_age_days
        self.compression = compression
        self.row_group_size = row_group_size
        
        # Initialize stats
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "errors": 0,
            "space_saved": 0,
            "records_processed": 0,
            "start_time": time.time(),
            "end_time": None,
            "operations": {},
        }
        
        logger.info(f"Initialized ParquetMaintenance with data directory: {self.data_dir}")
        logger.info(f"Backup directory: {self.backup_dir}")
        logger.info(f"Max age days: {self.max_age_days}")
        logger.info(f"Compression: {self.compression}")
        logger.info(f"Row group size: {self.row_group_size}")
    
    def list_parquet_files(self) -> List[str]:
        """
        List all Parquet files in the data directory.
        
        Returns:
            List of Parquet file paths
        """
        file_pattern = os.path.join(self.data_dir, "*_sentiment.parquet")
        files = glob.glob(file_pattern)
        self.stats["total_files"] = len(files)
        return files
    
    def apply_retention_policy(self, dry_run: bool = False) -> int:
        """
        Apply data retention policy by archiving old data.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Number of files archived
        """
        logger.info(f"Applying retention policy (max age: {self.max_age_days} days)")
        
        # Start operation stats
        op_name = "retention_policy"
        self.stats["operations"][op_name] = {
            "started": time.time(),
            "completed": None,
            "files_processed": 0,
            "files_archived": 0,
            "space_freed": 0
        }
        
        # Get cut-off date
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # Process files
        archived_count = 0
        space_freed = 0
        files = self.list_parquet_files()
        
        for file_path in files:
            try:
                # Get file modification time
                file_mtime = os.path.getmtime(file_path)
                file_size = os.path.getsize(file_path)
                
                # Check if file is older than cut-off
                if file_mtime < cutoff_timestamp:
                    file_name = os.path.basename(file_path)
                    archive_path = os.path.join(self.backup_dir, file_name)
                    
                    logger.info(f"File {file_name} is older than {self.max_age_days} days")
                    
                    if not dry_run:
                        # Create timestamped archive file
                        timestamp = datetime.fromtimestamp(file_mtime).strftime("%Y%m%d")
                        archive_path = os.path.join(self.backup_dir, f"{timestamp}_{file_name}")
                        
                        # Copy file to archive
                        shutil.copy2(file_path, archive_path)
                        logger.info(f"Archived {file_name} to {archive_path}")
                        
                        # Remove original file
                        os.remove(file_path)
                        logger.info(f"Removed original file {file_path}")
                        
                        archived_count += 1
                        space_freed += file_size
                    else:
                        logger.info(f"Would archive {file_name} to {archive_path} (dry run)")
                        archived_count += 1
                        space_freed += file_size
                
                self.stats["operations"][op_name]["files_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self.stats["errors"] += 1
        
        # Update stats
        self.stats["operations"][op_name]["completed"] = time.time()
        self.stats["operations"][op_name]["files_archived"] = archived_count
        self.stats["operations"][op_name]["space_freed"] = space_freed
        self.stats["space_saved"] += space_freed
        
        logger.info(f"Retention policy applied: {archived_count} files archived, {space_freed} bytes freed")
        return archived_count
    
    def optimize_file(self, file_path: str, dry_run: bool = False) -> int:
        """
        Optimize a single Parquet file.
        
        Args:
            file_path: Path to the Parquet file
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Bytes saved by optimization
        """
        logger.info(f"Optimizing file: {file_path}")
        
        try:
            # Get original file size
            original_size = os.path.getsize(file_path)
            
            if dry_run:
                logger.info(f"Would optimize {file_path} (dry run)")
                return 0
            
            # Read the Parquet file
            table = pq.read_table(file_path)
            
            # Create a temporary file path
            temp_path = f"{file_path}.optimized"
            
            # Write the file with optimized settings
            pq.write_table(
                table,
                temp_path,
                compression=self.compression,
                row_group_size=self.row_group_size
            )
            
            # Get optimized file size
            optimized_size = os.path.getsize(temp_path)
            
            # Calculate space savings
            space_saved = original_size - optimized_size
            
            if space_saved > 0:
                # Make backup of original file
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
                
                # Replace original with optimized file
                os.replace(temp_path, file_path)
                
                # Remove backup after successful operation
                os.remove(backup_path)
                
                logger.info(f"Optimized {file_path}, saved {space_saved} bytes")
                return space_saved
            else:
                # If no space saved, remove the temporary file
                os.remove(temp_path)
                logger.info(f"No optimization benefit for {file_path}")
                return 0
                
        except Exception as e:
            logger.error(f"Error optimizing file {file_path}: {e}")
            self.stats["errors"] += 1
            
            # Clean up temporary file if it exists
            temp_path = f"{file_path}.optimized"
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return 0
    
    def compact_files(self, dry_run: bool = False) -> int:
        """
        Compact and optimize Parquet files.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Total bytes saved
        """
        logger.info("Starting file compaction and optimization")
        
        # Start operation stats
        op_name = "compaction"
        self.stats["operations"][op_name] = {
            "started": time.time(),
            "completed": None,
            "files_processed": 0,
            "files_optimized": 0,
            "space_saved": 0
        }
        
        # Process files
        total_saved = 0
        files = self.list_parquet_files()
        
        for file_path in files:
            try:
                # Optimize the file
                saved = self.optimize_file(file_path, dry_run)
                
                if saved > 0:
                    self.stats["operations"][op_name]["files_optimized"] += 1
                    self.stats["operations"][op_name]["space_saved"] += saved
                    total_saved += saved
                
                self.stats["operations"][op_name]["files_processed"] += 1
                self.stats["processed_files"] += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self.stats["errors"] += 1
        
        # Update stats
        self.stats["operations"][op_name]["completed"] = time.time()
        self.stats["space_saved"] += total_saved
        
        logger.info(f"Compaction completed: {total_saved} bytes saved")
        return total_saved
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a Parquet file for integrity and data quality.
        
        Args:
            file_path: Path to the Parquet file
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        logger.info(f"Validating file: {file_path}")
        issues = []
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                issues.append(f"File does not exist: {file_path}")
                return False, issues
            
            # Try to read metadata
            try:
                metadata = pq.read_metadata(file_path)
                row_groups = metadata.num_row_groups
                num_rows = metadata.num_rows
                
                if row_groups == 0:
                    issues.append(f"File has 0 row groups")
                
                if num_rows == 0:
                    issues.append(f"File has 0 rows")
                    
            except Exception as e:
                issues.append(f"Metadata read error: {str(e)}")
                return False, issues
            
            # Try to read the actual data
            try:
                table = pq.read_table(file_path)
                
                # Check for required columns
                required_columns = ["timestamp", "ticker", "sentiment"]
                for col in required_columns:
                    if col not in table.column_names:
                        found = False
                        # Check for alternate column names
                        for alt_col in ["time", "date", "symbol", "stock", "sentiment_score", "score"]:
                            if alt_col in table.column_names:
                                found = True
                                break
                        
                        if not found:
                            issues.append(f"Missing required column: {col}")
                
                # Check for null values in critical columns
                for col in table.column_names:
                    if col in required_columns or col in ["time", "date", "symbol", "stock", "sentiment_score", "score"]:
                        column = table.column(col)
                        null_count = column.null_count
                        if null_count > 0:
                            issues.append(f"Column {col} has {null_count} null values")
                
            except Exception as e:
                issues.append(f"Data read error: {str(e)}")
                return False, issues
            
            # If we got here with no issues, file is valid
            if not issues:
                return True, issues
            else:
                return False, issues
                
        except Exception as e:
            issues.append(f"Validation error: {str(e)}")
            return False, issues
    
    def repair_file(self, file_path: str, issues: List[str], dry_run: bool = False) -> bool:
        """
        Attempt to repair a Parquet file.
        
        Args:
            file_path: Path to the Parquet file
            issues: List of identified issues
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            True if repairs were successful
        """
        logger.info(f"Attempting to repair file: {file_path}")
        
        if dry_run:
            logger.info(f"Would repair {file_path} (dry run)")
            return True
        
        try:
            # Create backup of original file
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)
            
            # Read data if possible
            try:
                table = pq.read_table(file_path)
                df = table.to_pandas()
            except Exception:
                # Try partial reading if full read fails
                try:
                    # Try reading individual row groups
                    file_reader = pq.ParquetFile(file_path)
                    dfs = []
                    
                    for i in range(file_reader.num_row_groups):
                        try:
                            row_group = file_reader.read_row_group(i)
                            dfs.append(row_group.to_pandas())
                        except Exception as e:
                            logger.warning(f"Skipping corrupted row group {i}: {e}")
                    
                    if dfs:
                        df = pd.concat(dfs, ignore_index=True)
                    else:
                        logger.error(f"Could not recover any data from {file_path}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Could not recover data from {file_path}: {e}")
                    return False
            
            # Fix common issues
            
            # 1. Fix missing required columns with defaults
            required_columns = {
                "timestamp": lambda df: datetime.now().isoformat(),
                "ticker": lambda df: os.path.basename(file_path).split("_")[0].upper(),
                "sentiment": lambda df: 0.0
            }
            
            for col, default_fn in required_columns.items():
                # Check if column exists under any name
                found = False
                for alt_col in ["timestamp", "time", "date", "ticker", "symbol", "stock", "sentiment", "sentiment_score", "score"]:
                    if alt_col in df.columns and alt_col.split("_")[0] == col.split("_")[0]:
                        found = True
                        # Rename to standard column name if needed
                        if alt_col != col:
                            df[col] = df[alt_col]
                        break
                
                # Add column with default value if missing
                if not found:
                    df[col] = default_fn(df)
            
            # 2. Fix null values
            for col in required_columns:
                if col in df.columns:
                    # Replace nulls with appropriate defaults
                    if col == "timestamp":
                        df[col] = df[col].fillna(datetime.now().isoformat())
                    elif col == "ticker":
                        ticker = os.path.basename(file_path).split("_")[0].upper()
                        df[col] = df[col].fillna(ticker)
                    elif col == "sentiment":
                        df[col] = df[col].fillna(0.0)
                    else:
                        df[col] = df[col].fillna("")
            
            # 3. Fix timestamp format if needed
            if "timestamp" in df.columns:
                if df["timestamp"].dtype != 'datetime64[ns]':
                    try:
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                    except Exception:
                        # If conversion fails, replace with current time
                        df["timestamp"] = datetime.now()
                        
                # Convert datetime to ISO format string
                df["timestamp"] = df["timestamp"].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            # 4. Ensure ticker is standardized
            if "ticker" in df.columns:
                df["ticker"] = df["ticker"].str.upper()
            
            # Write repaired file
            temp_path = f"{file_path}.repaired"
            table = pa.Table.from_pandas(df)
            
            pq.write_table(
                table,
                temp_path,
                compression=self.compression,
                row_group_size=self.row_group_size
            )
            
            # Validate the repaired file
            is_valid, new_issues = self.validate_file(temp_path)
            
            if is_valid:
                # Replace original with repaired file
                os.replace(temp_path, file_path)
                logger.info(f"Successfully repaired {file_path}")
                return True
            else:
                logger.error(f"Repair attempt did not fix all issues: {new_issues}")
                logger.info(f"Restoring from backup")
                os.replace(backup_path, file_path)
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
                return False
                
        except Exception as e:
            logger.error(f"Error repairing file {file_path}: {e}")
            
            # Restore from backup if it exists
            backup_path = f"{file_path}.bak"
            if os.path.exists(backup_path):
                os.replace(backup_path, file_path)
                
            # Clean up temporary file if it exists
            temp_path = f"{file_path}.repaired"
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return False
    
    def validate_and_repair(self, dry_run: bool = False) -> Tuple[int, int]:
        """
        Validate and repair Parquet files.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Tuple of (files with issues, files repaired)
        """
        logger.info("Starting file validation and repair")
        
        # Start operation stats
        op_name = "validation"
        self.stats["operations"][op_name] = {
            "started": time.time(),
            "completed": None,
            "files_processed": 0,
            "files_with_issues": 0,
            "files_repaired": 0
        }
        
        # Process files
        files_with_issues = 0
        files_repaired = 0
        files = self.list_parquet_files()
        
        for file_path in files:
            try:
                # Validate the file
                is_valid, issues = self.validate_file(file_path)
                
                if not is_valid:
                    files_with_issues += 1
                    self.stats["operations"][op_name]["files_with_issues"] += 1
                    
                    logger.warning(f"File {file_path} has issues: {issues}")
                    
                    # Attempt to repair
                    if self.repair_file(file_path, issues, dry_run):
                        files_repaired += 1
                        self.stats["operations"][op_name]["files_repaired"] += 1
                
                self.stats["operations"][op_name]["files_processed"] += 1
                self.stats["processed_files"] += 1
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self.stats["errors"] += 1
        
        # Update stats
        self.stats["operations"][op_name]["completed"] = time.time()
        
        logger.info(f"Validation completed: {files_with_issues} files with issues, {files_repaired} files repaired")
        return files_with_issues, files_repaired
    
    def create_backup(self, backup_name: str = None, dry_run: bool = False) -> str:
        """
        Create a backup of all Parquet files.
        
        Args:
            backup_name: Custom name for backup directory
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Path to backup directory
        """
        logger.info("Creating backup of Parquet files")
        
        # Start operation stats
        op_name = "backup"
        self.stats["operations"][op_name] = {
            "started": time.time(),
            "completed": None,
            "files_processed": 0,
            "backup_size": 0
        }
        
        # Create backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if backup_name:
            backup_dir = os.path.join(self.backup_dir, f"{backup_name}_{timestamp}")
        else:
            backup_dir = os.path.join(self.backup_dir, f"parquet_backup_{timestamp}")
        
        if not dry_run:
            os.makedirs(backup_dir, exist_ok=True)
        
        # Copy files
        files = self.list_parquet_files()
        total_size = 0
        
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(backup_dir, file_name)
                file_size = os.path.getsize(file_path)
                total_size += file_size
                
                if not dry_run:
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Backed up {file_name} to {dest_path}")
                else:
                    logger.info(f"Would back up {file_name} to {dest_path} (dry run)")
                
                self.stats["operations"][op_name]["files_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error backing up file {file_path}: {e}")
                self.stats["errors"] += 1
        
        # Create metadata file
        backup_info = {
            "timestamp": timestamp,
            "files": len(files),
            "total_size": total_size
        }
        
        if not dry_run:
            with open(os.path.join(backup_dir, "backup_info.json"), "w") as f:
                json.dump(backup_info, f, indent=2)
        
        # Update stats
        self.stats["operations"][op_name]["completed"] = time.time()
        self.stats["operations"][op_name]["backup_size"] = total_size
        
        logger.info(f"Backup completed: {len(files)} files backed up, {total_size} bytes total")
        return backup_dir
    
    def restore_backup(self, backup_dir: str, dry_run: bool = False) -> int:
        """
        Restore from a backup.
        
        Args:
            backup_dir: Path to backup directory
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Number of files restored
        """
        logger.info(f"Restoring from backup: {backup_dir}")
        
        # Start operation stats
        op_name = "restore"
        self.stats["operations"][op_name] = {
            "started": time.time(),
            "completed": None,
            "files_processed": 0,
            "files_restored": 0
        }
        
        # Verify backup directory
        if not os.path.exists(backup_dir):
            logger.error(f"Backup directory not found: {backup_dir}")
            return 0
        
        # Check for backup info
        info_path = os.path.join(backup_dir, "backup_info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r") as f:
                    backup_info = json.load(f)
                logger.info(f"Found backup info: {backup_info}")
            except Exception:
                logger.warning("Could not read backup info")
                backup_info = {}
        else:
            backup_info = {}
        
        # List backup files
        files = glob.glob(os.path.join(backup_dir, "*_sentiment.parquet"))
        
        if not files:
            logger.error(f"No Parquet files found in backup directory: {backup_dir}")
            return 0
        
        # Create a temporary backup of current files before restoring
        if not dry_run:
            temp_backup = self.create_backup("pre_restore", dry_run=False)
            logger.info(f"Created temporary backup of current files: {temp_backup}")
        
        # Restore files
        files_restored = 0
        
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(self.data_dir, file_name)
                
                if not dry_run:
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Restored {file_name} to {dest_path}")
                    files_restored += 1
                else:
                    logger.info(f"Would restore {file_name} to {dest_path} (dry run)")
                    files_restored += 1
                
                self.stats["operations"][op_name]["files_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error restoring file {file_path}: {e}")
                self.stats["errors"] += 1
        
        # Update stats
        self.stats["operations"][op_name]["completed"] = time.time()
        self.stats["operations"][op_name]["files_restored"] = files_restored
        
        logger.info(f"Restore completed: {files_restored} files restored")
        return files_restored
    
    def run_full_maintenance(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run a full maintenance cycle.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            Stats dictionary with results
        """
        logger.info("Starting full maintenance cycle")
        
        # Create a backup first
        backup_dir = self.create_backup(dry_run=dry_run)
        
        # Run validation and repair
        self.validate_and_repair(dry_run=dry_run)
        
        # Run compaction and optimization
        self.compact_files(dry_run=dry_run)
        
        # Apply retention policy
        self.apply_retention_policy(dry_run=dry_run)
        
        # Finalize stats
        self.stats["end_time"] = time.time()
        self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
        
        logger.info(f"Full maintenance cycle completed in {self.stats['duration']:.2f} seconds")
        logger.info(f"Files processed: {self.stats['processed_files']}")
        logger.info(f"Space saved: {self.stats['space_saved']} bytes")
        logger.info(f"Errors: {self.stats['errors']}")
        
        return self.stats


def create_cron_script() -> None:
    """
    Create a script for cron scheduling.
    """
    script_content = """#!/bin/bash
# Parquet maintenance cron script

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Path to the Python script
MAINTENANCE_SCRIPT="$SCRIPT_DIR/parquet_maintenance.py"

# Log file
LOG_FILE="$SCRIPT_DIR/parquet_maintenance_cron.log"

# Run full maintenance
echo "$(date) - Starting scheduled maintenance" >> "$LOG_FILE"
python3 "$MAINTENANCE_SCRIPT" --full >> "$LOG_FILE" 2>&1
echo "$(date) - Maintenance complete" >> "$LOG_FILE"
"""
    
    # Write script to file
    script_path = "parquet_maintenance_cron.sh"
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    logger.info(f"Created cron script at {script_path}")
    logger.info("To schedule maintenance, add to crontab:")
    logger.info("0 2 * * * /path/to/parquet_maintenance_cron.sh")


def main():
    """Main function to parse arguments and run operations."""
    parser = argparse.ArgumentParser(description='Parquet Maintenance Utilities')
    
    # Operation selection arguments
    parser.add_argument('--full', action='store_true', help='Run full maintenance cycle')
    parser.add_argument('--validate', action='store_true', help='Validate and repair files')
    parser.add_argument('--compact', action='store_true', help='Compact and optimize files')
    parser.add_argument('--retention', action='store_true', help='Apply retention policy')
    parser.add_argument('--backup', action='store_true', help='Create a backup')
    parser.add_argument('--restore', metavar='BACKUP_DIR', help='Restore from backup')
    parser.add_argument('--create-cron', action='store_true', help='Create a cron script')
    
    # Configuration arguments
    parser.add_argument('--data-dir', help='Directory containing Parquet files')
    parser.add_argument('--backup-dir', help='Directory for backups')
    parser.add_argument('--max-age', type=int, default=365, help='Maximum age for data retention in days')
    parser.add_argument('--compression', default='snappy', help='Compression codec for optimized files')
    parser.add_argument('--row-group-size', type=int, default=100000, help='Row group size for optimized files')
    
    # Control arguments
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # Handle create cron script
    if args.create_cron:
        create_cron_script()
        return
    
    # Create maintenance utility
    maintenance = ParquetMaintenance(
        data_dir=args.data_dir,
        backup_dir=args.backup_dir,
        max_age_days=args.max_age,
        compression=args.compression,
        row_group_size=args.row_group_size
    )
    
    # Run selected operations
    if args.full:
        maintenance.run_full_maintenance(dry_run=args.dry_run)
    else:
        if args.validate:
            maintenance.validate_and_repair(dry_run=args.dry_run)
            
        if args.compact:
            maintenance.compact_files(dry_run=args.dry_run)
            
        if args.retention:
            maintenance.apply_retention_policy(dry_run=args.dry_run)
            
        if args.backup:
            maintenance.create_backup(dry_run=args.dry_run)
            
        if args.restore:
            maintenance.restore_backup(args.restore, dry_run=args.dry_run)
    
    # Show a message if no operation was selected
    if not any([args.full, args.validate, args.compact, args.retention, args.backup, args.restore, args.create_cron]):
        logger.error("No operation selected. Use --help to see available options.")


if __name__ == "__main__":
    main()