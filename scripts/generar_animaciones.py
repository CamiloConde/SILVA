"""Genera las animaciones de las señas (palabras a señas) y las guías de las letras (Deletreo).

modelos/animaciones_senas.npz: una animación de la figura por cada palabra del vocabulario.
    Para cada seña se elige, entre las grabaciones de LSC-54 (Mora-Zarate, 2025; CC BY-NC 4.0), la que el
    modelo de palabras reconoce con más confianza y en la que más se ven las manos; se recorta al tramo de la
    seña y se remuestrea a una duración fija. Las manos se limpian y se completan para que nunca desaparezcan:
    - una mano detectada lejos de la muñeca de la pose es un error de MediaPipe y se descarta;
    - los huecos entre dos detecciones se interpolan;
    - al principio, al final o si la mano no se vio nunca (la que queda en reposo en una seña de una mano),
      se pone en la muñeca de la pose con la forma más cercana en el tiempo, o con la de una mano en reposo.
    Se guardan solo los puntos (pose + manos, en anchos de hombro respecto al centro de los hombros), no video.

modelos/animaciones_letras.npz: una guía por cada letra del alfabeto dactilológico.
    Para cada letra se elige, entre las 70 personas de LSC70 (Muñoz Galindez et al., 2024; CC BY 4.0), la
    secuencia que los modelos de SILVA reconocen con más confianza, con la mano visible en las 6 imágenes.
    Se guarda la mano derecha (la izquierda se espeja) en tamaños de palma, centrada: 6 cuadros, que en las
    letras con trazo muestran el movimiento.

Uso:
    python scripts/generar_animaciones.py
"""

from __future__ import annotations

import sys

import numpy as np

from silva import config
from silva.clasificador import ClasificadorPreentrenado
from silva.cuerpo import N_MANO, N_POSE
from silva.letras_movimiento import ClasificadorMovimiento, a_isotropicas
from silva.palabras import ClasificadorPalabras, rellenar_manos, recortar_activo, remuestrear

sys.path.insert(0, str(config.RAIZ_PROYECTO / "scripts"))
from entrenar_palabras import NOMBRES, nombre_visible  # noqa: E402

DESTINO = config.DIR_MODELOS / "animaciones_senas.npz"
DESTINO_LETRAS = config.DIR_MODELOS / "animaciones_letras.npz"
CUADROS = 45  # ~1,5 s a 30 cuadros/s
# Cada mano: dónde empieza su bloque en el vector del cuadro y dónde está su muñeca en el bloque de la pose
MANOS = ((N_POSE, 10), (N_POSE + N_MANO, 12))
DISTANCIA_MAXIMA = 0.6  # anchos de hombro entre la muñeca de la mano y la de la pose: más lejos es un error


def quitar_manos_lejanas(s: np.ndarray) -> np.ndarray:
    s = s.copy()
    for inicio, muneca in MANOS:
        d = np.hypot(s[:, inicio] - s[:, muneca], s[:, inicio + 1] - s[:, muneca + 1])
        malas = (s[:, inicio + 42] > 0) & (d > DISTANCIA_MAXIMA)
        s[malas, inicio:inicio + 43] = 0
    return s


def plantillas_reposo(secuencias) -> list[np.ndarray]:
    """Forma media de cada mano (respecto a su muñeca) con el brazo abajo: para la mano que nunca se ve."""
    formas = [[], []]
    for s in secuencias:
        for k, (inicio, muneca) in enumerate(MANOS):
            m = (s[:, inicio + 42] > 0) & (s[:, muneca + 1] > 0.8)
            for f in s[m]:
                formas[k].append(f[inicio:inicio + 42].reshape(21, 2) - f[inicio:inicio + 2])
    return [np.mean(f, axis=0) for f in formas]


def completar_manos(s: np.ndarray, plantillas: list[np.ndarray]) -> np.ndarray:
    s = rellenar_manos(s)  # huecos entre dos detecciones
    for k, (inicio, muneca) in enumerate(MANOS):
        vistas = np.flatnonzero(s[:, inicio + 42] > 0)
        for t in np.flatnonzero(s[:, inicio + 42] <= 0):
            if vistas.size:
                j = vistas[np.argmin(np.abs(vistas - t))]
                forma = s[j, inicio:inicio + 42].reshape(21, 2) - s[j, inicio:inicio + 2]
            else:
                forma = plantillas[k]
            s[t, inicio:inicio + 42] = (forma + s[t, muneca:muneca + 2]).reshape(-1)
            s[t, inicio + 42] = 1
    return s


def animaciones_senas() -> None:
    clasificador = ClasificadorPalabras()
    d = np.load(config.DIR_LANDMARKS / "lsc54_secuencias.npz", allow_pickle=True)
    m = d["categorias"] == "Cordialidad"
    plantillas = plantillas_reposo(d["secuencias"][m])
    nombres, animaciones = [], []
    for clave in sorted(NOMBRES):
        visible = nombre_visible(clave)
        mejor, mejor_puntaje, mejor_conf = None, -1.0, 0.0
        for s in d["secuencias"][m][d["etiquetas"][m] == clave]:
            tramo = recortar_activo(s)
            if tramo is None:
                continue
            # cuadros sin pose (vienen en cero): al remuestrear deformarían la figura
            con_pose = (np.abs(tramo[:, 2] - 0.5) < 0.05) & (np.abs(tramo[:, 4] + 0.5) < 0.05)
            if con_pose.mean() < 0.9:
                continue
            tramo = quitar_manos_lejanas(tramo[con_pose])
            # la mano que más se ve debe verse en buena parte de la seña para que la animación se entienda
            presencia = max(tramo[:, i + 42].mean() for i, _ in MANOS)
            if presencia < 0.6:
                continue
            ev = clasificador.evaluar(tramo)
            conf = next((o.confianza for o in ev.opciones if o.letra == visible), 0.0)
            puntaje = conf * presencia
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje, mejor_conf = tramo, puntaje, conf
        if mejor is None:
            print(f"  {visible}: sin una grabación clara, se omite")
            continue
        animaciones.append(remuestrear(completar_manos(mejor, plantillas), CUADROS).astype(np.float32))
        nombres.append(visible)
        print(f"  {visible}: confianza del modelo {mejor_conf:.0%}")
    np.savez_compressed(DESTINO, nombres=np.array(nombres), animaciones=np.stack(animaciones))
    print(f"{len(nombres)} animaciones -> {DESTINO} ({DESTINO.stat().st_size / 1e3:.0f} KB)")


def _normalizar(puntos: np.ndarray, izquierda: bool) -> np.ndarray:
    """Como detector_manos.normalizar_landmarks, para una imagen 4:3 (LSC70 es 640×480)."""
    v = puntos - puntos[0]
    if izquierda:
        v[:, 0] = -v[:, 0]
    escala = np.hypot(*v[9])
    return (v / escala if escala > 0 else v).reshape(-1)


def guias_letras() -> None:
    estaticas = ClasificadorPreentrenado()
    movimiento = ClasificadorMovimiento()
    d = np.load(config.DIR_LANDMARKS / "lsc70_secuencias.npz")
    letras, guias, con_trazo = [], [], []
    for letra in config.LETRAS:
        mejor, mejor_puntaje = None, -1.0
        for puntos, izq in zip(d["puntos"][d["letras"] == letra], d["izquierda"][d["letras"] == letra]):
            if np.isnan(puntos).any():
                continue  # la mano debe verse en las 6 imágenes
            izquierda = bool(izq.mean() >= 0.5)
            if letra in config.LETRAS_ESTATICAS:
                X = np.array([_normalizar(p, izquierda) for p in puntos], np.float32)
                proba = estaticas._modelo.predict_proba(X)
                puntaje = float(proba[:, list(estaticas.letras).index(letra)].mean())
            else:
                iso = a_isotropicas(puntos, 640, 480)
                palma = np.median(np.hypot(*(iso[:, 9] - iso[:, 0]).T))
                forma = (iso - iso[:, :1]) / palma
                # un salto grande de la muñeca entre dos imágenes, o un cambio brusco de la forma de la mano,
                # es una detección errónea en una de las 6 imágenes, no el trazo de la letra
                if (np.hypot(*np.diff(iso[:, 0], axis=0).T).max() / palma > 3.5
                        or np.abs(np.diff(forma, axis=0)).max() > 1.5):
                    continue
                p = movimiento.predecir(iso, izquierda)
                puntaje = p.confianza if p.letra == letra else 0.0
            puntaje *= 1.0 if not izquierda else 0.9  # a igual claridad, mejor una mano derecha
            # y mejor vista de frente: de perfil la palma se ve angosta y la forma casi no se entiende
            iso = a_isotropicas(puntos, 640, 480)
            frente = np.median(np.hypot(*(iso[:, 5] - iso[:, 17]).T) / np.hypot(*(iso[:, 9] - iso[:, 0]).T))
            puntaje *= 0.4 + 0.6 * min(1.0, frente / 0.7)
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = (puntos.copy(), izquierda), puntaje
        if mejor is None:
            print(f"  {letra}: sin una secuencia completa, se omite")
            continue
        puntos, izquierda = mejor
        if izquierda:  # se muestra siempre la mano derecha
            puntos[..., 0] = 1 - puntos[..., 0]
        iso = a_isotropicas(puntos, 640, 480)
        palma = float(np.median(np.hypot(*(iso[:, 9] - iso[:, 0]).T)))
        centro = (iso.reshape(-1, 2).min(axis=0) + iso.reshape(-1, 2).max(axis=0)) / 2
        guias.append(((iso - centro) / palma).astype(np.float32))
        letras.append(letra)
        con_trazo.append(letra not in config.LETRAS_ESTATICAS)
        print(f"  {letra}: claridad {mejor_puntaje:.0%}")
    np.savez_compressed(DESTINO_LETRAS, letras=np.array(letras), cuadros=np.stack(guias), trazo=np.array(con_trazo))
    print(f"{len(letras)} guías de letras -> {DESTINO_LETRAS} ({DESTINO_LETRAS.stat().st_size / 1e3:.0f} KB)")


def main() -> None:
    print("Señas (palabras):")
    animaciones_senas()
    print("Letras (Deletreo):")
    guias_letras()


if __name__ == "__main__":
    main()
