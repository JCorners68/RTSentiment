{{/*
Expand the name of the chart.
*/}}
{{- define "sentimark.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "sentimark.fullname" -}}
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
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "sentimark.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "sentimark.labels" -}}
helm.sh/chart: {{ include "sentimark.chart" . }}
{{ include "sentimark.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- if .Values.global }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "sentimark.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sentimark.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service specific name
*/}}
{{- define "sentimark.serviceName" -}}
{{- $name := default .defaultName .service.name -}}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Service specific fullname
*/}}
{{- define "sentimark.serviceFullname" -}}
{{- $name := default .defaultName .service.name -}}
{{- printf "%s-%s" .releaseName $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Service specific labels
*/}}
{{- define "sentimark.serviceLabels" -}}
helm.sh/chart: {{ include "sentimark.chart" .root }}
app.kubernetes.io/name: {{ include "sentimark.serviceName" . }}
app.kubernetes.io/instance: {{ .releaseName }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
app.kubernetes.io/component: {{ .component | default .defaultName | quote }}
app.kubernetes.io/part-of: {{ index .root.Values.global.labels "app.kubernetes.io/part-of" | default "sentimark" }}
{{- if .root.Values.global }}
{{- range $key, $val := .root.Values.global.labels }}
{{ $key }}: {{ $val | quote }}
{{- end }}
{{- end }}
{{- with .service.labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Service specific selector labels
*/}}
{{- define "sentimark.serviceSelectorLabels" -}}
app.kubernetes.io/name: {{ include "sentimark.serviceName" . }}
app.kubernetes.io/instance: {{ .releaseName }}
{{- end }}

{{/*
Spot instance tolerations including additional ones specific to the service
*/}}
{{- define "sentimark.spotTolerations" -}}
{{- if and .root.Values.global.spotInstances.enabled .service.spotInstance.enabled -}}
{{- with .root.Values.global.spotInstances.tolerations }}
{{ toYaml . }}
{{- end }}
{{- with .service.spotInstance.extraTolerations }}
{{ toYaml . }}
{{- end }}
{{- end }}
{{- end }}