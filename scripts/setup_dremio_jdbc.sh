#\!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DRIVERS_DIR="${PROJECT_ROOT}/drivers"

# Create drivers directory if it doesn't exist
mkdir -p "${DRIVERS_DIR}"

# Set JDBC driver URL and destination
JDBC_URL="https://download.dremio.com/jdbc-driver/dremio-jdbc-driver-LATEST.jar"
JDBC_DEST="${DRIVERS_DIR}/dremio-jdbc-driver.jar"

echo "Setting up Dremio JDBC driver..."
echo "  Project root: ${PROJECT_ROOT}"
echo "  Drivers directory: ${DRIVERS_DIR}"

# Download the JDBC driver if not already present
if [ \! -f "${JDBC_DEST}" ]; then
    echo "Downloading Dremio JDBC driver from ${JDBC_URL}..."
    curl -fSL -o "${JDBC_DEST}" "${JDBC_URL}"
    echo "Driver downloaded to ${JDBC_DEST}"
else
    echo "Dremio JDBC driver already exists at ${JDBC_DEST}"
fi

echo "Dremio JDBC driver setup completed successfully."
    
# Create symlinks in the project root for easier discovery
SYMLINK_PATH="${PROJECT_ROOT}/dremio-jdbc-driver.jar"
echo "Creating symlink at ${SYMLINK_PATH} -> ${JDBC_DEST}"
ln -sf "${JDBC_DEST}" "${SYMLINK_PATH}"
