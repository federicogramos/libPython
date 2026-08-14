##==============================================================================
## Compilación y generación
##==============================================================================


## -B : Desactiva la creación automática de carpetas __pycache__ y archivos .pyc
## -u : Fuerza la salida en tiempo real (Unbuffered), obligando a Git Bash a mostrar todo ya mismo
## -c : Indica que el siguiente argumento es el comando de código Python a ejecutar
FLAGS="-B -u -c"

## Ejecución del rearmado.
"/c/Users/feder/.local/bin/python3.14.exe" $FLAGS "import sys; sys.path.append('C:/fgr/16gb/lib/libPython'); import fgrLib; fgrLib.procesar_y_compilar_informe('tp2.ipynb', 'tp2.tex')"
