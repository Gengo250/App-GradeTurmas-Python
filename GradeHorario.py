# -*- coding: utf-8 -*-
"""
Gera a grade (Excel + PDF) a partir de data/professores.csv

• Cada professor só aparece quando marcou disponibilidade.
• Nunca há dois horários simultâneos para o mesmo professor.
• Se não houver professor suficiente, o slot permanece vazio.
• Integração com a interface: ano da turma e quantidade de turmas (rótulos 1A, 1B, ...).
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from textwrap import shorten
import json
import string

import pandas as pd
import numpy as np
from fpdf import FPDF

# ─────────────── CONFIGURAÇÕES BÁSICAS ──────────────── #
root_path   = Path(__file__).resolve().parent
data_path   = root_path / "data"
csv_file    = data_path / "professores.csv"
ui_config   = data_path / "ui_config.json"  # gravado pela GUI

dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira",
               "Quinta-feira", "Sexta-feira", "Sábado"]

horarios_br = ["12h-13h", "13h-14h", "14h-15h", "15h-16h", "16h-17h"]

seed        = 42
txt_vazio   = ""   # o que aparece quando falta professor
cell_w_pdf  = 38   # largura padrão das células no PDF
# ------------------------------------------------------ #

# Parâmetros ativos (podem ser definidos pela GUI)
_PARAM_ANO: Optional[int] = None
_PARAM_QTD: Optional[int] = None
_PARAM_TURMAS: Optional[List[str]] = None


# ╭───────────────────────── SUPORTE A PARÂMETROS ─────────────────────────╮
def _gerar_codigos_turma(ano: int, qtd: int) -> List[str]:
    """Gera rótulos: 1A, 1B, ..., 1Z, 1AA, 1AB, ... conforme 'qtd'."""
    if ano <= 0: ano = 1
    if qtd <= 0: qtd = 1
    letras = string.ascii_uppercase  # A..Z
    codes = []
    i = 0
    while len(codes) < qtd:
        if i < 26:
            sufixo = letras[i]
        else:
            first = (i // 26) - 1
            second = i % 26
            sufixo = letras[first] + letras[second]
        codes.append(f"{ano}{sufixo}")
        i += 1
    return codes


def _carregar_params_de_arquivo() -> Tuple[int, int, List[str]]:
    """Lê ano/qtd/turmas do ui_config.json, ou retorna defaults (ano=1, qtd=10)."""
    ano, qtd = 1, 10
    turmas: List[str] = _gerar_codigos_turma(ano, qtd)
    if ui_config.exists():
        try:
            data = json.loads(ui_config.read_text(encoding="utf-8"))
            ano  = int(data.get("ano", ano))
            qtd  = int(data.get("qtd_turmas", data.get("qtd", qtd)))
            t    = data.get("turmas")
            turmas = t if isinstance(t, list) and len(t) > 0 else _gerar_codigos_turma(ano, qtd)
        except Exception:
            pass
    return ano, qtd, turmas


def _resolver_params(ano: Optional[int], qtd: Optional[int], turmas: Optional[List[str]]) -> Tuple[int, int, List[str]]:
    """Resolve parâmetros a partir de set_params, args, arquivo e defaults."""
    # Prioridade: params explícitos > set_params globais > arquivo > defaults
    a = ano if ano is not None else _PARAM_ANO
    q = qtd if qtd is not None else _PARAM_QTD
    t = turmas if turmas is not None else _PARAM_TURMAS

    if a is not None and q is not None and t:
        return int(a), int(q), list(t)

    if a is not None and q is not None and not t:
        return int(a), int(q), _gerar_codigos_turma(int(a), int(q))

    # cai para arquivo/config
    a2, q2, t2 = _carregar_params_de_arquivo()
    return a if a is not None else a2, q if q is not None else q2, t if t else t2


def set_params(ano: int, qtd: int, turmas: Optional[List[str]] = None) -> None:
    """Permite a GUI setar parâmetros globalmente antes de chamar main()."""
    global _PARAM_ANO, _PARAM_QTD, _PARAM_TURMAS
    _PARAM_ANO = int(ano)
    _PARAM_QTD = int(qtd)
    _PARAM_TURMAS = list(turmas) if turmas else _gerar_codigos_turma(_PARAM_ANO, _PARAM_QTD)
# ╰─────────────────────────────────────────────────────────────────────────╯


# ╭───────────────────────── UTILITÁRIOS ─────────────────────────╮
def carregar_disponibilidade() -> Dict[Tuple[str, str], List[Tuple[int, int]]]:
    """
    Lê o CSV e devolve:
        {(professor, matéria): [(idx_dia, idx_hora), ...]}
    """
    if not csv_file.exists():
        return {}

    df = pd.read_csv(csv_file)
    if df.empty:
        return {}

    mapa_dia   = {dia: i for i, dia in enumerate(dias_semana)}
    mapa_hora  = {h: i for i, h in enumerate(horarios_br)}

    disp: Dict[Tuple[str, str], List[Tuple[int, int]]] = defaultdict(list)
    for row in df.itertuples(index=False):
        dia_idx  = mapa_dia.get(row.Dia)
        hora_idx = mapa_hora.get(row.Horario)
        if dia_idx is not None and hora_idx is not None:
            disp[(row.Professor, row.Materia)].append((dia_idx, hora_idx))
    return disp


def montar_grade(
    disp: Dict[Tuple[str, str], List[Tuple[int, int]]],
    num_turmas: int
) -> np.ndarray:
    """
    Retorna grade [dia, turma, hora] com
        "Matéria (Prof.)"  ou  txt_vazio
    """
    rng = np.random.default_rng(seed)
    grade = np.full((len(dias_semana), num_turmas, len(horarios_br)), txt_vazio, dtype=object)

    # evita que o mesmo professor dê duas aulas na MESMA hora
    ocupado: Dict[Tuple[int, int], set] = defaultdict(set)

    pares = list(disp.keys())
    rng.shuffle(pares)

    for (prof, mat) in pares:
        # permuta lista de horários disponíveis p/ variabilidade
        for (dia, hora) in rng.permutation(disp[(prof, mat)]):
            # procura qualquer turma vaga naquele slot
            vagas = [t for t in range(num_turmas) if grade[dia, t, hora] == txt_vazio]
            if vagas and prof not in ocupado[(dia, hora)]:
                turma = rng.choice(vagas)
                grade[dia, turma, hora] = f"{mat} ({prof})"
                ocupado[(dia, hora)].add(prof)
            # Caso contrário: ou não há vaga, ou professor já está ocupado -> passa

    return grade


def validar_grade(grade: np.ndarray, disp: Dict[Tuple[str, str], List[Tuple[int, int]]]) -> Tuple[int, int]:
    """
    Verifica:
      - alocação só em horários disponíveis
      - nenhum professor duplicado no mesmo (dia, hora)
    Retorna (#erros_fora_disp, #conflitos_mesmo_prof_no_slot).
    """
    import re
    fora_disp = 0
    conflitos = 0
    avail = {k: set(v) for k, v in disp.items()}

    # 1) alocação só em horários disponíveis
    for d in range(grade.shape[0]):
        for t in range(grade.shape[1]):
            for h in range(grade.shape[2]):
                x = grade[d, t, h]
                if x == txt_vazio: 
                    continue
                m = re.match(r"^(.*)\s+\((.*)\)$", x)
                if not m: 
                    fora_disp += 1; continue
                mat, prof = m.group(1), m.group(2)
                if (prof, mat) not in avail or (d, h) not in avail[(prof, mat)]:
                    fora_disp += 1

    # 2) nenhum professor duplicado no mesmo slot
    for d in range(grade.shape[0]):
        for h in range(grade.shape[2]):
            vistos = set()
            for t in range(grade.shape[1]):
                x = grade[d, t, h]
                if x == txt_vazio: 
                    continue
                prof = x.split("(")[-1].rstrip(")")
                if prof in vistos:
                    conflitos += 1
                else:
                    vistos.add(prof)

    return fora_disp, conflitos
# ╰──────────────────────────────────────────────────────╯


# ╭────────────────────────── EXPORTAÇÃO ─────────────────────────╮
def salvar_excel_pdf(grade: np.ndarray, turmas_labels: List[str],
                     xlsx_path: Path, pdf_path: Path,
                     legenda: Dict[str, List[str]]) -> None:
    # ---------- Excel ----------
    with pd.ExcelWriter(xlsx_path) as writer:
        for d in range(len(dias_semana)):
            df = pd.DataFrame(
                grade[d],
                index=turmas_labels,                  # <— usa rótulos das turmas!
                columns=horarios_br,
            )
            df.to_excel(writer, sheet_name=dias_semana[d])

    # ---------- PDF ----------
    pdf = FPDF(orientation="L")
    pdf.set_auto_page_break(auto=True, margin=10)

    # capa
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 12, "GRADE DE HORÁRIOS", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, "Gerado a partir de professores.csv", ln=True, align="C")
    pdf.ln(2)

    # grade por dia
    for d in range(len(dias_semana)):
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, dias_semana[d], ln=True)
        pdf.ln(2)

        # cabeçalhos
        pdf.set_font("Arial", "B", 10)
        pdf.cell(cell_w_pdf, 8, "Turma / Horário", border=1, align="C")
        for h in horarios_br:
            pdf.cell(cell_w_pdf, 8, h, border=1, align="C")
        pdf.ln()

        # linhas
        pdf.set_font("Arial", size=9)
        for idx_turma, turma_lbl in enumerate(turmas_labels):
            pdf.cell(cell_w_pdf, 8, turma_lbl, border=1)
            for h in range(len(horarios_br)):
                txt = shorten(str(grade[d, idx_turma, h]), width=18, placeholder="…")
                pdf.cell(cell_w_pdf, 8, txt, border=1, align="C")
            pdf.ln()

    # página-legenda
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Professores & Matérias", ln=True)
    pdf.ln(3)

    pdf.set_font("Arial", size=11)
    for prof, mats in sorted(legenda.items()):
        pdf.cell(0, 7, f"{prof}: {', '.join(sorted(set(mats)))}", ln=True)

    pdf.output(str(pdf_path))
# ╰──────────────────────────────────────────────────────╯


def main(*args):
    """
    Compatível com:
      - main()                         -> tenta ler ui_config.json
      - main(ano, qtd)                 -> gera turmas automaticamente
      - main(ano, qtd, turmas: list)   -> usa rótulos fornecidos
    """
    # Resolve parâmetros de entrada
    ano = qtd = turmas = None
    if len(args) == 2:
        ano, qtd = int(args[0]), int(args[1])
    elif len(args) == 3:
        ano, qtd, turmas = int(args[0]), int(args[1]), list(args[2])

    ano, qtd, turmas_labels = _resolver_params(ano, qtd, turmas)

    disp = carregar_disponibilidade()
    if not disp:
        print("Nenhum professor cadastrado! Use a interface para gravar disponibilidades.")
        return

    grade = montar_grade(disp, num_turmas=qtd)

    # validação de segurança
    e1, e2 = validar_grade(grade, disp)
    if e1 or e2:
        print(f"[ALERTA] Regras violadas: fora_disp={e1}, conflitos={e2}")

    # legenda professor → lista de matérias
    legenda: Dict[str, List[str]] = defaultdict(list)
    for (prof, mat) in disp:
        legenda[prof].append(mat)

    out_xlsx = root_path / "horarios_escolares_matricial.xlsx"
    out_pdf  = root_path / "horarios_escolares_matricial.pdf"
    salvar_excel_pdf(grade, turmas_labels, out_xlsx, out_pdf, legenda)

    print("Grade gerada com sucesso:")
    print(out_xlsx)
    print(out_pdf)


if __name__ == "__main__":
    main()
