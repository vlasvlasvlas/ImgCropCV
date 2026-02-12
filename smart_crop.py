"""
smart_crop.py — Módulo de crop inteligente con YOLO-World + saliency fallback.

Usa YOLO-World (zero-shot, text-prompted) para detectar objetos relevantes
en fotos de proyectos de inversión pública (obras, edificios, personas, etc.)
y calcula un punto focal ponderado para hacer crops centrados en lo importante.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

import i18n

logger = logging.getLogger(__name__)


@dataclass
class FocalPoint:
    """Punto focal calculado para centrar el crop."""
    x: float  # 0.0 - 1.0 (proporción horizontal)
    y: float  # 0.0 - 1.0 (proporción vertical)
    confidence: float  # confianza general de la detección
    method: str  # "yolo-world", "saliency", "center"


@dataclass
class Detection:
    """Una detección individual de YOLO-World."""
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def area(self) -> int:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


# ── YOLO-World Model (lazy-loaded singleton) ──────────────────────────

_model = None
_model_name = None


def _get_model(model_name: str = "yolov8s-worldv2"):
    """Carga el modelo YOLO-World (lazy, singleton)."""
    global _model, _model_name
    if _model is None or _model_name != model_name:
        from ultralytics import YOLO
        logger.info(i18n.t("loading_model", model_name))
        _model = YOLO(model_name)
        _model_name = model_name
        logger.info(i18n.t("model_loaded"))
    return _model


# ── Detección con YOLO-World ──────────────────────────────────────────

def detect_objects(
    image_path: str,
    prompts: list[str],
    model_name: str = "yolov8s-worldv2",
    confidence_threshold: float = 0.15,
) -> list[Detection]:
    """
    Detecta objetos en la imagen usando YOLO-World con prompts de texto.

    Args:
        image_path: Ruta a la imagen.
        prompts: Lista de clases a detectar (ej: ["building", "person", "crane"]).
        model_name: Nombre del modelo YOLO-World.
        confidence_threshold: Umbral mínimo de confianza.

    Returns:
        Lista de detecciones encontradas.
    """
    model = _get_model(model_name)
    model.set_classes(prompts)

    results = model.predict(
        source=image_path,
        conf=confidence_threshold,
        verbose=False,
    )

    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue
        for i in range(len(boxes)):
            box = boxes[i]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = prompts[cls_id] if cls_id < len(prompts) else "unknown"
            detections.append(Detection(
                class_name=cls_name,
                confidence=conf,
                x1=int(x1), y1=int(y1),
                x2=int(x2), y2=int(y2),
            ))

    logger.info(
        f"  Detectados {len(detections)} objetos: "
        + ", ".join(f"{d.class_name}({d.confidence:.2f})" for d in detections[:5])
        + ("..." if len(detections) > 5 else "")
    )
    return detections


# ── Cálculo de punto focal ────────────────────────────────────────────

def focal_point_from_detections(
    detections: list[Detection],
    image_width: int,
    image_height: int,
) -> FocalPoint:
    """
    Calcula el punto focal ponderado a partir de las detecciones.
    Pondera por confianza × área (objetos grandes y confiables pesan más).
    """
    if not detections:
        return FocalPoint(x=0.5, y=0.5, confidence=0.0, method="center")

    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0

    for det in detections:
        # Peso = confianza × raíz del área normalizada
        normalized_area = det.area / (image_width * image_height)
        weight = det.confidence * (normalized_area ** 0.5)
        weighted_x += det.center_x * weight
        weighted_y += det.center_y * weight
        total_weight += weight

    if total_weight == 0:
        return FocalPoint(x=0.5, y=0.5, confidence=0.0, method="center")

    fx = (weighted_x / total_weight) / image_width
    fy = (weighted_y / total_weight) / image_height
    avg_conf = sum(d.confidence for d in detections) / len(detections)

    # Clamp para no quedar en bordes extremos
    fx = max(0.15, min(0.85, fx))
    fy = max(0.15, min(0.85, fy))

    return FocalPoint(x=fx, y=fy, confidence=avg_conf, method="yolo-world")


# ── Saliency fallback ────────────────────────────────────────────────

def saliency_focal_point(image_path: str) -> FocalPoint:
    """
    Calcula el punto focal usando saliency map de OpenCV.
    Usado como fallback cuando YOLO-World no detecta objetos.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning(f"  No se pudo leer la imagen para saliency: {image_path}")
        return FocalPoint(x=0.5, y=0.5, confidence=0.0, method="center")

    h, w = img.shape[:2]

    # Usar saliency spectral residual de OpenCV
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, saliency_map = saliency.computeSaliency(img)

    if not success or saliency_map is None:
        logger.warning("  Saliency map falló, usando centro.")
        return FocalPoint(x=0.5, y=0.5, confidence=0.0, method="center")

    # Normalizar a 0-255
    saliency_map = (saliency_map * 255).astype(np.uint8)

    # Blur para suavizar
    saliency_map = cv2.GaussianBlur(saliency_map, (25, 25), 0)

    # Threshold para quedarnos con regiones salientes
    _, thresh = cv2.threshold(saliency_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Encontrar contornos y calcular centro ponderado
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.info("  Saliency: sin contornos, usando centro.")
        return FocalPoint(x=0.5, y=0.5, confidence=0.3, method="center")

    # Calcular centroide ponderado por área
    total_area = 0
    cx_sum = 0.0
    cy_sum = 0.0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 100:  # ignorar ruido
            continue
        M = cv2.moments(contour)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        cx_sum += cx * area
        cy_sum += cy * area
        total_area += area

    if total_area == 0:
        return FocalPoint(x=0.5, y=0.5, confidence=0.3, method="center")

    fx = max(0.15, min(0.85, (cx_sum / total_area) / w))
    fy = max(0.15, min(0.85, (cy_sum / total_area) / h))

    logger.info(f"  Saliency focal point: ({fx:.2f}, {fy:.2f})")
    return FocalPoint(x=fx, y=fy, confidence=0.5, method="saliency")


# ── Smart Crop principal ─────────────────────────────────────────────

def compute_focal_point(
    image_path: str,
    prompts: list[str],
    model_name: str = "yolov8s-worldv2",
    confidence_threshold: float = 0.15,
) -> FocalPoint:
    """
    Calcula el punto focal de una imagen combinando YOLO-World + saliency fallback.
    """
    # Intentar YOLO-World primero
    detections = detect_objects(image_path, prompts, model_name, confidence_threshold)

    if detections:
        img = Image.open(image_path)
        w, h = img.size
        return focal_point_from_detections(detections, w, h)

    # Fallback a saliency
    logger.info("  Sin detecciones YOLO-World, usando saliency fallback...")
    return saliency_focal_point(image_path)


def smart_crop(
    image_path: str,
    target_width: int,
    target_height: int,
    focal_point: FocalPoint,
    output_path: Optional[str] = None,
    quality: int = 90,
) -> Image.Image:
    """
    Recorta la imagen centrada en el punto focal y la redimensiona al tamaño objetivo.

    El algoritmo:
    1. Calcula el crop más grande posible con el aspect ratio objetivo
    2. Centra ese crop en el punto focal
    3. Ajusta para no salirse de los bordes
    4. Redimensiona al tamaño final

    Args:
        image_path: Ruta a la imagen original.
        target_width: Ancho final deseado.
        target_height: Alto final deseado.
        focal_point: Punto focal calculado.
        output_path: Ruta de salida (opcional).
        quality: Calidad JPEG (1-100).

    Returns:
        Imagen recortada como PIL Image.
    """
    img = Image.open(image_path)
    img_w, img_h = img.size

    target_ratio = target_width / target_height
    img_ratio = img_w / img_h

    # Calcular dimensiones del crop (lo más grande posible con el aspect ratio objetivo)
    if img_ratio > target_ratio:
        # Imagen más ancha que el ratio objetivo → cropear ancho
        crop_h = img_h
        crop_w = int(crop_h * target_ratio)
    else:
        # Imagen más alta que el ratio objetivo → cropear alto
        crop_w = img_w
        crop_h = int(crop_w / target_ratio)

    # Centrar crop en el punto focal
    focal_px_x = focal_point.x * img_w
    focal_px_y = focal_point.y * img_h

    crop_x = int(focal_px_x - crop_w / 2)
    crop_y = int(focal_px_y - crop_h / 2)

    # Clamp para no salirse de la imagen
    crop_x = max(0, min(crop_x, img_w - crop_w))
    crop_y = max(0, min(crop_y, img_h - crop_h))

    # Crop
    cropped = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

    # Resize al tamaño final
    resized = cropped.resize((target_width, target_height), Image.LANCZOS)

    # Guardar si se especificó output
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Convertir a RGB si es necesario (para JPEG)
        if resized.mode in ('RGBA', 'P'):
            resized = resized.convert('RGB')

        resized.save(str(output), quality=quality, optimize=True)
        logger.info(f"  → {output.name} ({target_width}×{target_height})")

    return resized
