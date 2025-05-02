"""
Azure Blob Storage configuration and utility module for Iceberg lakehouse.

This module provides utilities for setting up and configuring Azure Blob Storage
as the storage backend for Iceberg tables via Dremio.
"""
import logging
import os
from typing import Dict, Any, Optional, Tuple

# Check for azure-storage-blob library
try:
    from azure.storage.blob import BlobServiceClient, ContainerClient
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False


class AzureBlobStorageConfig:
    """Configuration class for Azure Blob Storage integration with Iceberg/Dremio."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        container_name: str = "iceberg-warehouse",
        folder_path: str = "sentiment-data",
        service_principal_id: Optional[str] = None,
        service_principal_secret: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize Azure Blob Storage configuration.
        
        Either connection_string OR (account_name + account_key) must be provided.
        For service principal authentication, provide service_principal_id, 
        service_principal_secret, and tenant_id.
        
        Args:
            connection_string: Azure Storage connection string (preferred)
            account_name: Azure Storage account name (alternative to connection_string)
            account_key: Azure Storage account key (alternative to connection_string)
            container_name: Azure Storage container name for Iceberg data
            folder_path: Path within the container for Iceberg tables
            service_principal_id: Service principal client ID for authentication
            service_principal_secret: Service principal client secret
            tenant_id: Azure tenant ID for service principal
        """
        self.logger = logging.getLogger(__name__)
        
        # Require either connection_string or account credentials
        if not connection_string and not (account_name and account_key) and not (service_principal_id and service_principal_secret and tenant_id):
            raise ValueError(
                "Either connection_string OR (account_name + account_key) OR "
                "(service_principal_id + service_principal_secret + tenant_id) must be provided"
            )
        
        # Store configuration
        self.connection_string = connection_string
        self.account_name = account_name
        self.account_key = account_key
        self.container_name = container_name
        self.folder_path = folder_path
        self.service_principal_id = service_principal_id
        self.service_principal_secret = service_principal_secret
        self.tenant_id = tenant_id
        
        # Normalize folder path
        if self.folder_path and not self.folder_path.endswith('/'):
            self.folder_path += '/'
            
        # Verify Azure SDK availability
        if not AZURE_SDK_AVAILABLE:
            self.logger.warning(
                "Azure Storage SDK not found. Please install with: "
                "pip install azure-storage-blob azure-identity"
            )
    
    @classmethod
    def from_env(cls) -> 'AzureBlobStorageConfig':
        """
        Create configuration from environment variables.
        
        Environment variables:
            AZURE_STORAGE_CONNECTION_STRING: Connection string
            AZURE_STORAGE_ACCOUNT: Account name
            AZURE_STORAGE_KEY: Account key
            AZURE_STORAGE_CONTAINER: Container name
            AZURE_STORAGE_FOLDER: Folder path
            AZURE_CLIENT_ID: Service principal client ID
            AZURE_CLIENT_SECRET: Service principal client secret
            AZURE_TENANT_ID: Azure tenant ID
            
        Returns:
            AzureBlobStorageConfig: Configuration instance
        """
        return cls(
            connection_string=os.environ.get('AZURE_STORAGE_CONNECTION_STRING'),
            account_name=os.environ.get('AZURE_STORAGE_ACCOUNT'),
            account_key=os.environ.get('AZURE_STORAGE_KEY'),
            container_name=os.environ.get('AZURE_STORAGE_CONTAINER', 'iceberg-warehouse'),
            folder_path=os.environ.get('AZURE_STORAGE_FOLDER', 'sentiment-data'),
            service_principal_id=os.environ.get('AZURE_CLIENT_ID'),
            service_principal_secret=os.environ.get('AZURE_CLIENT_SECRET'),
            tenant_id=os.environ.get('AZURE_TENANT_ID')
        )


class AzureBlobStorageManager:
    """
    Manager for Azure Blob Storage integration with Iceberg/Dremio.
    
    This class provides utilities for setting up and configuring Azure Blob Storage
    as the storage backend for Iceberg tables via Dremio.
    """
    
    def __init__(self, config: Optional[AzureBlobStorageConfig] = None):
        """
        Initialize the Azure Blob Storage manager.
        
        Args:
            config: Azure Blob Storage configuration (optional, loads from env if not provided)
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or AzureBlobStorageConfig.from_env()
        
        # Verify Azure SDK availability
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure Storage SDK not found. Please install with: "
                "pip install azure-storage-blob azure-identity"
            )
        
        # Initialize client
        self.blob_service_client = None
        
    def _get_blob_service_client(self) -> BlobServiceClient:
        """
        Get or create a BlobServiceClient.
        
        Returns:
            BlobServiceClient: Azure Blob Storage service client
        """
        if self.blob_service_client is None:
            try:
                if self.config.connection_string:
                    # Connect using connection string (preferred)
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                elif self.config.account_name and self.config.account_key:
                    # Connect using account credentials
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self.blob_service_client = BlobServiceClient(
                        account_url=account_url,
                        credential=self.config.account_key
                    )
                elif self.config.service_principal_id and self.config.service_principal_secret and self.config.tenant_id:
                    # Connect using service principal
                    try:
                        from azure.identity import ClientSecretCredential
                    except ImportError:
                        raise ImportError(
                            "Azure Identity package not found. "
                            "Please install with: pip install azure-identity"
                        )
                    
                    credential = ClientSecretCredential(
                        tenant_id=self.config.tenant_id,
                        client_id=self.config.service_principal_id,
                        client_secret=self.config.service_principal_secret
                    )
                    
                    account_url = f"https://{self.config.account_name}.blob.core.windows.net"
                    self.blob_service_client = BlobServiceClient(
                        account_url=account_url,
                        credential=credential
                    )
                else:
                    raise ValueError("Invalid Azure Storage configuration")
                
                self.logger.info(f"Connected to Azure Blob Storage account: {self.blob_service_client.account_name}")
            
            except Exception as e:
                self.logger.error(f"Failed to connect to Azure Blob Storage: {str(e)}")
                raise
        
        return self.blob_service_client
    
    def ensure_container_exists(self) -> ContainerClient:
        """
        Ensure the Azure Storage container exists, create if not.
        
        Returns:
            ContainerClient: Container client for the specified container
        """
        blob_service_client = self._get_blob_service_client()
        container_client = blob_service_client.get_container_client(self.config.container_name)
        
        try:
            container_properties = container_client.get_container_properties()
            self.logger.info(f"Container exists: {self.config.container_name}")
        except ResourceNotFoundError:
            self.logger.info(f"Creating container: {self.config.container_name}")
            try:
                container_client = blob_service_client.create_container(self.config.container_name)
                self.logger.info(f"Created container: {self.config.container_name}")
            except ResourceExistsError:
                # Handle race condition (container created between check and create)
                self.logger.info(f"Container already exists: {self.config.container_name}")
        
        return container_client
    
    def create_folder_structure(self) -> None:
        """
        Create the folder structure in the Azure Storage container.
        
        In Azure Blob Storage, folders are virtual and represented by blob names.
        This method creates a marker blob to represent the folder.
        """
        container_client = self.ensure_container_exists()
        
        if not self.config.folder_path:
            return
            
        # Create marker blob for the folder
        marker_blob_name = f"{self.config.folder_path}.iceberg_ready"
        blob_client = container_client.get_blob_client(marker_blob_name)
        
        try:
            blob_client.get_blob_properties()
            self.logger.info(f"Folder marker exists: {marker_blob_name}")
        except ResourceNotFoundError:
            self.logger.info(f"Creating folder marker: {marker_blob_name}")
            blob_client.upload_blob(b"", overwrite=True)
            self.logger.info(f"Created folder marker: {marker_blob_name}")
    
    def get_dremio_storage_location(self) -> str:
        """
        Get the storage location string for Dremio configuration.
        
        Returns:
            str: Dremio-compatible storage location URI
        """
        account_name = self.config.account_name
        if not account_name and self.blob_service_client:
            account_name = self.blob_service_client.account_name
        
        if not account_name:
            raise ValueError("Azure Storage account name not available")
            
        # Format for Dremio: abfss://<container>@<account>.dfs.core.windows.net/<path>
        storage_location = f"abfss://{self.config.container_name}@{account_name}.dfs.core.windows.net/{self.config.folder_path}"
        return storage_location
    
    def configure_dremio_source(self) -> Dict[str, Any]:
        """
        Generate Dremio source configuration for Azure Blob Storage.
        
        Returns:
            Dict[str, Any]: Dremio source configuration for Azure Blob Storage
        """
        # Ensure container and folder exist
        self.create_folder_structure()
        
        # Get storage location URI
        storage_location = self.get_dremio_storage_location()
        
        # Build Dremio source configuration
        dremio_config = {
            "storage_location": storage_location,
            "connection_properties": {
                "type": "AZURE",
                "accountName": self.config.account_name,
                "container": self.config.container_name,
                "connectionType": "AZURE_STORAGE"
            }
        }
        
        # Add authentication details based on available credentials
        if self.config.account_key:
            dremio_config["connection_properties"]["accessKey"] = self.config.account_key
            dremio_config["connection_properties"]["authenticationType"] = "ACCESS_KEY"
        elif self.config.service_principal_id:
            dremio_config["connection_properties"]["authenticationType"] = "SERVICE_PRINCIPAL"
            dremio_config["connection_properties"]["clientId"] = self.config.service_principal_id
            dremio_config["connection_properties"]["clientSecret"] = self.config.service_principal_secret
            dremio_config["connection_properties"]["tenantId"] = self.config.tenant_id
        
        return dremio_config
    
    def test_connectivity(self) -> Tuple[bool, str]:
        """
        Test connectivity to Azure Blob Storage.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get blob service client
            blob_service_client = self._get_blob_service_client()
            
            # Try to list containers (basic permissions test)
            containers = list(blob_service_client.list_containers(max_results=1))
            
            # Ensure our container exists
            container_client = self.ensure_container_exists()
            
            # Try uploading and downloading a test blob
            test_blob_name = f"{self.config.folder_path}__azure_connectivity_test"
            blob_client = container_client.get_blob_client(test_blob_name)
            
            # Upload test content
            test_content = b"Azure connectivity test"
            blob_client.upload_blob(test_content, overwrite=True)
            
            # Download and verify content
            downloaded_content = blob_client.download_blob().readall()
            if downloaded_content != test_content:
                return False, "Content verification failed"
                
            # Delete test blob
            blob_client.delete_blob()
            
            return True, "Azure Blob Storage connectivity successful"
            
        except Exception as e:
            return False, f"Azure Blob Storage connectivity failed: {str(e)}"
            
    def get_required_permissions(self) -> Dict[str, Any]:
        """
        Get the required Azure Blob Storage permissions for Iceberg/Dremio.
        
        Returns:
            Dict[str, Any]: Required permissions information
        """
        return {
            "storage_blob_data_contributor": {
                "description": "Required for full read/write access to blob data",
                "scope": f"Storage account: {self.config.account_name}"
            },
            "storage_blob_data_reader": {
                "description": "Minimum required for read-only access",
                "scope": f"Storage account: {self.config.account_name} or Container: {self.config.container_name}"
            },
            "permissions": [
                "Microsoft.Storage/storageAccounts/blobServices/containers/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/write",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete"
            ]
        }