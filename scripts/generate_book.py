#!/usr/bin/env python3
"""
AI 对话录 — LaTeX 出版脚本 v2 (XeLaTeX)

按时间顺序排列所有 Q&A 单元，标注 session。每个"我提问→AI回答"为最小单元。
用法:  uv run python scripts/generate_book.py
       cd book && bash compile.sh
"""

import json, os, re, sys
from datetime import datetime

EMOJI = re.compile('[' '\U0001F000-\U0002FFFF\U0000E000-\U0000F8FF'
    '\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0000200D'
    '\U00002B50\U00002764\U0000203C\U00002049'
    '\U000000A9\U000000AE\U00002122\U00003030\U0000303D'
    ']')

def strip_ctrl(t):
    return ''.join(c for c in t if c in '\n\r\t' or ord(c) >= 32)

def latex_escape(t):
    t = strip_ctrl(t); t = EMOJI.sub('', t)
    t = t.replace('\\','\\textbackslash{}').replace('{','\\{').replace('}','\\}')
    t = t.replace('$','\\$').replace('&','\\&').replace('%','\\%').replace('#','\\#')
    t = t.replace('_','\\_').replace('^','\\textasciicircum{}').replace('~','\\textasciitilde{}')
    t = t.replace('|','\\textbar{}').replace('<','\\textless{}').replace('>','\\textgreater{}')
    return t

def fmt_ts(ts):
    if not ts: return ''
    try:
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    except: pass
    try:
        if isinstance(ts, (int,float)):
            return datetime.fromtimestamp(ts/1000 if ts>1e12 else ts).strftime('%Y-%m-%d %H:%M:%S')
    except: pass
    return str(ts)[:19]

def md_inline(text):
    """对单行文本做 markdown 转换（粗体/斜体/行内代码）+ latex_escape"""
    codes = []
    text = re.sub(r'`([^`]+)`', lambda m: codes.append(m.group(1)) or f'!!C{len(codes)-1}!!', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'!!B!!\1!!B!!', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'!!I!!\1!!I!!', text)
    text = latex_escape(text)
    text = re.sub(r'!!B!!(.+?)!!B!!', lambda m: r'\textbf{' + m.group(1) + '}', text)
    text = re.sub(r'!!I!!(.+?)!!I!!', lambda m: r'\textit{' + m.group(1) + '}', text)
    for i, c in enumerate(codes):
        text = text.replace(f'!!C{i}!!', r'\texttt{' + latex_escape(c) + '}')
    return text

def format_content(text):
    """Markdown → LaTeX（粗体/斜体/代码/标题）+ latex_escape"""
    if not text: return ''
    text = strip_ctrl(text); text = EMOJI.sub('', text)
    lines = text.split('\n'); result = []; in_code = False; in_table = False
    for line in lines:
        if line.startswith('```'):
            if in_table: result.append(r'\end{tabular}\par'); in_table = False
            result.append(r'\end{quote}' if in_code else r'\begin{quote}\small')
            in_code = not in_code; continue
        # 检测 markdown 表格
        if re.match(r'^\|.*\|$', line.strip()):
            if not in_table:
                in_table = True
                # 初始化表格：先存表头行，下一行是分隔符用于确定列数
                table_header = line
                table_sep = None
                table_rows = []
                continue
            else:
                # 检查是否是分隔符行
                if re.match(r'^\|\s*[\-:]+\s*\|', line.strip()):
                    table_sep = line
                    continue
                else:
                    table_rows.append(line)
                    continue
        if in_table:
            # 表格结束，输出
            if table_sep:
                cols = table_sep.count('|') - 1
                # 确定对齐方式
                aligns = []
                parts = table_sep.strip().split('|')[1:-1]
                for p in parts:
                    p = p.strip()
                    if p.startswith(':') and p.endswith(':'): aligns.append('c')
                    elif p.endswith(':'): aligns.append('r')
                    elif p.startswith(':'): aligns.append('l')
                    else: aligns.append('l')
                col_fmt = ''.join(aligns) if aligns else 'l' * cols
                result.append(r'\par\medskip\noindent{\small\resizebox{\linewidth}{!}{\begin{tabular}{' + col_fmt + r'}')
                # 表头
                hdr_cells = [md_inline(c.strip()) for c in table_header.strip().split('|')[1:-1]]
                result.append(r'\hline ' + ' & '.join(hdr_cells) + r' \\ \hline')
                for r in table_rows:
                    cells = [md_inline(c.strip()) for c in r.strip().split('|')[1:-1]]
                    result.append(' & '.join(cells) + r' \\')
                result.append(r'\hline\end{tabular}}}\par\medskip')
            in_table = False

        if in_code:
            result.append(latex_escape(line))
        else:
            codes = []
            line = re.sub(r'`([^`]+)`', lambda m: codes.append(m.group(1)) or f'!!C{len(codes)-1}!!', line)
            line = re.sub(r'\*\*(.+?)\*\*', r'!!B!!\1!!B!!', line)
            line = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'!!I!!\1!!I!!', line)
            line = re.sub(r'^#{1,3}\s+(.+)$', r'!!H!!\1', line)
            line = re.sub(r'^\s*---+\s*$', '!!R!!', line)
            line = latex_escape(line)
            line = re.sub(r'!!B!!(.+?)!!B!!', lambda m: r'\textbf{' + m.group(1) + '}', line)
            line = re.sub(r'!!I!!(.+?)!!I!!', lambda m: r'\textit{' + m.group(1) + '}', line)
            line = re.sub(r'!!H!!(.+)', lambda m: r'\noindent\textbf{' + m.group(1) + '}', line)
            line = line.replace('!!R!!', r'\par\medskip\hrule\medskip\par')
            for i, c in enumerate(codes):
                line = line.replace(f'!!C{i}!!', r'\texttt{' + latex_escape(c) + '}')
            result.append(line)
    if in_code: result.append(r'\end{quote}')
    return '\n'.join(result)


def build_qa_units(data):
    """将对话展平为 Q&A 单元列表"""
    units = []
    for conv in data['conversations']:
        session_file = conv.get('source_file', '')
        session_title = session_file.replace('.json', '') if session_file else ''
        model = conv.get('model', 'Unknown')
        msgs = conv.get('messages', [])
        i = 0
        while i < len(msgs):
            if msgs[i].get('role') == 'user':
                user_msg = msgs[i]
                user_ts = user_msg.get('created_at')
                # 找之后第一个非 thinking 的消息
                j = i + 1
                think_msgs = []
                while j < len(msgs):
                    r = msgs[j].get('role')
                    if r == 'thinking':
                        think_msgs.append(msgs[j])
                    elif r == 'assistant':
                        break
                    elif r == 'user':
                        j -= 1
                        break
                    j += 1
                if j < len(msgs) and msgs[j].get('role') == 'assistant':
                    units.append((user_ts, session_title, session_file, model, user_msg, msgs[j], think_msgs))
                    i = j + 1
                else:
                    units.append((user_ts, session_title, session_file, model, user_msg, None, think_msgs))
                    i = j + 1
            else:
                i += 1
    # 按时间戳排序
    def sort_key(u):
        ts = u[0]
        if isinstance(ts, str): return ts
        if isinstance(ts, (int,float)): return str(ts)
        return ''
    units.sort(key=sort_key)
    return units


def generate_book(data, output_dir):
    units = build_qa_units(data)
    total = len(units)

    os.makedirs(output_dir, exist_ok=True)
    L = []

    # Preamble
    L.extend([
        r'% !TEX program = xelatex',
        r'\documentclass[10pt,a5paper,twoside]{book}',
        r'\usepackage{ctex}',
        r'\usepackage[margin=1.8cm,top=2.5cm,bottom=2.5cm,headsep=0.5cm]{geometry}',
        r'\usepackage{fancyhdr}', r'\usepackage{xcolor}', r'\usepackage{titlesec}',
        r'\usepackage{tocloft}', r'\usepackage{hyperref}', r'\usepackage{setspace}',
        r'\usepackage{enumitem}', r'\usepackage{bookmark}', r'\usepackage{needspace}',
        r'\usepackage{fontspec}',
        r'\usepackage{graphicx}',
        r'\setmainfont{Times New Roman}', r'\setmonofont{Menlo}',
        r'\setCJKmainfont{Songti SC}',
        r'\definecolor{themecolor}{HTML}{3B82F6}',
        r'\definecolor{chatgptcolor}{HTML}{10A37F}',
        r'\definecolor{geminicolor}{HTML}{8B5CF6}',
        r'\definecolor{usercolor}{HTML}{1E40AF}',
        r'\definecolor{userbg}{HTML}{EFF6FF}',
        r'\definecolor{thinkbg}{HTML}{FFFBEB}',
        r'\definecolor{thinkcolor}{HTML}{92400E}',
        r'\hypersetup{colorlinks=true,linkcolor=themecolor,urlcolor=themecolor}',
        r'\pagestyle{fancy}', r'\fancyhf{}',
        r'\fancyhead[LE]{\small\leftmark}', r'\fancyhead[RO]{\small\rightmark}',
        r'\fancyfoot[LE,RO]{\thepage}', r'\renewcommand{\headrulewidth}{0.4pt}',
        r'\titleformat{\chapter}[display]{\normalfont\huge\bfseries\color{themecolor}}{\chaptertitlename\ \thechapter}{20pt}{\Huge}',
        r'\titlespacing*{\chapter}{0pt}{-20pt}{20pt}', r'\setstretch{1.15}',
        r'\setlength{\parindent}{0pt}', r'\setlength{\parskip}{3pt}',
        r'\tolerance=5000', r'\emergencystretch=3em', r'\sloppy',
        # 会话标记
        r'\newcommand{\qapair}[5]{%',
        r'  \par\medskip',
        r'  \noindent\textcolor{usercolor}{\small\textbf{我}~\textit{#1}}',
        r'  \hfill\small\textcolor{gray}{#5}\par',
        r'  {\leftskip=1em\relax\small\raggedright #2\par}',
        r'  \par\medskip',
        r'  \noindent\textcolor{#3}{\small\textbf{#4}}',
        r'  \par\noindent',
        r'}',
        r'\newcommand{\sessionmark}[1]{%',
        r'  \par\bigskip',
        r'  \noindent\textcolor{themecolor}{\large\textbf{> #1}}',
        r'  \par\medskip',
        r'}',
        r'\newcommand{\thinking}[1]{%',
        r'  \par\medskip',
        r'  \noindent\textcolor{thinkcolor}{\small\textbf{[Gemini 推理过程]}}',
        r'  \par',
        r'  {\leftskip=1em\relax\footnotesize\itshape\raggedright #1\par}',
        r'  \par\medskip',
        r'}',
        r'\renewenvironment{quote}{%',
        r'  \par\medskip\noindent\textit{--- code ---}\par',
        r'  \footnotesize\ttfamily\setstretch{1.0}\raggedright\noindent\ignorespaces}{%',
        r'  \normalsize\par\medskip}',
        r'\begin{document}',
    ])

    # Cover
    dates = [fmt_ts(u[0]) for u in units if u[0]]
    span = dates[0][:7] + ' ~ ' + dates[-1][:7] if len(dates)>=2 else ''
    chatgpt = sum(1 for c in data['conversations'] if c['model']=='ChatGPT')
    gemini = len(data['conversations']) - chatgpt
    L.extend([
        r'\begin{titlepage}', r'\centering', r'\vspace*{2cm}',
        r'{\Huge\bfseries\color{themecolor} AI 对话录}\\[12pt]',
        r'{\Large\color{gray} 一篇学术论文背后的 AI 辅助科研记录}\\[24pt]',
        r'\rule{0.6\textwidth}{1pt}\\[24pt]',
        r'{\large 论文：\textbf{A Hierarchical Multimodal Feature Fusion Physical-Layer \\',
        r'Key Generation Scheme for Non-Reciprocal Channels}}\\[24pt]',
        r'\rule{0.6\textwidth}{1pt}\\[24pt]',
        fr'\textbf{{{total}}} 次问答  ·  {span}\\[8pt]',
        fr'ChatGPT \textcolor{{chatgptcolor}}{{{chatgpt}}} / Gemini \textcolor{{geminicolor}}{{{gemini}}}\\[24pt]',
        r'\vfill', r'{\large 编于 \today}\\[12pt]', r'\end{titlepage}',
        r'\tableofcontents',
        r'\chapter*{引言}', r'\addcontentsline{toc}{chapter}{引言}',
        r'这篇论文从投稿到接收，经历了一年多的修改与打磨。',
        r'AI 大模型作为学术伙伴，参与了从构思、撰写、润色到审稿回复的每一个环节。',
        fr'本书按照时间顺序收录了 {total} 次问答（{chatgpt} 次来自 ChatGPT，{gemini} 次来自 Gemini），',
        r'以「我提问 → AI 回答」为最小单元排列，完整记录了一篇学术论文从初稿到接收的 AI 辅助历程。',
    ])

    # 按月分组 Q&A 单元
    month_units = {}  # YYYY-MM -> [(ts, sess_title, ...), ...]
    for u in units:
        ts_str = fmt_ts(u[0])
        month_key = ts_str[:7] if len(ts_str) >= 7 else 'unknown'
        month_units.setdefault(month_key, []).append(u)

    sorted_months = sorted(month_units.keys())

    for month_key in sorted_months:
        # 章节标题：2025年6月
        year, mo = month_key.split('-')
        chapter_title = f'{year}年{int(mo)}月'
        L.append(f'\\chapter{{{chapter_title}}}')

        last_session = None
        for u in month_units[month_key]:
            ts, sess_title, sess_file, model, user_msg, asst_msg, think_msgs = u
            ts_str = fmt_ts(ts)
            model_color = 'chatgptcolor' if model == 'ChatGPT' else 'geminicolor'

            if sess_title != last_session:
                L.append(f'\\sessionmark{{{latex_escape(sess_title)}}}')
                last_session = sess_title

            user_content = format_content(user_msg.get('content',''))
            L.append(f'\\qapair{{{ts_str}}}{{{user_content}}}{{{model_color}}}{{{model}}}{{{latex_escape(sess_title)}}}')

            for tm in think_msgs:
                tc = format_content(tm.get('content',''))
                L.append(f'\\thinking{{{tc}}}')

            if asst_msg:
                L.append(format_content(asst_msg.get('content','')))
        L.append(r'\par\medskip')

    L.append(r'\end{document}')

    main_path = os.path.join(output_dir, 'main.tex')
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print(f'  ✓ main.tex ({len(L)} 行, {total} 个问答单元)')

    with open(os.path.join(output_dir, 'compile.sh'), 'w') as f:
        f.write('#!/bin/bash\ncd "$(dirname "$0")"\nfor i in 1 2 3; do\n  xelatex -interaction=nonstopmode main.tex > /dev/null 2>&1\ndone\necho "DONE: $(pwd)/main.pdf"\n')
    os.chmod(os.path.join(output_dir, 'compile.sh'), 0o755)
    print(f'  ✓ compile.sh')


def main():
    with open('data/conversations.json') as f:
        data = json.load(f)
    print(f'读取 {len(data["conversations"])} 个对话')
    generate_book(data, 'book')
    print('完成！')

if __name__ == '__main__':
    main()
