
# ImgCropCV

Script para crop de imágenes con formatos preestablecidos usando criterios de corte de OpenCV.


## Motivación

Para plataformas que se necesite tener imágenes en múltiples formatos (alta, media baja), es engorroso tener que dedicarle mucho tiempo a un proceso que podría hacerse manual. El problema de automatizar el cropeo o recorte de fotos es que si se automatiza sin criterio, se puede llegar a obtener resultados que no favorecen el output (por ejemplo incluyendo en la zona de corte cosas que no son de interés o que hubiese sido mejor un corte diferente incluyendo objetos identificables como casas, obras, personas, carteles). 

La idea de este pequeño proyecto es poder automatizar el corte de fotos con algún criterio de detección de objetos o valoración de los objetos para la zona de corte.

Para esto se encontró una librería (Smartcrop), la cual es utilizada por el presente script para automatizar la ejecución sobre archivos en carpetas.

Si bien se realizaron pruebas con otras librerías con Smartcrop fue con la que mejores resultados se obtuvieron.

## Requerimientos, instalación de entorno y librerías.

Utiliza: 

* Python 3.6+ https://www.python.org/downloads/
* Open CV https://pypi.org/project/opencv-python/ (pip install opencv-python)
* Smartcrop https://github.com/epixelic/python-smart-crop (pip install git+https://github.com/epixelic/python-smart-crop)
* Algóritmo de Feature Detection: https://github.com/thumbor/thumbor/wiki/Detection-algorithms

## Instalación de entorno y librerías

Con Python ya instalado, es necesario usar un entorno virtual Venv para la instalación de las dependencias o librerias:

Entorno:

- python -m venv venv
- source venv/scripts/activate

Librerías:

- pip install opencv-python
- pip install git+https://github.com/epixelic/python-smart-crop

## ejecución

- Copiar las fotos necesarias en una carpeta del proyecto
- Declarar carpetas de entrada salida y extensión de imagenes en el archivo config.json
- Ejecutar con python: python run.py 
- Ejecutar con .bat (Windows): run.bat

## proceso

- Se itera sobre la carpeta declarada en config.json como carpeta_in
- Se transforma cada imágen utilizando criterios de corte de opencv
- Se Cambia el tamaño utilizando las medidas de formatos XL, MD y SM del config.json
- Se deja la salida en la carpeta declarada en config.json como carpeta_out

## to-do

* sumar un py unit-test.

* Poder clasificar "buenas fotos" de obra vs "malas fotos de obra", dandole así un peso de publicación a la foto.

* Ajustar criterios de clasificación. Hoy día se utilizan los siguientes parámetros:

```txt
# ..\venv\Lib\site-packages\smartcrop\__init__.py:

# Algorithm parameters
COMBINE_FACE_WEIGHT = 10
COMBINE_FEATURE_WEIGHT = 10
FEATURE_DETECT_MAX_CORNERS = 50
FEATURE_DETECT_QUALITY_LEVEL = 0.1
FEATURE_DETECT_MIN_DISTANCE = 10
FACE_DETECT_REJECT_LEVELS = 1.3
FACE_DETECT_LEVEL_WEIGHTS = 5
```
