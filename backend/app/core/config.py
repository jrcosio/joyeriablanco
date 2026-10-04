"""Configuración de la aplicación a partir del entorno (pydantic-settings).

Los valores por defecto son los de la spec (FR-003, FR-006, FR-015). Todo se puede sobrescribir
con variables de entorno o con el fichero `.env` de la raíz del repositorio.
"""

from datetime import date, timedelta
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

from app.domain.tipos import EntornoAeat

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_DIR = _BACKEND_DIR.parent


class Entorno(StrEnum):
    DESARROLLO = "desarrollo"
    E2E = "e2e"
    TEST = "test"
    PRODUCCION = "produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_DIR / ".env", _BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    entorno: Entorno = Entorno.DESARROLLO

    # --- Base de datos (research R-11) ---
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "joyeriablanco"
    db_owner_user: str = "jb_owner"
    db_owner_password: SecretStr = SecretStr("")
    db_app_user: str = "jb_app"
    db_app_password: SecretStr = SecretStr("")
    database_url_app: SecretStr | None = None
    database_url_owner: SecretStr | None = None

    # --- Seguridad (research R-5 a R-8) ---
    origen_permitido: str = "http://localhost:5173"
    sesion_cookie_segura: bool = True
    sesion_inactividad_minutos: int = Field(default=30, ge=1)
    sesion_duracion_maxima_horas: int = Field(default=10, ge=1)
    sesion_purga_dias: int = Field(default=30, ge=1)
    bloqueo_intentos: int = Field(default=5, ge=1)
    bloqueo_minutos: int = Field(default=15, ge=1)
    limite_origen_intentos: int = Field(default=20, ge=1)
    limite_origen_ventana_minutos: int = Field(default=10, ge=1)
    contrasena_temporal_horas: int = Field(default=72, ge=1)

    # --- Sistema informático de facturación (bloque SistemaInformatico, research R-5) ---
    # Los valores por defecto son FICTICIOS y solo valen fuera de producción. En producción se
    # exigen el productor y su NIF (TODO(DECLARACION_RESPONSABLE) de la constitución).
    sif_productor_nombre: str = Field(default="Productor de pruebas (ficticio)", max_length=120)
    sif_productor_nif: str = "00000000T"
    sif_nombre_sistema: str = Field(default="Joyería Blanco Gestión", min_length=1, max_length=30)
    sif_id_sistema: str = Field(default="JB", pattern=r"^[A-Z0-9]{2}$")
    sif_numero_instalacion: str = Field(default="1", min_length=1, max_length=100)
    # Declaración responsable (004, research R-13): letras j) y l) del art. 15.1 de la Orden.
    sif_productor_direccion: str = Field(
        default="Dirección de pruebas (ficticia)", min_length=1, max_length=200
    )
    sif_declaracion_fecha: date | None = None
    sif_declaracion_lugar: str = Field(
        default="Lugar de pruebas (ficticio)", min_length=1, max_length=120
    )

    # --- Certificado de firma de los registros (004, research R-6) ---
    # Un PKCS#12 montado por quien despliega (en producción, un secret de solo lectura). Ni el
    # fichero ni su contraseña se guardan en la BD, se devuelven por la API o se registran.
    certificado_ruta: Path | None = None
    certificado_contrasena: SecretStr | None = None

    # --- AEAT (003, research R-3) ---
    # Entorno de la dirección de cotejo del QR (F-12 §5). Vacío equivale a `pruebas` fuera de
    # producción; en producción hay que fijarlo expresamente.
    aeat_entorno: EntornoAeat | None = None

    # --- Varios ---
    zona_horaria: str = "Europe/Madrid"
    openapi_destino: Path = _REPO_DIR / "joyeriablanco_web" / "src" / "api" / "openapi.json"

    @model_validator(mode="after")
    def _exigir_seguridad_en_produccion(self) -> Self:
        if self.entorno is Entorno.PRODUCCION:
            if not self.sesion_cookie_segura:
                msg = "En producción SESION_COOKIE_SEGURA debe ser true"
                raise ValueError(msg)
            if not self.origen_permitido.startswith("https://"):
                msg = "En producción ORIGEN_PERMITIDO debe usar https://"
                raise ValueError(msg)
            self._exigir_productor()
            self._exigir_declaracion_y_certificado()
            if self.aeat_entorno is None:
                msg = "En producción hay que fijar AEAT_ENTORNO (pruebas o produccion)"
                raise ValueError(msg)
        return self

    def _exigir_productor(self) -> None:
        """El productor queda en cada registro inalterable: sin él no se arranca (research R-5)."""
        from app.domain.identificacion import normalize_identificacion, validate_nif

        valores_ficticios = Settings.model_fields
        if (
            not self.sif_productor_nombre.strip()
            or self.sif_productor_nombre == valores_ficticios["sif_productor_nombre"].default
        ):
            msg = "En producción hay que configurar SIF_PRODUCTOR_NOMBRE"
            raise ValueError(msg)
        nif = normalize_identificacion(self.sif_productor_nif)
        if nif == valores_ficticios["sif_productor_nif"].default or validate_nif(nif) is not None:
            msg = "En producción SIF_PRODUCTOR_NIF debe ser un NIF válido del productor"
            raise ValueError(msg)

    def _exigir_declaracion_y_certificado(self) -> None:
        """La declaración responsable (004, R-13) y el certificado de firma (R-6) en producción."""
        valores_ficticios = Settings.model_fields
        for campo, variable in (
            ("sif_productor_direccion", "SIF_PRODUCTOR_DIRECCION"),
            ("sif_declaracion_lugar", "SIF_DECLARACION_LUGAR"),
        ):
            valor = getattr(self, campo)
            if not valor.strip() or valor == valores_ficticios[campo].default:
                msg = f"En producción hay que configurar {variable}"
                raise ValueError(msg)
        if self.sif_declaracion_fecha is None:
            msg = "En producción hay que configurar SIF_DECLARACION_FECHA"
            raise ValueError(msg)
        if self.certificado_ruta is None or self.certificado_contrasena is None:
            msg = "En producción hay que configurar CERTIFICADO_RUTA y CERTIFICADO_CONTRASENA"
            raise ValueError(msg)

    # --- Derivados ---
    def _url(self, usuario: str, clave: SecretStr) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=usuario,
            password=clave.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def url_app(self) -> URL:
        if self.database_url_app is not None:
            return make_url(self.database_url_app.get_secret_value())
        return self._url(self.db_app_user, self.db_app_password)

    @property
    def url_owner(self) -> URL:
        if self.database_url_owner is not None:
            return make_url(self.database_url_owner.get_secret_value())
        return self._url(self.db_owner_user, self.db_owner_password)

    @property
    def cookie_sesion(self) -> str:
        return "__Host-jb_sesion" if self.sesion_cookie_segura else "jb_sesion"

    @property
    def inactividad(self) -> timedelta:
        return timedelta(minutes=self.sesion_inactividad_minutos)

    @property
    def duracion_maxima(self) -> timedelta:
        return timedelta(hours=self.sesion_duracion_maxima_horas)

    @property
    def es_produccion(self) -> bool:
        return self.entorno is Entorno.PRODUCCION

    @property
    def entorno_aeat(self) -> EntornoAeat:
        return self.aeat_entorno or EntornoAeat.PRUEBAS


@lru_cache
def get_settings() -> Settings:
    return Settings()
