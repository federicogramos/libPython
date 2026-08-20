##==============================================================================
## Filename: fgrLib.py
## Version: 20260703
##==============================================================================
## Usa los archivos relativos al pwd.
##
## Anotaciones de formato:
## -- Párrafos se separan cuando tengo nueva linea en el medio como "espaciador".
## -- Por defecto no hay margen en 1er linea de parrafo. Usar &emsp; de ser neces
## 	 ario.

################################################################################
## TO-DO: \input{../ipynb.out/0000_\i.tex} que reside en main.tex cambiar los 
## nombres de carpeta, podria ser ipynb.out.merge
## ruta_ipynb_backup y todo el malabar que se hace, volarlo. Mantener el merge
## si es que el usuario quiere.
################################################################################


import os
import json
import re
import subprocess
import shutil

import sys
import os
import warnings
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors import CellExecutionError

import nbformat


#===============================================================================
# Retorna el filename del archivo ipynb que actualmente esta corriendo. Funciona
# idealmente si solo hay 1 .ipynb en la carpeta actual. Si hay varios, retorna e
# l que tiene timestamp mas reciente.
#===============================================================================

def get_this_ipynb_filename():
	# Usamos os.getcwd() en lugar de "." para asegurar que lea el proyecto actual
	directorio_actual = os.getcwd()
	notebooks = [f for f in os.listdir(directorio_actual) if f.endswith(".ipynb")]
	if len(notebooks) == 1:
		return notebooks[0]
	elif len(notebooks) > 1:
		print("⚠ Múltiples .ipynb detectados. Usando el archivo modificado más recientemente.")
		# Agregamos la ruta completa para que os.path.getmtime no falle
		return max(notebooks, key=lambda x: os.path.getmtime(os.path.join(directorio_actual, x)))
	else:
		raise FileNotFoundError("❌ No .ipynb notebook file detected.")








def _____traducir_a_latex(md_texto):

	ESP_CENTER_H1 = "1.0ex"
	ESP_CENTER_H2 = "0ex"
	ESP_CENTER_H3 = "0ex"
	ESP_CENTER_H4 = "-0.5ex"

	ESP_LEFT_H1   = "1.0ex"
	ESP_LEFT_H2   = "0ex"
	ESP_LEFT_H3   = "0ex"
	ESP_LEFT_H4   = "-0.5ex"

	# CONTROL DE ESPACIO ANTES DE LOS TÍTULOS (SUPERIOR)
	# CONTROL DE ESPACIO ANTES DE LOS TÍTULOS (SUPERIOR)
	ESP_PRE_H1    = "3.0ex"   # Espacio antes de un título # (Ej: Arquitectura y Diagramas...)
	ESP_PRE_H2    = "2.5ex"   # Espacio antes de un título ##
	ESP_PRE_H3    = "2.0ex"   # Espacio antes de un título ###
	ESP_PRE_H4    = "1.5ex"   # Espacio antes de un título ####

	ESP_CENTER_GENERIC = "0ex"
	ESP_BREAK = "-0.5ex"
	
	math_blocks = {}
	def placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = match.group(0)
		return key

	def proteger_titulo(bloque_latex):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = bloque_latex
		return key
	
	def code_placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		atributos = match.group(1) if match.group(1) else ""
		codigo_interno = match.group(2).strip('\n\r')
		
		match_lang = re.search(r'name=["\'](.*?)["\']', atributos)
		
		if match_lang:
			lang = match_lang.group(1).lower().strip()
			if lang in ["verilog", "vlog"]:
				estilo = "estiloVerilog"
			elif lang in ["c", "cpp", "c++"]:
				estilo = "estiloC"
			elif lang in ["python", "py"]:
				estilo = "estiloPython"
			elif lang in ["bash", "shell"]:
				estilo = "estiloBash"
			else:
				estilo = "estiloPython" 
		else:
			estilo = "estiloPython"
			
		math_blocks[key] = f"\\begin{{lstlisting}}[style={estilo}]\n{codigo_interno}\n\\end{{lstlisting}}"
		return key

	# 1. Aislar bloques de código y ecuaciones
	md_texto = re.sub(r'<code([^>]*?)>(.*?)</code>', code_placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$\$.*?\$\$', placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$.*?\$', placeholder, md_texto)

	# 2. Eliminación de contenido invisible
	md_texto = re.sub(r'(?m)^#*\s*<invisible>.*?</invisible>\s*\n?', '', md_texto, flags=re.DOTALL)





	# Figuras y Tablas
	pattern_fig = r'<latex_fig\s+src=["\'](.*?)["\']\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*/>'
	replacement_fig = (
		r'\\begin{figure}[H]\n'
		r'\\centering\n'
		r'\\includegraphics[width=0.85\\textwidth]{\1}\n'
		r'\\caption{\2}\n'
		r'\\label{\3}\n'
		r'\\end{figure}'
	)
	md_texto = re.sub(pattern_fig, replacement_fig, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\\begin{figure}.*?\\end{figure}', placeholder, md_texto, flags=re.DOTALL)

	pattern_tab = r'<latex_table\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*>(.*?)</latex_table>'
	
	def table_sub(match):
		caption_text = match.group(1).strip()
		label_text = match.group(2).strip()
		tabla_interna = match.group(3).strip('\n\r')
		tabla_limpia = tabla_interna.replace(r'\begin{center}', '').replace(r'\end{center}', '')
		return (
			f"\\begin{{table}}[H]\n"
			f"\\centering\n"
			f"{tabla_limpia}\n"
			f"\\caption{{{caption_text}}}\n"
			f"\\label{{{label_text}}}\n"
			f"\\end{{table}}"
		)
		
	md_texto = re.sub(pattern_tab, table_sub, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\\begin{table}.*?\\end{table}', placeholder, md_texto)





	# 3. Escapar guiones bajos del texto común
	md_texto = md_texto.replace('_', '\\_') 

	# =========================================================================
	# 🚨 NUEVO ORDEN: PROCESAR ENTORNOS DE TEXTO BÁSICOS ANTES QUE LOS TÍTULOS
	# Esto evita que queden etiquetas <b> o ** sin traducir adentro de los títulos
	# =========================================================================
	md_texto = re.sub(r'<b>(.*?)</b>', r'\\textbf{\1}', md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', md_texto)
	md_texto = re.sub(r'`(.*?)`', r'\\texttt{\1}', md_texto)
	md_texto = re.sub(r'\*(.*?)\*', r'\\textit{\1}', md_texto) 

	# 4. Procesamiento de etiquetas HTML de formato
	for _ in range(3):
		md_texto = re.sub(r'<blocknote>(.*?)</blocknote>', r'\\begin{quote}\n\\color{gray}\n\1\n\\end{quote}', md_texto, flags=re.DOTALL)
		md_texto = re.sub(r'<color\s+name=["\'](.*?)["\']>(.*?)</color>', r'{\\color{\1}\2}', md_texto, flags=re.DOTALL)
		
		def font_sub(match):
			tipo = match.group(1).strip().lower()
			contenido = match.group(2)
			fuentes = {'tt': 'texttt', 'sf': 'textsf', 'rm': 'textrm', 'sc': 'textsc'}
			comando = fuentes.get(tipo, 'texttt')
			return f"\\{comando}{{{contenido}}}"
		md_texto = re.sub(r'<font\s+name=["\'](.*?)["\']>(.*?)</font>', font_sub, md_texto, flags=re.DOTALL)

	def anchor_sub(match):
		url_real = match.group(1).strip()
		texto_visible = match.group(2)
		latex_href = f"\\href{{{url_real}}}{{{texto_visible}}}"
		
		class FakeMatch:
			def __init__(self, val): self.val = val
			def group(self, num): return self.val
		return placeholder(FakeMatch(latex_href))

	md_texto = re.sub(r'<a\s+href=["\'](.*?)["\']\s*>(.*?)</a>', anchor_sub, md_texto, flags=re.DOTALL)

	# =========================================================================
	# TÍTULOS PROTEGIDOS (CORREGIDOS CON ESPACIADO SEGURO DE LATEX)
	# Usamos \addvspace para el espacio superior y \leavevmode para asegurar párrafo
	# =========================================================================
	
	# A. Títulos Centrados (Usando comandos simples de un solo backslash)
	md_texto = re.sub(r'^####\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \normalsize {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \Large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \LARGE {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H1}}}'), md_texto, flags=re.M)

	# B. ETAPA UNIFICADA: Títulos a la izquierda (ESPACIADO COMPACTO Y PREDECIBLE ANTES DEL TÍTULO)
	md_texto = re.sub(r'^####\s+(.+)$', lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H4}}}\noindent{{\normalsize {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+(.+)$',  lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H3}}}\noindent{{\large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+(.+)$',   lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H2}}}\noindent{{\Large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+(.+)$',    lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H1}}}\noindent{{\LARGE {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H1}}}'), md_texto, flags=re.M)

	# =========================================================================

	# 5. Estilos y bloques restantes
	# 5. Estilos y bloques restantes (Corregido con doble barra para evitar bad escape \c)
	md_texto = re.sub(r'<center>(.*?)</center>', fr'{{\\centering \1\\par}}\vspace*{{{ESP_CENTER_GENERIC}}}', md_texto, flags=re.DOTALL)

	pattern_merge = r'</problem>\s*<problem>'
	while re.search(pattern_merge, md_texto, flags=re.DOTALL):
		md_texto = re.sub(pattern_merge, '\n', md_texto, flags=re.DOTALL)

	md_texto = re.sub(r'<problem>(.*?)</problem>', r'\\begin{problem}\n\1\n\\end{problem}', md_texto, flags=re.DOTALL)

	md_texto = md_texto.replace('&nbsp;', '~')
	md_texto = md_texto.replace('&ensp;', '\\quad ')   
	md_texto = md_texto.replace('&emsp;', '\\qquad ')  



	# Saltos de línea y reglas
	md_texto = re.sub(r'^\s*</?br\s*/?>\s*$', fr'~\\par\\vspace*{{{ESP_BREAK}}}', md_texto, flags=re.M | re.IGNORECASE)
	md_texto = re.sub(r'</?br\s*/?>', r'\\\\ ', md_texto, flags=re.IGNORECASE)
	md_texto = re.sub(r'^---\s*$', r'\\hrule\n\\vspace{0.4cm}', md_texto, flags=re.M)

	# Listas
	md_texto = re.sub(r'^\s*[\*\-]\s+(.+)$', r'\\item \1', md_texto, flags=re.M)
	md_texto = re.sub(r'((?:\\item .+(?:\n|$))+)', r'\\begin{itemize}\n\1\\end{itemize}', md_texto)
	
	# Restauración final de placeholders
	for _ in range(2):
		for key, original_content in math_blocks.items():
			md_texto = md_texto.replace(key, original_content)
		
	return md_texto






import re

def traducir_a_latex(md_texto):

	ESP_CENTER_H1 = "1.0ex"
	ESP_CENTER_H2 = "0ex"
	ESP_CENTER_H3 = "0ex"
	ESP_CENTER_H4 = "-0.5ex"

	ESP_LEFT_H1   = "1.0ex"
	ESP_LEFT_H2   = "0ex"
	ESP_LEFT_H3   = "0ex"
	ESP_LEFT_H4   = "-0.5ex"

	# CONTROL DE ESPACIO ANTES DE LOS TÍTULOS (SUPERIOR)
	ESP_PRE_H1    = "3.0ex"   # Espacio antes de un título #
	ESP_PRE_H2    = "2.5ex"   # Espacio antes de un título ##
	ESP_PRE_H3    = "2.0ex"   # Espacio antes de un título ###
	ESP_PRE_H4    = "1.5ex"   # Espacio antes de un título ####

	ESP_CENTER_GENERIC = "0ex"
	ESP_BREAK = "-0.5ex"
	
	math_blocks = {}
	def placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = match.group(0)
		return key

	def proteger_titulo(bloque_latex):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = bloque_latex
		return key

	## <code name="bash" lbl="codigo_bash_00">. La label permite hacer referencias latex.
	def code_placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		atributos = match.group(1) if match.group(1) else ""
		codigo_interno = match.group(2).strip('\n\r')
		
		# 1. Detectar el lenguaje (Tu lógica actual)
		match_lang = re.search(r'name=["\'](.*?)["\']', atributos)
		if match_lang:
			lang = match_lang.group(1).lower().strip()
			if lang in ["verilog", "vlog"]:
				estilo = "estiloVerilog"
			elif lang in ["c", "cpp", "c++"]:
				estilo = "estiloC"
			elif lang in ["python", "py"]:
				estilo = "estiloPython"
			elif lang in ["bash", "shell"]:
				estilo = "estiloBash"
			else:
				estilo = "estiloPython" 
		else:
			estilo = "estiloPython"
			
		# 🔥 NUEVA LÓGICA: Detectar si hay un atributo lbl="..." para la referencia
		match_lbl = re.search(r'lbl=["\'](.*?)["\']', atributos)
		if match_lbl:
			label_val = match_lbl.group(1).strip()
			opciones_lst = f"style={estilo},label={label_val}"
		else:
			opciones_lst = f"style={estilo}"
			
		# Se inyectan las opciones dinámicas en el entorno lstlisting
		math_blocks[key] = f"\\begin{{lstlisting}}[{opciones_lst}]\n{codigo_interno}\n\\end{{lstlisting}}"
		return key

	# 1. Aislar bloques de código y ecuaciones
	md_texto = re.sub(r'<code([^>]*?)>(.*?)</code>', code_placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$\$.*?\$\$', placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$.*?\$', placeholder, md_texto)
	
	# 🔥 NUEVA LÍNEA: Proteger comandos de control LaTeX con llaves (ej: \ref{...}, \pageref{...}, \label{...})
	# Esto evita que el reemplazo de guiones bajos rompa los identificadores internos.
	md_texto = re.sub(r'\\[a-zA-Z]+\{[^{}]+\}', placeholder, md_texto)

	# 2. Eliminación de contenido invisible
	md_texto = re.msub = re.sub(r'(?m)^#*\s*<invisible>.*?</invisible>\s*\n?', '', md_texto, flags=re.DOTALL)

	# Figuras y Tablas
	pattern_fig = r'<latex_fig\s+src=["\'](.*?)["\']\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*/>'
	replacement_fig = (
		r'\\begin{figure}[H]\n'
		r'\\centering\n'
		r'\\includegraphics[width=0.85\\textwidth]{\1}\n'
		r'\\caption{\2}\n'
		r'\\label{\3}\n'
		r'\\end{figure}'
	)
	md_texto = re.sub(pattern_fig, replacement_fig, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\\begin{figure}.*?\\end{figure}', placeholder, md_texto, flags=re.DOTALL)

	pattern_tab = r'<latex_table\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*>(.*?)</latex_table>'
	
	def table_sub(match):
		caption_text = match.group(1).strip()
		label_text = match.group(2).strip()
		tabla_interna = match.group(3).strip('\n\r')
		tabla_limpia = tabla_interna.replace(r'\begin{center}', '').replace(r'\end{center}', '')
		return (
			f"\\begin{{table}}[H]\n"
			f"\\centering\n"
			f"{tabla_limpia}\n"
			f"\\caption{{{caption_text}}}\n"
			f"\\label{{{label_text}}}\n"
			f"\\end{{table}}"
		)
		
	md_texto = re.sub(pattern_tab, table_sub, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\\begin{table}.*?\\end{table}', placeholder, md_texto)

	# 3. Escapar guiones bajos del texto común
	md_texto = md_texto.replace('_', '\\_') 

	# =========================================================================
	# 🚨 NUEVO ORDEN: PROCESAR ENTORNOS DE TEXTO BÁSICOS ANTES QUE LOS TÍTULOS
	# =========================================================================
	md_texto = re.sub(r'<b>(.*?)</b>', r'\\textbf{\1}', md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', md_texto)
	md_texto = re.sub(r'`(.*?)`', r'\\texttt{\1}', md_texto)
	md_texto = re.sub(r'\*(.*?)\*', r'\\textit{\1}', md_texto) 

	# 4. Procesamiento de etiquetas HTML de formato
	for _ in range(3):
		md_texto = re.sub(r'<blocknote>(.*?)</blocknote>', r'\\begin{quote}\n\\color{gray}\n\1\n\\end{quote}', md_texto, flags=re.DOTALL)
		md_texto = re.sub(r'<color\s+name=["\'](.*?)["\']>(.*?)</color>', r'{\\color{\1}\2}', md_texto, flags=re.DOTALL)
		
		def font_sub(match):
			tipo = match.group(1).strip().lower()
			contenido = match.group(2)
			fuentes = {'tt': 'texttt', 'sf': 'textsf', 'rm': 'textrm', 'sc': 'textsc'}
			comando = fuentes.get(tipo, 'texttt')
			return f"\\{comando}{{{contenido}}}"
		md_texto = re.sub(r'<font\s+name=["\'](.*?)["\']>(.*?)</font>', font_sub, md_texto, flags=re.DOTALL)

	def anchor_sub(match):
		url_real = match.group(1).strip()
		texto_visible = match.group(2)
		latex_href = f"\\href{{{url_real}}}{{{texto_visible}}}"
		
		class FakeMatch:
			def __init__(self, val): self.val = val
			def group(self, num): return self.val
		return placeholder(FakeMatch(latex_href))

	md_texto = re.sub(r'<a\s+href=["\'](.*?)["\']\s*>(.*?)</a>', anchor_sub, md_texto, flags=re.DOTALL)

	# =========================================================================
	# TÍTULOS PROTEGIDOS
	# =========================================================================
	md_texto = re.sub(r'^####\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \normalsize {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \Large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \LARGE {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H1}}}'), md_texto, flags=re.M)

	md_texto = re.sub(r'^####\s+(.+)$', lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H4}}}\noindent{{\normalsize {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+(.+)$',  lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H3}}}\noindent{{\large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+(.+)$',   lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H2}}}\noindent{{\Large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+(.+)$',    lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H1}}}\noindent{{\LARGE {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H1}}}'), md_texto, flags=re.M)

	# 5. Estilos y bloques restantes
	md_texto = re.sub(r'<center>(.*?)</center>', fr'{{\\centering \1\\par}}\vspace*{{{ESP_CENTER_GENERIC}}}', md_texto, flags=re.DOTALL)

	pattern_merge = r'</problem>\s*<problem>'
	while re.search(pattern_merge, md_texto, flags=re.DOTALL):
		md_texto = re.sub(pattern_merge, '\n', md_texto, flags=re.DOTALL)

	md_texto = re.sub(r'<problem>(.*?)</problem>', r'\\begin{problem}\n\1\n\\end{problem}', md_texto, flags=re.DOTALL)

	md_texto = md_texto.replace('&nbsp;', '~')
	md_texto = md_texto.replace('&ensp;', '\\quad ')   
	md_texto = md_texto.replace('&emsp;', '\\qquad ')  

	# Saltos de línea y reglas
	md_texto = re.sub(r'^\s*</?br\s*/?>\s*$', fr'~\\par\\vspace*{{{ESP_BREAK}}}', md_texto, flags=re.M | re.IGNORECASE)
	md_texto = re.sub(r'</?br\s*/?>', r'\\\\ ', md_texto, flags=re.IGNORECASE)
	md_texto = re.sub(r'^---\s*$', r'\\hrule\n\\vspace{0.4cm}', md_texto, flags=re.M)

	# Listas
	md_texto = re.sub(r'^\s*[\*\-]\s+(.+)$', r'\\item \1', md_texto, flags=re.M)
	md_texto = re.sub(r'((?:\\item .+(?:\n|$))+)', r'\\begin{itemize}\n\1\\end{itemize}', md_texto)
	
	# Restauración final de placeholders
	for _ in range(2):
		for key, original_content in math_blocks.items():
			md_texto = md_texto.replace(key, original_content)
		
	return md_texto




def procesar_notebook_completo(verbose=False):
	"""Recorre el notebook en dos pasadas:
	Pasada 1: Procesa el notebook de forma normal traduciendo y generando los archivos 
	          originales (NNNN_xxxx_iiii.tex) intactos. Al mismo tiempo, agrupa el Markdown 
	          por prefijo en memoria.
	Pasada 2: Toma el Markdown consolidado de cada familia (NNNN_xxxx), lo traduce de un 
	          solo viaje (lo que mergea los <problem> contiguos) y genera un NUEVO archivo 
	          intermedio consolidado.
	"""
	nombre_notebook = get_this_ipynb_filename()
	
	with open(nombre_notebook, "r", encoding="utf-8") as f:
		cells = json.load(f)["cells"]
		
	# Diccionario para agrupar el Markdown por prefijo base
	bloques_unificados = {}  # Clave: "0001_answer" -> Valor: [lista de textos de celdas]
	orden_prefijos = []      # Guarda el orden cronológico de los prefijos
	
	archivo_actual = None
	prefijo_actual = None
	bloque_actual_celda = []
	archivos_originales_count = 0
	archivos_intermedios_count = 0
	
	carpeta_salida = os.path.abspath(os.path.join(os.getcwd(), "ipynb.out"))
	os.makedirs(carpeta_salida, exist_ok=True)

	# ==========================================================================
	# PASADA 1: TRADUCCIÓN ORIGINAL INDIVIDUAL Y AGRUPAMIENTO EN MEMORIA
	# ==========================================================================
	for cell in cells:
		texto_celda = ""
		
		if cell["cell_type"] == "markdown":
			texto_celda = "".join(cell["source"])
		elif cell["cell_type"] == "code":
			for output in cell.get("outputs", []):
				if "data" in output and "text/plain" in output["data"]:
					texto_celda = "".join(output["data"]["text/plain"])
					break
				elif "text" in output:
					texto_celda = "".join(output["text"])
					break
		
		if not texto_celda.strip():
			continue

		match = re.search(r'(?m)^\s*<!--\s*fgrLib\.export_this_(?:markdown|output)\("(.*?)"\)\s*-->', texto_celda)
		
		if match:
			# Guardamos el archivo de la celda anterior antes de cambiar de ruta
			if archivo_actual and bloque_actual_celda:
				latex_individual = traducir_a_latex("".join(bloque_actual_celda))
				with open(archivo_actual, "w", encoding="utf-8") as f_out:
					f_out.write(latex_individual)
				archivos_originales_count += 1
				if verbose:
					print(f"☑ Generado Original: {archivo_actual}")
				bloque_actual_celda = []
			
			archivo_original_nombre = match.group(1)  # Ej: "0001_answer_0000.tex"
			archivo_actual = os.path.join(carpeta_salida, archivo_original_nombre)
			
			# Extraemos el prefijo aislando el índice final _iiii
			match_prefijo = re.match(r'^(\d{4}_[a-zA-Z0-9_]+?)_(\d{4})\.tex$', archivo_original_nombre)
			if match_prefijo:
				prefijo_actual = match_prefijo.group(1)  # Ej: "0001_answer"
			else:
				prefijo_actual = archivo_original_nombre.replace(".tex", "")
			
			if prefijo_actual not in bloques_unificados:
				bloques_unificados[prefijo_actual] = []
				orden_prefijos.append(prefijo_actual)
			
			texto_celda = texto_celda.replace(match.group(0), "").lstrip('\n')
		
		if archivo_actual and texto_celda.strip():
			if cell["cell_type"] == "markdown" or match:
				bloque_actual_celda.append(texto_celda + "\n\n")
				# Acumulamos también en el gran bloque de memoria para la segunda pasada
				bloques_unificados[prefijo_actual].append(texto_celda + "\n\n")
				
	# Guardar el último archivo original rezagado
	if archivo_actual and bloque_actual_celda:
		latex_individual = traducir_a_latex("".join(bloque_actual_celda))
		with open(archivo_actual, "w", encoding="utf-8") as f_out:
			f_out.write(latex_individual)
		archivos_originales_count += 1
		if verbose:
			print(f"☑ Generado Original: {archivo_actual}")

	# ==========================================================================
	# PASADA 2: GENERACIÓN DE ARCHIVOS INTERMEDIOS CONSOLIDADOS
	# ==========================================================================
	for prefijo in orden_prefijos:
		contenido_acumulado = "".join(bloques_unificados[prefijo])
		if not contenido_acumulado.strip():
			continue
			
		# Pasamos el bloque entero. Aquí tu regex de 'traducir_a_latex' 
		# va a unificar todos los <problem> contiguos en un único entorno.
		latex_consolidado = traducir_a_latex(contenido_acumulado)
		
		# Creamos el nuevo archivo intermedio (Ej: 0001_answer.tex)
		ruta_archivo_intermedio = os.path.join(carpeta_salida, f"{prefijo}.tex")
		
		with open(ruta_archivo_intermedio, "w", encoding="utf-8") as f_out:
			f_out.write(latex_consolidado)
			
		archivos_intermedios_count += 1
		if verbose:
			print(f"⚙️ Generado Intermedio Consolidado: {ruta_archivo_intermedio}")

	if not verbose:
		print(f"☑ Proceso de extracción completo. Originales: {archivos_originales_count} | Nuevos Intermedios: {archivos_intermedios_count}")


#===============================================================================
#===============================================================================

def compilar_pdf_automatico(archivo_principal="tp.tex", clean=True):

	"""Compila el archivo .tex principal a PDF de forma segura y sin colgarse."""
	if not os.path.exists(archivo_principal):
		print(f"⚠ No se encontró el archivo '{archivo_principal}' para compilar.")
		return

	# Verificar si latexmk está instalado en el PATH del sistema
	if not shutil.which("latexmk"):
		print("❌ Error: 'latexmk' no está instalado o no se encuentra en el PATH de Windows.")
		return

	# 1. Separar el directorio y el nombre del archivo para fijar la ruta relativa
	dir_trabajo = os.path.dirname(archivo_principal)
	nombre_base = os.path.basename(archivo_principal)
	cwd_destino = dir_trabajo if dir_trabajo else None

	print(f"⛭ Compilando '{archivo_principal}' con latexmk...")
	try:
		# Ejecuta el comando de compilación con latexmk de forma controlada
		resultado = subprocess.run(
			["latexmk", "-g", "-synctex=0", "-interaction=nonstopmode", "-file-line-error", "-pdf", "-auxdir=tmp", nombre_base],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			cwd=cwd_destino,
			timeout=30
		)

		# Filtrar advertencias rastreando el archivo de origen
		advertencias = []
		archivo_actual = nombre_base
		
		if resultado.stdout:
			for linea in resultado.stdout.splitlines():
				linea_clean = linea.strip()
				
				# Detectar cuándo LaTeX abre un archivo nuevo
				if "(" in linea_clean and ".tex" in linea_clean:
					for palabra in linea_clean.split():
						if "(" in palabra and ".tex" in palabra:
							# Limpiar los caracteres de apertura y cierre de LaTeX
							nom = palabra.replace("(", "").replace(")", "")
							# Extraer solo el nombre del archivo final de forma segura
							archivo_actual = os.path.basename(nom)

				# Capturar las advertencias y asociarlas a su archivo correspondiente
				if "warning" in linea_clean.lower() or "overfull" in linea_clean.lower() or "underfull" in linea_clean.lower():
					mensaje = f"[{archivo_actual}] {linea_clean}"
					if mensaje not in advertencias:
						advertencias.append(mensaje)
		
		# Desplegar resultado sintético detallado con archivos
		if advertencias:
			print(f"⚠ Se encontraron {len(advertencias)} advertencias en la compilación:")
			for adv in advertencias:
				print(f"  • {adv}")
		else:
			print("Advertencias de compilación = 0")

		if resultado.returncode == 0:

			print("✅ PDF generado y actualizado ok.")

			if clean==True:

				# ESTRATEGIA DE LIMPIEZA: Solo si la compilación fue exitosa
				ruta_ipynb_out = os.path.abspath(os.path.join(os.getcwd(), "ipynb.out"))
				if os.path.exists(ruta_ipynb_out):
					shutil.rmtree(ruta_ipynb_out)
					print("➔ Carpeta ipynb.out eliminada tras compilar LaTeX  ok.", flush=True)

				# 2. Eliminar carpeta latex/tmp (NUEVO)
				ruta_latex_tmp = os.path.abspath(os.path.join(os.getcwd(), "latex", "tmp"))
				if os.path.exists(ruta_latex_tmp):
					shutil.rmtree(ruta_latex_tmp)
					print("➔ Archivos /latex/tmp/ eliminados tras compilar LaTeX ok.", flush=True)

			else:
				print("⚠ [clean = 0] Archivos auxiliares no eliminados.")

		else:
			print("❌ Error de compilación en LaTeX. Revisa el archivo log o la sintaxis.")
			# Muestra las últimas 5 líneas del error para saber qué falló
			lineas_error = resultado.stdout.splitlines()[-5:]
			print("\n".join(lineas_error))
			
	except subprocess.TimeoutExpired:
		print("❌ La compilación tardó demasiado y fue interrumpida de forma segura para evitar cuelgues.")
	except Exception as e:
		print(f"❌ Ocurrió un error inesperado al lanzar pdflatex: {e}")


#===============================================================================
# Para armar todo desde un script usando la consola
#===============================================================================




def procesar_y_compilar_informe(nombre_notebook, texFile, clean): 
	# SILENCIAR ADVERTENCIA DE ZMQ: Oculta el cartel molesto del bucle de eventos asíncronos en Windows 
	warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Proactor event loop.*") 
	
	base_dir = os.getcwd() 

	# LIMPIEZA PREVENTIVA AL INICIO: Borra fantasmas de corridas anteriores.
	ruta_ipynb_out = os.path.abspath(os.path.join(base_dir, "ipynb.out"))
	if os.path.exists(ruta_ipynb_out):
		shutil.rmtree(ruta_ipynb_out)
		print("♻ Limpieza inicial: ipynb.out eliminada.", flush=True)

	# Borrar la carpeta latex/tmp vieja si existe
	ruta_latex_tmp = os.path.abspath(os.path.join(base_dir, "latex", "tmp"))
	if os.path.exists(ruta_latex_tmp):
		shutil.rmtree(ruta_latex_tmp)
		print("♻ Limpieza inicial: Archivos auxiliares de LaTeX (tmp) eliminados.", flush=True)

	# Convertir la ruta del .tex a RUTA ABSOLUTA para evitar bloqueos de Windows 
	ruta_tex_absoluta = os.path.abspath(os.path.join(base_dir, "latex", texFile)) 
	
	print(f"⛭ Ejecutando Notebook: {nombre_notebook}...", flush=True) 
	try: 
		with open(nombre_notebook, "r", encoding="utf-8") as f: 
			nb = nbformat.read(f, as_version=4) 
			
		ep = ExecutePreprocessor(timeout=10, kernel_name="python3") 
		ep.preprocess(nb, {'metadata': {'path': base_dir}}) 
		
		with open(nombre_notebook, "w", encoding="utf-8") as f: 
			nbformat.write(nb, f) 
		print("☑ Ejecución celdas ok. Output saved.", flush=True) 
	except CellExecutionError as e: 
		print("\n❌ EL NOTEBOOK SE DETUVO PORQUE UNA CELDA TARDÓ DEMASIADO O FALLÓ:", flush=True) 
		print(e, flush=True) 
		sys.exit(1) 
	except Exception as e: 
		print(f"❌ Error general en la preparación: {e}", flush=True) 
		sys.exit(1) 
		
	print("Generando ipynb.out desde bloques especificados ipynb...", flush=True) 
	procesar_notebook_completo() 

	# ==========================================================================
	# >>> ENTORNO ESPEJO TEMPORAL PARA COMPILACIÓN DE MERGES SEGURA <<<
	# ==========================================================================
	ruta_ipynb_compile = os.path.abspath(os.path.join(base_dir, "ipynb.out_compile"))
	ruta_ipynb_backup = os.path.abspath(os.path.join(base_dir, "ipynb.out_original_bak"))

	if os.path.exists(ruta_ipynb_out):
		print("⚙️ Estructurando entorno de compilación temporal en espejo...", flush=True)
		# 1. Clonamos ipynb.out intacto en una carpeta temporal de compilación
		if os.path.exists(ruta_ipynb_compile):
			shutil.rmtree(ruta_ipynb_compile)
		shutil.copytree(ruta_ipynb_out, ruta_ipynb_compile)
		
		# 2. Hacemos las modificaciones de merge SOLO en la carpeta temporal espejo
		archivos_en_compile = os.listdir(ruta_ipynb_compile)
		for archivo in archivos_en_compile:
			# Validamos que sea un archivo de texto consolidado intermedio (ej: 0001_answer.tex)
			if archivo.endswith(".tex") and not re.search(r'_\d{4}\.tex$', archivo):
				prefijo_base = archivo.replace(".tex", "")
				ruta_consolidada = os.path.join(ruta_ipynb_compile, archivo)
				
				with open(ruta_consolidada, "r", encoding="utf-8") as f_cons:
					contenido_mergeado = f_cons.read()
				
				# Buscamos sus archivos hijos individuales asociados (ej: _0000.tex, _0001.tex)
				patron_hijos = re.compile(rf'^{re.escape(prefijo_base)}_\d{{4}}\.tex$')
				archivos_hijos = sorted([f for f in archivos_en_compile if patron_hijos.match(f)])
				
				for idx, archivo_hijo in enumerate(archivos_hijos):
					ruta_hijo = os.path.join(ruta_ipynb_compile, archivo_hijo)
					with open(ruta_hijo, "w", encoding="utf-8") as f_hijo:
						if idx == 0:
							# El archivo _0000 absorbe TODO el contenido mergeado de un viaje
							f_hijo.write(contenido_mergeado)
						else:
							# Los archivos _0001, _0002, etc., quedan vacíos para no duplicar en el PDF
							f_hijo.write(f"% Contenido absorbido unificadamente en el archivo _0000 de {prefijo_base}\n")

		# 3. Intercambiamos las carpetas en caliente para engañar a LaTeX:
		# Resguardamos la original intacta y ponemos la clonada modificada como 'ipynb.out'
		os.rename(ruta_ipynb_out, ruta_ipynb_backup)
		os.rename(ruta_ipynb_compile, ruta_ipynb_out)
	# ==========================================================================

	print("⛭ Compilando LaTeX...", flush=True) 
	
	try:
		import gc 
		gc.set_threshold(0) 
		
		# Invocamos la compilación. LaTeX leerá la carpeta 'ipynb.out' modificada temporalmente
		compilar_pdf_automatico(ruta_tex_absoluta, clean) 
	finally:
		# ==========================================================================
		# >>> RESTAURACIÓN DE SEGURIDAD INDESTRUCTIBLE EN EL FINALLY <<<
		# ==========================================================================
		# Ocurra lo que ocurra (termine bien o falle LaTeX), devolvemos tus archivos 
		# originales exactamente a su lugar en ipynb.out y borramos la basura temporal.
		if os.path.exists(ruta_ipynb_backup):
			if os.path.exists(ruta_ipynb_out):
				shutil.rmtree(ruta_ipynb_out) # Borramos la modificada de compilación
			os.rename(ruta_ipynb_backup, ruta_ipynb_out) # Restauramos tu carpeta original intacta
			print("☑ Restauración completa: Tus archivos originales en ipynb.out quedaron intactos.", flush=True)
		
		if os.path.exists(ruta_ipynb_compile):
			shutil.rmtree(ruta_ipynb_compile)
		# ==========================================================================

	# 4. Salida limpia saltándose los cuelgues de hilos ocultos de Python
	os._exit(0)
