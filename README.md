# TurmaGrid — Cadastro de Disponibilidade & Geração de Grade (GUI + Engine)

Sistema completo para **cadastrar disponibilidades de professores** e **gerar automaticamente** uma **grade escolar** em **Excel** e **PDF**. 
A aplicação combina uma interface moderna em **Tkinter/ttk** com um mecanismo de alocação reproduzível (semente fixa) e validação de regras.
  
> **Stack**: Python 3.x • Tkinter/ttk • pandas • NumPy • fpdf • Pathlib • JSON

---

## 🎯 Objetivo

Transformar disponibilidades pontuais (por professor e matéria) em uma grade semanal coerente, visualmente organizada e pronta para distribuição.

---

## 🧭 Arquitetura & Fluxo de Dados

- **GUI (`gui_professor_fullscreen.py`)**
  - Grava a base `data/professores.csv` com colunas: **Professor, Materia, Dia, Horario**.
  - Persiste parâmetros de geração em `data/ui_config.json` (**ano**, **quantidade de turmas** e **rótulos**).
- **Engine (`GradeHorario`)**
  - Lê o CSV + parâmetros, **monta a grade** e exporta:
    - `horarios_escolares_matricial.xlsx`
    - `horarios_escolares_matricial.pdf`
- **Reprodutibilidade**: usa `seed=42` para resultados consistentes entre execuções.

**Convenções do sistema**
- Dias: `Segunda-feira` … `Sábado`
- Faixas horárias (exemplo padrão): `12h-13h` … `16h-17h`
- Rótulos de turma: `1A, 1B, …, 1Z, 1AA, 1AB, …` (gerados a partir de **ano** e **qtd**).

---

## 🖥️ Funcionalidades da Interface Gráfica

- **Tema escuro moderno** com componentes `ttk` customizados.
- **Formulário** com:
  - *Nome do Professor* e *Matéria* (validação de campos).
  - *Ano da turma* (spin) e *Quantidade de turmas* (spin).
  - **Pré-visualização dinâmica** das turmas (badges: `1A, 1B, …`).
- **Seleção de disponibilidade** por *dia × horário* usando “**chips**” clicáveis (substituem checkboxes).
- **Persistência idempotente**: ao salvar, a disponibilidade de `(Professor, Matéria)` é substituída pela seleção atual (evita duplicatas antigas).
- **Geração da grade** com confirmação em *messagebox* e **paths absolutos** de saída.
- **Limpar Base** com confirmação (zera `data/professores.csv` e reseta UI).
- **Full-screen / zoom** automático (Windows/Linux/macOS).

---

## 📸 Capturas de Tela

### 1) Tela de Menu (GUI principal)
![Tela de menu](assets/screens/menu.png)

### 2) Geração dos Arquivos (confirmação)
![Geração dos arquivos](assets/screens/geracao_arquivos.png)

### 3) Limpar Base (confirmação)
![Limpar base](assets/screens/limpar_base.png)

### 4) Resultado no PDF (exemplo de dia)
![Resultado do PDF](assets/screens/resultado_pdf.png)

---

## 📐 Modelagem Teórica (resumo matemático)

Considere:
- Conjuntos: dias **D** (6), horários **H** (5), turmas **T**, professores **P** e pares **K ⊆ P × M** (professor–matéria).
- Para cada par \(k ∈ K\), há um conjunto de disponibilidades \(A_k ⊆ D × H\).

**Variável binária**
- \(x_{{k,t,d,h}} = 1\) se \(k\) leciona a turma \(t\) no slot \((d,h)\), caso contrário 0.

**Restrições** (implementadas/validadas):
1. **Disponibilidade**: \(x_{{k,t,d,h}} = 0\) se \((d,h) \not\in A_k\).
2. **Professor único por slot**: \(\sum_{t} \sum_{k: prof(k)=p} x_{{k,t,d,h}} ≤ 1\) para todo professor \(p\) e todo \((d,h)\).
3. **Capacidade turma/slot**: \(\sum_{k} x_{{k,t,d,h}} ≤ 1\) para toda turma \(t\) e todo \((d,h)\).

**Objetivo implícito**: **maximizar** o preenchimento \(\sum x_{{k,t,d,h}}\).  
Com essas restrições, o problema **decompõe por slot** \((d,h)\): para cada horário do dia, trata-se de um **emparelhamento bipartido** entre *turmas* e *professores disponíveis*.

**Limite superior de preenchimento**
Para cada \((d,h)\): no máximo \(\min\{{T, |P_{{d,h}}|}}\) alocações, em que \(P_{{d,h}}\) é o conjunto de professores disponíveis no slot.  
A taxa máxima global é:
\[
\text{{fill\_max}} \le \frac{\sum_{d,h} \min(T, |P_{{d,h}}|)}{|D|\cdot|H|\cdot T}.
\]

---

## ⚙️ Algoritmo de Alocação (implementado)

- **Entrada**: disponibilidades por `(Professor, Matéria)` → lista de slots \((d,h)\).
- **Processo** (*greedy* com aleatoriedade controlada):
  1. Embaralha os pares `(prof, mat)` com RNG (semente 42).
  2. Percorre os slots disponíveis desse par; em cada slot, escolhe **qualquer turma vaga** naquele \((d,h)\) e aloca, desde que o professor ainda não esteja ocupando aquele slot.
  3. Continua até varrer todos os pares/slots.
- **Validação** (pós-alocação):
  - Somente horários disponíveis foram usados.
  - Nenhum professor aparece duas vezes no mesmo \((d,h)\).

**Complexidade**: aproximadamente \(O(A\cdot T)\), onde \(A\) é o nº total de marcações de disponibilidade; adequado para dezenas de turmas.

---

## 🧾 Exportação (Excel + PDF)

- **Excel**: uma planilha por dia; linhas = **turmas**, colunas = **faixas horárias**; células do tipo `"Matéria (Professor)"` ou vazio.
- **PDF**:
  - Capa + páginas por dia (tabela com turmas × horários).
  - **Legenda** final com mapeamento **Professor → Matérias**.
  - Ajustes de largura/cortes de texto para manter legibilidade.

---

## 🔧 Estrutura de Pastas

```
.
├─ gui_professor_fullscreen.py
├─ GradeHorario.py              # (arquivo privado — ver .gitignore abaixo)
├─ data/
│  ├─ professores.csv           # base gravada pela GUI
│  └─ ui_config.json            # parâmetros vindo da GUI
├─ horarios_escolares_matricial.xlsx
├─ horarios_escolares_matricial.pdf
└─ assets/
   └─ screens/
      ├─ menu.png
      ├─ geracao_arquivos.png
      ├─ limpar_base.png
      └─ resultado_pdf.png
```

---

## ▶️ Como Executar (local)

1. **Instale dependências**  
   ```bash
   pip install pandas numpy fpdf
   ```

2. **Execute a interface**  
   ```bash
   python gui_professor_fullscreen.py
   ```

3. **Fluxo**  
   - Preencha *Professor* e *Matéria* → marque disponibilidades → **Salvar**.  
   - Ajuste **Ano** e **Quantidade de turmas** (pré-visualização aparece em “Turmas”).  
   - Clique **Gerar Grade (Excel + PDF)** para produzir os arquivos finais.  
   - **Limpar Base** para zerar `data/professores.csv` (confirmação mostrada).

---

## ✅ Regras de negócio atendidas

- Professor **não** é alocado em **dois horários simultâneos**.
- Somente slots efetivamente **marcados como disponíveis** são usados.
- Se **faltarem professores** em um slot, a célula **permanece vazia**.
- Geração reproduzível (RNG com semente fixa).

---

## 👤 Autor

**Miguel Gengo** — Engenheiro da Computação  
[LinkedIn](https://www.linkedin.com/in/miguel-gengo-8157b72a1)

--- 

## 📄 Licença

Projeto acadêmico/demonstrativo. Adapte conforme sua política interna.
