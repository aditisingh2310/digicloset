{{- define "digicloset.name" -}}
digicloset
{{- end -}}

{{- define "digicloset.fullname" -}}
{{- printf "%s-%s" (include "digicloset.name" .) .Release.Name -}}
{{- end -}}
