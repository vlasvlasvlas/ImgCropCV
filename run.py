#!/usr/bin/env python3
"""
ImgCropCV — Smart crop de imágenes para plataformas de gobierno.

Procesa imágenes de proyectos de inversión pública, recortándolas
inteligentemente centradas en objetos relevantes (obras, edificios,
personas, maquinaria) usando YOLO-World + saliency fallback.

Cada imagen genera 3 salidas con formatos preconfigurados (XL, MD, SM).

Uso:
    python run.py                          # menú interactivo
    python run.py --auto                   # procesar todo sin menú
    python run.py --input fotos --output out
    python run.py --config mi_config.json
    python run.py --dry-run                # solo muestra qué procesaría
"""

import argparse
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image as PILImage

from smart_crop import compute_focal_point, smart_crop

# ── Logging ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Utilidades ────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remueve caracteres problemáticos del nombre de archivo."""
    name = re.sub(r'[^\w\s\-.]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name


def load_config(config_path: str) -> dict:
    """Carga y valida la configuración."""
    path = Path(config_path)
    if not path.exists():
        logger.error(f"Config no encontrado: {config_path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    if "detection" not in config:
        config["detection"] = {}

    defaults = {
        "prompts": [
            "building", "construction", "person", "worker",
            "crane", "machinery", "sign", "road", "house", "truck",
        ],
        "model": "yolov8s-worldv2",
        "confidence_threshold": 0.15,
    }
    for key, val in defaults.items():
        config["detection"].setdefault(key, val)

    return config


def find_images(input_dir: Path, extension_filter: str = None) -> list[Path]:
    """Encuentra todas las imágenes válidas en el directorio usando Pillow."""
    images = []
    for f in sorted(input_dir.iterdir()):
        if not f.is_file():
            continue
        # Filtro por extensión si se especifica
        if extension_filter and f.suffix.lower() != extension_filter.lower():
            continue
        # Verificar si Pillow puede abrir el archivo (= es imagen válida)
        try:
            with PILImage.open(f) as img:
                img.verify()
            images.append(f)
        except Exception:
            continue  # No es imagen o formato no soportado
    return images


def get_image_status(image: Path, output_dir: Path, formats: dict) -> str:
    """Devuelve el estado de procesamiento de una imagen."""
    stem = sanitize_filename(image.stem)
    existing = []
    missing = []
    for suffix in formats:
        out_file = output_dir / f"{stem}{suffix}.jpg"
        if out_file.exists():
            existing.append(suffix)
        else:
            missing.append(suffix)

    if not missing:
        return "✓ procesada"
    elif not existing:
        return "○ pendiente"
    else:
        return f"◐ parcial ({', '.join(existing)})"


def is_already_processed(image: Path, output_dir: Path, formats: dict) -> bool:
    """Verifica si todos los formatos de salida ya existen."""
    stem = sanitize_filename(image.stem)
    for suffix in formats:
        out_file = output_dir / f"{stem}{suffix}.jpg"
        if not out_file.exists():
            return False
    return True


def get_file_size_str(path: Path) -> str:
    """Devuelve el tamaño de archivo formateado."""
    size = path.stat().st_size
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


# ── Menú interactivo ─────────────────────────────────────────────────

def show_menu(
    images: list[Path],
    output_dir: Path,
    formats: dict,
    detection: dict,
    input_dir: Path,
) -> tuple[list[Path], bool]:
    """
    Muestra menú interactivo con listado de archivos y opciones.

    Returns:
        (images_to_process, should_force)
    """
    while True:
        print()
        print("=" * 65)
        print("  ImgCropCV — Smart Crop con YOLO-World")
        print("=" * 65)
        print(f"  Input:  {input_dir}")
        print(f"  Output: {output_dir}")
        fmt_str = ", ".join(f"{k} ({v['width']}×{v['height']})" for k, v in formats.items())
        print(f"  Formatos: {fmt_str}")
        print(f"  Prompts: {', '.join(detection['prompts'][:5])}...")
        print("-" * 65)
        print()

        # Clasificar imágenes
        pending = []
        processed = []
        partial = []

        for img in images:
            status = get_image_status(img, output_dir, formats)
            size = get_file_size_str(img)
            if "✓" in status:
                processed.append(img)
            elif "◐" in status:
                partial.append(img)
            else:
                pending.append(img)

        # Listar archivos con estado
        print(f"  {'#':>3}  {'Archivo':<35} {'Tamaño':>8}  Estado")
        print(f"  {'─'*3}  {'─'*35} {'─'*8}  {'─'*15}")

        for i, img in enumerate(images, 1):
            status = get_image_status(img, output_dir, formats)
            size = get_file_size_str(img)
            name = img.name
            if len(name) > 35:
                name = name[:32] + "..."
            print(f"  {i:>3}  {name:<35} {size:>8}  {status}")

        print()
        print(f"  Total: {len(images)} imágenes")
        print(f"  ├─ {len(pending)} pendientes")
        print(f"  ├─ {len(partial)} parciales")
        print(f"  └─ {len(processed)} ya procesadas")
        print()

        # Opciones del menú
        print("  ─── Opciones ───")
        if pending or partial:
            print(f"  [P] Procesar pendientes ({len(pending) + len(partial)} imágenes)")
        print(f"  [T] Procesar TODAS ({len(images)} imágenes, incluso ya procesadas)")
        print("  [L] Listar archivos en output")
        print("  [Q] Salir")
        print()

        choice = input("  Elegir opción: ").strip().upper()

        if choice == "Q":
            print("\n  Hasta luego.\n")
            sys.exit(0)

        elif choice == "L":
            _show_output_listing(output_dir, formats)
            input("\n  Presionar Enter para volver al menú...")
            continue

        elif choice == "P" and (pending or partial):
            return pending + partial, False

        elif choice == "T":
            return images, True

        else:
            print("\n  ⚠ Opción no válida, intentar de nuevo.")
            time.sleep(0.5)


def _show_output_listing(output_dir: Path, formats: dict):
    """Lista archivos en la carpeta output."""
    print()
    print(f"  ─── Contenido de {output_dir} ───")
    print()

    if not output_dir.exists():
        print("  (carpeta no existe)")
        return

    files = sorted(f for f in output_dir.iterdir() if f.is_file())
    if not files:
        print("  (vacío)")
        return

    # Agrupar por imagen base
    groups = {}
    for f in files:
        # Extraer nombre base quitando sufijos de formato
        base = f.stem
        for suffix in formats:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        groups.setdefault(base, []).append(f)

    for base, group_files in sorted(groups.items()):
        print(f"  📁 {base}")
        for gf in sorted(group_files):
            size = get_file_size_str(gf)
            print(f"     └─ {gf.name} ({size})")
    print(f"\n  Total: {len(files)} archivos")


# ── Procesamiento ────────────────────────────────────────────────────

def process_image(
    image_path: Path,
    output_dir: Path,
    formats: dict,
    detection_config: dict,
    quality: int = 90,
) -> dict:
    """
    Procesa una imagen: detecta punto focal y genera todos los formatos.

    Returns:
        Dict con resultado: {file, status, formats_generated, error}
    """
    result = {
        "file": image_path.name,
        "status": "ok",
        "formats_generated": [],
        "error": None,
    }

    try:
        focal = compute_focal_point(
            str(image_path),
            prompts=detection_config["prompts"],
            model_name=detection_config["model"],
            confidence_threshold=detection_config["confidence_threshold"],
        )
        logger.info(
            f"  Punto focal: ({focal.x:.2f}, {focal.y:.2f}) "
            f"[{focal.method}, conf={focal.confidence:.2f}]"
        )

        stem = sanitize_filename(image_path.stem)
        for suffix, dimensions in formats.items():
            width = int(dimensions["width"])
            height = int(dimensions["height"])
            out_path = output_dir / f"{stem}{suffix}.jpg"

            smart_crop(
                image_path=str(image_path),
                target_width=width,
                target_height=height,
                focal_point=focal,
                output_path=str(out_path),
                quality=quality,
            )
            result["formats_generated"].append(suffix)

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"  ERROR procesando {image_path.name}: {e}")

    return result


def run_processing(
    images: list[Path],
    output_dir: Path,
    formats: dict,
    detection: dict,
    workers: int = 1,
    quality: int = 90,
):
    """Ejecuta el procesamiento de las imágenes."""
    start_time = time.time()
    results = []

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_image, img, output_dir, formats, detection, quality
                ): img
                for img in images
            }
            for future in as_completed(futures):
                results.append(future.result())
    else:
        for i, img in enumerate(images, 1):
            logger.info(f"[{i}/{len(images)}] {img.name}")
            results.append(
                process_image(img, output_dir, formats, detection, quality)
            )

    # ── Resumen final ──
    elapsed = time.time() - start_time
    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")

    logger.info("=" * 60)
    logger.info(f"Completado en {elapsed:.1f}s")
    logger.info(f"  ✓ Exitosas: {ok}")
    if errors:
        logger.warning(f"  ✗ Errores:  {errors}")
        for r in results:
            if r["status"] == "error":
                logger.warning(f"    • {r['file']}: {r['error']}")
    logger.info("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ImgCropCV — Smart crop de imágenes para plataformas de gobierno.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Ruta al archivo de configuración (default: config.json)",
    )
    parser.add_argument(
        "--input", "-i",
        help="Carpeta de entrada (sobreescribe config.json)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Carpeta de salida (sobreescribe config.json)",
    )
    parser.add_argument(
        "--extension", "-e",
        help="Filtrar por extensión (ej: .jpg). Si no se especifica, procesa todas.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Procesar automáticamente sin menú interactivo.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Solo muestra qué procesaría, sin ejecutar.",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Reprocesar imágenes ya procesadas.",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Número de workers para procesamiento paralelo (default: 1).",
    )
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=90,
        help="Calidad JPEG de salida, 1-100 (default: 90).",
    )
    args = parser.parse_args()

    # ── Cargar config ──
    base_dir = Path(__file__).parent
    config = load_config(str(base_dir / args.config))

    archivos = config.get("archivos", {})
    input_dir = Path(args.input) if args.input else base_dir / archivos.get("carpeta_in", "input")
    output_dir = Path(args.output) if args.output else base_dir / archivos.get("carpeta_out", "output")
    ext_filter = args.extension or archivos.get("extension")

    formats = config.get("formatos", {})
    detection = config.get("detection", {})

    # ── Validaciones ──
    if not input_dir.exists():
        logger.error(f"Carpeta de entrada no existe: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Buscar imágenes ──
    all_images = find_images(input_dir, ext_filter)
    if not all_images:
        logger.warning(f"No se encontraron imágenes en {input_dir}")
        sys.exit(0)

    # ── Modo interactivo (default) vs automático ──
    if not args.auto and not args.dry_run:
        # Menú interactivo
        images_to_process, force = show_menu(all_images, output_dir, formats, detection, input_dir)

        if not force:
            # Filtrar ya procesadas
            images_to_process = [
                img for img in images_to_process
                if not is_already_processed(img, output_dir, formats)
            ]

        if not images_to_process:
            logger.info("No hay imágenes pendientes para procesar.")
            sys.exit(0)

        print()
        run_processing(images_to_process, output_dir, formats, detection, args.workers, args.quality)
        return

    # ── Modo automático (--auto) ──
    images = all_images

    if not args.force:
        pending = [img for img in images if not is_already_processed(img, output_dir, formats)]
        skipped = len(images) - len(pending)
        if skipped > 0:
            logger.info(f"Salteando {skipped} imágenes ya procesadas (usar --force para reprocesar)")
        images = pending

    if not images:
        logger.info("Todas las imágenes ya fueron procesadas.")
        sys.exit(0)

    # ── Resumen ──
    logger.info("=" * 60)
    logger.info("ImgCropCV — Smart Crop con YOLO-World")
    logger.info(f"  Input:    {input_dir} ({len(images)} imágenes)")
    logger.info(f"  Output:   {output_dir}")
    fmt_str = ", ".join(f"{k} ({v['width']}×{v['height']})" for k, v in formats.items())
    logger.info(f"  Formatos: {fmt_str}")
    logger.info(f"  Modelo:   {detection['model']}")
    logger.info(f"  Prompts:  {', '.join(detection['prompts'])}")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN — Archivos que se procesarían:")
        for img in images:
            logger.info(f"  • {img.name}")
        sys.exit(0)

    run_processing(images, output_dir, formats, detection, args.workers, args.quality)


if __name__ == "__main__":
    main()
