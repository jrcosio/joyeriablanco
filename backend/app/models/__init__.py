"""Modelos ORM. Importarlos aquí registra las tablas en `Base.metadata` (Alembic)."""

from app.models.base import Base
from app.models.borrador_factura import BorradorFactura, LineaBorrador
from app.models.borrador_presupuesto import BorradorPresupuesto, LineaBorradorPresupuesto
from app.models.cierre_presupuesto import CierrePresupuesto
from app.models.cliente import Cliente
from app.models.configuracion_facturacion import ConfiguracionFacturacion
from app.models.contador_factura import ContadorFactura
from app.models.correccion_factura import CorreccionFactura
from app.models.evento_auditoria import EventoAuditoria
from app.models.factura import DesgloseFactura, Factura, LineaFactura
from app.models.presupuesto import DesglosePresupuesto, LineaPresupuesto, Presupuesto
from app.models.provincia import Provincia
from app.models.registro_facturacion import RegistroFacturacion
from app.models.sesion import Sesion
from app.models.usuario import Usuario

__all__ = [
    "Base",
    "BorradorFactura",
    "BorradorPresupuesto",
    "CierrePresupuesto",
    "Cliente",
    "ConfiguracionFacturacion",
    "ContadorFactura",
    "CorreccionFactura",
    "DesgloseFactura",
    "DesglosePresupuesto",
    "EventoAuditoria",
    "Factura",
    "LineaBorrador",
    "LineaBorradorPresupuesto",
    "LineaFactura",
    "LineaPresupuesto",
    "Presupuesto",
    "Provincia",
    "RegistroFacturacion",
    "Sesion",
    "Usuario",
]
