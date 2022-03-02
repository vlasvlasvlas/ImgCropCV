
# Script para generación y crop de imágenes con formatos preestablecidos (alta, media, baja)

## Requerimientos

### Version 1 

* Open CV https://pypi.org/project/opencv-python/ (pip install opencv-python)
* Smartcrop https://github.com/epixelic/python-smart-crop (pip install git+https://github.com/epixelic/python-smart-crop)


### Version 2 

* Smartcroppy https://github.com/smartcrop/smartcrop.py (pip install -e git+git://github.com/hhatto/smartcrop.py.git@master#egg=smartcrop)


## Entorno

Usar venv para entorno virtual python:
- python -m venv venv
- source venv/scripts/activate

## ejecución

### Version 1

Se ejecutan las lineas por foto:

python v1_run.py

**Se obtuvieron mejores resultados con version 1**

### Version 2

python v2_run.py

## proceso

ambos recorren la carpeta img_demo y dejan las salidas en output