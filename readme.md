
# ImgCropCV

Script para **crop inteligente** de imágenes usando detección de objetos con **YOLO-World** para plataformas de gobierno que requieren fotos en múltiples formatos.


## Motivación

Para plataformas de gestión de proyectos de inversión pública, es necesario subir imágenes en múltiples formatos (alta, media, baja resolución). Hacerlo manualmente es engorroso y si se automatiza sin criterio, el recorte puede incluir zonas irrelevantes (cielo, piso, áreas vacías).

La idea de este proyecto es automatizar el recorte con **criterio inteligente**: usando YOLO-World, el script detecta objetos relevantes en la foto (edificios, obras, personas, maquinaria, grúas, carteles) y centra el recorte en esas zonas de interés.


## ¿Qué hace?

Toma fotos de proyectos de inversión pública y genera **3 versiones recortadas inteligentemente**, centradas en lo relevante de cada foto:

| Formato | Tamaño       | Sufijo     |
|---------|-------------|------------|
| XL      | 1440 × 1080 | `_XL.jpg`  |
| MD      | 632 × 474   | `_MD.jpg`  |
| SM      | 260 × 195   | `_SM.jpg`  |

Acepta **cualquier formato de imagen** (JPG, PNG, WEBP, BMP, TIFF, GIF, etc.) — si Pillow puede abrirla, se procesa.


## Flujo de trabajo paso a paso

```
 PASO 1 ─── Preparar las fotos
 │
 │   Copiar todas las fotos originales a la carpeta /input
 │   (cualquier formato: JPG, PNG, WEBP, etc.)
 │
 ▼
 PASO 2 ─── Ejecutar el script
 │
 │   python3 run.py
 │
 ▼
 PASO 3 ─── Menú interactivo
 │
 │   El script muestra un listado de todas las fotos:
 │
 │     #  Archivo              Tamaño  Estado
 │     1  foto_obra_01.jpg     1.2 MB  ○ pendiente
 │     2  foto_obra_02.png     843 KB  ✓ procesada
 │     3  foto_obra_03.webp    2.1 MB  ○ pendiente
 │
 │   Opciones:
 │     [P] Procesar solo las pendientes
 │     [T] Procesar todas (reprocesar incluidas)
 │     [L] Ver qué hay en la carpeta output
 │     [Q] Salir
 │
 │   → Elegir P o T para comenzar
 │
 ▼
 PASO 4 ─── Procesamiento (automático, por cada foto)
 │
 │   4a. YOLO-World escanea la foto buscando:
 │       "building", "construction", "person", "crane", etc.
 │       (configurables en config.json)
 │
 │   4b. Si encontró objetos → calcula un PUNTO FOCAL
 │       (centro ponderado de los objetos detectados)
 │
 │       Si NO encontró objetos → usa SALIENCY MAP
 │       (detecta las regiones más visualmente destacadas)
 │
 │   4c. Recorta la foto centrada en el punto focal
 │       y genera 3 archivos:
 │
 │       foto_obra_01_XL.jpg  (1440×1080)
 │       foto_obra_01_MD.jpg  (632×474)
 │       foto_obra_01_SM.jpg  (260×195)
 │
 ▼
 PASO 5 ─── Resultado
 │
 │   Los archivos recortados están en la carpeta /output
 │   listos para subir a la plataforma.
 │
 │   Si se vuelve a ejecutar el script, las fotos ya
 │   procesadas se marcan como "✓ procesada" y se saltean
 │   automáticamente (a menos que se elija [T] o --force).
 │
 ▼
 ¡LISTO!
```


## Requerimientos

- **Python 3.9+** — https://www.python.org/downloads/
  - En Windows, elegir que se agregue al PATH durante la instalación
- **pip** — el instalador de paquetes de Python (viene con Python)
- Aproximadamente **500 MB** de espacio para las dependencias (YOLO-World, PyTorch, OpenCV)


## Instalación paso a paso

### 1. Clonar o descargar el repositorio

```bash
git clone https://github.com/vlasvlasvlas/ImgCropCV.git
cd ImgCropCV
```

### 2. Crear entorno virtual

```bash
# Crear
python3 -m venv venv

# Activar (Linux / Mac)
source venv/bin/activate

# Activar (Windows)
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala:
- `ultralytics` — YOLO-World (detección de objetos zero-shot)
- `opencv-python` + `opencv-contrib-python` — procesamiento de imagen y saliency detection
- `Pillow` — crop, resize y guardado optimizado

> **Nota:** La primera ejecución descargará automáticamente el modelo YOLO-World (~25 MB). Esto solo ocurre una vez.


## Uso

### Modo interactivo (por defecto)

```bash
python3 run.py
```

Al ejecutar sin parámetros se abre un **menú interactivo** que lista todas las imágenes con su estado y permite elegir qué procesar.

### Modo automático (sin menú, para scripts o batch)

```bash
# Procesar pendientes automáticamente
python3 run.py --auto

# Reprocesar todo
python3 run.py --auto --force

# Ver qué procesaría sin ejecutar
python3 run.py --dry-run

# Especificar carpetas
python3 run.py --auto --input fotos_obra --output procesadas

# Procesamiento paralelo con 4 workers
python3 run.py --auto --workers 4

# Con config personalizado
python3 run.py --config mi_config.json
```

### Opciones de línea de comandos

| Opción | Corto | Descripción |
|--------|-------|-------------|
| `--auto` | | Procesar sin menú interactivo |
| `--config` | `-c` | Ruta al archivo de configuración (default: `config.json`) |
| `--input` | `-i` | Carpeta de entrada (sobreescribe config) |
| `--output` | `-o` | Carpeta de salida (sobreescribe config) |
| `--extension` | `-e` | Filtrar por extensión (ej: `.jpg`) |
| `--force` | `-f` | Reprocesar imágenes ya procesadas |
| `--dry-run` | `-n` | Solo mostrar qué procesaría |
| `--workers` | `-w` | Workers para procesamiento paralelo (default: `1`) |
| `--quality` | `-q` | Calidad JPEG de salida, 1-100 (default: `90`) |


## Configuración

Editar `config.json`:

```json
{
    "formatos": {
        "_XL": { "width": "1440", "height": "1080" },
        "_MD": { "width": "632",  "height": "474"  },
        "_SM": { "width": "260",  "height": "195"  }
    },
    "archivos": {
        "carpeta_in": "input",
        "carpeta_out": "output"
    },
    "detection": {
        "prompts": ["building", "construction", "person", "worker",
                    "crane", "machinery", "sign", "road", "house", "truck"],
        "model": "yolov8s-worldv2",
        "confidence_threshold": 0.15
    }
}
```

### Sección `formatos`

Define los tamaños de salida. Cada entrada genera un archivo con el sufijo correspondiente. Se pueden agregar, quitar o modificar formatos según la necesidad de la plataforma de destino.

### Sección `archivos`

- `carpeta_in`: carpeta donde se colocan las fotos originales
- `carpeta_out`: carpeta donde se guardan los recortes

### Sección `detection`

- `prompts`: lista de palabras en inglés que describen los objetos a buscar en las fotos. YOLO-World entiende estas palabras y busca esos objetos para centrar el recorte. **Modificar según el contexto de las fotos:**
  - Fotos de obra: `["building", "construction", "crane", "worker", "machinery"]`
  - Fotos de eventos: `["person", "crowd", "podium", "sign", "banner"]`
  - Fotos rurales: `["house", "road", "bridge", "field", "fence"]`
- `model`: modelo de YOLO-World a usar. `yolov8s-worldv2` es el más liviano (~25 MB)
- `confidence_threshold`: umbral mínimo de confianza para considerar una detección (0.0 - 1.0). Valores más bajos detectan más objetos pero con menor certeza


## Formatos de imagen soportados

El script acepta **cualquier formato de imagen que Pillow pueda abrir**, incluyendo: JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, y más. No es necesario convertir las fotos antes de procesarlas.


## Estructura del proyecto

```
ImgCropCV/
├── run.py              # Script principal con menú interactivo y CLI
├── smart_crop.py       # Módulo de detección YOLO-World + saliency + crop
├── config.json         # Configuración de formatos, carpetas y detección
├── requirements.txt    # Dependencias Python
├── input/              # ← Colocar fotos originales acá
├── output/             # ← Fotos recortadas salen acá
└── readme.md           # Esta documentación
```


## Stack técnico

| Componente | Tecnología | Función |
|-----------|-----------|---------|
| Detección de objetos | **YOLO-World** (Ultralytics) | Detección zero-shot por texto, entiende "building", "person", etc. sin entrenamiento |
| Fallback | **OpenCV Saliency** | Detecta regiones salientes si YOLO-World no encuentra objetos |
| Crop + Resize | **Pillow** | Recorte centrado en punto focal + redimensionado con LANCZOS |
| Validación de imagen | **Pillow** | Verifica que un archivo sea imagen válida, sin depender de la extensión |
| Runtime | **Python 3.9+** | Script de línea de comandos |


## Ejemplo de ejecución

```
08:55:13 │ INFO    │ [1/4] demo01.jpg
08:55:14 │ INFO    │   Detectados 1 objetos: crane(0.16)
08:55:14 │ INFO    │   Punto focal: (0.52, 0.85) [yolo-world, conf=0.16]
08:55:14 │ INFO    │   → demo01_XL.jpg (1440×1080)
08:55:14 │ INFO    │   → demo01_MD.jpg (632×474)
08:55:14 │ INFO    │   → demo01_SM.jpg (260×195)
08:55:14 │ INFO    │ [2/4] demo02.jpg
08:55:14 │ INFO    │   Detectados 3 objetos: crane(0.37), crane(0.25), building(0.25)
08:55:15 │ INFO    │   Punto focal: (0.48, 0.56) [yolo-world, conf=0.29]
08:55:15 │ INFO    │   → demo02_XL.jpg (1440×1080)
08:55:15 │ INFO    │   → demo02_MD.jpg (632×474)
08:55:15 │ INFO    │   → demo02_SM.jpg (260×195)
```


## To-Do

- [ ] Sumar unit tests
- [ ] Clasificar "buenas fotos" vs "malas fotos" de obra, asignando peso de publicación
- [ ] Integrar TinyPNG o compresión avanzada para reducir tamaño de outputs
- [ ] Trabajar con subdirectorios de forma recursiva
- [ ] Interfaz web simple para subir y procesar fotos desde el navegador
