def traducir_a_latex(md_texto):
	ESP_CENTER_H1 = "1.0ex"
	ESP_CENTER_H2 = "0ex"
	ESP_CENTER_H3 = "0ex"
	ESP_CENTER_H4 = "-0.5ex"
	ESP_LEFT_H1   = "1.0ex"
	ESP_LEFT_H2   = "0ex"
	ESP_LEFT_H3   = "0ex"
	ESP_LEFT_H4   = "-0.5ex"
	ESP_PRE_H1    = "3.0ex"   
	ESP_PRE_H2    = "2.5ex"   
	ESP_PRE_H3    = "2.0ex"   
	ESP_PRE_H4    = "1.5ex"   
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
		match_lbl = re.search(r'lbl=["\'](.*?)["\']', atributos)
		if match_lbl:
			label_val = match_lbl.group(1).strip()
			opciones_lst = f"style={estilo},label={label_val}"
		else:
			opciones_lst = f"style={estilo}"
		math_blocks[key] = f"\\begin{{lstlisting}}[{opciones_lst}]\n{codigo_interno}\n\\end{{lstlisting}}"
		return key
	md_texto = re.sub(r'<code([^>]*?)>(.*?)</code>', code_placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$\$.*?\$\$', placeholder, md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\$.*?\$', placeholder, md_texto)
	md_texto = re.sub(r'\\[a-zA-Z]+\{[^{}]+\}', placeholder, md_texto)
	md_texto = re.msub = re.sub(r'(?m)^#*\s*<invisible>.*?</invisible>\s*\n?', '', md_texto, flags=re.DOTALL)
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
	md_texto = md_texto.replace('_', '\\_') 
	md_texto = re.sub(r'<b>(.*?)</b>', r'\\textbf{\1}', md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', md_texto)
	md_texto = re.sub(r'`(.*?)`', r'\\texttt{\1}', md_texto)
	md_texto = re.sub(r'\*(.*?)\*', r'\\textit{\1}', md_texto) 
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
	md_texto = re.sub(r'^####\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \normalsize {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \Large {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+<center>\s*(.*?)\s*</center>$', lambda m: proteger_titulo(fr'\leavevmode{{\centering \LARGE {m.group(1)}\par}}\vspace*{{{ESP_CENTER_H1}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^####\s+(.+)$', lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H4}}}\noindent{{\normalsize {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H4}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^###\s+(.+)$',  lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H3}}}\noindent{{\large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H3}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^##\s+(.+)$',   lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H2}}}\noindent{{\Large {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H2}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'^#\s+(.+)$',    lambda m: proteger_titulo(fr'\vspace*{{{ESP_PRE_H1}}}\noindent{{\LARGE {m.group(1)}\par}}\vspace*{{{ESP_LEFT_H1}}}'), md_texto, flags=re.M)
	md_texto = re.sub(r'<center>(.*?)</center>', fr'{{\\centering \1\\par}}\vspace*{{{ESP_CENTER_GENERIC}}}', md_texto, flags=re.DOTALL)
	pattern_merge = r'</problem>\s*<problem>'
	while re.search(pattern_merge, md_texto, flags=re.DOTALL):
		md_texto = re.sub(pattern_merge, '\n', md_texto, flags=re.DOTALL)
	md_texto = re.sub(r'<problem>(.*?)</problem>', r'\\begin{problem}\n\1\n\\end{problem}', md_texto, flags=re.DOTALL)
	md_texto = md_texto.replace('&nbsp;', '~')
	md_texto = md_texto.replace('&ensp;', '\\quad ')   
	md_texto = md_texto.replace('&emsp;', '\\qquad ')  
	md_texto = re.sub(r'^\s*</?br\s*/?>\s*$', fr'~\\par\\vspace*{{{ESP_BREAK}}}', md_texto, flags=re.M | re.IGNORECASE)
	md_texto = re.sub(r'</?br\s*/?>', r'\\\\ ', md_texto, flags=re.IGNORECASE)
	md_texto = re.sub(r'^---\s*$', r'\\hrule\n\\vspace{0.4cm}', md_texto, flags=re.M)
	md_texto = re.sub(r'^\s*[\*\-]\s+(.+)$', r'\\item \1', md_texto, flags=re.M)
	md_texto = re.sub(r'((?:\\item .+(?:\n|$))+)', r'\\begin{itemize}\n\1\\end{itemize}', md_texto)
	for _ in range(2):
		for key, original_content in math_blocks.items():
			md_texto = md_texto.replace(key, original_content)
	return md_texto
