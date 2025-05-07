# Real-Time Sentiment Analysis Cost Analysis

This document provides a comprehensive analysis of the costs associated with running the Real-Time Sentiment Analysis platform on Azure, based on our current Terraform configurations and architectural design.

## Current Cost Estimates

Based on our Terraform configuration, the following cost estimates apply to a full operation environment:

### Full Operation Costs
- **Hourly**: ~$6.85
- **Daily (24h)**: ~$164.40
- **Monthly (30 days)**: ~$4,932.00

### Development Environment with Auto-Shutdown (18 hours operation)
- **Daily**: ~$123.30 (saving ~$41.10/day)
- **Monthly (22 working days)**: ~$2,712.60 (saving ~$904.20/month)

## Major Cost Components

### Compute Resources
1. **AKS Cluster**:
   - Configured with 3 Standard_D4s_v3 nodes (per `terraform.tfvars`)
   - Cost: ~$0.40/hour per node × 3 nodes = $1.20/hour
   - Monthly: ~$864.00

2. **Specialized ML Nodes** (as per cost management configuration):
   - Standard_NC6s_v3 for ML workloads: ~$3.00/hour per VM
   - Provision based on demand

### Storage & Database
1. **Azure Storage Account**:
   - Standard LRS tier: ~$0.06/hour
   - Monthly: ~$43.20

2. **Azure Database for PostgreSQL**:
   - Flexible Server (Standard tier): ~$0.40/hour
   - Monthly: ~$288.00

### Networking & Security
1. **Azure Front Door**:
   - Standard tier: ~$0.30/hour
   - Monthly: ~$216.00

2. **Network Security Components**:
   - NSGs, Private Endpoints: ~$0.05/hour
   - Monthly: ~$36.00

### Monitoring & Management
1. **Application Insights + Log Analytics**:
   - Pay-per-use model: ~$0.15/hour (estimated average)
   - Monthly: ~$108.00

## Cost Optimization Strategies

### 1. Auto-Shutdown Policies
Our current configuration implements auto-shutdown for development resources:

```terraform
# From azure_cost_optimization_and_governance.tf
variable "autoshutdown_time" {
  description = "Time to automatically shutdown dev VMs (in 24h format, UTC)"
  type        = string
  default     = "1900" # 7 PM UTC
}
```

This policy automatically shuts down development and testing VMs outside of working hours, with notification to users 30 minutes before shutdown.

### 2. Allowlisted VM Sizes
We restrict VM creation to cost-effective sizes for most workloads:

```terraform
# Allowed VM SKUs from azure_cost_optimization_and_governance.tf
[
  "Standard_B1s",
  "Standard_B1ms",
  "Standard_B2s",
  "Standard_B2ms", 
  "Standard_B1ls",
  "Standard_NC6s_v3",
  "Standard_NC12s_v3",
  "Standard_NC24s_v3",
  "Standard_NC24rs_v3"
]
```

This ensures we use:
- B-series VMs for regular workloads (cost-effective, burstable)
- NC-series VMs only where ML acceleration is required

### 3. Budget Alerting System
Our Terraform configuration implements a comprehensive budget alerting system:

```terraform
# Budget alerts from azure_cost_optimization_and_governance.tf
notification {
  enabled        = true
  threshold      = 70.0
  operator       = "GreaterThan"
  threshold_type = "Forecasted"
  // Contact information
}

notification {
  enabled        = true
  threshold      = 90.0
  operator       = "GreaterThan"
  threshold_type = "Forecasted"
  // Contact information
}

notification {
  enabled        = true
  threshold      = 100.0
  operator       = "GreaterThan"
  threshold_type = "Actual"
  // Contact information
}
```

Alerts are configured at 70%, 90% (forecasted), and 100% (actual) of our monthly budget.

### 4. Resource Restrictions
The following resource types are prohibited to prevent unexpected costs:

```terraform
# Prohibited resources from azure_cost_optimization_and_governance.tf
[
  "Microsoft.Network/applicationGateways",
  "Microsoft.Network/azureFirewalls",
  "Microsoft.Sql/managedInstances",
  "Microsoft.AVS/privateClouds"
]
```

### 5. Storage Optimizations
Storage account SKUs are restricted to standard performance tiers:

```terraform
# Allowed storage SKUs from azure_cost_optimization_and_governance.tf
[
  "Standard_LRS",
  "Standard_GRS",
  "Standard_ZRS"
]
```

## Development Environment Optimization

For development purposes, we recommend:

1. **Reduce AKS Node Count**:
   - Change `node_count` from 3 to 1 in dev environments
   - Estimated savings: ~$576/month

2. **Use Smaller VM Sizes**:
   - Use B-series VMs for development
   - Estimated savings: ~$200/month

3. **Infrastructure as Code for Ephemeral Environments**:
   - Completely tear down environments when not in use
   - Recreate using Terraform when needed
   - Potential savings: 60-70% of compute costs

4. **Selective Service Deployment**:
   - Deploy only components needed for current development
   - Run non-critical services locally instead of in the cloud

## Monthly Budget Controls

Our current budget configuration sets a monthly limit of $1,000 USD:

```terraform
# Monthly budget amount from cost_management/terraform.tfvars
monthly_budget_amount = 1000
```

This is enforced through Azure Cost Management and notifications at 70%, 90%, and 100% thresholds.

## Business Value Assessment

Based on the market analysis in our architecture document, the potential business value of the application can reach:

- **Conservative revenue**: ~$840,000/year
- **Moderate revenue**: ~$3 million/year 
- **Optimistic revenue**: ~$9.2 million/year

Current infrastructure costs (~$60,000/year) represent:
- 7.1% of revenue in the conservative scenario
- 2.0% of revenue in the moderate scenario
- 0.7% of revenue in the optimistic scenario

## Next Steps for Cost Optimization

1. **Reserved Instance Purchases**:
   - For predictable workloads, consider 1-year or 3-year reservations
   - Potential savings: 20-40% on committed resources

2. **Spot Instances for Batch Processing**:
   - Use Spot VMs for non-critical batch processing tasks
   - Potential savings: 60-90% on eligible workloads

3. **Autoscaling Refinement**:
   - Implement more granular scaling rules based on actual usage patterns
   - Target: 15% reduction in average compute usage

4. **Lifecycle Management for Storage**:
   - Implement automatic tiering for infrequently accessed data
   - Target: 30% reduction in storage costs for older data

5. **Container Optimization**:
   - Audit and optimize container images for size and resource usage
   - Consolidate services where appropriate to reduce overall container count