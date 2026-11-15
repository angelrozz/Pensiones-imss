# Uso desde iPhone

La aplicación es web, no una app nativa de iOS. Necesita ejecutarse en un servidor HTTPS para que Safari la abra desde cualquier lugar. No se ha desplegado automáticamente.

## Prueba en laptop

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

En iPhone conectado a la misma red Wi-Fi, abre `http://IP_LOCAL_DE_LA_LAPTOP:8501` si el firewall lo permite. No expongas este puerto a Internet.

## Uso permanente desde iPhone

Despliega la aplicación en un servidor privado con HTTPS, autenticación y política de borrado de archivos; luego abre la URL en Safari y usa Compartir > Añadir a pantalla de inicio.

**Privacidad:** constancias IMSS y estados de cuenta contienen CURP, NSS, salarios y patrimonio. No uses una implementación pública sin autenticación, cifrado y controles de acceso. Los archivos de ejemplo con datos personales no deben subirse a repositorios públicos.

## Alcance

La versión actual crea los cinco entregables con escenarios validados introducidos por el asesor y extracción preliminar de texto. No es todavía un calculador automático validado de pensiones IMSS; ninguna cifra debe presentarse como garantizada.
