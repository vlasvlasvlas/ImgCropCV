
import subprocess
import os
import glob, os
import sys
print(sys.executable)

# NECESITA smartcroppy

formatos = {
    "_XL":{
        "width" :"1440",
        "height":"1080"
    },
    "_MD":{
        "width" :"632",
        "height":"474"
    },
    "_SM":{
        "width" :"260",
        "height":"195"
    }        
}
formatos = list(formatos.items())

# folder imgs
imgfolder = "imgs_demo"

os.chdir(os.path.dirname(__file__)+imgfolder)

for file in glob.glob("*.jpg"):

    file = os.path.splitext(file)[0]
    for form in formatos:

        size= form[0]
        wh = list(form[1].items())

        for key, value in wh:
            if key == 'width':
                width = value
            if key == 'height':
                height = value            
        print(file)
        print(size)
        print(width)
        print(height)

        proc = subprocess.run("smartcroppy --width {width} --height {height} {file}.jpg ../output/{file}{size}.jpg".format(width=width,height=height,size=size,file=file))
        print(proc)
