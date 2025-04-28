#!/usr/bin/env python3
"""
Local Iceberg test script to verify configuration is working.

This script verifies the Iceberg configuration and catalog connection 
by loading the catalog properties.
"""
import sys
import os
import dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env.iceberg file
dotenv.load_dotenv('.env.iceberg')

# Add the project root to Python path if needed
sys.path.insert(0, os.path.abspath('.'))

try:
    # Import PyIceberg to test the catalog configuration
    import pyiceberg
    from pyiceberg.catalog import load_catalog
    
    logger.info(f"PyIceberg version: {pyiceberg.__version__}")
    
    # Print environment variables for debugging
    logger.info("Environment variables:")
    relevant_vars = [
        "PYICEBERG_CATALOG__DEFAULT__URI",
        "PYICEBERG_CATALOG__DEFAULT__WAREHOUSE",
        "PYICEBERG_CATALOG__DEFAULT__NAMESPACE",
        "AWS_ACCESS_KEY_ID", 
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION", 
        "S3_ENDPOINT"
    ]
    
    for var in relevant_vars:
        value = os.environ.get(var, "Not set")
        # Mask sensitive values
        if "SECRET" in var or "PASSWORD" in var or "KEY" in var and value != "Not set":
            value = value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
        logger.info(f"  {var}: {value}")
    
    # Try to load the catalog with explicit configuration
    logger.info("\nAttempting to load catalog using explicit configuration...")
    
    uri = os.environ.get("PYICEBERG_CATALOG__DEFAULT__URI", "http://localhost:8181")
    
    # Create explicit catalog configuration
    catalog_config = {
        "uri": uri,
        "warehouse": os.environ.get("PYICEBERG_CATALOG__DEFAULT__WAREHOUSE", "s3a://warehouse"),
        "s3.endpoint": os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        "s3.access-key-id": os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
        "s3.secret-access-key": os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        "s3.path-style-access": "true"
    }
    
    # Show the catalog config (masking sensitive data)
    safe_config = catalog_config.copy()
    for k, v in safe_config.items():
        if "secret" in k or "access-key" in k and v:
            safe_config[k] = v[:3] + "***" + v[-3:] if len(v) > 6 else "***"
    
    logger.info(f"Catalog config: {safe_config}")
    
    # Try to load catalog
    try:
        logger.info("Attempting to connect to catalog...")
        catalog = load_catalog("default", **catalog_config)
        logger.info("Catalog loaded successfully!")
        
        # Try to list namespaces
        try:
            namespaces = catalog.list_namespaces()
            logger.info(f"Available namespaces: {namespaces}")
        except Exception as e:
            logger.error(f"Failed to list namespaces: {str(e)}")
        
        # Try to create namespace if it doesn't exist
        try:
            namespace = os.environ.get("PYICEBERG_CATALOG__DEFAULT__NAMESPACE", "sentiment")
            if (namespace,) not in namespaces:
                logger.info(f"Creating namespace: {namespace}")
                catalog.create_namespace(namespace)
                logger.info(f"Created namespace: {namespace}")
            else:
                logger.info(f"Namespace {namespace} already exists")
        except Exception as e:
            logger.error(f"Failed to create namespace: {str(e)}")
        
    except Exception as e:
        logger.error(f"Failed to load catalog: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    logger.error("Make sure you're running in the virtual environment with required packages:")
    logger.error("  source iceberg_venv/bin/activate")
    sys.exit(1)

logger.info("\nTest completed successfully! Configuration is valid.")