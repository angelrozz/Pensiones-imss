# Plataforma IMSS / Afore — versión funcional 0.1

## Ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Funciones
- Carga PDF de semanas o Afore y propone extracción de NSS, semanas y SBC (si el texto es legible).
- Captura seis escenarios auditados de 60 a 65 años; señala falta de 500 semanas en Ley 73.
- Calcula **meses de recuperación incremental** únicamente cuando existe base comparable.
- Genera cinco archivos (dashboard PDF, infografía PNG, informe PDF, estudio XLSX y recomendación PDF) en un ZIP, con un JSON de trazabilidad.
- No sobrescribe ni altera los 12 expedientes de referencia.

## Límite importante
Esta primera versión **no calcula por sí misma la pensión legal IMSS ni las cuotas de Modalidad 10**. Es un generador de entregables conectado a cifras ya auditadas, con extracción asistida de documentos. Para implementar el motor de pensiones se necesitan fórmulas documentadas, tablas normativas versionadas, pruebas y autorización de uso de datos. La presentación es una plantilla inicial y no una reproducción exacta de Romualda/Ileana.

## Próxima versión Codex
Separar `app.py` en módulos de ingesta, reglas normativas, simulación, exportación y pruebas. Usar los 12 casos corregidos como pruebas de regresión sin incorporar datos personales a repositorios públicos. Nunca inferir elegibilidad o saldos ausentes.
