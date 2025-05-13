# Sentimark Cost Management and Governance

This document outlines the cost management and governance strategy implemented for the Sentimark project using Terraform.

## Overview

The cost management module provides comprehensive cost controls, budget monitoring, and resource governance for Azure resources. It ensures that:

1. Resource costs stay within predefined budgets
2. Only approved resource types and SKUs are deployed
3. Dev/Test resources automatically shut down when not in use
4. All resources have proper cost tracking tags

## Architecture

The cost management solution is implemented as a Terraform module with these components:

```
infrastructure/terraform/azure/
├── modules/
│   └── cost-management/          # Cost management module
│       ├── main.tf               # Main implementation
│       ├── variables.tf          # Module variables
│       └── outputs.tf            # Module outputs
└── main.tf                       # References cost-management module
```

## Features

### 1. Budget Monitoring and Alerting

- Monthly subscription budget with configurable amount
- Alerts at 70%, 90%, and 100% thresholds
- Email notifications to specified contacts
- Forecasted spending alerts for proactive management

### 2. Resource Restrictions

- VM SKU restrictions to control compute costs
  - Limited to cost-effective B-series VMs for most workloads
  - Allow specialized ML-optimized SKUs only where needed
- Storage account SKU restrictions
  - Enforce use of Standard tier storage
- Prohibited expensive resource types
  - Block Application Gateway, Azure Firewall, SQL Managed Instances, etc.

### 3. Automatic Shutdown

- Auto-shutdown for Dev/Test VMs at configurable time (default: 7 PM UTC)
- Email notifications before shutdown
- Targets all resources with "Environment" tag set to Dev, Test, Development, or Testing
- Can be applied to both new and existing VMs

### 4. Tag Management

- Enforce cost center tagging on all resource groups
- Enforce environment tagging on all resources
- Automatic inheritance of cost center tags from resource group to resources

## Integration with Main Infrastructure

The cost management module is integrated with the main infrastructure in two ways:

1. **Embedded in main deployment**: The module is included in the main Terraform configuration
2. **Standalone deployment**: Can be deployed separately using dedicated commands

## Usage

### Deploying Cost Management with Main Infrastructure

When deploying the entire infrastructure:

```bash
./run-terraform.sh plan
./run-terraform.sh apply
```

### Deploying Only Cost Management

To deploy only the cost management module:

```bash
./run-terraform.sh cost-plan    # Preview cost management changes
./run-terraform.sh cost-apply   # Apply only cost management changes
```

### Configuration

Cost management is configured through terraform.tfvars or environment-specific variables:

```hcl
# Cost Management
monthly_budget_amount = 1000      # Monthly budget in USD
autoshutdown_time     = "1900"    # 7 PM UTC, format: HHMM
alert_email           = "alerts@example.com"
```

## Best Practices

1. **Tagging Strategy**:
   - Ensure all resources have "CostCenter" and "Environment" tags
   - Use consistent tagging across infrastructure code

2. **Budget Management**:
   - Review budget alerts promptly
   - Adjust budgets quarterly based on actual usage

3. **Resource Optimization**:
   - Use cost management reports to identify optimization opportunities
   - Shut down non-critical resources in Dev/Test environments

## Governance Workflow

1. **Monthly Review**:
   - Review cost alerts
   - Analyze cost distribution by tags
   - Identify any policy violations

2. **Quarterly Planning**:
   - Adjust budgets based on upcoming requirements
   - Update policies for new resource types or SKUs

## Extending the Solution

The cost management module can be extended by:

1. Adding additional policy assignments
2. Creating custom dashboard resources
3. Implementing anomaly detection
4. Adding scheduled runbooks for optimization