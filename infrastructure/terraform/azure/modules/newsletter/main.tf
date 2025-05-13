/**
 * Newsletter Subscription System Terraform Module
 * Integrates with existing Sentimark infrastructure
 */

# Reference existing resources
data "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  resource_group_name = var.resource_group_name
}

data "azurerm_cosmos_db_account" "data_tier" {
  name                = var.cosmos_db_account_name
  resource_group_name = var.resource_group_name
}

# Create Azure API Management service (if not using existing one)
resource "azurerm_api_management" "newsletter_api" {
  count               = var.create_new_apim ? 1 : 0
  name                = "sentimark-newsletter-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  publisher_name      = "Sentimark"
  publisher_email     = var.admin_email
  sku_name            = "Consumption_0"
  
  tags = merge(var.tags, {
    component = "newsletter"
  })
}

# Get reference to existing API Management if using one
data "azurerm_api_management" "existing_apim" {
  count               = var.create_new_apim ? 0 : 1
  name                = var.existing_apim_name
  resource_group_name = var.resource_group_name
}

locals {
  apim_id = var.create_new_apim ? azurerm_api_management.newsletter_api[0].id : data.azurerm_api_management.existing_apim[0].id
  apim_name = var.create_new_apim ? azurerm_api_management.newsletter_api[0].name : data.azurerm_api_management.existing_apim[0].name
}

# Create a newsletter API
resource "azurerm_api_management_api" "newsletter_api" {
  name                = "newsletter-api"
  resource_group_name = var.resource_group_name
  api_management_name = local.apim_name
  revision            = "1"
  display_name        = "Newsletter Subscription API"
  path                = "newsletter"
  protocols           = ["https"]
  service_url         = "https://${var.aks_ingress_hostname}/api/newsletter"
  
  subscription_required = true
}

# Create a subscription API key
resource "azurerm_api_management_subscription" "newsletter_subscription" {
  resource_group_name = var.resource_group_name
  api_management_name = local.apim_name
  display_name        = "Newsletter API Subscription"
  api_id              = azurerm_api_management_api.newsletter_api.id
  state               = "active"
}

# Create a rate limit policy
resource "azurerm_api_management_api_policy" "rate_limit_policy" {
  resource_group_name = var.resource_group_name
  api_management_name = local.apim_name
  api_name            = azurerm_api_management_api.newsletter_api.name

  xml_content = <<XML
<policies>
  <inbound>
    <base />
    <rate-limit calls="${var.rate_limit_calls}" renewal-period="${var.rate_limit_period}" />
    <cors>
      <allowed-origins>
        <origin>${var.allowed_origins}</origin>
      </allowed-origins>
      <allowed-methods>
        <method>POST</method>
        <method>OPTIONS</method>
      </allowed-methods>
      <allowed-headers>
        <header>Content-Type</header>
        <header>Ocp-Apim-Subscription-Key</header>
      </allowed-headers>
    </cors>
  </inbound>
</policies>
XML
}

# Create a Cosmos DB container for subscribers
resource "azurerm_cosmosdb_sql_container" "subscribers" {
  name                = "subscribers"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmos_db_account.data_tier.name
  database_name       = var.cosmos_db_database_name
  partition_key_path  = "/email"
  
  indexing_policy {
    indexing_mode = "consistent"
    
    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
  
  unique_key {
    paths = ["/email"]
  }
}

# Create Azure Communication Service for email
resource "azurerm_communication_service" "newsletter" {
  name                = "sentimark-newsletter-${var.environment}"
  resource_group_name = var.resource_group_name
  data_location       = "United States"
  
  tags = merge(var.tags, {
    component = "newsletter"
  })
}

# Create Event Grid Topic for notifications
resource "azurerm_eventgrid_topic" "newsletter_events" {
  name                = "sentimark-newsletter-events-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  
  tags = merge(var.tags, {
    component = "newsletter"
  })
}

# Create Application Insights for monitoring
resource "azurerm_application_insights" "newsletter" {
  name                = "sentimark-newsletter-insights-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  
  tags = merge(var.tags, {
    component = "newsletter"
  })
}

# Add the monitoring to the app configuration
module "app_config" {
  source = "../app-config"
  
  resource_group_name = var.resource_group_name
  app_config_name     = var.app_config_name
  
  configuration_entries = {
    "Newsletter:SubscriptionKey"       = azurerm_api_management_subscription.newsletter_subscription.primary_key
    "Newsletter:EventGridTopicEndpoint" = azurerm_eventgrid_topic.newsletter_events.endpoint
    "Newsletter:EventGridTopicKey"     = azurerm_eventgrid_topic.newsletter_events.primary_access_key
    "Newsletter:CommunicationServiceConnectionString" = azurerm_communication_service.newsletter.primary_connection_string
    "Newsletter:CosmosDbConnectionString" = data.azurerm_cosmos_db_account.data_tier.connection_strings[0]
    "Newsletter:ApplicationInsightsInstrumentationKey" = azurerm_application_insights.newsletter.instrumentation_key
  }
}
