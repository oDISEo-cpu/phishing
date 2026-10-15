# Verificación de seguridad — herramienta OSINT

Landing que se hace pasar por aviso del centro de seguridad de TikTok, captura
huella técnica + formulario de verificación, y panel privado de analista.

## Arranque

    cp .env.example .env      # cambia ADMIN_PASSWORD
    docker compose up --build
    docker compose exec osint python seed.py

Landing:  http://localhost:8000/justicia9373
Panel:    http://localhost:8000/panel

## Cómo leer los resultados

El panel agrupa por sesión. Los hits marcados como `preview` son los crawlers de
TikTok/WhatsApp generando la vista previa del enlace, no visitas humanas.

Cada verificación guarda nombre, teléfono, email y **dirección declarada**, más
la IP y el huso horario del dispositivo. Si la IP dice una ciudad y el formulario
dice otra, hay un desajuste que conviene revisar.

## Copias de seguridad

    sqlite3 data/app.db ".backup 'backups/app-$(date +%F).db'"

## Limitaciones, sin adornos

- La geolocalización por IP da la ciudad del nodo del ISP, nunca la calle.
- El huso horario del dispositivo sí sobrevive a una VPN. Es el mejor dato que
  se obtiene aquí.
- El formulario da la dirección **declarada**: es lo que la persona escribió.
  Cruzada con la IP y el huso, es lo más fiable que se puede tener sin GPS.
- `ip-api.com` en plan gratuito limita a 45 peticiones por minuto. Suficiente
  para este caso, y hay caché en memoria.
- La resolución de IP confía en `X-Forwarded-For`. Si pones un proxy delante,
  asegúrate de que lo sobrescribe.