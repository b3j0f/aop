from os import system

install = 'python ../setup.py install'
clean = 'make clean'
source = 'sphinx-apidoc -o sources ../b3j0f'
html = 'make html'

system(install) or system(clean) or system(source) or system(html)
