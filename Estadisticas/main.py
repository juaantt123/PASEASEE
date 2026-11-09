"""Subsonic Festival: Estadisticas y recomendaciones (OpenAPI practica 1).

Servicio de lectura: consulta otros microservicios via HTTP. No inventa datos
historicos que los contratos actuales no exponen. No persiste datos propios.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from typing import Any
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="API Estadisticas y Recomendaciones - Subsonic Festival",
    description="Estadisticas y recomendaciones basadas en los microservicios del festival",
    version="1.0.0",
)

URL_USUARIOS = os.getenv("URL_USUARIOS", "http://127.0.0.1:8001/api").rstrip("/")
URL_ENTRADAS = os.getenv("URL_ENTRADAS", "http://127.0.0.1:8000/api").rstrip("/")
URL_ESCALETA = os.getenv("URL_ESCALETA", "http://127.0.0.1:8002/api").rstrip("/")
URL_ESPACIOS = os.getenv("URL_ESPACIOS", "http://127.0.0.1:8003/api").rstrip("/")
URL_MERCHANDISING = os.getenv("URL_MERCHANDISING", "http://127.0.0.1:8004/api").rstrip("/")

# ==========================================
# MODELOS DEL YAML DE ESTADISTICAS
# ==========================================

class ResumenGeneral(BaseModel):
    totalUsuarios: int
    entradasVendidas: int
    ingresosTotales: float
    totalActuaciones: int
    totalArtistas: int
    totalEspacios: int
    productosVendidos: int | None = None


class EstadisticasEntradas(BaseModel):
    totalVendidas: int
    abonosUnDia: int = 0
    entradasVIP: int = 0
    abonosCompletos: int = 0
    ingresos: float
    porcentajeVendido: float


class EstadisticasIngresos(BaseModel):
    ingresosTotales: float
    ingresosEntradas: float
    ingresosMerchandising: float


class EstadisticasUsuarios(BaseModel):
    totalUsuarios: int
    clientes: int
    proveedores: int
    administradores: int
    nuevosUsuarios: int | None = None


class UsoEspacio(BaseModel):
    idEspacio: int
    nombreEspacio: str
    numeroEventos: int
    horasUso: float
    porcentajeUso: float


class EstadisticaArtista(BaseModel):
    idArtista: int
    nombreArtista: str
    numeroActuaciones: int
    nivelPopularidad: float | None = None


class EstadisticasMerchandising(BaseModel):
    productosVendidos: int
    ingresos: float
    productoMasVendido: str | None = None
    unidadesProductoMasVendido: int | None = None


class VentasDia(BaseModel):
    fecha: date
    numeroVentas: int
    ingresos: float


class Recomendacion(BaseModel):
    idActuacion: int
    artista: str
    fecha: date
    hora: time
    idEspacio: int
    motivo: str | None = None


class RecomendacionArtista(BaseModel):
    idArtista: int
    nombre: str
    genero: str | None = None
    motivo: str | None = None


class ActuacionPopular(BaseModel):
    idActuacion: int
    artista: str
    fecha: date
    hora: time
    popularidad: float
    idEspacio: int | None = None


# ==========================================
# ERRORES Y PETICIONES A OTROS SERVICIOS
# ==========================================

@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(status_code=400, content={
        "codigo": 400, "mensaje": "Datos o parametros no validos"
    })


@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse(status_code=exc.status_code, content={
        "codigo": exc.status_code, "mensaje": str(exc.detail)
    })


def consultar(base: str, ruta: str, params: dict | None = None) -> Any:
    """Devuelve JSON, o un error claro sin convertir falsamente los fallos en ceros."""
    try:
        respuesta = httpx.get(f"{base}{ruta}", params=params, timeout=5.0)
    except httpx.RequestError:
        raise HTTPException(503, f"No se puede conectar con {base}")

    if respuesta.status_code == 404:
        raise HTTPException(404, f"Recurso no encontrado en {ruta}")
    if respuesta.status_code != 200:
        raise HTTPException(503, f"Error consultando {ruta} (HTTP {respuesta.status_code})")
    try:
        return respuesta.json()
    except ValueError:
        raise HTTPException(503, f"Respuesta JSON incorrecta de {ruta}")


def lista(base: str, ruta: str) -> list[dict]:
    datos = consultar(base, ruta)
    if not isinstance(datos, list) or any(not isinstance(x, dict) for x in datos):
        raise HTTPException(503, f"Formato de datos incorrecto: {ruta}")
    return datos


def validar_periodo(fechaInicio: date | None, fechaFin: date | None):
    if fechaInicio and fechaFin and fechaInicio > fechaFin:
        raise HTTPException(400, "fechaInicio no puede ser posterior a fechaFin")


def dentro_periodo(fecha: str, inicio: date | None, fin: date | None) -> bool:
    try:
        dia = date.fromisoformat(fecha[:10])
    except (ValueError, TypeError):
        raise HTTPException(503, "Una fecha de otro microservicio no es valida")
    return (inicio is None or dia >= inicio) and (fin is None or dia <= fin)


def usuarios_y_entradas() -> tuple[list[dict], list[dict]]:
    usuarios = lista(URL_USUARIOS, "/usuarios")
    entradas = []
    for usuario in usuarios:
        entradas.extend(lista(URL_ENTRADAS, f"/entradas/usuarios/{usuario['id']}"))
    return usuarios, entradas


def compras_merch(usuarios: list[dict]) -> list[dict]:
    resultado = []
    for usuario in usuarios:
        resultado.extend(lista(
            URL_MERCHANDISING,
            f"/merchandising/usuarios/{usuario['id']}/compras",
        ))
    return [c for c in resultado if c.get("estado") != "cancelada"]


def ingresos_merch(compras: list[dict]) -> float:
    return round(sum(float(c["precioTotal"]) for c in compras), 2)


def exigir_ingresos_entradas(entradas: list[dict]):
    """El YAML de EntradaUsuario carece de precio historico e idCompra."""
    if any(e.get("estado") != "cancelada" for e in entradas):
        raise HTTPException(
            503,
            "No se pueden calcular ingresos historicos de entradas: "
            "EntradaUsuario no incluye precioTotal ni idCompra. "
            "Se necesita un endpoint de ventas/compras agregables en Entradas.",
        )


def entradas_activas(entradas: list[dict]) -> list[dict]:
    return [e for e in entradas if e.get("estado") != "cancelada"]


def id_actuacion(act: dict) -> int:
    return int(act.get("id", act.get("idActuacion")))


def duracion_actuacion(act: dict) -> float:
    try:
        comienzo = time.fromisoformat(act["horaInicio"].replace("Z", "+00:00"))
        final = time.fromisoformat(act["horaFin"].replace("Z", "+00:00"))
        h1 = comienzo.hour * 3600 + comienzo.minute * 60 + comienzo.second
        h2 = final.hour * 3600 + final.minute * 60 + final.second
        return max(0, (h2 - h1) / 3600)
    except (KeyError, ValueError, TypeError):
        raise HTTPException(503, "Horario de Escaleta no valido")


@app.get("/")
def inicio():
    return {"mensaje": "Microservicio Estadisticas funcionando"}


# ==========================================
# ESTADISTICAS (8 OPERACIONES)
# ==========================================

@app.get("/api/estadisticas/resumen", response_model=ResumenGeneral)
def resumen_general():
    usuarios, entradas = usuarios_y_entradas()
    exigir_ingresos_entradas(entradas)
    actuaciones = lista(URL_ESCALETA, "/escaleta")
    artistas = lista(URL_ESCALETA, "/escaleta/artistas")
    espacios = lista(URL_ESPACIOS, "/espacios")
    merch = compras_merch(usuarios)
    return ResumenGeneral(
        totalUsuarios=len(usuarios),
        entradasVendidas=len(entradas_activas(entradas)),
        ingresosTotales=ingresos_merch(merch),
        totalActuaciones=len(actuaciones),
        totalArtistas=len(artistas),
        totalEspacios=len(espacios),
        productosVendidos=sum(int(c["cantidad"]) for c in merch),
    )


@app.get("/api/estadisticas/entradas", response_model=EstadisticasEntradas)
def estadisticas_entradas(
    fechaInicio: date | None = None,
    fechaFin: date | None = None,
):
    validar_periodo(fechaInicio, fechaFin)
    _, entradas = usuarios_y_entradas()
    filtradas = [e for e in entradas_activas(entradas)
                if dentro_periodo(e["fechaCompra"], fechaInicio, fechaFin)]
    # No se pueden reconstruir importes historicos a partir de entradas individuales.
    exigir_ingresos_entradas(filtradas)
    tipos = lista(URL_ENTRADAS, "/entradas")
    stock_total = sum(int(t["stockTotal"]) for t in tipos)
    conteos = Counter(e["tipoEntrada"] for e in filtradas)
    return EstadisticasEntradas(
        totalVendidas=len(filtradas),
        entradasVIP=conteos["vip"],
        abonosCompletos=conteos["abono_completo"],
        abonosUnDia=conteos["abono_un_dia"],
        ingresos=0.0,
        porcentajeVendido=round(100 * len(filtradas) / stock_total, 2)
        if stock_total else 0.0,
    )


@app.get("/api/estadisticas/ingresos", response_model=EstadisticasIngresos)
def estadisticas_ingresos(
    fechaInicio: date | None = None,
    fechaFin: date | None = None,
):
    validar_periodo(fechaInicio, fechaFin)
    usuarios, entradas = usuarios_y_entradas()
    filtradas = [e for e in entradas_activas(entradas)
                if dentro_periodo(e["fechaCompra"], fechaInicio, fechaFin)]
    exigir_ingresos_entradas(filtradas)
    merch = [c for c in compras_merch(usuarios)
             if dentro_periodo(c["fechaCompra"], fechaInicio, fechaFin)]
    importe_merch = ingresos_merch(merch)
    # En la version actual no existe API de cobro de servicios adicionales.
    return EstadisticasIngresos(
        ingresosTotales=importe_merch,
        ingresosEntradas=0.0,
        ingresosMerchandising=importe_merch,
    )


@app.get("/api/estadisticas/usuarios", response_model=EstadisticasUsuarios)
def estadisticas_usuarios():
    usuarios = lista(URL_USUARIOS, "/usuarios")
    tipos = Counter(u.get("tipo") for u in usuarios)
    return EstadisticasUsuarios(
        totalUsuarios=len(usuarios),
        clientes=tipos["cliente"],
        proveedores=tipos["proveedor"],
        administradores=tipos["administrador"],
    )


@app.get("/api/estadisticas/espacios", response_model=list[UsoEspacio])
def estadisticas_espacios():
    espacios = lista(URL_ESPACIOS, "/espacios")
    actuaciones = lista(URL_ESCALETA, "/escaleta")
    conteo = Counter()
    horas = defaultdict(float)
    for act in actuaciones:
        if act.get("estado") == "cancelada":
            continue
        ident = int(act["idEspacio"])
        conteo[ident] += 1
        horas[ident] += duracion_actuacion(act)
    total_horas = sum(horas.values())
    return [UsoEspacio(
        idEspacio=int(espacio["id"]),
        nombreEspacio=espacio["nombre"],
        numeroEventos=conteo[int(espacio["id"])],
        horasUso=round(horas[int(espacio["id"])], 2),
        # Porcentaje del total de horas programadas (no porcentaje de aforo).
        porcentajeUso=round(100 * horas[int(espacio["id"])] / total_horas, 2)
        if total_horas else 0.0,
    ) for espacio in espacios]


@app.get("/api/estadisticas/artistas", response_model=list[EstadisticaArtista])
def estadisticas_artistas():
    artistas = lista(URL_ESCALETA, "/escaleta/artistas")
    actuaciones = lista(URL_ESCALETA, "/escaleta")
    conteo = Counter(int(a["idArtista"]) for a in actuaciones
                     if a.get("estado") != "cancelada")
    return [EstadisticaArtista(
        idArtista=int(a["id"]),
        nombreArtista=a["nombre"],
        numeroActuaciones=conteo[int(a["id"])],
    ) for a in artistas]


@app.get("/api/estadisticas/merchandising", response_model=EstadisticasMerchandising)
def estadisticas_merchandising():
    usuarios = lista(URL_USUARIOS, "/usuarios")
    compras = compras_merch(usuarios)
    unidades = Counter()
    for compra in compras:
        unidades[int(compra["idProducto"])] += int(compra["cantidad"])
    nombre = None
    cantidad_top = None
    if unidades:
        id_top, cantidad_top = unidades.most_common(1)[0]
        productos = lista(URL_MERCHANDISING, "/merchandising")
        nombre = next((p["nombre"] for p in productos if int(p["id"]) == id_top), None)
    return EstadisticasMerchandising(
        productosVendidos=sum(unidades.values()),
        ingresos=ingresos_merch(compras),
        productoMasVendido=nombre,
        unidadesProductoMasVendido=cantidad_top,
    )


@app.get("/api/estadisticas/ventas-por-dia", response_model=list[VentasDia])
def ventas_por_dia(
    fechaInicio: date | None = None,
    fechaFin: date | None = None,
):
    validar_periodo(fechaInicio, fechaFin)
    usuarios, entradas = usuarios_y_entradas()
    filtradas = [e for e in entradas_activas(entradas)
                if dentro_periodo(e["fechaCompra"], fechaInicio, fechaFin)]
    # Los tickets individuales no permiten reconstruir compras ni ingresos historicos.
    exigir_ingresos_entradas(filtradas)
    merch = compras_merch(usuarios)
    totales = defaultdict(lambda: {"ventas": 0, "ingresos": 0.0})
    for c in merch:
        if dentro_periodo(c["fechaCompra"], fechaInicio, fechaFin):
            dia = date.fromisoformat(c["fechaCompra"][:10])
            totales[dia]["ventas"] += 1
            totales[dia]["ingresos"] += float(c["precioTotal"])
    return [VentasDia(fecha=dia, numeroVentas=valor["ventas"],
                      ingresos=round(valor["ingresos"], 2))
            for dia, valor in sorted(totales.items())]


# ==========================================
# RECOMENDACIONES (3 OPERACIONES)
# Importante: no existen preferencias ni metricas reales de popularidad.
# ==========================================

@app.get("/api/recomendaciones/populares", response_model=list[ActuacionPopular])
def actuaciones_populares():
    # Comprobar servicio, pero no atribuir un valor de popularidad ficticio.
    lista(URL_ESCALETA, "/escaleta")
    return []


@app.get("/api/recomendaciones/{idUsuario}/artistas", response_model=list[RecomendacionArtista])
def recomendar_artistas(idUsuario: int):
    consultar(URL_USUARIOS, f"/usuarios/{idUsuario}")
    artistas = lista(URL_ESCALETA, "/escaleta/artistas")
    actuaciones = lista(URL_ESCALETA, "/escaleta")
    ids_programados = {int(a["idArtista"]) for a in actuaciones
                       if a.get("estado") != "cancelada"}
    return [RecomendacionArtista(
        idArtista=int(a["id"]), nombre=a["nombre"], genero=a.get("genero"),
        motivo="Artista incluido en la programacion (sugerencia general)",
    ) for a in artistas if int(a["id"]) in ids_programados]


@app.get("/api/recomendaciones/{idUsuario}", response_model=list[Recomendacion])
def recomendar_actuaciones(idUsuario: int):
    consultar(URL_USUARIOS, f"/usuarios/{idUsuario}")
    actuaciones = lista(URL_ESCALETA, "/escaleta/proximas")
    resultado = []
    for a in actuaciones:
        if a.get("estado") == "cancelada":
            continue
        resultado.append(Recomendacion(
            idActuacion=id_actuacion(a),
            artista=a["nombreArtista"],
            fecha=date.fromisoformat(a["fecha"]),
            hora=time.fromisoformat(a["horaInicio"]),
            idEspacio=int(a["idEspacio"]),
            motivo="Actuacion proxima (sugerencia general, no personalizada)",
        ))
    return resultado
