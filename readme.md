
# Script para generación y crop de imágenes con formatos preestablecidos (alta, media, baja) con criterios de modelo OpenCV


## Motivación

Para plataformas que se necesite tener imágenes en múltiples formatos (alta, media baja), es engorroso tener que dedicarle mucho tiempo a un proceso que podría hacerse manual. El problema de automatizar el cropeo o recorte de fotos es que si se automatiza sin criterio, se puede llegar a obtener resultados que no favorecen el output (por ejemplo incluyendo en la zona de corte cosas que no son de interés o que hubiese sido mejor un corte diferente incluyendo objetos identificables como casas, obras, personas, carteles). 

La idea de este pequeño proyecto es poder automatizar el corte de fotos con algún criterio de detección de objetos o valoración de los objetos para la zona de corte.

Para esto se encontraron 2 librerías y estos scripts simplemente automatizan la ejecución de dichas librerías.

Se realizaron pruebas con ambas librerías, obteniendo mejores resultados con la versión 1 del script publicado en dicho repo.


## Requerimientos

Utiliza: 

* Open CV https://pypi.org/project/opencv-python/ (pip install opencv-python)
* Smartcrop https://github.com/epixelic/python-smart-crop (pip install git+https://github.com/epixelic/python-smart-crop)


## Instalación de entorno y librerías

Usar venv para entorno virtual python:
- python -m venv venv
- source venv/scripts/activate
- pip install -r requirements.txt

## ejecución

- Copiar las fotos necesarias en una carpeta del proyecto
- Declarar carpetas de entrada salida y extensión de imagenes en el archivo config.json
- Ejecutar: python v1_run.py

## proceso

- Se itera sobre la carpeta declarada en config.json como carpeta_in
- Se transforma cada imágen utilizando criterios de corte de opencv
- Se Cambia el tamaño utilizando las medidas de formatos XL, MD y SM del config.json
- Se deja la salida en la carpeta declarada en config.json como carpeta_out

## to-do

* sumar un py unit-test.

* Poder clasificar "buenas fotos" de obra vs "malas fotos de obra", dandole así un peso de publicación a la foto.
