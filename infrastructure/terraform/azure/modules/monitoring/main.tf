# Sentimark - Azure Monitoring Module
# This module sets up monitoring and observability for Iceberg in production

# Enhanced Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "iceberg_monitoring" {
  name                = var.log_analytics_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  
  tags = var.tags
}

# Enhanced Application Insights for Data Tier
resource "azurerm_application_insights" "data_tier" {
  name                = "${var.base_name}-data-tier-insights"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.iceberg_monitoring.id
  
  tags = var.tags
}

# Dashboard for Iceberg Monitoring (using portal_dashboard resource type)
resource "azurerm_portal_dashboard" "iceberg_dashboard" {
  name                 = "${var.base_name}-iceberg-dashboard"
  resource_group_name  = var.resource_group_name
  location             = var.location
  dashboard_properties = <<DASH
{
  "lenses": {
    "0": {
      "order": 0,
      "parts": {
        "0": {
          "position": {
            "x": 0,
            "y": 0,
            "colSpan": 6,
            "rowSpan": 4
          },
          "metadata": {
            "inputs": [
              {
                "name": "resourceTypeMode",
                "isOptional": true,
                "value": "workspace"
              },
              {
                "name": "ComponentId",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
              },
              {
                "name": "Scope",
                "isOptional": true,
                "value": {
                  "resourceIds": [
                    "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
                  ]
                }
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Iceberg Query Performance"
              },
              {
                "name": "Version",
                "isOptional": true,
                "value": "2.0"
              },
              {
                "name": "TimeRange",
                "isOptional": true,
                "value": "P1D"
              },
              {
                "name": "Query",
                "isOptional": true,
                "value": "traces | where customDimensions.operationType == 'IcebergQuery' | summarize avgDuration=avg(duration), maxDuration=max(duration), count=count() by bin(timestamp, 15m), customDimensions.queryType | render timechart"
              },
              {
                "name": "PartTitle",
                "isOptional": true,
                "value": "Iceberg Query Performance"
              },
              {
                "name": "PartSubTitle",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.name}"
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Iceberg Query Performance"
              },
              {
                "name": "aiRepeatDirective",
                "isOptional": true,
                "value": "data"
              }
            ],
            "type": "Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart"
          }
        },
        "1": {
          "position": {
            "x": 6,
            "y": 0,
            "colSpan": 6,
            "rowSpan": 4
          },
          "metadata": {
            "inputs": [
              {
                "name": "resourceTypeMode",
                "isOptional": true,
                "value": "workspace"
              },
              {
                "name": "ComponentId",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
              },
              {
                "name": "Scope",
                "isOptional": true,
                "value": {
                  "resourceIds": [
                    "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
                  ]
                }
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Storage Operations"
              },
              {
                "name": "Version",
                "isOptional": true,
                "value": "2.0"
              },
              {
                "name": "TimeRange",
                "isOptional": true,
                "value": "P1D"
              },
              {
                "name": "Query",
                "isOptional": true,
                "value": "traces | where customDimensions.operationType == 'StorageOperation' | summarize count=count() by bin(timestamp, 15m), customDimensions.operationName | render timechart"
              },
              {
                "name": "PartTitle",
                "isOptional": true,
                "value": "Storage Operations"
              },
              {
                "name": "PartSubTitle",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.name}"
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Storage Operations"
              },
              {
                "name": "aiRepeatDirective",
                "isOptional": true,
                "value": "data"
              }
            ],
            "type": "Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart"
          }
        },
        "2": {
          "position": {
            "x": 0,
            "y": 4,
            "colSpan": 6,
            "rowSpan": 4
          },
          "metadata": {
            "inputs": [
              {
                "name": "resourceTypeMode",
                "isOptional": true,
                "value": "workspace"
              },
              {
                "name": "ComponentId",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
              },
              {
                "name": "Scope",
                "isOptional": true,
                "value": {
                  "resourceIds": [
                    "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
                  ]
                }
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Database Backend Usage"
              },
              {
                "name": "Version",
                "isOptional": true,
                "value": "2.0"
              },
              {
                "name": "TimeRange",
                "isOptional": true,
                "value": "P1D"
              },
              {
                "name": "Query",
                "isOptional": true,
                "value": "traces | where customDimensions.componentType == 'Repository' | summarize count=count() by bin(timestamp, 15m), customDimensions.dbBackend | render piechart"
              },
              {
                "name": "PartTitle",
                "isOptional": true,
                "value": "Database Backend Usage"
              },
              {
                "name": "PartSubTitle",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.name}"
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Database Backend Usage"
              },
              {
                "name": "aiRepeatDirective",
                "isOptional": true,
                "value": "data"
              }
            ],
            "type": "Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart"
          }
        },
        "3": {
          "position": {
            "x": 6,
            "y": 4,
            "colSpan": 6,
            "rowSpan": 4
          },
          "metadata": {
            "inputs": [
              {
                "name": "resourceTypeMode",
                "isOptional": true,
                "value": "workspace"
              },
              {
                "name": "ComponentId",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
              },
              {
                "name": "Scope",
                "isOptional": true,
                "value": {
                  "resourceIds": [
                    "${azurerm_log_analytics_workspace.iceberg_monitoring.id}"
                  ]
                }
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Database Errors"
              },
              {
                "name": "Version",
                "isOptional": true,
                "value": "2.0"
              },
              {
                "name": "TimeRange",
                "isOptional": true,
                "value": "P1D"
              },
              {
                "name": "Query",
                "isOptional": true,
                "value": "traces | where severityLevel == 3 or severityLevel == 4 | where customDimensions.componentType == 'Repository' | summarize count=count() by bin(timestamp, 15m), customDimensions.dbBackend, customDimensions.errorType | render barchart"
              },
              {
                "name": "PartTitle",
                "isOptional": true,
                "value": "Database Errors"
              },
              {
                "name": "PartSubTitle",
                "isOptional": true,
                "value": "${azurerm_log_analytics_workspace.iceberg_monitoring.name}"
              },
              {
                "name": "PartId",
                "isOptional": true,
                "value": "Database Errors"
              },
              {
                "name": "aiRepeatDirective",
                "isOptional": true,
                "value": "data"
              }
            ],
            "type": "Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart"
          }
        }
      }
    }
  },
  "metadata": {
    "model": {
      "timeRange": {
        "value": {
          "relative": {
            "duration": 24,
            "timeUnit": 1
          }
        },
        "type": "MsPortalFx.Composition.Configuration.ValueTypes.TimeRange"
      }
    }
  }
}
DASH

  tags = var.tags
}

# Create monitor action group for Iceberg alerts
resource "azurerm_monitor_action_group" "iceberg_alerts" {
  name                = "${var.base_name}-iceberg-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "iceAlerts"
  
  email_receiver {
    name                    = "admin"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
  
  tags = var.tags
}

# Alert for Iceberg query performance degradation
resource "azurerm_monitor_scheduled_query_rules_alert" "query_performance" {
  name                = "${var.base_name}-iceberg-query-perf-alert"
  resource_group_name = var.resource_group_name
  location            = var.location
  
  action {
    action_group           = [azurerm_monitor_action_group.iceberg_alerts.id]
    email_subject          = "Iceberg Query Performance Alert"
    custom_webhook_payload = "{}"
  }
  
  data_source_id = azurerm_application_insights.data_tier.id
  description    = "Alert when Iceberg query performance degrades"
  enabled        = true
  
  query       = <<-QUERY
    traces
    | where customDimensions.operationType == 'IcebergQuery'
    | summarize avgDuration=avg(toreal(customDimensions.durationMs)) by bin(timestamp, 15m), tostring(customDimensions.queryType)
    | where avgDuration > ${var.query_performance_threshold}
  QUERY
  severity    = 1
  frequency   = 15
  time_window = 30
  
  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }
  
  tags = var.tags
}

# Alert for high database error rate
resource "azurerm_monitor_scheduled_query_rules_alert" "error_rate" {
  name                = "${var.base_name}-iceberg-error-rate-alert"
  resource_group_name = var.resource_group_name
  location            = var.location
  
  action {
    action_group           = [azurerm_monitor_action_group.iceberg_alerts.id]
    email_subject          = "Iceberg Error Rate Alert"
    custom_webhook_payload = "{}"
  }
  
  data_source_id = azurerm_application_insights.data_tier.id
  description    = "Alert when Iceberg error rate exceeds threshold"
  enabled        = true
  
  query       = <<-QUERY
    traces
    | where customDimensions.dbBackend == 'iceberg'
    | where severityLevel >= 3
    | summarize errorCount=count() by bin(timestamp, 15m)
    | where errorCount > ${var.error_threshold}
  QUERY
  severity    = 1
  frequency   = 15
  time_window = 30
  
  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }
  
  tags = var.tags
}

# Diagnostic setting for App Insights (without deprecated retention policy)
resource "azurerm_monitor_diagnostic_setting" "app_insights" {
  name                       = "app-insights-logs"
  target_resource_id         = azurerm_application_insights.data_tier.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.iceberg_monitoring.id
  
  # Using log_category_group format for logs
  enabled_log {
    category_group = "allLogs"
  }
  
  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# Storage account for logs if needed
resource "azurerm_storage_account" "logs" {
  count                    = var.log_retention_days > 0 ? 1 : 0
  name                     = lower(replace("${var.base_name}logs${random_string.suffix[0].result}", "-", ""))
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  tags = var.tags
}

# Create random suffix for storage account
resource "random_string" "suffix" {
  count   = 1
  length  = 6
  special = false
  upper   = false
}

# Storage management policy for log retention
resource "azurerm_storage_management_policy" "retention" {
  count              = var.log_retention_days > 0 ? 1 : 0
  storage_account_id = azurerm_storage_account.logs[0].id

  rule {
    name    = "logs-retention"
    enabled = true
    
    filters {
      prefix_match = ["logs/insights-logs"]
      blob_types   = ["appendBlob"]
    }
    
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = var.log_retention_days
      }
    }
  }
}