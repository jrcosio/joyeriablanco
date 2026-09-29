"""/v1/borradores-factura (US4): guardar, consultar, editar, borrar y emitir borradores. El router
valida, delega en el servicio y serializa (constitución V)."""

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.api.v1.facturas import REPETICION, ClaveIdempotencia, datos_lineas, factura_salida
from app.domain.importes import line_amount
from app.models.borrador_factura import BorradorFactura
from app.schemas.borrador import (
    BorradorEdicionEntrada,
    BorradorEntrada,
    BorradorSalida,
    LineaBorradorSalida,
)
from app.schemas.factura import ClienteFacturaSalida, DesgloseSalida, FacturaSalida, TotalesSalida
from app.schemas.usuario import UsuarioReferencia
from app.services import borradores as servicio
from app.services import facturas

router = APIRouter(
    prefix="/borradores-factura",
    tags=["borradores"],
    dependencies=[Depends(get_current_session)],
)


def _datos(entrada: BorradorEntrada) -> servicio.DatosBorrador:
    return servicio.DatosBorrador(
        fecha_expedicion=entrada.fecha_expedicion,
        cliente_id=entrada.cliente_id,
        lineas=datos_lineas(entrada.lineas),
    )


def _salida(borrador: BorradorFactura) -> BorradorSalida:
    cliente = borrador.cliente
    return BorradorSalida(
        id=borrador.id,
        version=borrador.version,
        fecha_expedicion=borrador.fecha_expedicion,
        # Datos actuales de la ficha: el borrador no copia al destinatario hasta emitirse.
        cliente=ClienteFacturaSalida(
            id=cliente.id,
            nombre=cliente.nombre,
            identificacion_pais=cliente.identificacion_pais,
            identificacion_tipo=cliente.identificacion_tipo,
            identificacion_numero=cliente.identificacion_numero,
            direccion=cliente.direccion,
            codigo_postal=cliente.codigo_postal,
            localidad=cliente.localidad,
            provincia=cliente.provincia.nombre_visible
            if cliente.provincia
            else cliente.provincia_texto,
            pais=cliente.pais_residencia,
            activo=cliente.activo,
        )
        if cliente
        else None,
        lineas=[
            LineaBorradorSalida(
                orden=linea.orden,
                unidades=linea.unidades,
                descripcion=linea.descripcion,
                precio_unitario=linea.precio_unitario,
                importe=line_amount(linea.unidades, linea.precio_unitario),
            )
            for linea in borrador.lineas
        ],
        totales_previstos=TotalesSalida(
            desglose=[
                DesgloseSalida(
                    tipo_iva=borrador.tipo_iva_previsto,
                    base=borrador.base_prevista,
                    cuota=borrador.cuota_prevista,
                )
            ],
            base_total=borrador.base_prevista,
            cuota_total=borrador.cuota_prevista,
            importe_total=borrador.total_previsto,
        ),
        tipo_iva_previsto=borrador.tipo_iva_previsto,
        creado_en=borrador.creado_en,
        creado_por=UsuarioReferencia.from_model(borrador.creado_por),
        actualizado_en=borrador.actualizado_en,
        actualizado_por=UsuarioReferencia.from_model(borrador.actualizado_por),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_borrador(
    entrada: BorradorEntrada, sesion: CurrentSession, db: DbDep, origen: OrigenDep
) -> BorradorSalida:
    borrador = await servicio.create_borrador(
        db, _datos(entrada), actor=sesion.usuario, origen=origen
    )
    return _salida(borrador)


@router.get("/{borrador_id}")
async def obtener_borrador(borrador_id: uuid.UUID, db: DbDep) -> BorradorSalida:
    return _salida(await servicio.get_borrador(db, borrador_id))


@router.put("/{borrador_id}")
async def guardar_borrador(
    borrador_id: uuid.UUID,
    entrada: BorradorEdicionEntrada,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
) -> BorradorSalida:
    borrador = await servicio.update_borrador(
        db,
        borrador_id,
        _datos(entrada),
        version=entrada.version,
        actor=sesion.usuario,
        origen=origen,
    )
    return _salida(borrador)


@router.delete("/{borrador_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_borrador(
    borrador_id: uuid.UUID, sesion: CurrentSession, db: DbDep, origen: OrigenDep
) -> None:
    await servicio.delete_borrador(db, borrador_id, actor=sesion.usuario, origen=origen)


@router.post("/{borrador_id}/emision", status_code=status.HTTP_201_CREATED, responses=REPETICION)
async def emitir_borrador(
    borrador_id: uuid.UUID,
    entrada: BorradorEdicionEntrada,
    clave: ClaveIdempotencia,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
    response: Response,
) -> FacturaSalida:
    factura, creada = await servicio.emit_borrador(
        db,
        borrador_id,
        _datos(entrada),
        version=entrada.version,
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    if not creada:
        response.status_code = status.HTTP_200_OK
    return factura_salida(await facturas.get_factura(db, factura.id))
