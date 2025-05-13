# Canary Deployment Implementation Plan for Sentimark

## Executive Summary

This document outlines a comprehensive strategy for implementing canary deployments for Sentimark's data tier, enabling safe, gradual rollout of the PostgreSQL to Iceberg migration. The plan leverages existing Azure App Configuration for feature flags and extends the current Kubernetes deployment architecture to support parallel deployments of stable and canary versions.

## 1. Architecture Overview

### Current State
- Single deployment of data tier services
- Feature flag system using Azure App Configuration
- PostgreSQL to Iceberg migration capabilities
- No traffic splitting or progressive delivery

### Target Architecture
- Dual-track deployment (stable + canary)
- Traffic splitting based on configurable rules
- Automated metrics-based promotion/rollback
- Integration with existing monitoring

## 2. Implementation Components

### 2.1 Terraform Changes

#### Azure App Configuration Module Enhancements

```hcl
# Add canary-specific feature flags
locals {
  canary_feature_flags = {
    "feature.canary-enabled" = {
      label = "production"
      value = var.enable_canary ? "true" : "false"
      type  = "kv"
    },
    "feature.canary-version" = {
      label = "production"
      value = var.canary_version
      type  = "kv"
    },
    "deployment.canary-traffic-percentage" = {
      label = "production"
      value = tostring(var.canary_traffic_percentage)
      type  = "kv"
    },
    "deployment.canary-auto-promotion-enabled" = {
      label = "production"
      value = var.canary_auto_promotion_enabled ? "true" : "false"
      type  = "kv"
    }
  }
}

# Add to existing feature_flags local
locals {
  feature_flags = merge(local.existing_feature_flags, local.canary_feature_flags)
}
```

#### Monitoring Module Enhancements

```hcl
# Add canary-specific alerts
resource "azurerm_monitor_metric_alert" "canary_error_rate" {
  name                = "canary-error-rate-alert"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_insights_id]
  description         = "Alert when canary error rate exceeds threshold"
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "exceptions/server"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 5
    
    dimension {
      name     = "cloud_RoleName"
      operator = "Include"
      values   = ["data-tier-canary"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.operations.id
  }
}

# Add dashboard for canary metrics
resource "azurerm_dashboard" "canary_dashboard" {
  name                = "canary-metrics-dashboard"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
  
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
              {...}
            ],
            "type": "Extension/AppInsightsExtension/PartType/MetricsExplorerBladePinnedPart",
            "settings": {
              "content": {
                "options": {
                  "chart": {
                    "metrics": [
                      {
                        "resourceMetadata": {
                          "id": "${var.app_insights_id}"
                        },
                        "name": "requests/failed",
                        "aggregationType": "sum",
                        "namespace": "microsoft.insights/components",
                        "metricVisualization": {
                          "displayName": "Failed requests"
                        }
                      }
                    ],
                    "title": "Failed requests by version",
                    "visualization": {
                      "chartType": "line",
                      "legendVisualization": {
                        "isVisible": true,
                        "position": "bottom",
                        "hideSubtitle": false
                      },
                      "axisVisualization": {
                        "x": {
                          "isVisible": true,
                          "axisType": "time"
                        },
                        "y": {
                          "isVisible": true,
                          "axisType": "linear"
                        }
                      }
                    },
                    "timespan": {
                      "relative": {
                        "duration": 86400000
                      },
                      "showUTCTime": false,
                      "grain": 1
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
DASH
}
```

### 2.2 Helm Chart Changes

#### Create Canary Templates

```yaml
# data-tier-canary-deployment.yaml
{{- if and .Values.dataTier.enabled .Values.dataTier.canary.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier-canary" "service" .Values.dataTier "releaseName" .Release.Name) }}
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "data-tier-canary" "service" .Values.dataTier "releaseName" .Release.Name "component" "data") | nindent 4 }}
    version: canary
  {{- with .Values.dataTier.canary.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  replicas: {{ .Values.dataTier.canary.replicaCount }}
  selector:
    matchLabels:
      {{- include "sentimark.serviceSelectorLabels" (dict "defaultName" "data-tier-canary" "service" .Values.dataTier "releaseName" .Release.Name) | nindent 6 }}
      version: canary
  template:
    metadata:
      labels:
        {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "data-tier-canary" "service" .Values.dataTier "releaseName" .Release.Name "component" "data") | nindent 8 }}
        version: canary
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8004"
        prometheus.io/path: "/actuator/prometheus"
    spec:
      # [... existing spec content ...]
      containers:
      - name: {{ .Values.dataTier.name }}-canary
        image: "{{ .Values.dataTier.image.repository }}:{{ .Values.dataTier.canary.image.tag | default "canary" }}"
        imagePullPolicy: {{ .Values.dataTier.image.pullPolicy }}
        # [... existing container spec content ...]
        env:
        {{- range .Values.dataTier.env }}
        - name: {{ .name }}
          {{- if .value }}
          value: {{ .value | quote }}
          {{- else if .valueFrom }}
          valueFrom:
            {{- toYaml .valueFrom | nindent 12 }}
          {{- end }}
        {{- end }}
        # Additional canary environment variables
        - name: APP_VERSION
          value: "canary"
        - name: APPLICATIONINSIGHTS_ROLE_NAME
          value: "data-tier-canary"
{{- end }}
```

#### Update Service to Support Traffic Splitting

```yaml
# data-tier-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name "component" "data") | nindent 4 }}
spec:
  type: {{ .Values.dataTier.service.type }}
  ports:
    - port: {{ .Values.dataTier.service.port }}
      targetPort: {{ .Values.dataTier.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "sentimark.serviceSelectorLabels" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) | nindent 4 }}
    {{- if and .Values.dataTier.canary.enabled (gt (.Values.dataTier.canary.trafficPercentage | int) 0) }}
    # No version selector when traffic splitting is enabled - will be handled by destination rules
    {{- else }}
    version: stable
    {{- end }}
```

#### Add Istio Resources for Traffic Management

```yaml
# data-tier-istio.yaml
{{- if and .Values.dataTier.enabled .Values.dataTier.canary.enabled -}}
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
spec:
  host: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
  subsets:
  - name: stable
    labels:
      version: stable
  - name: canary
    labels:
      version: canary
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
spec:
  hosts:
  - {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
  http:
  - route:
    - destination:
        host: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
        subset: stable
      weight: {{ sub 100 (.Values.dataTier.canary.trafficPercentage | int) }}
    - destination:
        host: {{ include "sentimark.serviceName" (dict "defaultName" "data-tier" "service" .Values.dataTier "releaseName" .Release.Name) }}
        subset: canary
      weight: {{ .Values.dataTier.canary.trafficPercentage | int }}
{{- end }}
```

#### Update Values.yaml

```yaml
# Add canary configuration to values.yaml
dataTier:
  # Existing configuration...
  
  # Canary deployment configuration
  canary:
    enabled: false
    replicaCount: 1
    trafficPercentage: 0
    image:
      tag: canary
    # Automatic promotion settings
    autoPromotion:
      enabled: false
      metrics:
        errorRate:
          threshold: 1.0
          duration: 30m
        responseTime:
          thresholdMs: 500
          duration: 30m
    # Rollback settings
    rollback:
      enabled: true
      metrics:
        errorRate:
          threshold: 5.0
          duration: 5m
    resources:
      limits:
        cpu: 1500m
        memory: 2Gi
      requests:
        cpu: 500m
        memory: 1Gi
```

## 3. Operational Workflow

### 3.1 Canary Deployment Process

1. **Preparation**
   - Tag new version as `canary` in container registry
   - Update configuration in App Configuration

2. **Deployment**
   - Deploy canary version with minimal replica count and 0% traffic
   - Verify deployment health

3. **Traffic Migration**
   - Gradually increase `canary.trafficPercentage` in Helm values
   - For each increment:
     - Update VirtualService via Helm upgrade
     - Monitor metrics for anomalies
     - Wait for stabilization period

4. **Promotion**
   - When canary receives 100% traffic and remains stable:
     - Promote canary image to stable tag
     - Perform rolling update on stable deployment
     - Reset canary traffic to 0%

5. **Rollback**
   - If metrics exceed thresholds:
     - Immediately set canary traffic to 0%
     - Notify operations team
     - Preserve canary pods for debugging

### 3.2 Automation Script

```bash
#!/bin/bash
# canary-deployment.sh
# Automates the canary deployment process for the data tier

set -e

NAMESPACE="sentimark"
RELEASE_NAME="sentimark"
CANARY_TAG="canary"
STABLE_TAG="stable"
SERVICE_NAME="data-tier"
TRAFFIC_INCREMENTS=(0 10 30 50 75 100)
STABILITY_PERIOD_MINUTES=15

# Process arguments
VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

# Step 1: Update canary configuration
echo "Updating canary configuration in App Configuration..."
az appconfig kv set --name sentimarkappconfig --key "feature.canary-version" --value "$VERSION" --label production --yes

# Step 2: Deploy new canary version
echo "Deploying canary version $VERSION with 0% traffic..."
helm upgrade --install $RELEASE_NAME ./infrastructure/helm/sentimark-services \
  --namespace $NAMESPACE \
  --set dataTier.canary.enabled=true \
  --set dataTier.canary.trafficPercentage=0 \
  --set dataTier.canary.image.tag=$VERSION

# Step 3: Verify initial deployment
echo "Verifying canary deployment health..."
kubectl wait --for=condition=available deployment/$SERVICE_NAME-canary -n $NAMESPACE --timeout=5m

# Step 4: Incremental traffic shifting
for TRAFFIC in "${TRAFFIC_INCREMENTS[@]}"; do
  if [ $TRAFFIC -eq 0 ]; then
    continue
  fi
  
  echo "Increasing canary traffic to $TRAFFIC%"
  helm upgrade $RELEASE_NAME ./infrastructure/helm/sentimark-services \
    --namespace $NAMESPACE \
    --set dataTier.canary.enabled=true \
    --set dataTier.canary.trafficPercentage=$TRAFFIC \
    --set dataTier.canary.image.tag=$VERSION \
    --reuse-values
  
  echo "Monitoring for $STABILITY_PERIOD_MINUTES minutes..."
  MONITORING_END=$(($(date +%s) + $STABILITY_PERIOD_MINUTES*60))
  
  while [ $(date +%s) -lt $MONITORING_END ]; do
    # Check error rate using Azure CLI
    ERROR_RATE=$(az monitor metrics list \
      --resource $APP_INSIGHTS_ID \
      --metric "exceptions/server" \
      --filter "cloud_RoleName eq 'data-tier-canary'" \
      --interval 5m \
      --aggregation count \
      --output json | jq '.value[0].timeseries[0].data[-1].count')
    
    if [ $ERROR_RATE -gt 5 ]; then
      echo "Error rate too high: $ERROR_RATE - rolling back"
      helm upgrade $RELEASE_NAME ./infrastructure/helm/sentimark-services \
        --namespace $NAMESPACE \
        --set dataTier.canary.trafficPercentage=0 \
        --reuse-values
      exit 1
    fi
    
    echo "Current error rate: $ERROR_RATE - continuing monitoring"
    sleep 60
  done
  
  echo "Traffic increment to $TRAFFIC% successful"
done

# Step 5: Promotion
if [ $TRAFFIC -eq 100 ]; then
  echo "Canary deployment successful, promoting to stable"
  
  # Tag the successful canary image as stable
  az acr import \
    --name rtsentiregistry \
    --source rtsentiregistry.azurecr.io/data-tier:$VERSION \
    --image data-tier:$STABLE_TAG \
    --force
  
  # Update stable deployment with rolling update
  helm upgrade $RELEASE_NAME ./infrastructure/helm/sentimark-services \
    --namespace $NAMESPACE \
    --set dataTier.image.tag=$STABLE_TAG \
    --set dataTier.canary.trafficPercentage=0 \
    --reuse-values
  
  echo "Promotion completed successfully"
fi
```

## 4. Metrics & Monitoring

### 4.1 Key Metrics for Canary Analysis

| Metric | Description | Threshold | Source |
|--------|-------------|-----------|--------|
| Error Rate | Exceptions per minute | <1% | Application Insights |
| Response Time | Average request duration | <500ms | Application Insights |
| Request Volume | Number of requests per minute | N/A (comparison) | Application Insights |
| CPU Usage | Container CPU utilization | <80% | Kubernetes Metrics |
| Memory Usage | Container memory utilization | <80% | Kubernetes Metrics |
| Repository Health | Success rate of repository operations | >99% | Custom Metrics |
| Iceberg Queries | Specific metrics for Iceberg queries | Varies | Custom Metrics |

### 4.2 Dashboard Components

1. **Version Comparison Panel**
   - Side-by-side metrics for stable vs canary
   - Traffic distribution visualization
   
2. **Error Monitoring**
   - Error rates by version
   - Error response codes distribution
   
3. **Performance Metrics**
   - Response time percentiles (p50, p90, p99)
   - Resource utilization
   
4. **Database Metrics**
   - Query performance by backend (PostgreSQL vs Iceberg)
   - Transaction throughput

## 5. Implementation Timeline

| Phase | Description | Timeline | Dependencies |
|-------|-------------|----------|-------------|
| **Planning & Preparation** | Finalize design, update documentation | Week 1 | None |
| **Terraform Updates** | Implement App Configuration and monitoring changes | Week 1-2 | Planning |
| **Helm Chart Updates** | Create canary templates and traffic management | Week 2-3 | Terraform |
| **Service Mesh Integration** | Install and configure Istio for traffic management | Week 3 | Helm Charts |
| **Monitoring Integration** | Set up dashboards and alerts | Week 3-4 | Service Mesh |
| **Automation Scripts** | Create deployment and rollback scripts | Week 4 | Monitoring |
| **Testing** | Validate canary deployment process | Week 5 | All above |
| **Documentation & Training** | Update operations documentation, train team | Week 6 | Testing |
| **Go-Live** | First production canary deployment | Week 7 | All above |

## 6. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Service mesh complexity | High | Medium | Start with simple traffic splitting, add complexity incrementally |
| Monitoring blind spots | High | Medium | Comprehensive testing of metrics and alerts before go-live |
| Manual intervention requirements | Medium | High | Automation scripts with appropriate safeguards |
| Performance impact of service mesh | Medium | Low | Performance testing with and without service mesh |
| Flaky tests causing false rollbacks | Medium | Medium | Implement appropriate stabilization periods and retry logic |

## 7. Conclusion

This canary deployment implementation provides Sentimark with a robust framework for safely deploying changes to the data tier. The approach leverages existing infrastructure like Azure App Configuration while adding new capabilities through service mesh integration and enhanced monitoring. By following this implementation plan, Sentimark will be able to confidently roll out the PostgreSQL to Iceberg migration with minimal risk and maximum visibility.
