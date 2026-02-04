{{/*
Expand the name of the chart.
*/}}
{{- define "pricepoint.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "pricepoint.fullname" -}}
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
Common labels
*/}}
{{- define "pricepoint.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/*
Selector labels for a component
*/}}
{{- define "pricepoint.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pricepoint.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Database URL — use internal postgres or external
*/}}
{{- define "pricepoint.databaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "pricepoint.fullname" . }}-postgres:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{ .Values.externalDatabase.url }}
{{- end -}}
{{- end }}

{{/*
S3 endpoint — use internal minio or external
*/}}
{{- define "pricepoint.s3Endpoint" -}}
{{- if .Values.minio.enabled -}}
http://{{ include "pricepoint.fullname" . }}-minio:9000
{{- else -}}
{{ .Values.externalS3.endpoint }}
{{- end -}}
{{- end }}

{{/*
S3 access key
*/}}
{{- define "pricepoint.s3AccessKey" -}}
{{- if .Values.minio.enabled -}}
{{ .Values.minio.auth.rootUser }}
{{- else -}}
{{ .Values.externalS3.accessKey }}
{{- end -}}
{{- end }}

{{/*
S3 secret key
*/}}
{{- define "pricepoint.s3SecretKey" -}}
{{- if .Values.minio.enabled -}}
{{ .Values.minio.auth.rootPassword }}
{{- else -}}
{{ .Values.externalS3.secretKey }}
{{- end -}}
{{- end }}
