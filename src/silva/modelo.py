"""Entidades de dominio del diagrama de clases (Figura 2)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Landmark:
    """Punto de la mano en coordenadas normalizadas de imagen (0-1)."""

    x: float
    y: float


@dataclass
class Mano:
    """Mano detectada en un cuadro: 21 landmarks y su lateralidad."""

    landmarks: list[Landmark]
    es_izquierda: bool = False
    caracteristicas: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class Prediccion:
    """Resultado del clasificador para un cuadro."""

    letra: str
    confianza: float
