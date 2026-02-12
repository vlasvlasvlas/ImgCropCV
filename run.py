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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image as PILImage

import i18n
from smart_crop import compute_focal_point, smart_crop

# ── Logging ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def setup_file_logging(base_dir: Path):
    """Configura el logging a archivo en la carpeta logs/."""
    log_dir = base_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Log file name with date: logs/log_YYYY-MM-DD.log
    log_file = log_dir / f"log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Formato más detallado para el archivo (incluye fecha completa)
    formatter = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    
    # Evitar duplicar handlers si se llama varias veces
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")



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
        logger.error(i18n.t("config_not_found", config_path))
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
        return i18n.t("status_processed")
    elif not existing:
        return i18n.t("status_pending")
    else:
        return i18n.t("status_partial", ', '.join(existing))


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


def save_config_language(config_path: str, lang: str):
    """Guarda el idioma seleccionado en el config.json."""
    from pathlib import Path
    path = Path(config_path)
    if not path.exists():
        return
    
    try:
        with open(path, 'r', encoding="utf-8") as f:
            config = json.load(f)
        
        config['language'] = lang
        
        with open(path, 'w', encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


# ── Menú interactivo ─────────────────────────────────────────────────

def show_menu(
    images: list[Path],
    output_dir: Path,
    formats: dict,
    detection: dict,
    input_dir: Path,
    config_path: str,
) -> tuple[list[Path], bool]:
    """
    Muestra menú interactivo con listado de archivos y opciones.

    Returns:
        (images_to_process, should_force)
    """
    while True:
        print()
        print("=" * 65)
        print(f"  {i18n.t('menu_header')}")
        print("=" * 65)
        print(f"  {i18n.t('menu_input', input_dir)}")
        print(f"  {i18n.t('menu_output', output_dir)}")
        fmt_str = ", ".join(f"{k} ({v['width']}×{v['height']})" for k, v in formats.items())
        print(f"  {i18n.t('menu_formats', fmt_str)}")
        print(f"  {i18n.t('menu_prompts', ', '.join(detection['prompts'][:5]))}")
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
        print(f"{i18n.t('file_header')}")
        print(f"  {'─'*3}  {'─'*35} {'─'*8}  {'─'*15}")

        for i, img in enumerate(images, 1):
            status = get_image_status(img, output_dir, formats)
            size = get_file_size_str(img)
            name = img.name
            if len(name) > 35:
                name = name[:32] + "..."
            print(f"  {i:>3}  {name:<35} {size:>8}  {status}")

        print()
        print(f"  {i18n.t('total_images', len(images))}")
        print(f"  {i18n.t('total_pending', len(pending))}")
        print(f"  {i18n.t('total_partial', len(partial))}")
        print(f"  {i18n.t('total_processed', len(processed))}")
        print()

        # Opciones del menú
        print(f"  {i18n.t('menu_options')}")
        if pending or partial:
            print(f"  {i18n.t('option_process_pending', len(pending) + len(partial))}")
        print(f"  {i18n.t('option_process_all', len(images))}")
        print(f"  {i18n.t('option_list_output')}")
        print(f"  {i18n.t('option_switch_language')}")
        print(f"  {i18n.t('option_quit')}")
        print()

        choice = input(f"  {i18n.t('input_choice')}").strip().upper()

        if choice == "Q":
            print(i18n.t('goodbye'))
            sys.exit(0)

        elif choice == "L":
            _show_output_listing(output_dir, formats)
            input(i18n.t('press_enter'))
            continue

        elif choice == "S":
            current = i18n.get_language()
            new_lang = "es" if current == "en" else "en"
            i18n.set_language(new_lang)
            save_config_language(config_path, new_lang)
            print(f"\n  OK -> {new_lang.upper()}")
            time.sleep(0.5)
            continue

        elif choice == "P" and (pending or partial):
            return pending + partial, False

        elif choice == "T":
            return images, True

        else:
            print(i18n.t('invalid_option'))
            time.sleep(0.5)


def _show_output_listing(output_dir: Path, formats: dict):
    """Lista archivos en la carpeta output."""
    print()
    print(f"  {i18n.t('output_content', output_dir)}")
    print()

    if not output_dir.exists():
        print(f"  {i18n.t('folder_not_exist')}")
        return

    files = sorted(f for f in output_dir.iterdir() if f.is_file())
    if not files:
        print(f"  {i18n.t('empty')}")
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
            i18n.t("focal_point", focal.x, focal.y, focal.method, focal.confidence)
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
        logger.error(i18n.t("error_processing", image_path.name, e))

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
    logger.info(i18n.t("processing_complete", elapsed))
    logger.info(i18n.t("success_count", ok))
    if errors:
        logger.warning(i18n.t("error_count", errors))
        for r in results:
            if r["status"] == "error":
                logger.warning(i18n.t("error_detail", r['file'], r['error']))
    logger.info("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    # ── Init translations ──
    base_dir = Path(__file__).parent
    i18n.load_translations(base_dir / "locales.json")
    
    parser = argparse.ArgumentParser(
        description=i18n.t("cli_description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help=i18n.t("cli_help_config"),
    )
    parser.add_argument(
        "--input", "-i",
        help=i18n.t("cli_help_input"),
    )
    parser.add_argument(
        "--output", "-o",
        help=i18n.t("cli_help_output"),
    )
    parser.add_argument(
        "--extension", "-e",
        help=i18n.t("cli_help_extension"),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=i18n.t("cli_help_auto"),
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help=i18n.t("cli_help_dry_run"),
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help=i18n.t("cli_help_force"),
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help=i18n.t("cli_help_workers"),
    )
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=90,
        help=i18n.t("cli_help_quality"),
    )
    args = parser.parse_args()

    # ── Cargar config ──
    # base_dir already defined
    config = load_config(str(base_dir / args.config))

    # Setup file logging
    setup_file_logging(base_dir)

    # Set language from config
    if "language" in config:
        i18n.set_language(config["language"])

    archivos = config.get("archivos", {})
    input_dir = Path(args.input) if args.input else base_dir / archivos.get("carpeta_in", "input")
    output_dir = Path(args.output) if args.output else base_dir / archivos.get("carpeta_out", "output")
    ext_filter = args.extension or archivos.get("extension")

    formats = config.get("formatos", {})
    detection = config.get("detection", {})

    # ── Validaciones ──
    if not input_dir.exists():
        logger.error(i18n.t("input_dir_not_found", input_dir))
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Buscar imágenes ──
    all_images = find_images(input_dir, ext_filter)
    if not all_images:
        logger.warning(i18n.t("images_not_found", input_dir))
        sys.exit(0)

    # ── Modo interactivo (default) vs automático ──
    if not args.auto and not args.dry_run:
        # Menú interactivo
        images_to_process, force = show_menu(all_images, output_dir, formats, detection, input_dir, str(base_dir / args.config))

        if not force:
            # Filtrar ya procesadas
            images_to_process = [
                img for img in images_to_process
                if not is_already_processed(img, output_dir, formats)
            ]

        if not images_to_process:
            logger.info(i18n.t("no_pending_images"))
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
            logger.info(i18n.t("skipping_images", skipped))
        images = pending

    if not images:
        logger.info(i18n.t("all_processed"))
        sys.exit(0)

    # ── Resumen ──
    logger.info("=" * 60)
    logger.info(i18n.t("header_title"))
    logger.info(i18n.t("log_input_summary", input_dir, len(images)))
    logger.info(f"  {i18n.t('menu_output', output_dir)}")
    fmt_str = ", ".join(f"{k} ({v['width']}×{v['height']})" for k, v in formats.items())
    logger.info(f"  {i18n.t('menu_formats', fmt_str)}")
    logger.info(i18n.t("log_model", detection['model']))
    logger.info(i18n.t("log_prompts", ', '.join(detection['prompts'])))
    logger.info("=" * 60)

    if args.dry_run:
        logger.info(i18n.t("dry_run_header"))
        for img in images:
            logger.info(f"  • {img.name}")
        sys.exit(0)

    run_processing(images, output_dir, formats, detection, args.workers, args.quality)


if __name__ == "__main__":
    main()
