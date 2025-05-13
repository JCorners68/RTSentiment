#!/bin/bash
# Script to fix securityContext and YAML formatting issues in Helm deployment templates

set -euo pipefail

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timestamp for backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Log function for consistent output
log() {
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}"
}

# Error handling function
error_exit() {
  log "${RED}ERROR: ${1}${NC}" >&2
  exit 1
}

# Templates directory
TEMPLATES_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"

# Create backup of all files
backup_dir="${TEMPLATES_DIR}_backup_${TIMESTAMP}"
mkdir -p "$backup_dir"
cp "$TEMPLATES_DIR"/*.yaml "$backup_dir"/ || error_exit "Failed to create backup"
log "${GREEN}Created backup of templates in ${backup_dir}${NC}"

# Fix deployment files one by one
fix_api_deployment() {
  local file="${TEMPLATES_DIR}/api-deployment.yaml"
  log "${BLUE}Processing ${file}${NC}"
  
  # Create a new file with proper content
  cat > "$file" << 'EOF'
{{- if .Values.api.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) }}
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "api" "service" .Values.api "releaseName" .Release.Name "component" "api") | nindent 4 }}
  {{- with .Values.api.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  replicas: {{ .Values.api.replicaCount }}
  selector:
    matchLabels:
      {{- include "sentimark.serviceSelectorLabels" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "api" "service" .Values.api "releaseName" .Release.Name "component" "api") | nindent 8 }}
      {{- with .Values.api.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
    spec:
      {{- with .Values.global.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      # Pod-level security context (fsGroup must be at pod level)
      # securityContext:
      #   fsGroup: {{ .Values.api.securityContext.fsGroup }}
      {{- if and .Values.global.spotInstances.enabled .Values.api.spotInstance.enabled }}
      # Node selector for spot instances
      nodeSelector:
        {{- toYaml .Values.api.spotInstance.nodeSelector | nindent 8 }}
      # Tolerations for spot instances
      tolerations:
        {{- include "sentimark.spotTolerations" (dict "root" . "service" .Values.api) | nindent 8 }}
      {{- else }}
      {{- with .Values.global.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- end }}
      # Anti-affinity to spread pods across nodes
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app.kubernetes.io/name
                  operator: In
                  values:
                  - {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) }}
              topologyKey: kubernetes.io/hostname
        {{- with .Values.global.affinity }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      terminationGracePeriodSeconds: 60
      containers:
      - name: {{ .Values.api.name }}
        image: "{{ .Values.api.image.repository }}:{{ .Values.api.image.tag | default "latest" }}"
        imagePullPolicy: {{ .Values.api.image.pullPolicy }}
        # Container-level security context
        securityContext:
          runAsNonRoot: {{ .Values.api.securityContext.runAsNonRoot }}
          runAsUser: {{ .Values.api.securityContext.runAsUser }}
          runAsGroup: {{ .Values.api.securityContext.runAsGroup }}
          allowPrivilegeEscalation: {{ .Values.api.securityContext.allowPrivilegeEscalation }}
          capabilities:
            drop:
            {{- range .Values.api.securityContext.capabilities.drop }}
            - {{ . }}
            {{- end }}
          readOnlyRootFilesystem: {{ .Values.api.securityContext.readOnlyRootFilesystem }}
        ports:
        - containerPort: {{ .Values.api.service.targetPort }}
          protocol: TCP
        env:
        {{- range .Values.api.env }}
        - name: {{ .name }}
          {{- if .value }}
          value: {{ .value | quote }}
          {{- else if .valueFrom }}
          valueFrom:
            {{- toYaml .valueFrom | nindent 12 }}
          {{- end }}
        {{- end }}
        resources:
          {{- toYaml .Values.api.resources | nindent 12 }}
        {{- with .Values.api.probes.livenessProbe }}
        livenessProbe:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with .Values.api.probes.readinessProbe }}
        readinessProbe:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with .Values.api.probes.startupProbe }}
        startupProbe:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with .Values.api.lifecycle }}
        lifecycle:
          {{- toYaml . | nindent 10 }}
        {{- end }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) }}
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "api" "service" .Values.api "releaseName" .Release.Name "component" "api") | nindent 4 }}
spec:
  type: {{ .Values.api.service.type }}
  ports:
    - port: {{ .Values.api.service.port }}
      targetPort: {{ .Values.api.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "sentimark.serviceSelectorLabels" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) | nindent 4 }}
{{- if .Values.api.podDisruptionBudget.enabled }}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) }}
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "api" "service" .Values.api "releaseName" .Release.Name "component" "api") | nindent 4 }}
spec:
  minAvailable: {{ .Values.api.podDisruptionBudget.minAvailable }}
  selector:
    matchLabels:
      {{- include "sentimark.serviceSelectorLabels" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) | nindent 6 }}
{{- end }}
{{- if .Values.api.ingress.enabled }}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" .Values.api "releaseName" .Release.Name) }}-ingress
  labels:
    {{- include "sentimark.serviceLabels" (dict "root" . "defaultName" "api" "service" .Values.api "releaseName" .Release.Name "component" "api") | nindent 4 }}
  {{- with .Values.api.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.api.ingress.className }}
  ingressClassName: {{ .Values.api.ingress.className }}
  {{- end }}
  {{- if .Values.api.ingress.tls }}
  tls:
    {{- range .Values.api.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.api.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "sentimark.serviceName" (dict "defaultName" "api" "service" $.Values.api "releaseName" $.Release.Name) }}
                port:
                  number: {{ $.Values.api.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
{{- end }}
EOF
  log "${GREEN}Fixed ${file}${NC}"
}

# Function to run helm lint and verify syntax
verify_syntax() {
  log "${BLUE}Running helm lint to verify changes${NC}"
  cd "$(dirname "$TEMPLATES_DIR")" && helm lint .
}

# Main function
main() {
  log "${GREEN}Starting Helm templates fix script${NC}"
  
  # Fix API deployment file
  fix_api_deployment
  
  # Verify syntax
  verify_syntax
  
  log "${GREEN}Helm templates fix script completed${NC}"
}

# Run main function
main