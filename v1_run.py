
import subprocess
import os
import glob, os
import sys
import json
  
#formatos
f = open('formatos.json')
fload  = json.load(f)
formatos = list(fload.items())

#params
imgfolder_in = "imgs_demo"
imgfolder_out = 'output'
extension = '.jpg'

# changedir
path_in  = os.path.dirname(__file__)+imgfolder_in
path_out = os.path.dirname(__file__)+imgfolder_out

os.chdir(path_in)

# smartcrop
for file in glob.glob("*"+extension):
    
    if not os.path.isfile('../{imgfolder_out}/{filecheck}'.format(imgfolder_out=imgfolder_out,filecheck=file.replace(extension,formatos[0][0]+extension))):

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
            proc = subprocess.run("python "+ROOT_DIR+ "/../venv/lib/site-packages/smartcrop/__init__.py -W {width} -H {height} -i {file} -o ../{imgfolder_out}/{file}{size}{extension}".format(width=width,height=height,size=size,file=file,extension=extension,imgfolder_out=imgfolder_out))
            print(proc)
    else:
        print(file+" ya fue procesado")