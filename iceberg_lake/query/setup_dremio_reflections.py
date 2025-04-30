#!/usr/bin/env python3
"""
Script to set up Dremio reflections for optimizing sentiment query performance.

This script creates Dremio reflections (materialized views) for common query patterns
in the sentiment analysis system, implementing part of Phase 3 of the data tier plan.

This script supports a --mock mode for demonstration purposes when a real
Dremio instance is not available.
"""
import os
import sys
import logging
import json
import argparse
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DremioReflectionManager:
    """Manager for creating and managing Dremio reflections."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9047,
        username: str = "dremio",
        password: str = "dremio123",
        catalog: str = "DREMIO",
        namespace: str = "sentiment",
        table_name: str = "sentiment_data",
        mock_mode: bool = False
    ):
        """
        Initialize the Dremio reflection manager.
        
        Args:
            host: Dremio host
            port: Dremio port
            username: Dremio username
            password: Dremio password
            catalog: Dremio catalog
            namespace: Dremio namespace/schema
            table_name: Dremio table name
            mock_mode: If True, run in mock mode without actually connecting to Dremio
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.catalog = catalog
        self.namespace = namespace
        self.table_name = table_name
        self.base_url = f"http://{host}:{port}/api/v3/"
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        
        # Authentication token
        self.token = None if not mock_mode else "mock-auth-token"
        
        # Initialize if not in mock mode
        if not mock_mode:
            self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Dremio REST API."""
        if self.mock_mode:
            self.logger.info("Mock mode: Skipping authentication")
            return
            
        self.logger.info(f"Authenticating with Dremio at {self.host}:{self.port}")
        
        url = urljoin(self.base_url, "login")
        
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "userName": self.username,
                    "password": self.password
                })
            )
            
            response.raise_for_status()
            self.token = response.json()["token"]
            self.logger.info("Authentication successful")
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for Dremio REST API requests.
        
        Returns:
            Dict[str, str]: Headers with authentication token
        """
        if self.mock_mode:
            return {"Content-Type": "application/json", "Authorization": "mock-auth-token"}
            
        if not self.token:
            self._authenticate()
            
        return {
            "Content-Type": "application/json",
            "Authorization": f"_dremio{self.token}"
        }
    
    def _get_dataset_path(self) -> List[str]:
        """
        Get the path to the sentiment dataset.
        
        Returns:
            List[str]: Path components for the dataset
        """
        return [self.catalog, self.namespace, self.table_name]
    
    def _find_dataset_id(self) -> Optional[str]:
        """
        Find the ID of the sentiment dataset.
        
        Returns:
            Optional[str]: Dataset ID if found, None otherwise
        """
        if self.mock_mode:
            self.logger.info("Mock mode: Using mock dataset ID")
            return "mock-dataset-id"
            
        self.logger.info(f"Finding dataset ID for {'.'.join(self._get_dataset_path())}")
        
        try:
            # Start with catalog
            path = []
            current_id = None
            
            # Traverse path
            for component in self._get_dataset_path():
                path.append(component)
                
                if current_id:
                    # Get children of current entity
                    url = urljoin(self.base_url, f"catalog/{current_id}")
                else:
                    # Get root catalog
                    url = urljoin(self.base_url, "catalog")
                
                response = requests.get(url, headers=self._get_headers())
                response.raise_for_status()
                
                # Find current component in response
                entity = None
                for item in response.json().get("data", []):
                    if item.get("name") == component:
                        entity = item
                        current_id = entity.get("id")
                        break
                
                if not entity:
                    self.logger.error(f"Dataset component not found: {'.'.join(path)}")
                    return None
            
            self.logger.info(f"Found dataset ID: {current_id}")
            return current_id
            
        except Exception as e:
            self.logger.error(f"Error finding dataset ID: {str(e)}")
            return None
    
    def create_raw_reflection(self, name: str = "raw_reflection") -> Dict[str, Any]:
        """
        Create a raw reflection for basic queries.
        
        Args:
            name: Name of the reflection
            
        Returns:
            Dict[str, Any]: Reflection details if successful, empty dict otherwise
        """
        if self.mock_mode:
            self.logger.info(f"Mock mode: Creating raw reflection '{name}'")
            return {
                "id": f"mock-{name}-id",
                "name": name,
                "type": "RAW",
                "status": "ENABLED"
            }
            
        self.logger.info(f"Creating raw reflection '{name}'")
        
        dataset_id = self._find_dataset_id()
        if not dataset_id:
            self.logger.error("Failed to find dataset ID, cannot create reflection")
            return {}
        
        url = urljoin(self.base_url, "reflection")
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                data=json.dumps({
                    "name": name,
                    "type": "RAW",
                    "datasetId": dataset_id,
                    "enabled": True
                })
            )
            
            response.raise_for_status()
            reflection = response.json()
            self.logger.info(f"Raw reflection '{name}' created successfully")
            return reflection
            
        except Exception as e:
            self.logger.error(f"Failed to create raw reflection: {str(e)}")
            return {}
    
    def create_aggregation_reflection(
        self,
        name: str,
        dimensions: List[str],
        measures: List[str],
        partition_fields: Optional[List[str]] = None,
        distribution_fields: Optional[List[str]] = None,
        sort_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create an aggregation reflection for optimized queries.
        
        Args:
            name: Name of the reflection
            dimensions: Dimension fields
            measures: Measure fields
            partition_fields: Partition fields (optional)
            distribution_fields: Distribution fields (optional)
            sort_fields: Sort fields (optional)
            
        Returns:
            Dict[str, Any]: Reflection details if successful, empty dict otherwise
        """
        if self.mock_mode:
            self.logger.info(f"Mock mode: Creating aggregation reflection '{name}'")
            return {
                "id": f"mock-{name}-id",
                "name": name,
                "type": "AGGREGATION",
                "status": "ENABLED",
                "dimensionFieldList": dimensions,
                "measureFieldList": measures
            }
            
        self.logger.info(f"Creating aggregation reflection '{name}'")
        
        dataset_id = self._find_dataset_id()
        if not dataset_id:
            self.logger.error("Failed to find dataset ID, cannot create reflection")
            return {}
        
        url = urljoin(self.base_url, "reflection")
        
        try:
            reflection_data = {
                "name": name,
                "type": "AGGREGATION",
                "datasetId": dataset_id,
                "dimensionFieldList": dimensions,
                "measureFieldList": measures,
                "enabled": True
            }
            
            if partition_fields:
                reflection_data["partitionFieldList"] = partition_fields
                
            if distribution_fields:
                reflection_data["distributionFieldList"] = distribution_fields
                
            if sort_fields:
                reflection_data["sortFieldList"] = sort_fields
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                data=json.dumps(reflection_data)
            )
            
            response.raise_for_status()
            reflection = response.json()
            self.logger.info(f"Aggregation reflection '{name}' created successfully")
            return reflection
            
        except Exception as e:
            self.logger.error(f"Failed to create aggregation reflection: {str(e)}")
            return {}
    
    def enable_reflection(self, reflection_id: str) -> bool:
        """
        Enable a reflection.
        
        Args:
            reflection_id: ID of the reflection to enable
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.mock_mode:
            self.logger.info(f"Mock mode: Enabling reflection '{reflection_id}'")
            return True
            
        self.logger.info(f"Enabling reflection '{reflection_id}'")
        
        url = urljoin(self.base_url, f"reflection/{reflection_id}")
        
        try:
            # First get current configuration
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            reflection = response.json()
            reflection["enabled"] = True
            
            # Update with enabled=True
            response = requests.put(
                url,
                headers=self._get_headers(),
                data=json.dumps(reflection)
            )
            
            response.raise_for_status()
            self.logger.info(f"Reflection '{reflection_id}' enabled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable reflection: {str(e)}")
            return False
    
    def refresh_reflection(self, reflection_id: str) -> bool:
        """
        Refresh a reflection.
        
        Args:
            reflection_id: ID of the reflection to refresh
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.mock_mode:
            self.logger.info(f"Mock mode: Refreshing reflection '{reflection_id}'")
            return True
            
        self.logger.info(f"Refreshing reflection '{reflection_id}'")
        
        url = urljoin(self.base_url, f"reflection/{reflection_id}/refresh")
        
        try:
            response = requests.post(url, headers=self._get_headers())
            response.raise_for_status()
            self.logger.info(f"Reflection '{reflection_id}' refresh started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to refresh reflection: {str(e)}")
            return False
    
    def get_reflection_status(self, reflection_id: str) -> Dict[str, Any]:
        """
        Get the status of a reflection.
        
        Args:
            reflection_id: ID of the reflection to check
            
        Returns:
            Dict[str, Any]: Reflection status details
        """
        if self.mock_mode:
            self.logger.info(f"Mock mode: Getting status for reflection '{reflection_id}'")
            return {
                "id": reflection_id,
                "status": "AVAILABLE",
                "enabled": True
            }
            
        self.logger.info(f"Getting status for reflection '{reflection_id}'")
        
        url = urljoin(self.base_url, f"reflection/{reflection_id}")
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get reflection status: {str(e)}")
            return {}
    
    def create_sentiment_reflections(self) -> Dict[str, Dict[str, Any]]:
        """
        Create all reflections needed for sentiment analysis.
        
        Returns:
            Dict[str, Dict[str, Any]]: Created reflections
        """
        self.logger.info("Creating sentiment analysis reflections")
        
        reflections = {}
        
        # Raw reflection for basic queries
        raw_reflection = self.create_raw_reflection(name="sentiment_data_raw")
        if raw_reflection:
            reflections["raw"] = raw_reflection
        
        # Time series reflection by ticker/day
        timeseries_reflection = self.create_aggregation_reflection(
            name="sentiment_timeseries_by_ticker_day",
            dimensions=["ticker", "DATE_TRUNC('DAY', event_timestamp) as day"],
            measures=[
                "COUNT(*) as message_count",
                "AVG(sentiment_score) as avg_sentiment",
                "AVG(sentiment_magnitude) as avg_magnitude",
                "AVG(subjectivity_score) as avg_subjectivity",
                "AVG(toxicity_score) as avg_toxicity",
                "AVG(influence_score) as avg_influence"
            ],
            partition_fields=["ticker", "DATE_TRUNC('DAY', event_timestamp)"],
            sort_fields=["ticker", "DATE_TRUNC('DAY', event_timestamp)"]
        )
        if timeseries_reflection:
            reflections["timeseries"] = timeseries_reflection
        
        # Source system aggregation
        source_reflection = self.create_aggregation_reflection(
            name="sentiment_by_source",
            dimensions=["source_system", "ticker"],
            measures=[
                "COUNT(*) as message_count",
                "AVG(sentiment_score) as avg_sentiment",
                "AVG(influence_score) as avg_influence"
            ],
            partition_fields=["source_system"],
            sort_fields=["source_system", "ticker"]
        )
        if source_reflection:
            reflections["source"] = source_reflection
        
        # Emotion distribution
        emotion_reflection = self.create_aggregation_reflection(
            name="sentiment_emotion_distribution",
            dimensions=["primary_emotion", "ticker"],
            measures=[
                "COUNT(*) as message_count",
                "AVG(sentiment_score) as avg_sentiment",
                "AVG(influence_score) as avg_influence"
            ],
            partition_fields=["primary_emotion"],
            sort_fields=["primary_emotion", "ticker"]
        )
        if emotion_reflection:
            reflections["emotion"] = emotion_reflection
        
        # Ticker volume aggregation
        ticker_reflection = self.create_aggregation_reflection(
            name="sentiment_ticker_volume",
            dimensions=["ticker"],
            measures=[
                "COUNT(*) as message_count",
                "AVG(sentiment_score) as avg_sentiment",
                "AVG(influence_score) as avg_influence"
            ],
            partition_fields=["ticker"],
            sort_fields=["ticker"]
        )
        if ticker_reflection:
            reflections["ticker"] = ticker_reflection
        
        # Intent aggregation
        intent_reflection = self.create_aggregation_reflection(
            name="sentiment_intent_distribution",
            dimensions=["user_intent", "ticker"],
            measures=[
                "COUNT(*) as message_count",
                "AVG(sentiment_score) as avg_sentiment",
                "AVG(influence_score) as avg_influence"
            ],
            partition_fields=["user_intent"],
            sort_fields=["user_intent", "ticker"]
        )
        if intent_reflection:
            reflections["intent"] = intent_reflection
        
        return reflections
    
    def setup_and_refresh_reflections(self) -> List[Dict[str, Any]]:
        """
        Set up and refresh all reflections for sentiment analysis.
        
        Returns:
            List[Dict[str, Any]]: Status of all reflections
        """
        # Create reflections
        reflections = self.create_sentiment_reflections()
        if not reflections:
            self.logger.error("Failed to create reflections")
            return []
        
        if self.mock_mode:
            self.logger.info("Mock mode: Skipping refresh")
            return list(reflections.values())
        
        # Ensure all reflections are enabled
        for reflection_type, reflection in reflections.items():
            self.enable_reflection(reflection["id"])
        
        # Refresh all reflections
        for reflection_type, reflection in reflections.items():
            self.refresh_reflection(reflection["id"])
        
        # Wait for reflections to update (in a real scenario, would be async)
        self.logger.info("Waiting for reflections to update...")
        time.sleep(2)
        
        # Get status of all reflections
        statuses = []
        for reflection_type, reflection in reflections.items():
            status = self.get_reflection_status(reflection["id"])
            if status:
                statuses.append(status)
        
        return statuses


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Set up Dremio reflections for sentiment analysis")
    parser.add_argument("--host", default="localhost", help="Dremio host")
    parser.add_argument("--port", type=int, default=9047, help="Dremio port")
    parser.add_argument("--username", default="dremio", help="Dremio username")
    parser.add_argument("--password", default="dremio123", help="Dremio password")
    parser.add_argument("--catalog", default="DREMIO", help="Dremio catalog")
    parser.add_argument("--namespace", default="sentiment", help="Dremio namespace")
    parser.add_argument("--table-name", default="sentiment_data", help="Dremio table name")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without connecting to Dremio")
    
    args = parser.parse_args()
    
    # Create reflection manager
    manager = DremioReflectionManager(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        catalog=args.catalog,
        namespace=args.namespace,
        table_name=args.table_name,
        mock_mode=args.mock
    )
    
    # Set up and refresh reflections
    statuses = manager.setup_and_refresh_reflections()
    
    # Print results
    if statuses:
        logger.info(f"Created {len(statuses)} reflections:")
        for status in statuses:
            logger.info(f"  - {status.get('name', 'Unknown')} ({status.get('type', 'Unknown')}): {status.get('status', 'Unknown')}")
    else:
        logger.error("No reflections were created")


if __name__ == "__main__":
    main()