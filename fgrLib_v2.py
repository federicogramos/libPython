##==============================================================================
## Filename: fgrLib_v2.py
## Version: 20261121
##==============================================================================
## Evoluciona a fgrLib (v1, descartada) agregando el objeto Informe para
## exportar bloques de contenido desde archivos .md / .tex (input_files/).
## Usa los archivos relativos al pwd (dir de compilacion = dir del .ipynb).
##
## Uso en el notebook (el setup se inyecta automaticamente al compilar):
##   informe = Informe("0010_answer")
##   informe.out("ejemplo1.md", "answer")   # .md  => markdown, wrap <answer>
##   informe.out("ejemplo2.tex", "answer")  # .tex => LaTeX literal (verbatim)
##
## -- Tablas markdown: se convierten al template estandar (tabular con
##    reglas, header/filas coloreadas, table[H]); caption opcional = linea
##    **bold** inmediatamente anterior a la tabla.
## -- img() agrega una figura (img/ por defecto, caption = nombre del archivo);
##    comparte el contador NNNN con out().
## Anotaciones de formato:
## -- Párrafos se separan cuando tengo nueva linea en el medio como "espaciador".
## -- Por defecto no hay margen en 1er linea de parrafo. Usar &emsp; de ser
##    necesario.
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
LIB_DIR = os.path.dirname(os.path.abspath(__file__))


#===============================================================================
# CLASE Informe | Exportacion de bloques de contenido desde archivos
#===============================================================================
# El notebook la usa sin importar nada a mano (el setup se inyecta al compilar):
#
#   informe = Informe("0010_answer")
#   informe.out("ejemplo1.md", "answer")   # .md  => markdown, wrap <answer>
#   informe.out("ejemplo2.tex", "answer")  # .tex => LaTeX literal (verbatim)
#
# Reglas:
# -- .md  : se procesa con la conversion markdown -> latex. Los tokens {nombre}
#           se reemplazan con las variables globales del notebook al llamar out().
# -- .tex : se emite VERBATIM envuelto en <latex> (sin conversion alguna).
# -- wrap="answer" agrega los tags <answer>...</answer> automaticamente.
# -- show (opcion) en out(): 'preview' (3 lineas no vacias, por defecto), 'all'
# (todo) o 'none' (silencio total). Solo cambia el output visual del notebook.
# -- Tablas markdown: template estandar (table[H], header/filas coloreadas);
#    caption opcional = linea **bold** inmediatamente anterior a la tabla.
# -- img() agrega una figura (img/ por defecto, caption = nombre del archivo);
#    comparte el contador NNNN con out() (ej: img('img/0010/x.png', 'answer')).
# -- Buses los archivos en input_files/ (directorio por defecto) o como ruta
#    relativa al directorio del notebook. Cada out() genera el siguiente indice:
#    NNNN_tipo_0000.tex, NNNN_tipo_0001.tex, ...
class Informe:

	DIR_INPUT = "input_files"   ## Directorio por defecto de los archivos a incluir.

	def __init__(self, prefix):
		if not re.match(r"^\d{4}(_[a-zA-Z0-9_]+)?$", prefix):
			raise ValueError(f"Prefijo invalido: '{prefix}' (formato: NNNN o NNNN_tipo, ej: 0010_answer).")
		self.prefix = prefix
		self._count = 0
		self._base_dir = os.getcwd()

	def _resolver(self, filename):
		candidates = []
		if os.path.isabs(filename):
			candidates.append(filename)
		else:
			candidates.append(os.path.join(self._base_dir, self.DIR_INPUT, filename))
			candidates.append(os.path.join(self._base_dir, filename))
		for ruta in candidates:
			if os.path.isfile(ruta):
				return ruta
		## Sin extension: intentar imagenes comunes (protocolo img()).
		if "." not in os.path.basename(filename):
			for ext in (".png", ".jpg", ".jpeg", ".pdf"):
				for base in candidates:
					if os.path.isfile(base + ext):
						return base + ext
		raise FileNotFoundError(
			f"El archivo '{filename}' no se encontro (buscado en: {', '.join(candidates)}).")

	@staticmethod
	def _sustituir_tokens(texto, env):
		def rep(m):
			nombre = m.group(1)
			return str(env[nombre]) if nombre in env else m.group(0)
		return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", rep, texto)

	@staticmethod
	def _sustituir_tokens_pct(texto, env):
		## Tokens %nombre% (para .tex): mismo esquema, reemplaza solo los conocidos.
		def rep(m):
			nombre = m.group(1)
			return str(env[nombre]) if nombre in env else m.group(0)
		return re.sub(r"%([a-zA-Z_][a-zA-Z0-9_]*)%", rep, texto)

	def out(self, filename, wrap=None, show="preview"):
		"""Exporta el contenido de 'filename' como el siguiente bloque del informe.
		filename : .md (markdown) o .tex (LaTeX literal, passthrough verbatim).
		wrap     : None (sin envolver) o 'answer' (wrap en <answer>).
		show     : preview del output del notebook: 'preview' (por defecto: 3
		           lineas no vacias), 'all' (bloque completo) o 'none' (silencio).
		Convenio : el nombre del .tex se INFERE del fuente (prefijo + contador),
		asi que 'filename' debe ser un LITERAL y cada celda hace UNA sola out()."""
		if show not in ("preview", "all", "none"):
			raise ValueError(f"show invalido: '{show}' (valores: 'preview', 'all', 'none').")
		ruta = self._resolver(filename)
		with open(ruta, "r", encoding="utf-8") as f:
			contenido = f.read()
			contenido = contenido.replace("\r\n", "\n").replace("\r", "\n")   ## Normalizar EOL.
		nombre_archivo = f"{self.prefix}_{self._count:04d}.tex"
		self._count += 1
		es_tex = filename.lower().endswith(".tex")
		try:
			env = sys._getframe(1).f_globals   ## Variables globales de la celda que llama a out().
		except Exception:
			env = {}
		if es_tex:
			## %VAR% con variables del notebook (protocolo de tablas, ej: tab_potencia.tex).
			contenido = self._sustituir_tokens_pct(contenido, env)
			cuerpo = f"<latex>\n{contenido.strip()}\n</latex>"
		else:
			cuerpo = self._sustituir_tokens(contenido, env).strip()
		if wrap:
			if wrap != "answer":
				raise ValueError(f"wrap invalido: '{wrap}' (solo se soporta 'answer').")
			cuerpo = f"<answer>\n\n{cuerpo}\n\n</answer>"
		## fgrLib_v2: el contenido PROCESADO (tokens sustituidos, tags aplicados) se
		## escribe en ipynb.out/<nombre>.tex: es la fuente de verdad del extractor
		## (procesar_notebook_completo solo lo lee en orden de celdas). El output
		## del notebook es solo un preview visual para el usuario.
		carpeta_out = os.path.join(self._base_dir, "ipynb.out")
		os.makedirs(carpeta_out, exist_ok=True)
		with open(os.path.join(carpeta_out, nombre_archivo), "w", encoding="utf-8", newline="\n") as f:
			f.write(cuerpo + "\n")
		if show == "all":
			print(f"{cuerpo}\n", flush=True)
		elif show == "preview":
			tot = [l for l in cuerpo.splitlines() if l.strip()]
			vista = "\n".join(tot[:3])
			if len(tot) > 3:
				vista += f"\n... {nombre_archivo} - {len(tot)} lineas - show=\"all\" | show=\"none\""
			print(f"{vista}\n", flush=True)
		## show == "none": silencio total (no se imprime nada).

	def img(self, imagen, wrap=None, show="preview"):
		"""Exporta una figura (entorno figure[H]) como el siguiente bloque
		del informe. Comparte el contador NNNN con out() (se alternan en el
		orden en que se llaman).
		imagen : ruta relativa al notebook (ej: 'img/0010/floorplan_v0.png').
		         Si no existe la ruta directa se prueba bajo img/ (directorio
		         por defecto de imagenes, ej: ./informe/img/0010/x.png). Tambien se
		         acepta sin extension: se prueba png/jpg/jpeg/pdf).
		show   : igual que out().
		Convenciones: caption = nombre de archivo sin extension; sin label
		             (evita labels duplicados entre bloques)."""
		if show not in ("preview", "all", "none"):
			raise ValueError(f"show invalido: '{show}' (valores: 'preview', 'all', 'none').")
		if wrap is not None and wrap != "answer":
			raise ValueError(f"wrap invalido: '{wrap}' (solo se soporta 'answer').")
		## Rutas candidatas: directa y con el directorio por defecto de
		## imagenes (img/ relativo al notebook, ej: ./informe/img).
		ruta = None
		for _cand in (imagen, os.path.join("img", imagen)):
			try:
				ruta = self._resolver(_cand)
				break
			except FileNotFoundError:
				continue
		if ruta is None:
			raise FileNotFoundError(
				f"La imagen '{imagen}' no se encontro (buscada directa y bajo img/).")
		rel = os.path.relpath(ruta, self._base_dir).replace(chr(92), '/')
		stem = os.path.splitext(os.path.basename(imagen))[0]
		## caption: stem con los caracteres especiales escapados (un '_' del
		## nombre de archivo sin escapar rompe la compilacion: 'Missing $ inserted').
		caption = (stem.replace('\\', r'\textbackslash{}')
			.replace('&', r'\&').replace('%', r'\%')
			.replace('$', r'\$').replace('#', r'\#')
			.replace('_', r'\_').replace('{', r'\{').replace('}', r'\}'))
		nombre_archivo = f"{self.prefix}_{self._count:04d}.tex"
		self._count += 1
		fig = (
			"\\begin{figure}[H]\n"
			"\\centering\n"
			f"\\includegraphics[width=0.85\\textwidth]{{../{rel}}}\n"
			f"\\caption{{{caption}}}\n"
			"\\end{figure}"
		)
		cuerpo = f"<latex>\n{fig}\n</latex>"
		if wrap:
			cuerpo = f"<answer>\n\n{cuerpo}\n\n</answer>"
		carpeta_out = os.path.join(self._base_dir, "ipynb.out")
		os.makedirs(carpeta_out, exist_ok=True)
		with open(os.path.join(carpeta_out, nombre_archivo), "w", encoding="utf-8", newline="\n") as f:
			f.write(cuerpo + "\n")
		if show == "all":
			print(f"{cuerpo}\n", flush=True)
		elif show == "preview":
			tot = [l for l in cuerpo.splitlines() if l.strip()]
			vista = "\n".join(tot[:3])
			if len(tot) > 3:
				vista += f"\n... {nombre_archivo} - {len(tot)} lineas - show=\"all\" | show=\"none\""
			print(f"{vista}\n", flush=True)


	def __repr__(self):
		return f'Informe(prefix="{self.prefix}", proximo=_"{self._count:04d}")'



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






import re

def traducir_a_latex(md_texto):
	## fgrLib_v2: sanitizar guion matematico unicode (U+2212) => guion comun.
	## pdflatex no soporta U+2212 y rompe la compilacion (Unicode character error).
	md_texto = md_texto.replace('\u2212', '-')

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
			elif lang in ["diff"]:
				estilo = "estiloDiff"
			else:
				estilo = "estiloDefault" 
		else:
			#estilo = "estiloPython"
			estilo = "estiloDefault"
			

			
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

	## <latex> ... </latex> : codigo LaTeX LITERAL (passthrough verbatim).
	## Se protege ANTES que cualquier regla de markdown -> latex y se
	## restaura tal cual al final (sin escapes de '_' ni conversiones).
	## Es el "otro lado" del protocolo que produce lib/latex_out.py.
	def latex_passthrough_sub(match):
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = match.group(1)
		return key

	# 0. PROTEGER BLOQUES <latex> (prioridad maxima: nada dentro se toca).
	## BLOQUES DE CODIGO FENCED (```lang ... ```) => <code name="lang">: se
	## corre ANTES de la proteccion <latex> para que el contenido (con sus
	## '$', '{' y '[' propios de scripts) quede protegido por code_placeholder.
	## Sanitizar no-ASCII: pdflatex + listings no soporta secuencias UTF-8 de
	## multi-byte dentro de lstlisting (rompe con 'Invalid UTF-8 byte sequence').
	## Se mapea a ASCII proximo; lo desconocido pasa a '?'.
	_CODE_ASCII = {
		'\u00B7': '*',    ## punto medio (diagramas ASCII art)
		'\u00D7': 'x',    ## x de multiplicar
		'\u00B5': 'u',    ## micro
		'\u03BC': 'u',    ## mu
		'\u00B0': ' deg', ## grado
		'\u00AB': '"',    ## comilla izquierda
		'\u00BB': '"',    ## comilla derecha
		'\u2013': '-',    ## guion medio
		'\u2014': '-',    ## guion largo
		'\u2026': '...',  ## puntos suspensivos
		'\u00A1': '!',    ## exclamacion invertida
		'\u00BF': '?',    ## interrogacion invertida
		'\u00E1': 'a', '\u00E9': 'e', '\u00ED': 'i', '\u00F3': 'o', '\u00FA': 'u',
		'\u00E2': 'a', '\u00EA': 'e', '\u00F4': 'o', '\u00FB': 'u',
		'\u00E0': 'a', '\u00E8': 'e', '\u00EC': 'i', '\u00F2': 'o', '\u00F9': 'u',
		'\u00F1': 'n', '\u00D1': 'N',
	}

	def _ascii_code(c):
		out = []
		for ch in c:
			out.append(ch if ord(ch) < 0x80 else _CODE_ASCII.get(ch, '?'))
		return ''.join(out)

	def _fence_sub(m):
		_lang = m.group(1).strip()
		_attr = f' name="{_lang}"' if _lang else ''
		return f'<code{_attr}>\n{_ascii_code(m.group(2))}\n</code>'
	md_texto = re.sub(r'```(\w*)\s*\n(.*?)```', _fence_sub, md_texto, flags=re.DOTALL)

	md_texto = re.sub(r'<latex>(.*?)</latex>', latex_passthrough_sub, md_texto, flags=re.DOTALL)

	##
	## fgrLib_v2: convertir caracteres unicode arriesgados a sus equivalentes
	## LaTeX (pdflatex + utf8.def no los conoce y rompen la compilacion con
	## 'Unicode character X not set up for use with LaTeX'). Los $...$ que se
	## inyectan no quedan traidos como matematica: la regla \$...\$ corrio
	## antes (con el contenido real ya protegido).
	_UNICODE_A_LATEX = {
		'\u2248': '$\\approx$',    ## casi igual a
		'\u2264': '$\\leq$',       ## menor o igual
		'\u2265': '$\\geq$',       ## mayor o igual
		'\u2260': '$\\neq$',       ## distinto
		'\u2261': '$\\equiv$',     ## identico
		'\u221A': '$\\sqrt{}$',    ## raiz cuadrada
		'\u221E': '$\\infty$',     ## infinito
		'\u2202': '$\\partial$',   ## derivada parcial
		'\u2205': '$\\varnothing$', ## vacio
		'\u00B1': '$\\pm$',        ## mas o menos
		'\u0394': '$\\Delta$',     ## delta mayuscula
		'\u2026': '\\textellipsis', ## puntos suspensivos
		'\u2013': '--',              ## guion medio (en-dash)
		'\u2014': '---',             ## guion largo (em-dash)
		## Griegas (pdflatex + utf8 no las soporta): se pasan a matematica.
		'\u03B1': '$\\alpha$',   ## alpha
		'\u03B2': '$\\beta$',    ## beta
		'\u03B3': '$\\gamma$',   ## gamma
		'\u03B4': '$\\delta$',   ## delta
		'\u03B5': '$\\epsilon$', ## epsilon
		'\u03B8': '$\\theta$',   ## theta
		'\u03BB': '$\\lambda$',  ## lambda
		'\u03BC': '$\\mu$',      ## mu
		'\u03C0': '$\\pi$',      ## pi
		'\u03C1': '$\\rho$',     ## rho
		'\u03C3': '$\\sigma$',   ## sigma
		'\u03C4': '$\\tau$',     ## tau
		'\u03D5': '$\\upsilon$', ## upsilon
		'\u03C6': '$\\phi$',     ## phi
		'\u03C7': '$\\chi$',     ## chi
		'\u03C8': '$\\psi$',     ## psi
		'\u03C9': '$\\omega$',   ## omega
		'\u0393': '$\\Gamma$',   ## Gamma
		'\u0398': '$\\Theta$',   ## Theta
		'\u039B': '$\\Lambda$',  ## Lambda
		'\u039E': '$\\Xi$',      ## Xi
		'\u03A0': '$\\Pi$',      ## Pi
		'\u03A3': '$\\Sigma$',   ## Sigma
		'\u03A6': '$\\Phi$',     ## Phi
		'\u03A8': '$\\Psi$',     ## Psi
		'\u03A9': '$\\Omega$',   ## Omega
	}
	for _ch, _eq in _UNICODE_A_LATEX.items():
		md_texto = md_texto.replace(_ch, _eq)

	## TABLAS MARKDOWN (| a | b |) => <latex_table> (template estandar: tabular
	## con reglas verticales, header y filas coloreadas, table[H] centrada).
	## Se corre ANTES de la regla <latex_table> de abajo para reutilizar table_sub.
	## Convenciones:
	## -- caption opcional: la linea **bold** inmediatamente antes de la tabla
	##    pasa a ser el \caption (y se quita del cuerpo).
	## -- celdas soportan `mono`, **negrita**, *cursiva* y $matematica$
	##    (la matematica, el '%' y el unicode ya vienen procesados aqui).
	## -- si alguna columna es larga se usa tabularx{\textwidth} con columnas X
	##    para que el texto envuelva en vez de desbordar la pagina.
	RE_TAB = re.compile(r'^\s*\|.*\|\s*$')
	RE_SEP = re.compile(r'^\s*\|[\s:\-|]+\|\s*$')
	RE_CAP_BOLD = re.compile(r'^\s*\*\*(.+?)\*\*\s*$')

	def _celda_tex(celda):
		## El contenido de la tabla queda protegido (placeholder) ANTES de las
		## reglas globales de '%', unicode y '_', asi que se procesan aqui.
		c = celda.strip()
		c = c.replace('%', '\\%')
		for _ch, _eq in _UNICODE_A_LATEX.items():
			c = c.replace(_ch, _eq)
		c = re.sub(r'`(.*?)`', r'\\texttt{\1}', c)
		c = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', c)
		c = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\\textit{\1}', c)
		c = c.replace('_', '\\_')
		return c

	def _split_filas(linea_tabla):
		return [_celda_tex(c) for c in linea_tabla.strip().strip('|').split('|')]

	def _cuerpo_tabula(cab, filas):
		if filas:
			anchos = [max(len(c) for c in col) for col in zip(cab, *filas)]
		else:
			anchos = [len(c) for c in cab]
		longas = [a > 30 for a in anchos]
		if any(longas):
			spec = ' | '.join('X' if lg else 'c' for lg in longas)
			env_in = f"\\begin{{tabularx}}{{\\textwidth}}{{|{spec}|}}"
			env_out = "\\end{tabularx}"
		else:
			env_in = f"\\begin{{tabular}}{{|{' | '.join(['c'] * len(cab))}|}}"
			env_out = "\\end{tabular}"
		out = [env_in, "\\hline"]
		out.append("\\rowcolor{tabColorHdr_085}\n    " + " & ".join(cab) + " \\\\ \\hline")
		for f in filas:
			out.append("\\rowcolor{tabColor}" + " & ".join(f) + " \\\\ \\hline")
		out.append(env_out)
		return "\n".join(out)

	_tab_lineas = md_texto.split('\n')
	_tab_nuevas = []
	_tab_i = 0
	while _tab_i < len(_tab_lineas):
		_l = _tab_lineas[_tab_i]
		if RE_TAB.match(_l) and _tab_i + 1 < len(_tab_lineas) and RE_SEP.match(_tab_lineas[_tab_i + 1]):
			_cab = _split_filas(_l)
			_tab_i += 2
			_filas = []
			while _tab_i < len(_tab_lineas) and RE_TAB.match(_tab_lineas[_tab_i]) and not RE_SEP.match(_tab_lineas[_tab_i]):
				_filas.append(_split_filas(_tab_lineas[_tab_i]))
				_tab_i += 1
			_cap = ""
			## caption: linea **bold** previa a la tabla (se saltan blanks).
			_k = len(_tab_nuevas) - 1
			while _k >= 0 and _tab_nuevas[_k].strip() == "":
				_k -= 1
			if _k >= 0 and RE_CAP_BOLD.match(_tab_nuevas[_k]):
				_cap = _celda_tex(RE_CAP_BOLD.match(_tab_nuevas[_k]).group(1))
				del _tab_nuevas[_k:]
			_tab_nuevas.append(f'<latex_table cap="{_cap}" lbl="">\n{_cuerpo_tabula(_cab, _filas)}\n</latex_table>')
			continue
		_tab_nuevas.append(_l)
		_tab_i += 1
	md_texto = '\n'.join(_tab_nuevas)
	pattern_tab = r'<latex_table\s+cap=["\'](.*?)["\']\s+lbl=["\'](.*?)["\']\s*>(.*?)</latex_table>'
	def table_sub(match):
		caption_text = match.group(1).strip()
		label_text = match.group(2).strip()
		tabla_interna = match.group(3).strip('\n\r')
		tabla_limpia = tabla_interna.replace(r'\begin{center}', '').replace(r'\end{center}', '')
		caption_ln = f"\\caption{{{caption_text}}}\n" if caption_text else ""
		label_ln = f"\\label{{{label_text}}}\n" if label_text else ""
		latex_table_str = (
			f"\\begin{{table}}[H]\n"
			f"\\centering\n"
			f"{tabla_limpia}\n"
			f"{caption_ln}"
			f"{label_ln}"
			f"\\end{{table}}"
		)
		class FakeMatch:
			def __init__(self, val): self.val = val
			def group(self, num): return self.val
		return placeholder(FakeMatch(latex_table_str))
	md_texto = re.sub(pattern_tab, table_sub, md_texto, flags=re.DOTALL)


	# 1. Aislar bloques de código y ecuaciones
	md_texto = re.sub(r'<code([^>]*?)>(.*?)</code>', code_placeholder, md_texto, flags=re.DOTALL)
	## Span `mono`: proteger ANTES de la regla de matematica. Un '$' de script
	## ('$i', 'ca_cnt($bc)') se escaparia mal: la regla \$...\$ empareja '$' que
	## estan en spans distintos o los deja sueltos. El '_' se escapa a mano:
	## dentro del placeholder ya no llega el reemplazo global.
	def _tick_protect(m):
		c = m.group(1).replace('$', '\\$').replace('_', '\\_')
		key = f"MATHBLOCKX{len(math_blocks)}X"
		math_blocks[key] = chr(92) + 'texttt{' + c + '}'
		return key
	md_texto = re.sub(r'`([^`]+)`', _tick_protect, md_texto)
	md_texto = re.sub(r'\$\$.*?\$\$', placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$.*?\$', placeholder, md_texto)
	## '$' sin pareja (ej: '$i' de scripts TCL en el texto): la regla anterior
	## solo protege pares; los impares quedarian literales y rompen la compilacion
	## ('Missing $ inserted'). Aca se escapan (los placeholders ya no traen '$').
	md_texto = md_texto.replace('$', '\\$')
	
	# 🔥 NUEVA LÍNEA: Proteger comandos de control LaTeX con llaves (ej: \ref{...}, \pageref{...}, \label{...})
	# Esto evita que el reemplazo de guiones bajos rompa los identificadores internos.
	md_texto = re.sub(r'\\[a-zA-Z]+\{[^{}]+\}', placeholder, md_texto)
	## fgrLib_v2: escapar '%' del texto comun. Un '%' libre abre comentario de
	## LaTeX y traga el resto de la linea (llaves sin cerrar => 'Missing }'
	## inserted' en el \end del bloque). Se aplica aqui (placeholder de
	## matematica/codigo/<latex> ya puestos) y ANTES de backticks/titulos,
	## que si no sus '%' quedarian sin escapar al restaurarse al final.
	md_texto = md_texto.replace('%', '\\%')

	# 2. Eliminación de contenido invisible
	md_texto = re.sub(r'(?m)^#*\s*<invisible>.*?</invisible>\s*\n?', '', md_texto, flags=re.DOTALL)

	md_texto = re.sub(r'\\begin{figure}.*?\\end{figure}', placeholder, md_texto, flags=re.DOTALL)


	# 3. Escapar guiones bajos del texto común
	################################################md_texto = md_texto.replace('_', '\\_') 

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

	pattern_merge = r'</answer>\s*<answer>'
	while re.search(pattern_merge, md_texto, flags=re.DOTALL):
		md_texto = re.sub(pattern_merge, '\n', md_texto, flags=re.DOTALL)

	md_texto = re.sub(r'<answer>(.*?)</answer>', r'\\begin{answer}\n\1\n\\end{answer}', md_texto, flags=re.DOTALL)

	md_texto = md_texto.replace('&nbsp;', '~')
	md_texto = md_texto.replace('&ensp;', '\\quad ')   
	md_texto = md_texto.replace('&emsp;', '\\qquad ')  

	# Saltos de línea y reglas
	md_texto = re.sub(r'^\s*</?br\s*/?>\s*$', fr'~\\par\\vspace*{{{ESP_BREAK}}}', md_texto, flags=re.M | re.IGNORECASE)
	md_texto = re.sub(r'</?br\s*/?>', r'\\\\ ', md_texto, flags=re.IGNORECASE)
	md_texto = re.sub(r'^---\s*$', r'\\hrule\n\\vspace{0.4cm}', md_texto, flags=re.M)

	# Listas (bullets y numeradas): se resuelve linea a linea, como un visor
	# de markdown clasifica cada linea por su prefijo. Sin sentinels ni
	# envoltorios por regex a texto completo.
	def _conv_listas(txt):
		BS = chr(92)  # backslash literal, sin ambiguedad de escapes
		pat_num = re.compile(r'^\s*(\d+)\.\s+(\S.*)$')
		pat_bul = re.compile(r'^\s*[*\-]\s+(.*)$')
		lineas = txt.split("\n")
		out = []
		modo = None  # "num" | "bul" | None
		def cerrar():
			nonlocal modo
			if modo == "num":
				out.append(BS + "end{enumerate}")
			elif modo == "bul":
				out.append(BS + "end{itemize}")
			modo = None
		for ln in lineas:
			mn = pat_num.match(ln)
			mb = pat_bul.match(ln)
			if mn:
				if modo != "num":
					cerrar()
					out.append(BS + "begin{enumerate}")
					out.append(BS + "setcounter{enumi}{" + str(int(mn.group(1)) - 1) + "}")
					modo = "num"
				out.append(BS + "item " + mn.group(2))
			elif mb:
				if modo != "bul":
					cerrar()
					out.append(BS + "begin{itemize}")
					modo = "bul"
				out.append(BS + "item " + mb.group(1))
			else:
				cerrar()
				out.append(ln)
		cerrar()
		return "\n".join(out)
	md_texto = _conv_listas(md_texto)
	md_texto = re.sub(r'\\ref\{[^{}]+\}', placeholder, md_texto)
	md_texto = md_texto.replace('_', '\\_') 

	# Restauración final de placeholders
	for _ in range(2):
		for key, original_content in math_blocks.items():
			md_texto = md_texto.replace(key, original_content)
		
	return md_texto




def procesar_notebook_completo(verbose=False):
	"""Recorre el notebook en dos pasadas:
	Pasada 1: Infere cada bloque desde el FUENTE de las celdas (prefijo de
	          Informe("<prefijo>") + contador) y lee su contenido procesado del
	          archivo que out() escribio en ipynb.out (NNNN_xxxx_iiii.tex),
	          agrupandolo por prefijo en memoria.
	Pasada 2: Toma el Markdown consolidado de cada familia (NNNN_xxxx), lo traduce de un
	          solo viaje (lo que mergea los <answer> contiguos) y genera un NUEVO archivo
	          intermedio consolidado.
	"""
	nombre_notebook = get_this_ipynb_filename()
	
	with open(nombre_notebook, "r", encoding="utf-8") as f:
		cells = json.load(f)["cells"]
		
	# Diccionario para agrupar el Markdown por prefijo base
	bloques_unificados = {}  # Clave: "0001_answer" -> Valor: [lista de bloques md]
	orden_prefijos = []      # Guarda el orden cronológico de los prefijos

	archivos_originales_count = 0
	archivos_intermedios_count = 0

	carpeta_salida = os.path.abspath(os.path.join(os.getcwd(), "ipynb.out"))
	os.makedirs(carpeta_salida, exist_ok=True)

	# ==========================================================================
	# PASADA 1: LECTURA DE BLOQUES (escritos por out()) Y AGRUPAMIENTO POR PREFIJO
	# ==========================================================================
	## El nombre del bloque se INFERE del FUENTE de la celda: el prefijo de
	## Informe("<prefijo>") + un contador por prefijo que espeja el _count real.
	## Convenio: 1 celda => N out()/img() (se procesan en orden de aparicion,
## uno por bloque, y el filename de cada llamada es un LITERAL).
	## El CONTENIDO se lee de ipynb.out/<nombre>.tex (out() lo escribio con los
	## tokens ya sustituidos y los tags aplicados); el output del notebook es
	## solo un preview y no se usa para nada.
	counters = {}            ## prefijo -> siguiente indice
	prefijo_corriente = None ## ultimo Informe("<prefijo>") visto en el fuente

	for cell in cells:
		fuente_celda = "".join(cell["source"])
		## Quitar comentarios de linea (# ...): el fuente de celdas que SOLO
		## documenta (ej: la celda de protocolo) no debe activar bloques.
		fuente_celda = chr(10).join(
			l.split("#")[0] for l in fuente_celda.splitlines())

		if cell["cell_type"] == "code":
			m_pref = re.search(r'\bInforme\(\s*["\']([^"\']+)["\']', fuente_celda)
			if m_pref:
				## Instancia nueva => su contador arranca en 0 (como el _count real).
				counters[m_pref.group(1)] = 0
				prefijo_corriente = m_pref.group(1)
			for m_out in re.finditer(r'\.\s*(?:out|img)\(\s*["\']([^"\']+)["\']', fuente_celda):
				if prefijo_corriente is None:
					print(f"⚠ Celda con out() pero sin Informe('<prefijo>') visible: bloque ignorado (out(\"{m_out.group(1)}\")).", flush=True)
					break
				idx = counters.get(prefijo_corriente, 0)
				counters[prefijo_corriente] = idx + 1
				nombre_tex = f"{prefijo_corriente}_{idx:04d}.tex"
				ruta_bloque = os.path.join(carpeta_salida, nombre_tex)
				if not os.path.exists(ruta_bloque):
					raise FileNotFoundError(
						f"No existe {ruta_bloque}: el notebook debio ejecutarse antes de extraer.")
				with open(ruta_bloque, "r", encoding="utf-8") as f:
					bloque_md = f.read().strip("\n")
				archivos_originales_count += 1
				if verbose:
					print(f"☑ Original leído: {ruta_bloque}")
				if prefijo_corriente not in bloques_unificados:
					bloques_unificados[prefijo_corriente] = []
					orden_prefijos.append(prefijo_corriente)
				bloques_unificados[prefijo_corriente].append(bloque_md + "\n\n")

		elif cell["cell_type"] == "markdown":
			## Celda markdown "suelta" (sin out()): se agrega al grupo abierto
			## mas reciente (solo afecta al archivo intermedio consolidado).
			texto_md = "".join(cell["source"])
			if texto_md.strip() and orden_prefijos:
				bloques_unificados[orden_prefijos[-1]].append(texto_md + "\n\n")


	# ==========================================================================
	# PASADA 2: GENERACIÓN DE ARCHIVOS INTERMEDIOS CONSOLIDADOS
	# ==========================================================================
	for prefijo in orden_prefijos:
		contenido_acumulado = "".join(bloques_unificados[prefijo])
		if not contenido_acumulado.strip():
			continue
			
		# Pasamos el bloque entero. Aquí tu regex de 'traducir_a_latex' 
		# va a unificar todos los <answer> contiguos en un único entorno.
		latex_consolidado = traducir_a_latex(contenido_acumulado)
		
		# Creamos el nuevo archivo intermedio (Ej: 0001_answer.tex)
		ruta_archivo_intermedio = os.path.join(carpeta_salida, f"{prefijo}.tex")
		
		with open(ruta_archivo_intermedio, "w", encoding="utf-8") as f_out:
			f_out.write(latex_consolidado)
			
		archivos_intermedios_count += 1
		if verbose:
			print(f"⛭ Generado Intermedio Consolidado: {ruta_archivo_intermedio}")

	if not verbose:
		print(f"☑ Proceso de extracción completo. Originales: {archivos_originales_count} | Nuevos Intermedios: {archivos_intermedios_count}")


#===============================================================================
#===============================================================================

def _leer_linea_archivo(archivo, linea, dir_base):
	"""
	Retorna el contenido de la 'linea' del 'archivo' si se puede resolver en disco
	(acepta rutas relativas al dir de compilacion o al cwd). Sirve para mostrar
	al usuario el fragmento exacto que esta causando el error de LaTeX.
	"""
	if not archivo or not linea:
		return None
	candidatos = [os.path.normpath(archivo)]
	if not os.path.isabs(archivo):
		candidatos.append(os.path.normpath(os.path.join(dir_base, archivo)))
		candidatos.append(os.path.normpath(os.path.join(os.getcwd(), archivo)))
	for ruta in candidatos:
		try:
			if os.path.isfile(ruta):
				with open(ruta, "r", encoding="utf-8") as f:
					todas = f.readlines()
				if 1 <= int(linea) <= len(todas):
					contenido = todas[int(linea) - 1].rstrip()
					return contenido[:160] + ("..." if len(contenido) > 160 else "")
		except (OSError, ValueError):
			continue
	return None


def _extraer_errores_latex(stdout):
	"""
	Extrae del output de latexmk/pdflatex los errores (archivo, linea, mensaje),
	para los dos formatos que emite pdflatex:
	  - Con -file-line-error : "../ipynb.out/0011_answer_0002.tex:4: Missing $ inserted."
	  - Clasico (nonstopmode): "! Missing $ inserted."
	"""
	patron_fle = re.compile(r'^(?P<archivo>[^\s:()]+?\.(?:tex|sty|cls)):(?P<linea>\d+):\s+(?P<msg>.+)$')
	errores = []
	for linea in (stdout or "").splitlines():
		limpia = linea.strip()
		m = patron_fle.match(limpia)
		if m:
			errores.append((m.group("archivo"), m.group("linea"), m.group("msg")))
		elif limpia.startswith("!"):
			errores.append((None, None, limpia))
	return errores


def _reportar_errores_latex(stdout, stderr, ruta_tex_absoluta):
	"""
	Muestra un reporte util de por que LaTeX no compilo:
	  - Errores concretos: archivo:linea + mensaje del compilador.
	  - El contenido real de la linea incriminada (se lee el .tex generado).
	"""
	MAX_ERRORES = 8
	dir_tex = os.path.dirname(ruta_tex_absoluta)
	
	print("", flush=True)
	print("❌ Error de compilación en LaTeX:", flush=True)
	
	errores = _extraer_errores_latex(stdout)
	vistos = set()
	n = 0
	for archivo, linea, mensaje in errores:
		contenido = _leer_linea_archivo(archivo, linea, dir_tex)
		if contenido:
			clave = (archivo, linea)
		else:
			clave = (archivo, linea, mensaje)
		if clave in vistos:
			continue
		vistos.add(clave)
		if n >= MAX_ERRORES:
			break
		n += 1
		donde = f"[{archivo}:{linea}]" if archivo else "[sin archivo/linea]"
		print(f"  • {donde} — {mensaje}", flush=True)
		if contenido:
					print(f"    {contenido}", flush=True)
	
	if n == 0:
		## Sin lineas de error reconocibles: mostrar el final del output para no perder nada.
		for linea in (stdout or "").splitlines()[-15:]:
			if linea.strip():
				print(f"         {linea.strip()}", flush=True)
		for linea in (stderr or "").splitlines()[-10:]:
			if linea.strip():
				print(f"         {linea.strip()}", flush=True)


#===============================================================================
#===============================================================================

def compilar_pdf_automatico(archivo_principal="tp.tex", clean=True):

	"""Compila el .tex principal a PDF de forma segura y sin colgarse.
	   Retorna True si el PDF se genero, False si la compilacion fallo
	   (en cuyo caso se muestra un reporte de errores con archivo/linea/mensaje)."""
	if not os.path.exists(archivo_principal):
		print(f"⚠ No se encontró el archivo '{archivo_principal}' para compilar.")
		return False

	# Verificar si latexmk está instalado en el PATH del sistema
	if not shutil.which("latexmk"):
		print("❌ Error: 'latexmk' no está instalado o no se encuentra en el PATH de Windows.")
		return False

	# 1. Separar el directorio y el nombre del archivo para fijar la ruta relativa
	dir_trabajo = os.path.dirname(archivo_principal)
	nombre_base = os.path.basename(archivo_principal)
	cwd_destino = dir_trabajo if dir_trabajo else None

	print(f"⛭ Compilando '{archivo_principal}' con latexmk...")
	try:
		# Ejecuta el comando de compilación con latexmk de forma controlada
		resultado = subprocess.run(
			["latexmk", "-g", "-synctex=0", "-interaction=nonstopmode", "-file-line-error", "-pdf", nombre_base],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			encoding="utf-8",      ## El output trae bytes ajenos a cp1252.
			errors="replace",      ## ...que crasheaban el decode y 'colgaban' la pasada.
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

			return True

		else:
			## Reporte util: que archivo, que linea, que mensaje, y donde corregir.
			_reportar_errores_latex(resultado.stdout, resultado.stderr, archivo_principal)
			return False
			
	except subprocess.TimeoutExpired:
		print("❌ La compilación tardó demasiado y fue interrumpida de forma segura para evitar cuelgues.")
		return False
	except Exception as e:
		print(f"❌ Ocurrió un error inesperado al lanzar pdflatex: {e}")
		return False


#===============================================================================
# Para armar todo desde un script usando la consola
#===============================================================================




def procesar_y_compilar_informe(nombre_notebook, texFile, clean): 
	## fgrLib_v2: no dejar que el charset de la consola (cp1252 en Windows) crashee los prints.
	for _stream in (sys.stdout, sys.stderr):
		try:
			_stream.reconfigure(errors="replace")
		except Exception:
			pass
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

	## Borra fantasmas de corridas crashadas (si existian, el os.rename del
	## intercambio en caliente del espejo fallaba con FileExistsError).
	for _ghost in ("ipynb.out_original_bak", "ipynb.out_compile"):
		_ruta_ghost = os.path.abspath(os.path.join(base_dir, _ghost))
		if os.path.exists(_ruta_ghost):
			shutil.rmtree(_ruta_ghost)
			print(f"♻ Limpieza inicial: {_ghost} (fantasma) eliminada.", flush=True)

	# Convertir la ruta del .tex a RUTA ABSOLUTA para evitar bloqueos de Windows 
	ruta_tex_absoluta = os.path.abspath(os.path.join(base_dir, "latex", texFile)) 
	
	print(f"⛭ Ejecutando Notebook: {nombre_notebook}...", flush=True) 
	try: 
		with open(nombre_notebook, "r", encoding="utf-8") as f: 
			nb = nbformat.read(f, as_version=4) 
		# >>> fgrLib_v2: inyectar celda de setup (sys.path + import de Informe).
		## Se quita despues de ejecutar para que no quede guardada en el notebook.
		celda_setup = nbformat.v4.new_code_cell(source=(
			"import sys as _sys_fgrv2\n"
			f"_sys_fgrv2.path.insert(0, {LIB_DIR!r})\n"
			"from fgrLib_v2 import Informe\n"
		))
		nb.cells.insert(0, celda_setup)
			
		ep = ExecutePreprocessor(timeout=10, kernel_name="python3") 
		ep.preprocess(nb, {'metadata': {'path': base_dir}}) 
		# >>> fgrLib_v2: quitar la celda de setup (no debe quedar en el notebook).
		nb.cells.pop(0)
		
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
		print("⛭ Estructurando entorno de compilación temporal en espejo...", flush = True)
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
	
	codigo_salida = 0  ## 0 = compilo ok | 1 = la compilacion de LaTeX fallo.
	try:
		import gc 
		gc.set_threshold(0) 

		## Invocamos la compilación. LaTeX leerá la carpeta 'ipynb.out' modifica
		## a temporalmente.
		print("⛭ Pasada 1/2...", flush = True)	## Doble pasada p/ paquete "las
			## tpage". Pasada 1: genera auxiliar. Me aseguro con clean = 0 que e
			## n esta pasada auxiliar no se borran los archivos temporales.
		if compilar_pdf_automatico(ruta_tex_absoluta, 0):
			print("⛭ Pasada 2/2...", flush = True)	# Pasada 2: Lee el auxiliar y a
			## plica el número de paginas final.
			if not compilar_pdf_automatico(ruta_tex_absoluta, clean):
				codigo_salida = 1
		else:
			print("⛭ La pasada 1/2 fallo: se omite la pasada 2/2 (ver el reporte de errores arriba).", flush = True)
			codigo_salida = 1

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
	os._exit(codigo_salida)
