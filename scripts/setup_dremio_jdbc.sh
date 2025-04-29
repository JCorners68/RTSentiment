#\!/bin/bash
# Script to download and set up the Dremio JDBC driver

# Enable error handling
set -e

echo "======================================================================"
echo "  DREMIO JDBC DRIVER SETUP"
echo "======================================================================"

# Create directory for drivers if it doesn't exist
DRIVER_DIR="drivers"
mkdir -p "$DRIVER_DIR"

# Define variables
# Current URL from Dremio docs: https://docs.dremio.com/software/drivers/jdbc/
DREMIO_JDBC_URL="https://download.dremio.com/jdbc-driver/dremio-jdbc-driver-LATEST.jar"
DRIVER_JAR="$DRIVER_DIR/dremio-jdbc-driver.jar"

# Download Dremio JDBC driver if not exists
if [ \! -f "$DRIVER_JAR" ] || [ \! -s "$DRIVER_JAR" ] || [ "$(file "$DRIVER_JAR"  < /dev/null |  grep -c "Java archive data")" -eq 0 ]; then
    echo -e "\n1. Downloading Dremio JDBC driver..."
    
    # Remove any existing invalid driver
    rm -f "$DRIVER_JAR"
    
    # Check if wget or curl is available
    if command -v wget &> /dev/null; then
        wget -O "$DRIVER_JAR" "$DREMIO_JDBC_URL" || {
            echo "   ⚠️  Failed to download using wget"
            if command -v curl &> /dev/null; then
                echo "   Trying with curl..."
                curl -L -o "$DRIVER_JAR" "$DREMIO_JDBC_URL"
            else
                echo "   ⚠️  Neither wget nor curl is available"
                echo "   Please download the driver manually from:"
                echo "   https://docs.dremio.com/software/drivers/jdbc/"
                echo "   and place it at: $DRIVER_JAR"
                exit 1
            fi
        }
    elif command -v curl &> /dev/null; then
        curl -L -o "$DRIVER_JAR" "$DREMIO_JDBC_URL" || {
            echo "   ⚠️  Failed to download using curl"
            echo "   Please download the driver manually from:"
            echo "   https://docs.dremio.com/software/drivers/jdbc/"
            echo "   and place it at: $DRIVER_JAR"
            exit 1
        }
    else
        echo "   ⚠️  Neither wget nor curl is available"
        echo "   Please download the driver manually from:"
        echo "   https://docs.dremio.com/software/drivers/jdbc/"
        echo "   and place it at: $DRIVER_JAR"
        exit 1
    fi
    
    # Verify downloaded file is a valid JAR
    if file "$DRIVER_JAR" | grep -q "Java archive data"; then
        echo "   ✓ Downloaded Dremio JDBC driver to $DRIVER_JAR"
    else
        echo "   ⚠️  The downloaded file is not a valid JAR file. Received:"
        file "$DRIVER_JAR"
        echo ""
        echo "   Please download the driver manually from:"
        echo "   https://docs.dremio.com/software/drivers/jdbc/"
        echo "   and place it at: $DRIVER_JAR"
        
        # Remove the invalid file
        rm -f "$DRIVER_JAR" 
        
        echo ""
        echo "   MANUAL INSTALLATION INSTRUCTIONS:"
        echo "   1. Go to https://docs.dremio.com/software/drivers/jdbc/"
        echo "   2. Download the latest JDBC driver"
        echo "   3. Save it to $DRIVER_JAR"
        echo "   4. Run this script again to verify the installation"
        
        exit 1
    fi
else
    echo -e "\n1. Dremio JDBC driver already exists at $DRIVER_JAR"
fi

# Create a symbolic link in the root directory for easier access
if [ \! -L "dremio-jdbc-driver.jar" ]; then
    echo -e "\n2. Creating symbolic link in project root..."
    ln -s "$DRIVER_JAR" "dremio-jdbc-driver.jar"
    echo "   ✓ Created symbolic link: dremio-jdbc-driver.jar -> $DRIVER_JAR"
else
    echo -e "\n2. Symbolic link already exists in project root"
fi

# Install required Python packages if virtual environment exists
VENV_DIR="iceberg_venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "\n3. Installing JDBC-related packages in virtual environment..."
    source "$VENV_DIR/bin/activate" || {
        echo "   ⚠️  Failed to activate virtual environment"
        exit 1
    }
    
    pip install --upgrade pip
    pip install jaydebeapi jpype1 || {
        echo "   ⚠️  Failed to install JDBC-related packages"
        exit 1
    }
    
    echo "   ✓ Installed JDBC-related packages in virtual environment"
else
    echo -e "\n3. Virtual environment not found at $VENV_DIR"
    echo "   Please create a virtual environment first using:"
    echo "   python -m venv $VENV_DIR"
    echo "   and then run this script again"
fi

# Create a simple test script to verify JDBC driver
TEST_SCRIPT="$DRIVER_DIR/test_jdbc_driver.py"
cat > "$TEST_SCRIPT" << 'EOF'
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
EOF

# Make the test script executable
chmod +x "$TEST_SCRIPT"

# Run the test script if virtual environment exists
if [ -d "$VENV_DIR" ]; then
    echo -e "\n4. Testing JDBC driver..."
    source "$VENV_DIR/bin/activate"
    python "$TEST_SCRIPT"
    if [ $? -eq 0 ]; then
        echo "   ✓ JDBC driver test passed"
    else
        echo "   ⚠️  JDBC driver test failed"
        echo "   Please check the error messages above and ensure that:"
        echo "   1. The JAR file is a valid Dremio JDBC driver"
        echo "   2. The JVM is properly configured"
        echo "   3. The 'com.dremio.jdbc.Driver' class is present in the driver"
        echo ""
        echo "   MANUAL INSTALLATION INSTRUCTIONS:"
        echo "   1. Go to https://docs.dremio.com/software/drivers/jdbc/"
        echo "   2. Download the latest JDBC driver"
        echo "   3. Save it to $DRIVER_JAR"
        echo "   4. Run this script again to verify the installation"
    fi
fi

echo -e "\n==================================================================="
echo " SETUP COMPLETE"
echo "==================================================================="
echo ""
echo "The Dremio JDBC driver has been set up at: $DRIVER_JAR"
echo "A symbolic link has been created in the project root: dremio-jdbc-driver.jar"
echo ""
echo "To use the driver in your code:"
echo "1. Ensure the JVM can find the driver by setting the classpath"
echo "2. Use the jar_path parameter in DremioJdbcWriter to specify the driver location"
echo "3. Run tests with: python tests/test_dremio_jdbc_writer_test.py"
echo ""
echo "For more information on using JDBC with Dremio, see:"
echo "https://docs.dremio.com/software/drivers/jdbc/"
echo "==================================================================="
