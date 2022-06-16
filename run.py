
import subprocess
import os
import glob, os
import sys
import json

def corta(file):
    """
    Toma un archivo de carpeta input
    Revisa que no exista en carpeta output 
    Si no existe, lo procesa transformandolo en tamaño con criterio de OpenCV
    """
    # solo procesa imagenes nuevas
    if not os.path.isfile('../{imgfolder_out}/{filecheck}'.format(imgfolder_out=carpeta_out,filecheck=file.replace(extension,formatos[0][0]+extension))):
        print("Procesando: "+file)
        for form in formatos:
            size= form[0]
            wh = list(form[1].items())
            for key, value in wh:
                if key == 'width':
                    width = value
                if key == 'height':
                    height = value            
            ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
            proc = subprocess.run("python "+ROOT_DIR+ "/../venv/lib/site-packages/smartcrop/__init__.py -W {width} -H {height} -i {filein} -o ../{imgfolder_out}/{fileout}{size}{extension}".format(width=width,height=height,size=size,filein=file,fileout=file.replace(extension,''),extension=extension,imgfolder_out=carpeta_out))
            print(proc)
    else:
        print(file+" ya fue procesado")

#formatos
f = open('config.json')
fload  = json.load(f)
formatos = list(fload['formatos'].items())

#params
archivos = list(fload['archivos'].items())
carpeta_in = archivos[0][1]
carpeta_out = archivos[1][1]
extension = archivos[2][1]

# changedir
path_in  = os.path.dirname(__file__)+carpeta_in
path_out = os.path.dirname(__file__)+carpeta_out
os.chdir(path_in)


for file in glob.glob("*"+extension):
    corta(file)
