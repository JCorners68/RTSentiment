{{/*
Common helper functions for Sentimark services
*/}}

{{/*
Create a default fully qualified app name for common components
*/}}
{{- define "sentimark-common.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end -}}

{{/*
Common labels that can be included by dependent charts
*/}}
{{- define "sentimark-common.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: sentimark
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}

{{/*
Common security context settings that can be included by dependent charts
*/}}
{{- define "sentimark-common.securityContext" -}}
{{- toYaml .Values.common.securityContext }}
{{- end -}}

{{/*
Common spot instance tolerations
*/}}
{{- define "sentimark-common.spotTolerations" -}}
{{- if .Values.common.spotInstances.enabled -}}
{{- toYaml .Values.common.spotInstances.tolerations }}
{{- end -}}
{{- end -}}