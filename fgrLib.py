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


#===============================================================================
# Aísla formulas matemáticas y traduce HTML+Markdown imitando bloque.
#===============================================================================


def traducir_a_latex(md_texto):

	# Espaciado posterior para títulos CENTRADOS
	ESP_CENTER_H1 = "1.0ex"
	ESP_CENTER_H2 = "0ex"
	ESP_CENTER_H3 = "0ex"
	ESP_CENTER_H4 = "-0.5ex"

	# Espaciado posterior para títulos ALINEADOS A LA IZQUIERDA
	ESP_LEFT_H1   = "1.0ex"
	ESP_LEFT_H2   = "0ex"
	ESP_LEFT_H3   = "0ex"
	ESP_LEFT_H4   = "-0.5ex"

	# Espaciado para etiquetas <center> genéricas sueltas
	ESP_CENTER_GENERIC = "0ex"

	# PARA EL RENGLÓN VACÍO (<br/> AISLADO)
	ESP_BREAK = "-0.5ex"

	#---------------------------------------------------------------------------
	# PROCESAMIENTO BASE Y PROTECCIÓN DE ENTORNOS

	math_blocks = {}
	def placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = match.group(0)
		return key
	
	# <code></code>
	def code_placeholder(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		codigo_interno = match.group(1).strip('\n\r')
		math_blocks[key] = f"\\begin{{lstlisting}}[language=Python]\n{codigo_interno}\n\\end{{lstlisting}}"
		return key

	md_texto = re.sub(r'<code>(.*?)</code>', code_placeholder, md_texto, flags=re.DOTALL)

	# Proteger ecuaciones intactas ($$ y $)
	md_texto = re.sub(r'\$\$.*?\$\$', placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$.*?\$', placeholder, md_texto)

	#---------------------------------------------------------------------------
	# Etiquetas con posibles anidamientos. N loops anidados para N etiquetas.
	#---------------------------------------------------------------------------
	# Ejecutamos pasadas fijas sin bucles abiertos. Esto disuelve capas 
	# de anidamiento de adentro hacia afuera de manera 100% controlada.
	for _ in range(3):
		# 1. blocknote para citas en gris
		md_texto = re.sub(r'<blocknote>(.*?)</blocknote>', r'\\begin{quote}\n\\color{gray}\n\1\n\\end{quote}', md_texto, flags=re.DOTALL)
		
		# 2. color name="..." dinámico (importante: el igual no tiene que tener espacios)
		md_texto = re.sub(r'<color\s+name=["\'](.*?)["\']>(.*?)</color>', r'{\\color{\1}\2}', md_texto, flags=re.DOTALL)
		
		# <font name="tt"|"sf"|"rm">
		def font_sub(match):
			tipo = match.group(1).strip().lower()
			contenido = match.group(2)
			fuentes = {
				'tt': 'texttt', # Monospace teletype.
				'sf': 'textsf', # Sans-serif (sin remates).
				'rm': 'textrm',  # Roman (con remates).
				'sc': 'textsc'  # Small Caps.
			}
			comando = fuentes.get(tipo, 'texttt')
			return f"\\{comando}{{{contenido}}}"
		md_texto = re.sub(r'<font\s+name=["\'](.*?)["\']>(.*?)</font>', font_sub, md_texto, flags=re.DOTALL)


	# Traduce <a href="...">Texto</a> a LaTeX y lo protege usando tu función placeholder
	def anchor_sub(match):
		url_real = match.group(1).strip()
		texto_visible = match.group(2)
		# Escapa el guion bajo únicamente en el texto visual, manteniendo la URL intacta
		texto_visible = texto_visible.replace('_', '\\_')
		
		# Construye la estructura nativa de LaTeX
		latex_href = f"\\href{{{url_real}}}{{{texto_visible}}}"
		
		# Lo pasamos por tu función placeholder original para aislarlo en math_blocks
		# Simula un comportamiento idéntico a lo que hacés con las tablas o imágenes
		class FakeMatch:
			def __init__(self, val): self.val = val
			def group(self, num): return self.val
		return placeholder(FakeMatch(latex_href))

	md_texto = re.sub(r'<a\s+href=["\'](.*?)["\']\s*>(.*?)</a>', anchor_sub, md_texto, flags=re.DOTALL)


	# Estructuras que nunca se anidan dentro de si mismas
	#---------------------------------------------------------------------------


	# 1. Títulos CENTRADOS (Mismo mecanismo de espaciado uniforme)
	md_texto = re.sub(r'^####\s+<center>\s*(.*?)\s*</center>$', fr'{{\\centering \\normalsize \1\\par}}\\vspace*{{{ESP_CENTER_H4}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+<center>\s*(.*?)\s*</center>$', fr'{{\\centering \\large \1\\par}}\\vspace*{{{ESP_CENTER_H3}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+<center>\s*(.*?)\s*</center>$', fr'{{\\centering \\Large \1\\par}}\\vspace*{{{ESP_CENTER_H2}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+<center>\s*(.*?)\s*</center>$', fr'{{\\centering \\LARGE \1\\par}}\\vspace*{{{ESP_CENTER_H1}}}', md_texto, flags=re.M)

	# 2. Títulos ALINEADOS A LA IZQUIERDA (Mecanismo estructural idéntico)
	md_texto = re.sub(r'^####\s+(.+)$', fr'\\noindent{{\\normalsize \1\\par}}\\vspace*{{{ESP_LEFT_H4}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+(.+)$', fr'\\noindent{{\\large \1\\par}}\\vspace*{{{ESP_LEFT_H3}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+(.+)$', fr'\\noindent{{\\Large \1\\par}}\\vspace*{{{ESP_LEFT_H2}}}', md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+(.+)$', fr'\\noindent{{\\LARGE \1\\par}}\\vspace*{{{ESP_LEFT_H1}}}', md_texto, flags=re.M)

	# 3. Limpieza de etiquetas Inline (Aplica la negrita adentro del bloque)
	md_texto = re.sub(r'<center>(.*?)</center>', fr'{{\\centering \1\\par}}\\vspace*{{{ESP_CENTER_GENERIC}}}', md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'<b>(.*?)</b>', r'\\textbf{\1}', md_texto, flags=re.DOTALL)

	# CONTENIDO INVISIBLE
	md_texto = re.sub(r'<invisible>(.*?)</invisible>', r'', md_texto, flags=re.DOTALL)

	## Merge <problem>. Permite en el notebook separar bloques transparentemente.
	pattern_merge = r'</problem>\s*<problem>'
	while re.search(pattern_merge, md_texto, flags=re.DOTALL):
		md_texto = re.sub(pattern_merge, '\n', md_texto, flags=re.DOTALL)

	# <problem>
	md_texto = re.sub(r'<problem>(.*?)</problem>', r'\\begin{problem}\n\1\n\\end{problem}', md_texto, flags=re.DOTALL)

	md_texto = md_texto.replace('&nbsp;', '~')
	md_texto = md_texto.replace('&ensp;', '\\quad ')   # Espacio equivalente a en-space
	md_texto = md_texto.replace('&emsp;', '\\qquad ')  # Espacio equivalente a em-space

	# !!! SOPORTE AUTOMÁTICO PARA ENTORNO FIGURE DE LATEX !!!
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

	# Traduce <latex_table cap="..." lbl="..."> ... </latex_table> de forma segura
	pattern_tab = r'<latex_table\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*>(.*?)</latex_table>'
	
	def table_sub(match):
		caption_text = match.group(1).strip()
		label_text = match.group(2).strip()
		tabla_interna = match.group(3).strip('\n\r')
		
		# Quitamos los entornos \begin{center} manuales si existieran para evitar conflictos
		tabla_limpia = tabla_interna.replace(r'\begin{center}', '').replace(r'\end{center}', '')
		
		# Colocamos el caption y el label ABAJO del cuerpo de la tabla
		return (
			f"\\begin{{table}}[H]\n"
			f"\\centering\n"
			f"{tabla_limpia}\n"
			f"\\caption{{{caption_text}}}\n"
			f"\\label{{{label_text}}}\n"
			f"\\end{{table}}"
		)
		
	md_texto = re.sub(pattern_tab, table_sub, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\\begin{table}.*?\\end{table}', placeholder, md_texto, flags=re.DOTALL)

	# =========================================================================

	# !!! 1. SI EL <br/> ESTÁ SOLO: Genera renglón vacío normal con ajuste ajustable !!!
	md_texto = re.sub(r'^\s*</?br\s*/?>\s*$', fr'~\\par\\vspace*{{{ESP_BREAK}}}', md_texto, flags=re.M | re.IGNORECASE)
		
	# !!! 2. SI EL <br/> ESTÁ EN LINEA: Hace salto de línea estándar !!!
	md_texto = re.sub(r'</?br\s*/?>', r'\\\\ ', md_texto, flags=re.IGNORECASE)

	md_texto = re.sub(r'^---\s*$', r'\\hrule\n\\vspace{0.4cm}', md_texto, flags=re.M)
	
	# Formatear estilos básicos de texto plano (Negritas y Monocromo).
	md_texto = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', md_texto)
	md_texto = re.sub(r'`(.*?)`', r'\\texttt{\1}', md_texto)
	
	md_texto = re.sub(r'\*(.*?)\*', r'\\textit{\1}', md_texto) # *cursiva*

	md_texto = md_texto.replace('_', '\\_') # Escapar guiones bajos en texto.

	# Procesar listas de ítems.
	md_texto = re.sub(r'^\s*[\*\-]\s+(.+)$', r'\\item \1', md_texto, flags=re.M)
	md_texto = re.sub(r'((?:\\item .+(?:\n|$))+)', r'\\begin{itemize}\n\1\\end{itemize}', md_texto)
	
	# --- PARCHE DE RESTAURACIÓN CON DOBLE PASADA DE LIMPIEZA ---
	for _ in range(2):
		for key, original_math in math_blocks.items():
			md_texto = md_texto.replace(key, original_math)
		
	return md_texto





#===============================================================================
# Todo markdown con encabezado:
# <!-- fgrLib.export_this_markdown("filename_ejemplo.tex") -->
# genera el archivo especificado en el argumento.
#===============================================================================

def __________________procesar_notebook_completo(verbose=False):
	"""Recorre el notebook de arriba a abajo y exporta bloques por comentario HTML,
	soportando tanto celdas Markdown como salidas de consola (print) de celdas de código.
	"""
	nombre_notebook = get_this_ipynb_filename()
	
	with open(nombre_notebook, "r", encoding="utf-8") as f:
		cells = json.load(f)["cells"]
		
	bloque_actual = []
	archivo_actual = None
	archivos_generados_count = 0  # 🔢 Contador para el reporte final
	
	for cell in cells:
		texto_celda = ""
		
		# --- EXTRACTOR DE TEXTO SEGÚN EL TIPO DE CELDA ---
		if cell["cell_type"] == "markdown":
			texto_celda = "".join(cell["source"])
			
		elif cell["cell_type"] == "code":
			# Recorremos los outputs de la ejecución buscando salidas de texto plano
			for output in cell.get("outputs", []):
				if "data" in output and "text/plain" in output["data"]:
					texto_celda = "".join(output["data"]["text/plain"])
					break
				elif "text" in output:
					texto_celda = "".join(output["text"])
					break
		
		# Si la celda no aportó texto o está vacía, pasamos a la siguiente
		if not texto_celda.strip():
			continue

		# --- LÓGICA ÚNICA DE CONTROL Y EXPORTACIÓN ---
		# CAMBIO SEGURO: Usamos re.search con (?m)^\s* para permitir saltos de línea previos (\n) 
		# que Jupyter agrega en los prints de consola, manteniendo el comportamiento del regex original.
		match = re.search(r'(?m)^\s*<!--\s*fgrLib\.export_this_(?:markdown|output)\("(.*?)"\)\s*-->', texto_celda)
		
		if match:
			# Si ya veníamos acumulando texto de un archivo anterior, lo procesamos y guardamos
			if archivo_actual and bloque_actual:
				latex_final = traducir_a_latex("".join(bloque_actual))
				os.makedirs(os.path.dirname(archivo_actual), exist_ok=True)
				with open(archivo_actual, "w", encoding="utf-8") as f_out:
					f_out.write(latex_final)
				
				archivos_generados_count += 1  # Incrementar contador
				if verbose:
					print(f"☑ Generado: {archivo_actual}")
					
				bloque_actual = []
			
			# Aseguramos que guarde la carpeta ipynb.out dentro de tu proyecto actual
			archivo_actual = os.path.abspath(os.path.join(os.getcwd(), "ipynb.out", match.group(1)))

			# CAMBIO SEGURO: Eliminamos la línea del tag sin importar si tiene saltos de línea previos
			texto_celda = texto_celda.replace(match.group(0), "").lstrip('\n')
		
		# --- ACUMULACIÓN ORIGINAL INTACTA ---
		# Mantiene al 100% tus reglas de negocio: el Markdown común se acumula en el archivo abierto,
		# y las celdas de código comunes sin tag se ignoran por completo.
		if archivo_actual and texto_celda.strip():
			if cell["cell_type"] == "markdown" or match:
				bloque_actual.append(texto_celda + "\n\n")
				
	# Guardar el último bloque rezagado al salir de todo el bucle
	if archivo_actual and bloque_actual:
		latex_final = traducir_a_latex("".join(bloque_actual))
		with open(archivo_actual, "w", encoding="utf-8") as f_out:
			f_out.write(latex_final)
		
		archivos_generados_count += 1  # Incrementar contador del último bloque
		if verbose:
			print(f"☑ Generado: {archivo_actual}")

	# 📊 REPORTE RESUMIDO: Si el flag verbose está apagado, reporta el total en una sola línea
	if not verbose:
		print(f"☑ Extracción completa. N = {archivos_generados_count} archivos LaTeX (.tex) en 'ipynb.out/'.")



def procesar_notebook_completo(verbose=False):
	"""Recorre el notebook de arriba a abajo y exporta bloques por comentario HTML,
	soportando tanto celdas Markdown como salidas de consola (print) de celdas de código.
	Si un nuevo archivo arranca con <problem> y el archivo anterior terminó con </problem>,
	los fusiona en el archivo anterior en lugar de crear uno nuevo.
	"""
	nombre_notebook = get_this_ipynb_filename()
	
	with open(nombre_notebook, "r", encoding="utf-8") as f:
		cells = json.load(f)["cells"]
		
	bloque_actual = []
	archivo_actual = None
	ultimo_archivo_escrito = None  # 🔄 Guardamos la ruta del último archivo guardado
	archivos_generados_count = 0  # 🔢 Contador para el reporte final
	
	def guardar_bloque(ruta_archivo, contenido_bloque):
		nonlocal archivos_generados_count, ultimo_archivo_escrito
		if not contenido_bloque:
			return
			
		texto_md = "".join(contenido_bloque)
		
		# 🚨 REGLA DE MERGE ENTRE DIFERENTES ARCHIVOS DE CELDAS CONTIGUAS 🚨
		# Si este nuevo bloque empieza con <problem> y el archivo anterior terminó en </problem>,
		# reabrimos el archivo anterior, quitamos el \end{problem} de LaTeX y le metemos el nuevo contenido.
		if ultimo_archivo_escrito and os.path.exists(ultimo_archivo_escrito) and texto_md.strip().startswith("<problem>"):
			with open(ultimo_archivo_escrito, "r", encoding="utf-8") as f_prev:
				contenido_anterior = f_prev.read()
			
			# Verificamos si efectivamente el archivo anterior finaliza cerrando un entorno problem
			if contenido_anterior.strip().endswith("\\end{problem}"):
				# Quitamos el cierre del entorno del archivo anterior
				contenido_previo_limpio = contenido_anterior.rstrip().rsplit("\\end{problem}", 1)[0]
				
				# Traducimos el bloque nuevo de forma aislada
				nuevo_latex = traducir_a_latex(texto_md)
				
				# Del nuevo LaTeX traducido, le removemos la apertura \begin{problem}
				if "\\begin{problem}" in nuevo_latex:
					nuevo_latex_limpio = nuevo_latex.split("\\begin{problem}", 1)[1]
					
					# Combinamos todo respetando la estructura interna
					latex_fusionado = contenido_previo_limpio + "\n" + nuevo_latex_limpio
					
					with open(ultimo_archivo_escrito, "w", encoding="utf-8") as f_out:
						f_out.write(latex_fusionado)
					if verbose:
						print(f"⟲ Fusionado y anexado en: {ultimo_archivo_escrito}")
					return # Salimos temprano porque ya fue absorbido por el anterior

		# Flujo normal si no hay merge entre archivos distintos
		latex_final = traducir_a_latex(texto_md)
		os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
		with open(ruta_archivo, "w", encoding="utf-8") as f_out:
			f_out.write(latex_final)
		
		archivos_generados_count += 1
		ultimo_archivo_escrito = ruta_archivo # Actualizamos el rastro
		if verbose:
			print(f"☑ Generado: {ruta_archivo}")

	for cell in cells:
		texto_celda = ""
		
		# --- EXTRACTOR DE TEXTO SEGÚN EL TIPO DE CELDA ---
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

		# --- LÓGICA ÚNICA DE CONTROL Y EXPORTACIÓN ---
		match = re.search(r'(?m)^\s*<!--\s*fgrLib\.export_this_(?:markdown|output)\("(.*?)"\)\s*-->', texto_celda)
		
		if match:
			if archivo_actual and bloque_actual:
				guardar_bloque(archivo_actual, bloque_actual)
				bloque_actual = []
			
			archivo_actual = os.path.abspath(os.path.join(os.getcwd(), "ipynb.out", match.group(1)))
			texto_celda = texto_celda.replace(match.group(0), "").lstrip('\n')
		
		# --- ACUMULACIÓN ORIGINAL INTACTA ---
		if archivo_actual and texto_celda.strip():
			if cell["cell_type"] == "markdown" or match:
				bloque_actual.append(texto_celda + "\n\n")
				
	# Guardar el último bloque rezagado al salir de todo el bucle
	if archivo_actual and bloque_actual:
		guardar_bloque(archivo_actual, bloque_actual)

	# 📊 REPORTE RESUMIDO
	if not verbose:
		print(f"☑ Extracción completa. N = {archivos_generados_count} archivos LaTeX (.tex) en 'ipynb.out/'.")


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
	
	# Usamos os.getcwd() que obtiene la carpeta actual de la terminal
	base_dir = os.getcwd() # Ya no hace falta os.chdir(base_dir) porque ya estás parado en esa carpeta

	# LIMPIEZA PREVENTIVA AL INICIO: Borra fantasmas de corridas anteriores.
	ruta_ipynb_out = os.path.abspath(os.path.join(base_dir, "ipynb.out"))
	if os.path.exists(ruta_ipynb_out):
		shutil.rmtree(ruta_ipynb_out)
		print("♻ Limpieza inicial: ipynb.out eliminada.", flush=True)

	# 2. Borrar la carpeta latex/tmp vieja si existe
	ruta_latex_tmp = os.path.abspath(os.path.join(base_dir, "latex", "tmp"))
	if os.path.exists(ruta_latex_tmp):
		shutil.rmtree(ruta_latex_tmp)
		print("♻ Limpieza inicial: Archivos auxiliares de LaTeX (tmp) eliminados.", flush=True)

	# 2. Convertir la ruta del .tex a RUTA ABSOLUTA para evitar bloqueos de Windows 
	ruta_tex_absoluta = os.path.abspath(os.path.join(base_dir, "latex", texFile)) 
	
	# El flush=True obliga a Git Bash a mostrar el texto en pantalla de inmediato 
	print(f"⛭ Ejecutando Notebook: {nombre_notebook}...", flush=True) 
	try: 
		with open(nombre_notebook, "r", encoding="utf-8") as f: 
			nb = nbformat.read(f, as_version=4) 
			
		# Timeout de 10 segundos por celda para interceptar cuelgues 
		ep = ExecutePreprocessor(timeout=10, kernel_name="python3") 
		ep.preprocess(nb, {'metadata': {'path': base_dir}}) 
		
		# 💾 NUEVA LÍNEA: Guarda los outputs generados de vuelta en el archivo físico 
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
	print("⛭ Compilando LaTeX...", flush=True) 
	
	# 3. Desactivamos los destructores automáticos de la memoria de Jupyter que traban el script 
	import gc 
	gc.set_threshold(0) 
	
	# Invocamos tu función original pasándole la ruta absoluta blindada 
	compilar_pdf_automatico(ruta_tex_absoluta, clean) 


	
	# 4. Salida limpia saltándose los cuelgues de hilos ocultos de Python 3.14 en Windows 
	os._exit(0)

