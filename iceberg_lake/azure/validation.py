"""
Validation framework for Iceberg migration integrity.

This module provides a comprehensive validation framework for ensuring data integrity
during migration from Parquet files to Iceberg tables in Azure Blob Storage.
"""
import logging
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set, Callable

import pandas as pd
import numpy as np
import jaydebeapi

from iceberg_lake.azure.writer import AzureDremioJdbcWriter


class MigrationValidator:
    """
    Validator for ensuring data integrity during Parquet to Iceberg migration.
    
    This class provides methods for validating the integrity of data migrated
    from Parquet files to Iceberg tables, including both statistical validation
    and record-by-record validation.
    """
    
    def __init__(
        self,
        dremio_writer: AzureDremioJdbcWriter,
        validation_sample_size: int = 100,
        statistical_fields: Optional[List[str]] = None,
        text_hash_fields: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Initialize the migration validator.
        
        Args:
            dremio_writer: Azure Dremio JDBC writer with connection to the target table
            validation_sample_size: Number of records to sample for validation
            statistical_fields: List of numeric fields to validate statistically
            text_hash_fields: List of text fields to validate using hash comparison
            progress_callback: Callback function for progress updates (message, progress)
        """
        self.logger = logging.getLogger(__name__)
        self.dremio_writer = dremio_writer
        self.validation_sample_size = validation_sample_size
        self.progress_callback = progress_callback
        
        # Default statistical fields (numeric fields)
        self.statistical_fields = statistical_fields or [
            "sentiment_score",
            "sentiment_magnitude",
            "subjectivity_score",
            "toxicity_score"
        ]
        
        # Default text hash fields (text fields)
        self.text_hash_fields = text_hash_fields or [
            "text_content",
            "primary_emotion",
            "user_intent"
        ]
    
    def _report_progress(self, message: str, progress: float = 0.0) -> None:
        """
        Report progress to the callback function if provided.
        
        Args:
            message: Progress message
            progress: Progress value (0.0 to 1.0)
        """
        self.logger.info(f"Validation progress: {message} ({progress:.2%})")
        if self.progress_callback:
            self.progress_callback(message, progress)
    
    def _get_dremio_connection(self) -> jaydebeapi.Connection:
        """
        Get a JDBC connection to Dremio.
        
        Returns:
            jaydebeapi.Connection: JDBC connection
        """
        return self.dremio_writer._get_connection()
    
    def _execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query against the Dremio database.
        
        Args:
            query: SQL query
            params: Query parameters (optional)
            
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries
        """
        connection = self._get_dremio_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(query, params or [])
            
            # Get column names
            columns = [col[0] for col in cursor.description]
            
            # Fetch results
            results = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                result = {}
                for i, value in enumerate(row):
                    result[columns[i]] = value
                results.append(result)
                
            return results
            
        finally:
            cursor.close()
    
    def _count_records(self, table_name: str, condition: Optional[str] = None) -> int:
        """
        Count records in a table with an optional condition.
        
        Args:
            table_name: Table name
            condition: SQL WHERE condition (optional)
            
        Returns:
            int: Record count
        """
        where_clause = f"WHERE {condition}" if condition else ""
        query = f"SELECT COUNT(*) as count FROM {table_name} {where_clause}"
        
        results = self._execute_query(query)
        return results[0]["count"] if results else 0
    
    def _calculate_column_statistics(
        self, 
        table_name: str, 
        column_name: str, 
        condition: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate statistics for a numeric column.
        
        Args:
            table_name: Table name
            column_name: Column name
            condition: SQL WHERE condition (optional)
            
        Returns:
            Dict[str, float]: Column statistics (min, max, avg, sum)
        """
        where_clause = f"WHERE {condition}" if condition else ""
        query = f"""
        SELECT 
            MIN("{column_name}") as min_value, 
            MAX("{column_name}") as max_value, 
            AVG("{column_name}") as avg_value, 
            SUM("{column_name}") as sum_value,
            COUNT("{column_name}") as count_value
        FROM {table_name} 
        {where_clause}
        """
        
        results = self._execute_query(query)
        return results[0] if results else {}
    
    def _sample_records(
        self, 
        table_name: str, 
        sample_size: int, 
        condition: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Sample records from a table.
        
        Args:
            table_name: Table name
            sample_size: Number of records to sample
            condition: SQL WHERE condition (optional)
            
        Returns:
            List[Dict[str, Any]]: Sampled records
        """
        where_clause = f"WHERE {condition}" if condition else ""
        # Use RAND() for random sampling in Dremio
        query = f"""
        SELECT * FROM {table_name} 
        {where_clause}
        ORDER BY RAND() 
        LIMIT {sample_size}
        """
        
        return self._execute_query(query)
    
    def _calculate_record_hash(self, record: Dict[str, Any], fields: List[str]) -> str:
        """
        Calculate a hash of specified fields in a record.
        
        Args:
            record: Record to hash
            fields: Fields to include in the hash
            
        Returns:
            str: Hash of the record fields
        """
        # Extract only the specified fields
        field_values = {}
        for field in fields:
            field_values[field] = record.get(field)
            
        # Sort the dictionary to ensure consistent hashing
        serialized = json.dumps(field_values, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def verify_row_counts(
        self, 
        source_df: pd.DataFrame, 
        target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that row counts match between source and target.
        
        Args:
            source_df: Source DataFrame from Parquet
            target_table: Target table name
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        source_count = len(source_df)
        target_count = self._count_records(target_table)
        
        is_valid = source_count == target_count
        
        validation_results = {
            "source_count": source_count,
            "target_count": target_count,
            "is_valid": is_valid,
            "difference": abs(source_count - target_count),
            "difference_percent": round(abs(source_count - target_count) / max(source_count, 1) * 100, 2)
        }
        
        self.logger.info(
            f"Row count validation: source={source_count}, "
            f"target={target_count}, valid={is_valid}"
        )
        
        return is_valid, validation_results
    
    def verify_statistics(
        self, 
        source_df: pd.DataFrame, 
        target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that statistical metrics match between source and target.
        
        Args:
            source_df: Source DataFrame from Parquet
            target_table: Target table name
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        validation_results = {
            "fields": {},
            "is_valid": True
        }
        
        for field in self.statistical_fields:
            if field not in source_df.columns:
                self.logger.warning(f"Field {field} not found in source DataFrame")
                continue
                
            # Calculate statistics from source DataFrame
            source_stats = {
                "min_value": float(source_df[field].min()),
                "max_value": float(source_df[field].max()),
                "avg_value": float(source_df[field].mean()),
                "sum_value": float(source_df[field].sum()),
                "count_value": int(source_df[field].count())
            }
            
            # Calculate statistics from target table
            target_stats = self._calculate_column_statistics(target_table, field)
            
            # Compare statistics
            field_valid = (
                abs(source_stats["min_value"] - float(target_stats["min_value"])) < 0.0001 and
                abs(source_stats["max_value"] - float(target_stats["max_value"])) < 0.0001 and
                abs(source_stats["avg_value"] - float(target_stats["avg_value"])) < 0.0001 and
                abs(source_stats["sum_value"] - float(target_stats["sum_value"])) < 0.0001 and
                source_stats["count_value"] == int(target_stats["count_value"])
            )
            
            validation_results["fields"][field] = {
                "source": source_stats,
                "target": target_stats,
                "is_valid": field_valid
            }
            
            if not field_valid:
                validation_results["is_valid"] = False
                
            self.logger.info(
                f"Statistical validation for {field}: valid={field_valid}, "
                f"source_mean={source_stats['avg_value']}, target_mean={target_stats['avg_value']}"
            )
        
        return validation_results["is_valid"], validation_results
    
    def verify_sample_records(
        self, 
        source_df: pd.DataFrame, 
        target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a sample of records between source and target.
        
        Args:
            source_df: Source DataFrame from Parquet
            target_table: Target table name
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        validation_results = {
            "sample_size": min(self.validation_sample_size, len(source_df)),
            "matched_records": 0,
            "mismatched_records": 0,
            "is_valid": True,
            "mismatch_examples": []
        }
        
        # Sample records from source
        source_sample = source_df.sample(n=validation_results["sample_size"]) if len(source_df) > validation_results["sample_size"] else source_df
        
        # Get message_ids from the sample
        message_ids = source_sample["message_id"].tolist()
        message_id_condition = f"message_id IN ({', '.join(['?' for _ in message_ids])})"
        
        # Get corresponding records from target
        target_records = self._execute_query(
            f"SELECT * FROM {target_table} WHERE {message_id_condition}",
            message_ids
        )
        
        # Index target records by message_id for easier lookup
        target_by_message_id = {record["message_id"]: record for record in target_records}
        
        # Calculate hash for each text field in the source sample
        for _, source_record in source_sample.iterrows():
            source_record_dict = source_record.to_dict()
            message_id = source_record_dict["message_id"]
            
            if message_id not in target_by_message_id:
                validation_results["mismatched_records"] += 1
                validation_results["mismatch_examples"].append({
                    "message_id": message_id,
                    "error": "Record not found in target"
                })
                continue
                
            target_record = target_by_message_id[message_id]
            
            # Validate text fields using hash comparison
            text_fields_valid = True
            text_field_mismatches = []
            
            for field in self.text_hash_fields:
                if field not in source_record_dict:
                    continue
                    
                source_value = str(source_record_dict.get(field, ""))
                target_value = str(target_record.get(field, ""))
                
                # Compare values
                if source_value != target_value:
                    text_fields_valid = False
                    text_field_mismatches.append({
                        "field": field,
                        "source_value": source_value,
                        "target_value": target_value
                    })
            
            if text_fields_valid:
                validation_results["matched_records"] += 1
            else:
                validation_results["mismatched_records"] += 1
                validation_results["mismatch_examples"].append({
                    "message_id": message_id,
                    "mismatches": text_field_mismatches
                })
                
                if len(validation_results["mismatch_examples"]) >= 5:
                    break  # Limit the number of examples
        
        # Calculate validation success percentage
        match_percentage = (validation_results["matched_records"] / validation_results["sample_size"]) * 100
        validation_results["match_percentage"] = match_percentage
        validation_results["is_valid"] = match_percentage >= 95  # At least 95% match rate
        
        self.logger.info(
            f"Sample validation: {validation_results['matched_records']} matched, "
            f"{validation_results['mismatched_records']} mismatched, "
            f"{match_percentage:.2f}% match rate"
        )
        
        return validation_results["is_valid"], validation_results
    
    def validate_migration(
        self, 
        source_df: pd.DataFrame, 
        target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a migration from Parquet to Iceberg.
        
        Performs comprehensive validation including row count comparison,
        statistical validation, and sample record validation.
        
        Args:
            source_df: Source DataFrame from Parquet
            target_table: Target table name
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        validation_results = {
            "source": source_df.shape,
            "target_table": target_table,
            "timestamp": datetime.utcnow().isoformat(),
            "row_count_validation": None,
            "statistical_validation": None,
            "sample_validation": None,
            "is_valid": False
        }
        
        try:
            # Step 1: Verify row counts
            self._report_progress("Validating row counts", 0.25)
            row_count_valid, row_count_results = self.verify_row_counts(source_df, target_table)
            validation_results["row_count_validation"] = row_count_results
            
            # Step 2: Verify statistics for numeric fields
            self._report_progress("Validating statistics", 0.50)
            stats_valid, stats_results = self.verify_statistics(source_df, target_table)
            validation_results["statistical_validation"] = stats_results
            
            # Step 3: Verify sample records
            self._report_progress("Validating sample records", 0.75)
            sample_valid, sample_results = self.verify_sample_records(source_df, target_table)
            validation_results["sample_validation"] = sample_results
            
            # Combine validation results
            validation_results["is_valid"] = row_count_valid and stats_valid and sample_valid
            
            self._report_progress(
                f"Validation complete: {'success' if validation_results['is_valid'] else 'failed'}",
                1.0
            )
            
            return validation_results["is_valid"], validation_results
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            self.logger.error(error_msg)
            validation_results["error"] = error_msg
            return False, validation_results
            
    def validate_parquet_file(
        self, 
        parquet_file: str, 
        target_table: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a migration from a Parquet file to Iceberg.
        
        Args:
            parquet_file: Path to the source Parquet file
            target_table: Target table name
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation_results)
        """
        try:
            # Read the Parquet file
            self.logger.info(f"Reading Parquet file: {parquet_file}")
            source_df = pd.read_parquet(parquet_file)
            
            # Perform validation
            return self.validate_migration(source_df, target_table)
            
        except Exception as e:
            error_msg = f"Failed to validate Parquet file {parquet_file}: {str(e)}"
            self.logger.error(error_msg)
            return False, {"error": error_msg}
            
    def generate_validation_report(
        self, 
        validation_results: Dict[str, Any], 
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate a detailed validation report.
        
        Args:
            validation_results: Validation results from validate_migration
            output_file: Path to write the report (optional)
            
        Returns:
            str: Validation report in JSON format
        """
        # Create a summary report
        report = {
            "validation_summary": {
                "timestamp": datetime.utcnow().isoformat(),
                "is_valid": validation_results.get("is_valid", False),
                "source_rows": validation_results.get("source", [0, 0])[0],
                "target_table": validation_results.get("target_table", ""),
                "row_count_match": validation_results.get("row_count_validation", {}).get("is_valid", False),
                "statistical_match": validation_results.get("statistical_validation", {}).get("is_valid", False),
                "sample_match": validation_results.get("sample_validation", {}).get("is_valid", False),
                "sample_match_percentage": validation_results.get("sample_validation", {}).get("match_percentage", 0)
            },
            "details": validation_results
        }
        
        # Convert to JSON
        report_json = json.dumps(report, indent=2, default=str)
        
        # Write to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_json)
                self.logger.info(f"Validation report written to {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to write validation report to {output_file}: {str(e)}")
        
        return report_json