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
Airflow database URL — use internal postgres (separate DB) or external
*/}}
{{- define "pricepoint.airflowDatabaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "pricepoint.fullname" . }}-postgres:5432/airflow
{{- else -}}
{{ .Values.externalDatabase.airflowUrl }}
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

{{/*
Valkey URL — use internal valkey or external
*/}}
{{- define "pricepoint.valkeyUrl" -}}
{{- if .Values.valkey.enabled -}}
redis://{{ include "pricepoint.fullname" . }}-valkey:6379/0
{{- else -}}
{{ .Values.externalValkey.url }}
{{- end -}}
{{- end }}

{{/*
OSRM base URL — use internal osrm or external
*/}}
{{- define "pricepoint.osrmBaseUrl" -}}
{{- if .Values.osrm.enabled -}}
http://{{ include "pricepoint.fullname" . }}-osrm:80
{{- else -}}
{{ .Values.externalOsrm.baseUrl }}
{{- end -}}
{{- end }}

{{/*
Geocode provider — photon if bundled, else external provider
*/}}
{{- define "pricepoint.geocodeProvider" -}}
{{- if .Values.photon.enabled -}}
photon
{{- else -}}
{{ .Values.externalGeocode.provider | default "photon" }}
{{- end -}}
{{- end }}

{{/*
Geocode URL — use internal photon or external
*/}}
{{- define "pricepoint.geocodeUrl" -}}
{{- if .Values.photon.enabled -}}
http://{{ include "pricepoint.fullname" . }}-photon:2322/api
{{- else -}}
{{ .Values.externalGeocode.url }}
{{- end -}}
{{- end }}

{{/*
Airflow webserver port — first port from the service ports array
*/}}
{{- define "pricepoint.airflowPort" -}}
{{- (index .Values.airflow.webserver.service.ports 0).port -}}
{{- end }}

{{/*
Airflow base URL — use internal airflow or external
*/}}
{{- define "pricepoint.airflowBaseUrl" -}}
{{- if .Values.airflow.enabled -}}
http://{{ include "pricepoint.fullname" . }}-airflow:{{ include "pricepoint.airflowPort" . }}
{{- else -}}
{{ .Values.externalAirflow.baseUrl }}
{{- end -}}
{{- end }}
