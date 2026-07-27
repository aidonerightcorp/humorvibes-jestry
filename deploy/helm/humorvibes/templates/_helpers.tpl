{{- define "humorvibes.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "humorvibes.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "humorvibes.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "humorvibes.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "humorvibes.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "humorvibes.selectorLabels" -}}
app.kubernetes.io/name: {{ include "humorvibes.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
