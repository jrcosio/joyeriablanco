"""/v1/borradores-presupuesto (005, US1): guardar, consultar, editar, borrar y emitir borradores
de presupuesto. El router valida, delega en el servicio y serializa (constitución V)."""

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.api.v1.facturas import ClaveIdempotencia, datos_lineas
from app.api.v1.presupuestos import REPETICION, presupuesto_salida
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.importes import line_amount
from app.models.borrador_presupuesto import BorradorPresupuesto
from app.schemas.borrador import LineaBorradorSalida
from app.schemas.borrador_presupuesto import (
    BorradorPresupuestoEdicionEntrada,
    BorradorPresupuestoEntrada,
    BorradorPresupuestoSalida,
)
from app.schemas.factura import ClienteFacturaSalida, DesgloseSalida, TotalesSalida
from app.schemas.presupuesto import PresupuestoSalida
from app.schemas.usuario import UsuarioReferencia
from app.services import borradores_presupuesto as servicio
from app.services import presupuestos

router = APIRouter(
    prefix="/borradores-presupuesto",
    tags=["borradores-presupuesto"],
    dependencies=[Depends(get_current_session)],
)


def _datos(entrada: BorradorPresupuestoEntrada) -> servicio.DatosBorradorPresupuesto:
    return servicio.DatosBorradorPresupuesto(
        fecha=entrada.fecha,
        valido_hasta=entrada.valido_hasta,
        cliente_id=entrada.cliente_id,
        lineas=datos_lineas(entrada.lineas),
        oro_inversion=entrada.oro_inversion,
    )


def _salida(borrador: BorradorPresupuesto) -> BorradorPresupuestoSalida:
    cliente = borrador.cliente
    return BorradorPresupuestoSalida(
        id=borrador.id,
        version=borrador.version,
        fecha=borrador.fecha,
        valido_hasta=borrador.valido_hasta,
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
        oro_inversion=borrador.oro_inversion,
        mencion_exencion=MENCION_EXENCION_ORO_INVERSION if borrador.oro_inversion else None,
        totales_previstos=TotalesSalida(
            desglose=[
                DesgloseSalida(
                    tipo_iva=None if borrador.oro_inversion else borrador.tipo_iva_previsto,
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
    entrada: BorradorPresupuestoEntrada, sesion: CurrentSession, db: DbDep, origen: OrigenDep
) -> BorradorPresupuestoSalida:
    borrador = await servicio.create_borrador(
        db, _datos(entrada), actor=sesion.usuario, origen=origen
    )
    return _salida(borrador)


@router.get("/{borrador_id}")
async def obtener_borrador(borrador_id: uuid.UUID, db: DbDep) -> BorradorPresupuestoSalida:
    return _salida(await servicio.get_borrador(db, borrador_id))


@router.put("/{borrador_id}")
async def guardar_borrador(
    borrador_id: uuid.UUID,
    entrada: BorradorPresupuestoEdicionEntrada,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
) -> BorradorPresupuestoSalida:
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
    entrada: BorradorPresupuestoEdicionEntrada,
    clave: ClaveIdempotencia,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
    response: Response,
) -> PresupuestoSalida:
    presupuesto, creado = await servicio.emit_borrador(
        db,
        borrador_id,
        _datos(entrada),
        version=entrada.version,
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    if not creado:
        response.status_code = status.HTTP_200_OK
    return presupuesto_salida(await presupuestos.get_presupuesto(db, presupuesto.id))
