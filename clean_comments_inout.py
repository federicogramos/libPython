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
