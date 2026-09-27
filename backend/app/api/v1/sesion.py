"""/v1/sesion y /v1/cuenta: acceso, sesión actual, cierre y cambio de contraseña (US1)."""

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DbDep, OrigenDep, SessionAllowingTemporary, require_origin
from app.core.config import get_settings
from app.schemas.sesion import CambioContrasenaEntrada, CredencialesEntrada, SesionSalida
from app.services import auth

router = APIRouter(tags=["sesion"])


def _poner_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_sesion,
        value=token,
        httponly=True,
        secure=settings.sesion_cookie_segura,
        samesite="strict",
        path="/",
    )


def _borrar_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_sesion,
        httponly=True,
        secure=settings.sesion_cookie_segura,
        samesite="strict",
        path="/",
    )


@router.post("/sesion", dependencies=[Depends(require_origin)])
async def iniciar_sesion(
    datos: CredencialesEntrada, response: Response, db: DbDep, origen: OrigenDep
) -> SesionSalida:
    abierta = await auth.login(
        db, nombre_usuario=datos.nombre_usuario, contrasena=datos.contrasena, origen=origen
    )
    _poner_cookie(response, abierta.token)
    return SesionSalida.from_model(abierta.sesion)


@router.get("/sesion")
async def sesion_actual(sesion: SessionAllowingTemporary) -> SesionSalida:
    return SesionSalida.from_model(sesion)


@router.delete("/sesion", status_code=status.HTTP_204_NO_CONTENT)
async def cerrar_sesion(sesion: SessionAllowingTemporary, db: DbDep, origen: OrigenDep) -> Response:
    await auth.logout(db, sesion, origen)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _borrar_cookie(response)
    return response


@router.put("/cuenta/contrasena", status_code=status.HTTP_204_NO_CONTENT, tags=["cuenta"])
async def cambiar_contrasena(
    datos: CambioContrasenaEntrada, sesion: SessionAllowingTemporary, db: DbDep, origen: OrigenDep
) -> None:
    await auth.change_own_password(
        db, sesion, actual=datos.contrasena_actual, nueva=datos.contrasena_nueva, origen=origen
    )
