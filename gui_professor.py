# gui_professor_fullscreen.py
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import font, messagebox
from tkinter import ttk
from pathlib import Path
import json
import string
import pandas as pd
import GradeHorario  # <— integra o gerador de Excel/PDF

# ───────────── Arquivos ───────────── #
root_path = Path(__file__).resolve().parent
data_path = root_path / "data"
csv_file  = data_path / "professores.csv"
config_file = data_path / "ui_config.json"

dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira",
               "Quinta-feira", "Sexta-feira", "Sábado"]
horarios_br = ["12h-13h", "13h-14h", "14h-15h", "15h-16h", "16h-17h"]

data_path.mkdir(exist_ok=True)
if not csv_file.exists():
    pd.DataFrame(columns=["Professor", "Materia", "Dia", "Horario"]).to_csv(csv_file, index=False)
# ──────────────────────────────────── #


# ---------- util: geração de códigos de turma ----------
def gerar_codigos_turma(ano: int, qtd: int):
    """
    Gera: 1A, 1B, ..., 1Z, 1AA, 1AB, ... conforme qtd.
    """
    if ano <= 0: ano = 1
    if qtd <= 0: qtd = 1
    letras = string.ascii_uppercase  # A..Z
    codes = []
    i = 0
    while len(codes) < qtd:
        if i < 26:
            sufixo = letras[i]
        else:
            # AA, AB, AC...
            first = (i // 26) - 1
            second = i % 26
            sufixo = letras[first] + letras[second]
        codes.append(f"{ano}{sufixo}")
        i += 1
    return codes


# ---------- callbacks (persistem dados no CSV) ----------
def salvar_dados():
    prof, mat = entry_prof.get().strip(), entry_mat.get().strip()
    if not prof or not mat:
        messagebox.showwarning("Campos vazios", "Preencha Nome do Professor e Matéria.")
        return

    linhas = [{"Professor": prof, "Materia": mat, "Dia": dia, "Horario": hor}
              for i_dia, dia in enumerate(dias_semana)
              for i_h,  hor in enumerate(horarios_br) if checks[i_dia][i_h].get()]

    if not linhas:
        messagebox.showwarning("Nenhum horário", "Selecione pelo menos um horário.")
        return

    df_novo  = pd.DataFrame(linhas)
    df_exist = pd.read_csv(csv_file) if csv_file.exists() else pd.DataFrame(columns=df_novo.columns)
    mask     = ~((df_exist["Professor"] == prof) & (df_exist["Materia"] == mat))
    pd.concat([df_exist[mask], df_novo], ignore_index=True).to_csv(csv_file, index=False)
    messagebox.showinfo("Salvo", f"{len(linhas)} horário(s) gravado(s) para {prof}.")
    limpar()


def limpar():
    entry_prof.delete(0, tk.END)
    entry_mat.delete(0, tk.END)
    for linha in checks:
        for var in linha:
            var.set(False)


def limpar_tudo():
    """
    Pergunta confirmação e limpa completamente a base (data/professores.csv).
    Depois, reseta os campos/seleções da tela.
    """
    if not messagebox.askyesno(
        "Confirmar limpeza",
        "Tem certeza que deseja APAGAR TODOS os professores e seus horários da base de dados?"
    ):
        return

    try:
        cols = ["Professor", "Materia", "Dia", "Horario"]
        pd.DataFrame(columns=cols).to_csv(csv_file, index=False)
        limpar()
        messagebox.showinfo("Base limpa", "Todos os registros foram apagados da base de dados.")
    except Exception as e:
        messagebox.showerror("Erro ao limpar", f"Não foi possível limpar a base.\n\nDetalhes: {e}")


def _chamar_gradehorario(ano: int, qtd: int, turmas: list):
    """
    Tenta repassar parâmetros ao GradeHorario. Suporta:
    - GradeHorario.set_params(ano, qtd, turmas)
    - GradeHorario.main(ano, qtd, turmas) / main(ano, qtd) / main()
    Sempre grava um config JSON para consumo externo.
    """
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"ano": ano, "qtd_turmas": qtd, "turmas": turmas}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if hasattr(GradeHorario, "set_params"):
        try:
            GradeHorario.set_params(ano, qtd, turmas)
        except Exception:
            pass

    # tenta diferentes assinaturas do main
    try:
        GradeHorario.main(ano, qtd, turmas)
        return
    except TypeError:
        pass
    try:
        GradeHorario.main(ano, qtd)
        return
    except TypeError:
        pass
    GradeHorario.main()


def gerar_grade():
    """
    Chama o pipeline de GradeHorario para ler o CSV, montar a grade e salvar
    os arquivos horarios_escolares_matricial.xlsx e .pdf, usando ano/qtd/turmas.
    """
    try:
        ano = int(spin_ano.get())
        qtd = int(spin_qtd.get())
        turmas = gerar_codigos_turma(ano, qtd)

        _chamar_gradehorario(ano, qtd, turmas)

        out_xlsx = root_path / "horarios_escolares_matricial.xlsx"
        out_pdf  = root_path / "horarios_escolares_matricial.pdf"

        msg = "Arquivos gerados com sucesso:\n"
        if out_xlsx.exists(): msg += f"• {out_xlsx}\n"
        if out_pdf.exists():  msg += f"• {out_pdf}\n"
        # também exibe as turmas usadas
        msg += f"\nTurmas: {', '.join(turmas)}"
        messagebox.showinfo("HORÓTIMO", msg)
    except Exception as e:
        messagebox.showerror("Erro na geração da grade", str(e))


# ───────────── GUI ───────────── #
root = tk.Tk()
root.title("Cadastro de Disponibilidade – HORÓTIMO")
try:
    root.state("zoomed")        # Windows
except tk.TclError:
    root.attributes("-zoomed", True)  # Linux/macOS

# Tipografia global
font.nametofont("TkDefaultFont").configure(size=12)

# Tema moderno ttk
style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

# Paleta (dark)
BG       = "#0b1220"
CARD     = "#111827"
CARD_HOV = "#1a2333"
BORDER   = "#1f2937"
FG       = "#e5e7eb"
SUBTLE   = "#94a3b8"
ACCENT   = "#22c55e"
ACCENT_2 = "#16a34a"
OFF      = "#0f172a"   # fundo interno dos chips

root.configure(bg=BG)

# Estilos ttk
style.configure("TFrame", background=BG)
style.configure("Card.TFrame", background=CARD, bordercolor=BORDER, relief="solid", borderwidth=1)
style.configure("Header.TLabel", background=BG, foreground=FG, font=("Segoe UI", 18, "bold"))
style.configure("Sub.TLabel", background=CARD, foreground=SUBTLE, font=("Segoe UI", 11))
style.configure("H1.TLabel", background=CARD, foreground=FG, font=("Segoe UI", 14, "bold"))
style.configure("Form.TLabel", background=CARD, foreground=FG, font=("Segoe UI", 12))
style.configure("Chip.TLabel", background=OFF, foreground=FG, padding=6, relief="flat")
style.configure("TLabel", background=BG, foreground=FG)
style.configure("TEntry", fieldbackground=OFF, background=OFF, foreground=FG,
                bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
style.map("TEntry",
          bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])

style.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT, padding=10)
style.map("Accent.TButton", background=[("active", ACCENT_2)], bordercolor=[("active", ACCENT_2)])
style.configure("TButton", padding=10)
style.map("TButton", background=[("active", "#273043")], foreground=[("active", FG)])

# Layout raiz (header + conteúdo)
root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)

# Header
header = ttk.Frame(root)
header.grid(row=0, column=0, sticky="ew", pady=(6, 0))
header.columnconfigure(0, weight=1)
ttk.Label(header, text="Cadastro de Disponibilidade", style="Header.TLabel")\
   .grid(row=0, column=0, sticky="w", padx=16, pady=(4, 10))

# Content container com padding
content = ttk.Frame(root)
content.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
content.rowconfigure(1, weight=1)  # a grade cresce
content.columnconfigure(0, weight=1)

# Card: Formulário
form_card = ttk.Frame(content, style="Card.TFrame")
form_card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 14))
for i in range(8):
    form_card.columnconfigure(i, weight=1)

ttk.Label(form_card, text="Informações do Professor", style="H1.TLabel")\
   .grid(row=0, column=0, columnspan=8, sticky="w", padx=16, pady=(16, 8))

# Linha 1: Professor / Matéria
ttk.Label(form_card, text="Nome do Professor:", style="Form.TLabel")\
   .grid(row=1, column=0, sticky="e", padx=(16, 8), pady=(0, 12))
entry_prof = ttk.Entry(form_card)
entry_prof.grid(row=1, column=1, columnspan=3, sticky="we", padx=(0, 16), pady=(0, 12))

ttk.Label(form_card, text="Matéria:", style="Form.TLabel")\
   .grid(row=1, column=4, sticky="e", padx=(16, 8), pady=(0, 12))
entry_mat = ttk.Entry(form_card)
entry_mat.grid(row=1, column=5, columnspan=3, sticky="we", padx=(0, 16), pady=(0, 12))

# Linha 2: Ano da turma / Quantidade de turmas (salas)
ttk.Label(form_card, text="Ano da turma:", style="Form.TLabel")\
   .grid(row=2, column=0, sticky="e", padx=(16, 8), pady=(0, 12))
spin_ano = ttk.Spinbox(form_card, from_=1, to=9, width=6, justify="center")
spin_ano.set(1)
spin_ano.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(0, 12))

ttk.Label(form_card, text="Quantidade de turmas:", style="Form.TLabel")\
   .grid(row=2, column=4, sticky="e", padx=(16, 8), pady=(0, 12))
spin_qtd = ttk.Spinbox(form_card, from_=1, to=60, width=6, justify="center")
spin_qtd.set(10)
spin_qtd.grid(row=2, column=5, sticky="w", padx=(0, 16), pady=(0, 12))

# Pré-visualização das turmas (badges)
turmas_frame = ttk.Frame(form_card, style="Card.TFrame")
turmas_frame.grid(row=3, column=0, columnspan=8, sticky="ew", padx=12, pady=(4, 12))
turmas_frame.columnconfigure(0, weight=1)

turmas_row = ttk.Frame(turmas_frame, style="Card.TFrame")
turmas_row.grid(row=0, column=0, sticky="w", padx=8, pady=8)

def refresh_turmas_preview(*_):
    for w in list(turmas_row.winfo_children()):
        w.destroy()
    try:
        ano = int(spin_ano.get())
        qtd = int(spin_qtd.get())
    except ValueError:
        ano, qtd = 1, 1
    codes = gerar_codigos_turma(ano, qtd)
    # Título
    ttk.Label(turmas_row, text="Turmas:", style="Form.TLabel").pack(side="left", padx=(4, 8))
    # Badges
    for code in codes:
        lbl = ttk.Label(turmas_row, text=code, style="Chip.TLabel")
        lbl.pack(side="left", padx=4, pady=2)

spin_ano.configure(command=refresh_turmas_preview)
spin_qtd.configure(command=refresh_turmas_preview)
refresh_turmas_preview()


# ======= Chips modernos (substitui o quadrado branco do Checkbutton) ======= #
def make_chip(parent, var: tk.BooleanVar):
    """
    Cria um 'chip' clicável (sem indicator branco). Mantém a mesma BooleanVar.
    Visual:
      - OFF: bg OFF, borda BORDER
      - HOVER: CARD_HOV (se off)
      - ON: bg ACCENT com ✓
    """
    chip = tk.Label(parent, text="", bg=OFF, fg=FG, width=4, height=1,
                    bd=0, relief="flat", cursor="hand2")
    chip.configure(highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)

    def refresh(*_):
        if var.get():
            chip.config(bg=ACCENT, fg="white", text="✓")
            chip.configure(highlightbackground=ACCENT_2)
        else:
            chip.config(bg=OFF, fg=FG, text="")
            chip.configure(highlightbackground=BORDER)

    def toggle(_):
        var.set(not var.get())
        refresh()

    chip.bind("<Button-1>", toggle)
    chip.bind("<Enter>", lambda e: chip.config(bg=CARD_HOV) if not var.get() else None)
    chip.bind("<Leave>", lambda e: refresh())

    refresh()
    return chip
# =========================================================================== #


# Card: Grade de horários (disponibilidade do professor)
grid_card = ttk.Frame(content, style="Card.TFrame")
grid_card.grid(row=1, column=0, sticky="nsew")
grid_card.columnconfigure(0, weight=1)
for c in range(1, len(horarios_br) + 1):
    grid_card.columnconfigure(c, weight=1)

ttk.Label(grid_card, text="Selecione os horários disponíveis", style="H1.TLabel")\
   .grid(row=0, column=0, columnspan=len(horarios_br)+1, sticky="w", padx=16, pady=(16, 8))
ttk.Label(grid_card, text="Marque os horários correspondentes a cada dia.", style="Sub.TLabel")\
   .grid(row=1, column=0, columnspan=len(horarios_br)+1, sticky="w", padx=16, pady=(0, 12))

# Cabeçalho da grade (horários)
ttk.Label(grid_card, text="Dia", style="Form.TLabel").grid(row=2, column=0, sticky="e", padx=(16, 10))
for i_h, htxt in enumerate(horarios_br, start=1):
    ttk.Label(grid_card, text=htxt, style="Form.TLabel").grid(row=2, column=i_h, sticky="n", padx=6, pady=(0, 6))

# Chips no lugar dos checkboxes (mantendo estrutura checks[i_dia][i_h])
checks = []
start_row = 3
for r, dia in enumerate(dias_semana, start=start_row):
    ttk.Label(grid_card, text=dia + ":", style="Form.TLabel").grid(row=r, column=0, sticky="e", padx=(16, 10))
    linha = []
    for c in range(len(horarios_br)):
        var = tk.BooleanVar(value=False)
        chip = make_chip(grid_card, var)
        chip.grid(row=r, column=c+1, sticky="n", padx=10, pady=8)
        linha.append(var)
    checks.append(linha)

# Barra de ações (dentro do card)
actions = ttk.Frame(grid_card, style="Card.TFrame")
actions.grid(row=start_row + len(dias_semana), column=0, columnspan=len(horarios_br)+1,
             sticky="ew", padx=0, pady=(8, 16))
for i in range(6):
    actions.columnconfigure(i, weight=1)

btn_gerar = ttk.Button(actions, text="Gerar Grade (Excel + PDF)",
                       style="Accent.TButton", command=gerar_grade)
btn_gerar.grid(row=0, column=1, sticky="ew", padx=(16, 8), pady=(12, 0))

btn_salvar = ttk.Button(actions, text="Salvar", command=salvar_dados)
btn_salvar.grid(row=0, column=2, sticky="ew", padx=(8, 8), pady=(12, 0))

btn_limpar = ttk.Button(actions, text="Limpar Base", command=limpar_tudo)
btn_limpar.grid(row=0, column=3, sticky="ew", padx=(8, 16), pady=(12, 0))

root.mainloop()
