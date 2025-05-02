"""
Azure authentication module for service principal authentication.

This module provides utilities for Azure authentication using service principals,
which is the recommended approach for non-interactive application authentication.
"""
import logging
import os
from typing import Dict, Any, Optional, Tuple

# Check for azure-identity library
try:
    from azure.identity import ClientSecretCredential, DefaultAzureCredential
    from azure.core.exceptions import ClientAuthenticationError
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False


class AzureServicePrincipalAuth:
    """
    Azure service principal authentication manager.
    
    This class provides utilities for authenticating with Azure using service principals,
    which is the recommended approach for non-interactive application authentication.
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize Azure service principal authentication.
        
        If any parameter is not provided, it will be loaded from environment variables.
        
        Args:
            client_id: Service principal client ID (Application ID)
            client_secret: Service principal client secret
            tenant_id: Azure tenant ID
        """
        self.logger = logging.getLogger(__name__)
        
        # Load from environment if not provided
        self.client_id = client_id or os.environ.get('AZURE_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('AZURE_CLIENT_SECRET')
        self.tenant_id = tenant_id or os.environ.get('AZURE_TENANT_ID')
        
        # Verify Azure Identity availability
        if not AZURE_IDENTITY_AVAILABLE:
            self.logger.warning(
                "Azure Identity package not found. Please install with: "
                "pip install azure-identity"
            )
    
    def validate_credentials(self) -> bool:
        """
        Validate that all required credentials are available.
        
        Returns:
            bool: True if all required credentials are available, False otherwise
        """
        if not self.client_id:
            self.logger.error("Service principal client ID not provided")
            return False
            
        if not self.client_secret:
            self.logger.error("Service principal client secret not provided")
            return False
            
        if not self.tenant_id:
            self.logger.error("Azure tenant ID not provided")
            return False
            
        return True
    
    def get_credential(self) -> Optional[ClientSecretCredential]:
        """
        Get an Azure credential object for the service principal.
        
        Returns:
            Optional[ClientSecretCredential]: Azure credential object, or None if not available
        """
        if not AZURE_IDENTITY_AVAILABLE:
            raise ImportError(
                "Azure Identity package not found. Please install with: "
                "pip install azure-identity"
            )
            
        if not self.validate_credentials():
            return None
            
        try:
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            return credential
        except Exception as e:
            self.logger.error(f"Failed to create credential: {str(e)}")
            return None
    
    def test_authentication(self) -> Tuple[bool, str]:
        """
        Test authentication with Azure using the service principal.
        
        This method attempts to get a token for the Azure Management API to verify
        that the service principal credentials are valid.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not AZURE_IDENTITY_AVAILABLE:
            return False, "Azure Identity package not installed"
            
        if not self.validate_credentials():
            return False, "Missing required credentials"
            
        try:
            credential = self.get_credential()
            if not credential:
                return False, "Failed to create credential"
                
            # Try to get a token for the Azure Management API
            # This will verify that the service principal credentials are valid
            token = credential.get_token("https://management.azure.com/.default")
            if not token:
                return False, "Failed to get token"
                
            return True, "Service principal authentication successful"
            
        except ClientAuthenticationError as e:
            return False, f"Authentication failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class AzureAuthHelper:
    """
    Helper class for Azure authentication with fallback mechanisms.
    
    This class provides a unified interface for authentication with Azure,
    with support for multiple authentication methods and automatic fallback.
    """
    
    @staticmethod
    def get_credential(use_default_credential: bool = True) -> Any:
        """
        Get an Azure credential object with automatic fallback.
        
        This method first tries to use service principal authentication.
        If that fails and use_default_credential is True, it falls back to
        DefaultAzureCredential which supports multiple authentication methods.
        
        Args:
            use_default_credential: Whether to fall back to DefaultAzureCredential
            
        Returns:
            Any: Azure credential object
        """
        if not AZURE_IDENTITY_AVAILABLE:
            raise ImportError(
                "Azure Identity package not found. Please install with: "
                "pip install azure-identity"
            )
            
        logger = logging.getLogger(__name__)
        
        # First try service principal
        sp_auth = AzureServicePrincipalAuth()
        credential = sp_auth.get_credential()
        
        if credential:
            logger.info("Using service principal authentication")
            return credential
            
        # Fall back to default credential if allowed
        if use_default_credential:
            logger.info("Falling back to DefaultAzureCredential")
            try:
                credential = DefaultAzureCredential()
                return credential
            except Exception as e:
                logger.error(f"Failed to create DefaultAzureCredential: {str(e)}")
        
        raise ValueError("Failed to get Azure credential")