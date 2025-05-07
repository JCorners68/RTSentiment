# RT Sentiment Analysis - Azure Terraform Variables
# This file contains the values for the variables defined in variables.tf

# Core Azure Configuration
subscription_id = "644936a7-e58a-4ccb-a882-0005f213f5bd"
tenant_id       = "1ced8c49-a03c-439c-9ff1-0c23f5128720"
client_id       = "00000000-0000-0000-0000-000000000000" # Placeholder for testing only
client_secret   = "dummy-secret-for-testing-only"        # Placeholder for testing only

# Resource Group
resource_group_name = "rt-sentiment-uat"
location            = "westus"  # US West region for low latency

# AKS Configuration
aks_cluster_name    = "rt-sentiment-aks"
kubernetes_version  = "1.26.6"
node_count          = 3
vm_size             = "Standard_D4s_v3"

# Proximity Placement Group
ppg_name = "rt-sentiment-ppg"

# Container Registry
acr_name = "rtsentiregistry"

# Storage
storage_account_name = "rtsentistorage"

# Front Door
front_door_name = "rt-sentiment-fd"

# Application Insights
app_insights_name = "rt-sentiment-insights"

# Log Analytics
log_analytics_name = "rt-sentiment-logs"

# Alerts and Notifications
alert_email = "jonathan.corners@gmail.com"

# Tags
tags = {
  environment = "uat"
  project     = "rt-sentiment"
  managedBy   = "terraform"
}

# Service configurations
data_acquisition_host = "data-acquisition.uat.example.com"