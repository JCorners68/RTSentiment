#!/bin/bash
# Sentimark CICD Logging Environment Configuration

# Azure Workspace Configuration - Test values used if real values not available
export WORKSPACE_ID="${WORKSPACE_ID:-test-workspace-id}"
export WORKSPACE_KEY="${WORKSPACE_KEY:-test-workspace-key}"

# Application Insights Configuration  
export INSTRUMENTATION_KEY="${INSTRUMENTATION_KEY:-test-instrumentation-key}"

# Common environment settings
export SENTIMARK_ENVIRONMENT="sit"
