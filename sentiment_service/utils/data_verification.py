"""
Data verification module for ensuring quality of Parquet sentiment data.
"""
import logging
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class VerificationLevel(Enum):
    """Verification level enum for validation severity."""
    ERROR = 0    # Failed validation, data unusable
    WARNING = 1  # Potential issue, but data usable
    INFO = 2     # Informational message, no issue


class ValidationResult:
    """Class representing a validation result."""
    
    def __init__(self, 
                 is_valid: bool, 
                 level: VerificationLevel, 
                 message: str,
                 field: Optional[str] = None,
                 record_id: Optional[str] = None):
        """
        Initialize a validation result.
        
        Args:
            is_valid (bool): Whether the validation passed
            level (VerificationLevel): Severity level
            message (str): Validation message
            field (Optional[str]): Field name that failed validation
            record_id (Optional[str]): ID of the record that failed
        """
        self.is_valid = is_valid
        self.level = level
        self.message = message
        self.field = field
        self.record_id = record_id
    
    def __str__(self) -> str:
        """String representation of validation result."""
        prefix = "PASS" if self.is_valid else self.level.name
        field_info = f" [{self.field}]" if self.field else ""
        record_info = f" (record: {self.record_id})" if self.record_id else ""
        return f"{prefix}{field_info}: {self.message}{record_info}"


class DataVerification:
    """
    Data verification class for validating sentiment event data.
    
    This class provides methods to verify required fields, sanitize data formats,
    and analyze datasets for quality issues.
    """
    
    def __init__(self, log_failures: bool = True):
        """
        Initialize the data verification.
        
        Args:
            log_failures (bool): Whether to log validation failures
        """
        self.log_failures = log_failures
        
        # Required fields and their expected types
        self.required_fields = {
            "timestamp": str,
            "ticker": str,
            "sentiment": (float, int),
            "confidence": (float, int),
            "source": str,
            "model": str,
            "article_id": str
        }
        
        # Optional fields and their expected types
        self.optional_fields = {
            "article_title": str,
            "text_snippet": str,
            "source_url": str,
            "source_credibility": (float, int),
            "event_weight": (float, int),
            "priority": str,
            "subscription_tier": str
        }
        
        # Field value constraints
        self.constraints = {
            "sentiment": {"min": -1.0, "max": 1.0},
            "confidence": {"min": 0.0, "max": 1.0},
            "source_credibility": {"min": 0.0, "max": 1.0},
            "event_weight": {"min": 0.0, "max": None}
        }
        
        # Allowable values for categorical fields
        self.allowed_values = {
            "priority": {"high", "standard", "low"},
            "subscription_tier": {"free", "premium", "professional"}
        }
        
        # Metrics for tracking verification activity
        self.metrics = {
            "total_records_verified": 0,
            "valid_records": 0,
            "error_records": 0,
            "warning_records": 0,
            "field_errors": {},
            "most_common_errors": {}
        }
    
    def verify_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Verify a single sentiment record.
        
        Args:
            record (Dict[str, Any]): Record to verify
            
        Returns:
            List[ValidationResult]: Validation results
        """
        results = []
        record_id = record.get("article_id", "unknown")
        
        self.metrics["total_records_verified"] += 1
        
        # Verify required fields exist
        for field, expected_type in self.required_fields.items():
            if field not in record:
                result = ValidationResult(
                    is_valid=False,
                    level=VerificationLevel.ERROR,
                    message=f"Required field missing",
                    field=field,
                    record_id=record_id
                )
                results.append(result)
                self._update_field_error_metrics(field, "missing")
                continue
            
            # Verify field type
            if not self._is_type_valid(record[field], expected_type):
                result = ValidationResult(
                    is_valid=False,
                    level=VerificationLevel.ERROR,
                    message=f"Invalid type: expected {expected_type}, got {type(record[field])}",
                    field=field,
                    record_id=record_id
                )
                results.append(result)
                self._update_field_error_metrics(field, "type_error")
                continue
            
            # Verify constraints
            if field in self.constraints:
                constraint_result = self._check_constraints(field, record[field], record_id)
                if constraint_result:
                    results.append(constraint_result)
                    self._update_field_error_metrics(field, "constraint_violation")
            
            # Verify allowed values
            if field in self.allowed_values and record[field] not in self.allowed_values[field]:
                result = ValidationResult(
                    is_valid=False,
                    level=VerificationLevel.WARNING,
                    message=f"Value not in allowed values: {record[field]} not in {self.allowed_values[field]}",
                    field=field,
                    record_id=record_id
                )
                results.append(result)
                self._update_field_error_metrics(field, "invalid_value")
        
        # Verify optional fields if present
        for field, expected_type in self.optional_fields.items():
            if field in record:
                # Verify field type
                if not self._is_type_valid(record[field], expected_type):
                    result = ValidationResult(
                        is_valid=False,
                        level=VerificationLevel.WARNING,
                        message=f"Invalid type: expected {expected_type}, got {type(record[field])}",
                        field=field,
                        record_id=record_id
                    )
                    results.append(result)
                    self._update_field_error_metrics(field, "type_error")
                    continue
                
                # Verify constraints
                if field in self.constraints:
                    constraint_result = self._check_constraints(field, record[field], record_id)
                    if constraint_result:
                        results.append(constraint_result)
                        self._update_field_error_metrics(field, "constraint_violation")
                
                # Verify allowed values
                if field in self.allowed_values and record[field] not in self.allowed_values[field]:
                    result = ValidationResult(
                        is_valid=False,
                        level=VerificationLevel.WARNING,
                        message=f"Value not in allowed values: {record[field]} not in {self.allowed_values[field]}",
                        field=field,
                        record_id=record_id
                    )
                    results.append(result)
                    self._update_field_error_metrics(field, "invalid_value")
        
        # Add timestamp validation
        if "timestamp" in record:
            timestamp_result = self._validate_timestamp(record["timestamp"], record_id)
            if not timestamp_result.is_valid:
                results.append(timestamp_result)
                self._update_field_error_metrics("timestamp", "invalid_format")
        
        # Verify ticker format
        if "ticker" in record:
            ticker_result = self._validate_ticker(record["ticker"], record_id)
            if not ticker_result.is_valid:
                results.append(ticker_result)
                self._update_field_error_metrics("ticker", "invalid_format")
        
        # Update metrics
        if results:
            has_errors = any(r.level == VerificationLevel.ERROR for r in results)
            if has_errors:
                self.metrics["error_records"] += 1
            else:
                self.metrics["warning_records"] += 1
                self.metrics["valid_records"] += 1
        else:
            self.metrics["valid_records"] += 1
            results.append(ValidationResult(
                is_valid=True,
                level=VerificationLevel.INFO,
                message="Record passed all validations",
                record_id=record_id
            ))
        
        # Log failures if enabled
        if self.log_failures:
            for result in results:
                if not result.is_valid:
                    log_level = logging.ERROR if result.level == VerificationLevel.ERROR else logging.WARNING
                    logger.log(log_level, str(result))
        
        return results
    
    def verify_dataframe(self, df: pd.DataFrame) -> Tuple[bool, List[ValidationResult]]:
        """
        Verify all records in a DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to verify
            
        Returns:
            Tuple[bool, List[ValidationResult]]: (is_valid, validation_results)
        """
        all_results = []
        is_valid = True
        
        # Convert to dict records for consistent processing
        records = df.to_dict(orient="records")
        
        for record in records:
            results = self.verify_record(record)
            all_results.extend(results)
            
            # Check if any errors (not just warnings)
            if any(not r.is_valid and r.level == VerificationLevel.ERROR for r in results):
                is_valid = False
        
        return is_valid, all_results
    
    def sanitize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a record by correcting common issues.
        
        Args:
            record (Dict[str, Any]): Record to sanitize
            
        Returns:
            Dict[str, Any]: Sanitized record
        """
        sanitized = record.copy()
        
        # Sanitize timestamp
        if "timestamp" in sanitized:
            sanitized["timestamp"] = self._sanitize_timestamp(sanitized["timestamp"])
        
        # Sanitize ticker
        if "ticker" in sanitized:
            sanitized["ticker"] = self._sanitize_ticker(sanitized["ticker"])
        
        # Sanitize numeric fields
        for field in ["sentiment", "confidence", "source_credibility", "event_weight"]:
            if field in sanitized:
                sanitized[field] = self._sanitize_numeric(sanitized[field], field)
        
        # Sanitize string fields
        for field in ["source", "model", "article_id", "article_title", "text_snippet", "source_url"]:
            if field in sanitized:
                sanitized[field] = self._sanitize_string(sanitized[field])
        
        # Sanitize categorical fields
        for field, allowed in self.allowed_values.items():
            if field in sanitized:
                sanitized[field] = self._sanitize_categorical(sanitized[field], field, allowed)
        
        return sanitized
    
    def sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sanitize all records in a DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to sanitize
            
        Returns:
            pd.DataFrame: Sanitized DataFrame
        """
        # Handle empty DataFrame
        if df.empty:
            return df.copy()
        
        # Make a copy to avoid modifying the original
        sanitized_df = df.copy()
        
        # Sanitize timestamp
        if "timestamp" in sanitized_df.columns:
            sanitized_df["timestamp"] = sanitized_df["timestamp"].apply(self._sanitize_timestamp)
        
        # Sanitize ticker
        if "ticker" in sanitized_df.columns:
            sanitized_df["ticker"] = sanitized_df["ticker"].apply(self._sanitize_ticker)
        
        # Sanitize numeric fields
        for field in ["sentiment", "confidence", "source_credibility", "event_weight"]:
            if field in sanitized_df.columns:
                sanitized_df[field] = sanitized_df[field].apply(
                    lambda x: self._sanitize_numeric(x, field)
                )
        
        # Sanitize string fields
        for field in ["source", "model", "article_id", "article_title", "text_snippet", "source_url"]:
            if field in sanitized_df.columns:
                sanitized_df[field] = sanitized_df[field].apply(self._sanitize_string)
        
        # Sanitize categorical fields
        for field, allowed in self.allowed_values.items():
            if field in sanitized_df.columns:
                sanitized_df[field] = sanitized_df[field].apply(
                    lambda x: self._sanitize_categorical(x, field, allowed)
                )
        
        return sanitized_df
    
    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a dataset for quality issues and statistics.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        analysis = {
            "record_count": len(df),
            "field_coverage": {},
            "value_distributions": {},
            "data_quality_issues": {},
            "duplicates": 0,
            "anomalies": {}
        }
        
        # Skip further analysis if DataFrame is empty
        if df.empty:
            return analysis
        
        # Analyze field coverage
        for field in list(self.required_fields.keys()) + list(self.optional_fields.keys()):
            if field in df.columns:
                non_null_count = df[field].notna().sum()
                coverage = (non_null_count / len(df)) * 100
                analysis["field_coverage"][field] = {
                    "present_count": non_null_count,
                    "coverage_percentage": coverage
                }
        
        # Analyze value distributions for key fields
        for field in ["sentiment", "confidence", "source", "model"]:
            if field in df.columns:
                if df[field].dtype in [np.float64, np.int64, float, int]:
                    # Numeric field
                    analysis["value_distributions"][field] = {
                        "min": df[field].min(),
                        "max": df[field].max(),
                        "mean": df[field].mean(),
                        "median": df[field].median(),
                        "std": df[field].std()
                    }
                else:
                    # Categorical field
                    value_counts = df[field].value_counts()
                    top_values = value_counts.head(10).to_dict()
                    analysis["value_distributions"][field] = {
                        "unique_count": len(value_counts),
                        "top_values": top_values
                    }
        
        # Analyze duplicates
        if "article_id" in df.columns:
            duplicate_ids = df[df.duplicated("article_id", keep=False)]["article_id"]
            analysis["duplicates"] = len(duplicate_ids)
            if not duplicate_ids.empty:
                analysis["data_quality_issues"]["duplicate_ids"] = duplicate_ids.unique().tolist()[:10]  # First 10
        
        # Analyze anomalies in sentiment scores
        if "sentiment" in df.columns:
            sentiment_mean = df["sentiment"].mean()
            sentiment_std = df["sentiment"].std()
            anomaly_threshold = 3  # 3 standard deviations
            
            anomalies = df[abs(df["sentiment"] - sentiment_mean) > anomaly_threshold * sentiment_std]
            if not anomalies.empty:
                analysis["anomalies"]["sentiment_outliers"] = len(anomalies)
                if "article_id" in df.columns:
                    analysis["data_quality_issues"]["sentiment_outlier_ids"] = anomalies["article_id"].tolist()[:10]
        
        # Analyze timestamp distribution
        if "timestamp" in df.columns:
            try:
                df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
                min_date = df["timestamp_dt"].min()
                max_date = df["timestamp_dt"].max()
                date_range = (max_date - min_date).days
                
                analysis["value_distributions"]["timestamp"] = {
                    "min_date": min_date.isoformat(),
                    "max_date": max_date.isoformat(),
                    "date_range_days": date_range
                }
                
                # Check for future dates
                now = pd.Timestamp.now()
                future_dates = df[df["timestamp_dt"] > now]
                if not future_dates.empty:
                    analysis["data_quality_issues"]["future_timestamps"] = len(future_dates)
                
                # Drop temporary column
                df.drop("timestamp_dt", axis=1, inplace=True)
            except Exception as e:
                analysis["data_quality_issues"]["timestamp_parsing_error"] = str(e)
        
        return analysis
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get verification metrics.
        
        Returns:
            Dict[str, Any]: Dictionary of metrics
        """
        return self.metrics
    
    def _update_field_error_metrics(self, field: str, error_type: str):
        """
        Update field error metrics.
        
        Args:
            field (str): Field name
            error_type (str): Type of error
        """
        if field not in self.metrics["field_errors"]:
            self.metrics["field_errors"][field] = {}
        
        if error_type not in self.metrics["field_errors"][field]:
            self.metrics["field_errors"][field][error_type] = 0
        
        self.metrics["field_errors"][field][error_type] += 1
        
        # Update most common errors
        error_key = f"{field}:{error_type}"
        if error_key not in self.metrics["most_common_errors"]:
            self.metrics["most_common_errors"][error_key] = 0
        
        self.metrics["most_common_errors"][error_key] += 1
    
    def _is_type_valid(self, value: Any, expected_types: Union[type, Tuple[type, ...]]) -> bool:
        """
        Check if value is of expected type.
        
        Args:
            value (Any): Value to check
            expected_types (Union[type, Tuple[type, ...]]): Expected type or types
            
        Returns:
            bool: True if type is valid
        """
        # Handle None values
        if value is None:
            return False
        
        # Handle tuple of types
        if isinstance(expected_types, tuple):
            return any(isinstance(value, t) for t in expected_types)
        
        # Handle single type
        return isinstance(value, expected_types)
    
    def _check_constraints(self, field: str, value: Any, record_id: str) -> Optional[ValidationResult]:
        """
        Check if value meets constraints.
        
        Args:
            field (str): Field name
            value (Any): Value to check
            record_id (str): Record ID for reporting
            
        Returns:
            Optional[ValidationResult]: Validation result if constraint violated, otherwise None
        """
        constraints = self.constraints.get(field, {})
        
        # Skip constraint check if value is not numeric
        if not isinstance(value, (int, float)):
            return None
        
        min_val = constraints.get("min")
        max_val = constraints.get("max")
        
        if min_val is not None and value < min_val:
            return ValidationResult(
                is_valid=False,
                level=VerificationLevel.ERROR,
                message=f"Value {value} below minimum {min_val}",
                field=field,
                record_id=record_id
            )
        
        if max_val is not None and value > max_val:
            return ValidationResult(
                is_valid=False,
                level=VerificationLevel.ERROR,
                message=f"Value {value} above maximum {max_val}",
                field=field,
                record_id=record_id
            )
        
        return None
    
    def _validate_timestamp(self, timestamp: str, record_id: str) -> ValidationResult:
        """
        Validate timestamp format.
        
        Args:
            timestamp (str): Timestamp to validate
            record_id (str): Record ID for reporting
            
        Returns:
            ValidationResult: Validation result
        """
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SS[.sss][Z|±HH:MM]
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
        
        if not re.match(iso_pattern, timestamp):
            return ValidationResult(
                is_valid=False,
                level=VerificationLevel.WARNING,
                message=f"Invalid timestamp format: {timestamp}, expected ISO 8601",
                field="timestamp",
                record_id=record_id
            )
        
        try:
            # Further validation: parseable as datetime
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return ValidationResult(
                is_valid=True,
                level=VerificationLevel.INFO,
                message="Valid timestamp format",
                field="timestamp",
                record_id=record_id
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                level=VerificationLevel.WARNING,
                message=f"Timestamp not parseable as datetime: {timestamp}",
                field="timestamp",
                record_id=record_id
            )
    
    def _validate_ticker(self, ticker: str, record_id: str) -> ValidationResult:
        """
        Validate ticker format.
        
        Args:
            ticker (str): Ticker to validate
            record_id (str): Record ID for reporting
            
        Returns:
            ValidationResult: Validation result
        """
        # Common ticker pattern: 1-5 uppercase letters (sometimes with . or -)
        ticker_pattern = r"^[A-Z0-9\.\-]{1,5}$"
        
        if not re.match(ticker_pattern, ticker):
            return ValidationResult(
                is_valid=False,
                level=VerificationLevel.WARNING,
                message=f"Invalid ticker format: {ticker}, expected 1-5 uppercase alphanumeric chars",
                field="ticker",
                record_id=record_id
            )
        
        return ValidationResult(
            is_valid=True,
            level=VerificationLevel.INFO,
            message="Valid ticker format",
            field="ticker",
            record_id=record_id
        )
    
    def _sanitize_timestamp(self, timestamp: Any) -> str:
        """
        Sanitize timestamp to ISO 8601 format.
        
        Args:
            timestamp (Any): Timestamp to sanitize
            
        Returns:
            str: Sanitized timestamp
        """
        if pd.isna(timestamp) or timestamp is None:
            return datetime.now().isoformat()
        
        if isinstance(timestamp, str):
            # Check if already ISO format
            iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
            if re.match(iso_pattern, timestamp):
                return timestamp
            
            # Try to parse with pandas
            try:
                dt = pd.to_datetime(timestamp)
                return dt.isoformat()
            except:
                return datetime.now().isoformat()
        
        # Handle datetime objects
        if isinstance(timestamp, (datetime, pd.Timestamp)):
            return timestamp.isoformat()
        
        # Handle numeric (unix timestamp)
        if isinstance(timestamp, (int, float)):
            try:
                return datetime.fromtimestamp(timestamp).isoformat()
            except:
                return datetime.now().isoformat()
        
        # Default fallback
        return datetime.now().isoformat()
    
    def _sanitize_ticker(self, ticker: Any) -> str:
        """
        Sanitize ticker symbol.
        
        Args:
            ticker (Any): Ticker to sanitize
            
        Returns:
            str: Sanitized ticker
        """
        if pd.isna(ticker) or ticker is None:
            return "UNKNOWN"
        
        if isinstance(ticker, str):
            # Remove whitespace and convert to uppercase
            sanitized = ticker.strip().upper()
            
            # Remove any special characters except . and -
            sanitized = re.sub(r'[^A-Z0-9\.\-]', '', sanitized)
            
            # Limit to 5 characters
            return sanitized[:5]
        
        # Convert non-string to string and sanitize
        return self._sanitize_ticker(str(ticker))
    
    def _sanitize_numeric(self, value: Any, field: str) -> float:
        """
        Sanitize numeric value.
        
        Args:
            value (Any): Value to sanitize
            field (str): Field name for constraints
            
        Returns:
            float: Sanitized value
        """
        constraints = self.constraints.get(field, {})
        min_val = constraints.get("min", -float('inf'))
        max_val = constraints.get("max", float('inf'))
        
        try:
            # Convert to float
            if pd.isna(value) or value is None:
                return 0.0
            
            if isinstance(value, str):
                # Remove non-numeric characters except . and -
                cleaned = re.sub(r'[^0-9\.\-]', '', value)
                value = float(cleaned)
            else:
                value = float(value)
            
            # Apply constraints
            value = max(min_val, value)
            if max_val is not None:
                value = min(max_val, value)
            
            return value
        except:
            # Default based on field
            if field == "sentiment":
                return 0.0
            elif field == "confidence":
                return 0.5
            elif field == "source_credibility":
                return 0.5
            elif field == "event_weight":
                return 1.0
            else:
                return 0.0
    
    def _sanitize_string(self, value: Any) -> str:
        """
        Sanitize string value.
        
        Args:
            value (Any): Value to sanitize
            
        Returns:
            str: Sanitized string
        """
        if pd.isna(value) or value is None:
            return ""
        
        if isinstance(value, str):
            # Strip whitespace
            return value.strip()
        
        # Convert non-string to string
        return str(value).strip()
    
    def _sanitize_categorical(self, value: Any, field: str, allowed_values: Set[str]) -> str:
        """
        Sanitize categorical value.
        
        Args:
            value (Any): Value to sanitize
            field (str): Field name
            allowed_values (Set[str]): Set of allowed values
            
        Returns:
            str: Sanitized categorical value
        """
        if pd.isna(value) or value is None:
            # Default values based on field
            if field == "priority":
                return "standard"
            elif field == "subscription_tier":
                return "free"
            else:
                return list(allowed_values)[0] if allowed_values else ""
        
        if isinstance(value, str):
            value = value.lower().strip()
            
            # Check if valid
            if value in allowed_values:
                return value
            
            # Try partial matches
            for allowed in allowed_values:
                if allowed.startswith(value) or value.startswith(allowed):
                    return allowed
            
            # Fallback to default
            if field == "priority":
                return "standard"
            elif field == "subscription_tier":
                return "free"
            else:
                return list(allowed_values)[0] if allowed_values else ""
        
        # Handle non-string
        return self._sanitize_categorical(str(value), field, allowed_values)