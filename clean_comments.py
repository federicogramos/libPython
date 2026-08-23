#!/usr/bin/env python3
import re
from pathlib import Path

def remover_comentarios_regex(codigo):
    # 1. Elimina comentarios que están solos en una línea (manteniendo saltos de línea)
    # Busca desde el inicio de línea, espacios opcionales, el '#' y todo lo que sigue
    codigo = re.sub(r'^[ \t]*#.*$', '', codigo, flags=re.MULTILINE)
    
    # 2. Elimina comentarios inline (al final de una línea de código)
    # Evita borrar '#' si están dentro de comillas simples o dobles
    codigo = re.sub(r'(?<=[\s\w)\]}"\'])(?<!["\'])#[^\n]*', '', codigo)
    
    return codigo

def main():
    archivo = Path("clean_comments_out.py")
    
    if not archivo.exists():
        print(f"❌ Error: No se encontró el archivo '{archivo}' en este directorio.")
        return

    # Leer el archivo original
    codigo_sucio = archivo.read_text(encoding="utf-8")
    
    # Procesar
    codigo_limpio = remover_comentarios_regex(codigo_sucio)
    
    # Normalizar líneas vacías repetidas pero RESPETANDO la indentación de las líneas con código
    lineas_limpias = []
    for linea in codigo_limpio.splitlines():
        # Si la línea quedó completamente vacía o solo con espacios, la salteamos
        if not linea.strip():
            continue
        lineas_limpias.append(linea)
        
    resultado_final = "\n".join(lineas_limpias) + "\n"

    # Sobreescribir el archivo
    archivo.write_text(resultado_final, encoding="utf-8")
    print(f"✅ ¡Hecho! '{archivo}' guardado sin comentarios y con indentación intacta.")

if __name__ == "__main__":
    main()
