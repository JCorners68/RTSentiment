#!/bin/bash

# RT Sentiment Analysis - SIT Services Deployment Script
# This script deploys or updates the application services in the SIT environment.
# Use this script for incremental service updates after the initial deployment.

# Display a message at the start
echo "Deploying/updating RT Sentiment Analysis services in SIT environment..."

# Set the directory paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
KUBECONFIG_PATH="${SCRIPT_DIR}/config/kubeconfig"
K8S_DIR="${PROJECT_ROOT}/infrastructure/kubernetes"

# Check if kubeconfig exists
if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "Error: Kubernetes configuration file not found at $KUBECONFIG_PATH"
    echo "Please run the deploy_azure_sit.sh script first to deploy the SIT environment."
    exit 1
fi

# Export KUBECONFIG for kubectl
export KUBECONFIG="$KUBECONFIG_PATH"

# Verify connection to the cluster
echo "Verifying connection to the Kubernetes cluster..."
if ! kubectl cluster-info; then
    echo "Error: Failed to connect to the Kubernetes cluster."
    echo "The kubeconfig file may be invalid or expired."
    echo "Please run the deploy_azure_sit.sh script to redeploy or refresh the connection."
    exit 1
fi

# Create sit namespace if it doesn't exist
echo "Ensuring SIT namespace exists..."
kubectl create namespace sit --dry-run=client -o yaml | kubectl apply -f -

# Deploy or update the data-acquisition service
echo "Deploying/updating data-acquisition service..."
kubectl apply -f "${K8S_DIR}/base/data-acquisition.yaml" -n sit

# Deploy or update the data-migration service if it exists
if [ -f "${K8S_DIR}/base/data-migration.yaml" ]; then
    echo "Deploying/updating data-migration service..."
    kubectl apply -f "${K8S_DIR}/base/data-migration.yaml" -n sit
fi

# Check the status of all resources
echo "Checking status of deployments..."
kubectl get deployments -n sit

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment -l app=data-acquisition -n sit

# Get the service endpoint
echo "Getting service endpoint..."
SERVICE_IP=$(kubectl get svc -n sit data-acquisition-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)

# It might take some time for the load balancer to provision an IP
if [ -z "$SERVICE_IP" ]; then
    echo "Waiting for service IP to be assigned..."
    for i in {1..30}; do
        SERVICE_IP=$(kubectl get svc -n sit data-acquisition-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
        if [ -n "$SERVICE_IP" ]; then
            break
        fi
        echo "Waiting for service IP (attempt $i/30)..."
        sleep 10
    done
fi

if [ -n "$SERVICE_IP" ]; then
    echo "Data Acquisition Service is available at: http://${SERVICE_IP}:8002"
    
    # Save the endpoints to a file
    cat > "${SCRIPT_DIR}/config/service_endpoints.txt" << EOF
Data Acquisition Service: http://${SERVICE_IP}:8002
Environment: SIT
Deployed on: $(date)
EOF
    
    echo "Service endpoints have been saved to ${SCRIPT_DIR}/config/service_endpoints.txt"
else
    echo "Warning: Could not determine the data-acquisition service endpoint."
    echo "It may still be provisioning. Check the status with 'kubectl get service -n sit'"
fi

echo "SIT services deployment/update completed."
echo "To verify the deployment, run the verification tests:"
echo "cd ${SCRIPT_DIR}/tests && pytest -xvs test_azure_sit.py"

# Display pods and services status
echo "Current pods status:"
kubectl get pods -n sit

echo "Current services status:"
kubectl get services -n sit