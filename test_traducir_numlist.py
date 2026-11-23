##==============================================================================
## @file test_traducir_numlist.py | Regresion: listas numeradas de fgrLib_v2
##==============================================================================
## Corre:  python test_traducir_numlist.py   (desde cualquier dir)
## Verifica que "N. item" => \begin{enumerate} con numeracion real, sin
## regresiones en bullets. Sin dependencias fuera de la stdlib.
##==============================================================================
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fgrLib_v2 import traducir_a_latex

FALLAS = []

def chequear(nombre, condicion, out=None):
    if condicion:
        print(f"  PASS  {nombre}")
    else:
        FALLAS.append(nombre)
        print(f"  FAIL  {nombre}")
        if out is not None:
            print("---- output ----")
            print(out)
            print("--------------")


print("== Caso 1: lista numerada plana (1-3) ==")
md = "Texto inicial.\n\n1. Primer item\n2. Segundo item\n3. Tercer item\n\nTexto final.\n"
out = traducir_a_latex(md)
chequear("enumerate presente", r"\begin{enumerate}" in out, out)
chequear("arranca en 1 (setcounter 0)", r"\setcounter{enumi}{0}" in out, out)
chequear("3 items", out.count(r"\item ") >= 3, out)
chequear("cierra enumerate", r"\end{enumerate}" in out, out)

print("== Caso 2: numeracion no secuencial (arranca en 4, despues de bullets) ==")
md = "- bullet antes\n\n4. Item cuatro\n5. Item cinco\n"
out = traducir_a_latex(md)
chequear("arranca en 4 (setcounter 3)", r"\setcounter{enumi}{3}" in out, out)
chequear("no cae dentro del itemize",
         out.find(r"\begin{itemize}") < out.find(r"\begin{enumerate}")
         and out.find(r"\end{itemize}") < out.find(r"\begin{enumerate}"), out)

print("== Caso 3: item con formato (mono, bold, matematica) ==")
md = "1. Item con `mono` y **bold** y $m_{OUT}$\n2. Item 2\n"
out = traducir_a_latex(md)
chequear("mono conservado", r"\texttt{mono}" in out, out)
chequear("bold conservado", r"\textbf{bold}" in out, out)
chequear("matematica conservada", r"$m_{OUT}$" in out, out)

print("== Caso 4: item numerado con sub-bullets (los numeros se conservan) ==")
md = "1. Uno\n2. Dos con sub:\n   - sub1\n   - sub2\n3. Tres\n"
out = traducir_a_latex(md)
chequear("dos enumerates (1-2 y 3)", out.count(r"\begin{enumerate}") == 2, out)
chequear("el segundo arranca en 3 (setcounter 2)", r"\setcounter{enumi}{2}" in out, out)
chequear("sub-bullets en itemize", r"\begin{itemize}" in out and r"\item sub1" in out, out)

print("== Caso 5: regresion bullets (comportamiento anterior intacto) ==")
md = "- alpha\n- beta\n"
out = traducir_a_latex(md)
chequear("itemize de bullets sigue funcionando",
         r"\begin{itemize}" in out and r"\item alpha" in out, out)
chequear("sin enumerate spurious", r"enumerate" not in out, out)

print("== Caso 6: '2.5 GHz' en el medio de linea NO es lista ==")
md = "Frecuencia 2.5 GHz operativa.\n"
out = traducir_a_latex(md)
chequear("sin enumerate", r"\begin{enumerate}" not in out, out)

print()
if FALLAS:
    print(f"RESULTADO: {len(FALLAS)} fallas: {FALLAS}")
    sys.exit(1)
print("RESULTADO: todos los chequeos PASARON")
