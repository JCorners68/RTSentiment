#\!/usr/bin/env python3
"""
Test script to verify that the Dremio JDBC driver can be loaded.
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_jdbc_driver():
    """Test that the JDBC driver can be loaded."""
    try:
        import jaydebeapi
        import jpype
        
        logger.info("Successfully imported jaydebeapi and jpype")
        
        # Use absolute path to resolve symlinks
        driver_jar = os.path.abspath("drivers/dremio-jdbc-driver.jar")
        if not os.path.exists(driver_jar):
            # Try alternate paths if the primary one fails
            alt_paths = [
                os.path.abspath("dremio-jdbc-driver.jar"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "dremio-jdbc-driver.jar")
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    driver_jar = path
                    break
            else:
                logger.error("Dremio JDBC driver JAR not found at any expected location")
                return False
            
        logger.info(f"Testing JAR at: {driver_jar}")
        
        # Verify JAR file
        import subprocess
        result = subprocess.run(['file', driver_jar], capture_output=True, text=True)
        logger.info(f"File type: {result.stdout.strip()}")
        
        if "Java archive data" not in result.stdout:
            logger.error(f"File is not a valid JAR: {result.stdout.strip()}")
            return False
        
        # Try to load the driver class
        if not jpype.isJVMStarted():
            jpype.startJVM(jpype.getDefaultJVMPath(), f"-Djava.class.path={driver_jar}")
            logger.info("JVM started")
        
        try:
            driver_class = jpype.JClass("com.dremio.jdbc.Driver")
            logger.info("Successfully loaded Dremio JDBC driver class")
            return True
        except Exception as e:
            logger.error(f"Failed to load Dremio JDBC driver class: {str(e)}")
            return False
            
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        logger.error("Please install required packages: pip install jaydebeapi jpype1")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_jdbc_driver()
    if success:
        logger.info("✅ Dremio JDBC driver test PASSED")
        sys.exit(0)
    else:
        logger.error("❌ Dremio JDBC driver test FAILED")
        sys.exit(1)
