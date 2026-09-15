# -*- coding: utf-8 -*-
"""
ADMISSÃO KESH BANK — Lider Limpe
App Streamlit para gerar o CSV de cadastro de novos colaboradores admitidos
no banco Kesh Bank a partir da planilha exportada do sistema Domínio.
"""

import io
import re
import unicodedata

import pandas as pd
import requests
import streamlit as st
from PIL import Image

# ----------------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------------
CEP_EMPRESA = "29108375"            # CEP padrão da empresa (29108-375)
CELULAR_PADRAO = "27999153249"      # celular padrão quando não informado
EMAIL_PADRAO = "naoexiste@naoexiste.com.br"

COLS_SAIDA = [
    "OPERACAO", "NOME", "CPF/CNPJ", "DATA_ADMISSAO", "NOME_MAE",
    "DATA_NASCIMENTO", "E-MAIL", "CELULAR", "SALARIO", "LOTACAO",
    "CEP", "PAIS", "ESTADO", "CIDADE", "BAIRRO", "RUA", "NUMERO",
    "COMPLEMENTO",
]

OBRIGATORIOS = [
    "OPERACAO", "NOME", "CPF/CNPJ", "DATA_ADMISSAO", "NOME_MAE",
    "DATA_NASCIMENTO", "E-MAIL", "CELULAR", "SALARIO", "CEP",
    "ESTADO", "CIDADE", "BAIRRO", "RUA", "NUMERO",
]

CORES = {"vermelho": "#FFD7D7", "amarelo": "#FFF3BF"}

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA + ESTILO
# ----------------------------------------------------------------------------
_logo = Image.open("logo.png")
st.set_page_config(
    page_title="Admissão Kesh Bank",
    page_icon=_logo,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --azul: #001975; --laranja: #ff5500; }
    .stApp { background: linear-gradient(180deg, #f4f6fb 0%, #ffffff 40%); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #001975 0%, #00289e 100%); }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .hero {
        background: linear-gradient(120deg, #001975 0%, #003ba1 70%, #0a4fc4 100%);
        border-radius: 18px; padding: 26px 32px; margin-bottom: 18px;
        display: flex; align-items: center; gap: 22px;
        box-shadow: 0 8px 24px rgba(0, 25, 117, .25);
    }
    .hero h1 { color: #ffffff; margin: 0; font-size: 2rem; font-weight: 800; }
    .hero p { color: #ffd9c7; margin: 4px 0 0 0; font-size: 1.02rem; }
    .hero img { border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,.35); }
    .card {
        background: #ffffff; border: 1px solid #e6eaf5; border-radius: 14px;
        padding: 18px 22px; margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0, 25, 117, .06);
    }
    .pill-ok  { background:#e6f9ed; color:#0c7a3d; border-radius:20px; padding:4px 14px; font-weight:700; }
    .pill-warn{ background:#fff3bf; color:#9a6b00; border-radius:20px; padding:4px 14px; font-weight:700; }
    .pill-err { background:#ffd7d7; color:#b30000; border-radius:20px; padding:4px 14px; font-weight:700; }
    div[data-testid="stDownloadButton"] button, .stButton > button {
        background: linear-gradient(120deg, #ff5500, #ff7733); color: #fff;
        border: none; border-radius: 10px; font-weight: 700; padding: .55rem 1.4rem;
    }
    div[data-testid="stDownloadButton"] button:hover, .stButton > button:hover {
        background: linear-gradient(120deg, #e04b00, #ff5500); color:#fff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hero():
    import base64
    with open("logo.png", "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <div class="hero">
            <img src="data:image/png;base64,{b64}" width="86"/>
            <div>
                <h1>Admissão Kesh Bank</h1>
                <p>Lider Limpe · Geração automática do CSV de cadastro de novos colaboradores a partir da planilha Domínio</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# FUNÇÕES DE TRATAMENTO
# ----------------------------------------------------------------------------
def so_digitos(v) -> str:
    return re.sub(r"\D", "", str(v)) if v is not None else ""


def num_str(v) -> str:
    """Converte números lidos como float (ex.: 18.0) em texto limpo ('18')."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, str) and v.strip().lower() in ("", "nan", "none"):
        return ""
    if isinstance(v, (int, float)):
        try:
            if float(v).is_integer():
                return str(int(v))
        except Exception:
            pass
        return str(v).strip()
    s = str(v).strip()
    if re.fullmatch(r"\d+\.0+", s):
        return s.split(".")[0]
    return s


def sem_acentos(s: str) -> str:
    s = s.replace("ç", "c").replace("Ç", "C")
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def texto(v, maiusculo=True) -> str:
    s = num_str(v)
    s = sem_acentos(s)
    return s.upper() if maiusculo else s.lower()


def fmt_cpf(v) -> str:
    d = so_digitos(num_str(v))
    return d.zfill(11) if d else ""


def fmt_celular(v):
    """Retorna (celular, status) — status: ok | padrao | formato."""
    d = so_digitos(num_str(v))
    if not d:
        return CELULAR_PADRAO, "padrao"
    while len(d) > 11 and d.startswith("0"):
        d = d[1:]
    if len(d) == 12 and d.startswith("0"):
        d = d[1:]
    if len(d) != 11:
        return d, "formato"
    return d, "ok"


def fmt_salario(v) -> str:
    s = num_str(v)
    if not s:
        return ""
    try:
        if "," in s:
            val = float(s.replace(".", "").replace(",", "."))
        else:
            val = float(s)
        return f"{val:.2f}".replace(".", ",")
    except Exception:
        return sem_acentos(s).upper()


def fmt_data(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    ts = pd.to_datetime(v, dayfirst=True, errors="coerce")
    return ts.strftime("%d/%m/%Y") if pd.notna(ts) else ""


def fmt_cep(v) -> str:
    d = so_digitos(num_str(v))
    return d.zfill(8) if d else ""


@st.cache_data(show_spinner=False, ttl=86400)
def buscar_cep(cep: str):
    """Consulta o ViaCEP. Retorna dict ou None."""
    try:
        r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=8)
        d = r.json()
        if d.get("erro"):
            return None
        return d
    except Exception:
        return None


# ----------------------------------------------------------------------------
# PROCESSAMENTO PRINCIPAL
# ----------------------------------------------------------------------------
def processar_dominio(df: pd.DataFrame):
    """Gera o dataframe de saída no layout do Kesh Bank."""
    df.columns = [str(c).strip() for c in df.columns]

    # Pré-busca dos CEPs (com barra de progresso)
    ceps = []
    for _, row in df.iterrows():
        cep = fmt_cep(row.get("Cep")) or CEP_EMPRESA
        if cep not in ceps:
            ceps.append(cep)
    if CEP_EMPRESA not in ceps:
        ceps.append(CEP_EMPRESA)

    info_cep = {}
    barra = st.progress(0, text="Consultando CEPs no ViaCEP...")
    for i, cep in enumerate(ceps):
        info_cep[cep] = buscar_cep(cep)
        barra.progress((i + 1) / len(ceps), text=f"Consultando CEPs no ViaCEP... ({i+1}/{len(ceps)})")
    barra.empty()

    registros = []
    for _, row in df.iterrows():
        cep = fmt_cep(row.get("Cep"))
        via = info_cep.get(cep) if cep else None
        if not cep or via is None:
            cep_final = cep or CEP_EMPRESA
            via_final = via or info_cep.get(CEP_EMPRESA) or {}
        else:
            cep_final, via_final = cep, via

        celular, _status_cel = fmt_celular(row.get("Celular"))

        reg = {
            "OPERACAO": "NOVO",
            "NOME": texto(row.get("Nome")),
            "CPF/CNPJ": fmt_cpf(row.get("CPF")),
            "DATA_ADMISSAO": fmt_data(row.get("Admissão")),
            "NOME_MAE": texto(row.get("Nome Mãe")),
            "DATA_NASCIMENTO": fmt_data(row.get("Data nascimento")),
            "E-MAIL": texto(row.get("Email"), maiusculo=False) or EMAIL_PADRAO,
            "CELULAR": celular,
            "SALARIO": fmt_salario(row.get("Salário")),
            "LOTACAO": texto(row.get("Descrição Ccusto")),
            "CEP": cep_final,
            "PAIS": "BRASIL",
            "ESTADO": texto(via_final.get("uf", "")),
            "CIDADE": texto(via_final.get("localidade", "")) or texto(row.get("Cidade")),
            "BAIRRO": texto(via_final.get("bairro", "")) or texto(row.get("Bairro")),
            "RUA": texto(via_final.get("logradouro", "")) or texto(row.get("Endereço")),
            "NUMERO": texto(via_final.get("numero", "")) or num_str(row.get("Numero")),
            "COMPLEMENTO": texto(via_final.get("complemento", "")) or texto(row.get("Complemento")),
        }
        registros.append(reg)

    return pd.DataFrame(registros, columns=COLS_SAIDA)


def validar(df: pd.DataFrame):
    """
    Recalcula destaques e problemas a partir do dataframe final.
    Retorna (flags {(linha, coluna): cor}, problemas [dict]).
    """
    flags, problemas = {}, []
    for i, row in df.iterrows():
        nome = row["NOME"] or f"LINHA {i+1}"
        # Vermelho — informação obrigatória faltando / valor padrão de urgência
        for col in ["NOME", "CPF/CNPJ", "DATA_ADMISSAO", "NOME_MAE", "DATA_NASCIMENTO"]:
            if not str(row[col]).strip():
                flags[(i, col)] = "vermelho"
                problemas.append({"Colaborador": nome, "Campo": col,
                                  "Situação": "⚠ FALTANDO INFORMAÇÃO", "Gravidade": "Crítico"})
        if row["CPF/CNPJ"] and len(so_digitos(row["CPF/CNPJ"])) != 11:
            flags[(i, "CPF/CNPJ")] = "vermelho"
            problemas.append({"Colaborador": nome, "Campo": "CPF/CNPJ",
                              "Situação": "⚠ CPF NÃO TEM 11 DÍGITOS", "Gravidade": "Crítico"})
        if row["CELULAR"] == CELULAR_PADRAO:
            flags[(i, "CELULAR")] = "vermelho"
            problemas.append({"Colaborador": nome, "Campo": "CELULAR",
                              "Situação": "⚠ CELULAR NÃO INFORMADO — USADO NÚMERO PADRÃO", "Gravidade": "Crítico"})
        elif len(so_digitos(row["CELULAR"])) != 11:
            flags[(i, "CELULAR")] = "amarelo"
            problemas.append({"Colaborador": nome, "Campo": "CELULAR",
                              "Situação": "CELULAR FORA DO PADRÃO DE 11 DÍGITOS", "Gravidade": "Atenção"})
        # Amarelo — valores padrão assumidos
        if row["E-MAIL"] == EMAIL_PADRAO or not str(row["E-MAIL"]).strip():
            flags[(i, "E-MAIL")] = "amarelo"
            problemas.append({"Colaborador": nome, "Campo": "E-MAIL",
                              "Situação": "E-MAIL NÃO INFORMADO — USADO E-MAIL PADRÃO", "Gravidade": "Atenção"})
        if row["CEP"] == CEP_EMPRESA:
            flags[(i, "CEP")] = "amarelo"
            problemas.append({"Colaborador": nome, "Campo": "CEP",
                              "Situação": "CEP NÃO LOCALIZADO — USADO CEP DA EMPRESA", "Gravidade": "Atenção"})
        for col in ["ESTADO", "CIDADE", "BAIRRO", "RUA", "NUMERO", "SALARIO"]:
            if not str(row[col]).strip():
                flags[(i, col)] = "amarelo"
                problemas.append({"Colaborador": nome, "Campo": col,
                                  "Situação": "CAMPO VAZIO — VERIFICAR", "Gravidade": "Atenção"})
    return flags, problemas


def estilizar(df: pd.DataFrame, flags: dict):
    def _estilo(_df):
        estilo = pd.DataFrame("", index=_df.index, columns=_df.columns)
        for (i, col), cor in flags.items():
            if i in estilo.index and col in estilo.columns:
                estilo.at[i, col] = f"background-color: {CORES[cor]}; font-weight: 600;"
        return estilo
    return df.style.apply(_estilo, axis=None)


def gerar_csv(df: pd.DataFrame, encoding: str) -> bytes:
    return df.to_csv(sep=";", index=False, lineterminator="\r\n").encode(encoding)


# ----------------------------------------------------------------------------
# LEITURA DE ARQUIVOS
# ----------------------------------------------------------------------------
def ler_planilha(upload) -> pd.DataFrame:
    nome = upload.name.lower()
    if nome.endswith((".xls", ".xlsx")):
        return pd.read_excel(upload)
    # txt / dat / csv
    bruto = upload.read()
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            texto_bruto = bruto.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto_bruto = bruto.decode("latin-1", errors="replace")
    amostra = texto_bruto[:4096]
    sep = max([";", ",", "\t", "|"], key=lambda s: amostra.count(s))
    return pd.read_csv(io.StringIO(texto_bruto), sep=sep, dtype=str)


# ----------------------------------------------------------------------------
# ABA 1 — ADMISSÃO
# ----------------------------------------------------------------------------
def aba_admissao():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1️⃣ Envie a planilha do sistema Domínio")
    upload = st.file_uploader(
        "Planilha de empregados exportada do Domínio",
        type=["xls", "xlsx", "csv", "txt", "dat"],
        help="Aceita o arquivo .xls exportado do Domínio (Empregados em Excel) ou CSV/TXT.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if upload is None:
        st.info("👆 Envie a planilha do Domínio para gerar o cadastro automaticamente.")
        return

    try:
        df_dom = ler_planilha(upload)
    except Exception as e:
        st.error(f"Não foi possível ler o arquivo: `{e}`")
        return

    faltando = [c for c in ["Nome", "CPF", "Admissão", "Nome Mãe", "Data nascimento",
                            "Email", "Celular", "Salário", "Descrição Ccusto", "Cep"]
                if c not in df_dom.columns]
    if faltando:
        st.warning(f"Colunas não encontradas na planilha: `{', '.join(faltando)}` — "
                   "esses campos sairão com os valores padrão.")

    with st.spinner("Processando colaboradores..."):
        df_out = processar_dominio(df_dom)

    st.session_state["df_original"] = df_out
    if "df_editado" not in st.session_state or st.session_state.get("fonte") != upload.name:
        st.session_state["df_editado"] = df_out.copy()
        st.session_state["fonte"] = upload.name

    df_atual = st.session_state["df_editado"]
    flags, problemas = validar(df_atual)
    n_crit = sum(1 for p in problemas if p["Gravidade"] == "Crítico")
    n_aten = sum(1 for p in problemas if p["Gravidade"] == "Atenção")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2️⃣ Resultado do processamento")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Colaboradores", len(df_atual))
    c2.metric("Campos preenchidos automaticamente", "18 colunas")
    c3.metric("⚠ Críticos (vermelho)", n_crit)
    c4.metric("Atenção (amarelo)", n_aten)
    if n_crit == 0 and n_aten == 0:
        st.markdown('<span class="pill-ok">✅ TUDO CERTO — NENHUM PROBLEMA ENCONTRADO</span>',
                    unsafe_allow_html=True)
    elif n_crit:
        st.markdown('<span class="pill-err">⚠ HÁ PENDÊNCIAS CRÍTICAS — CONFIRA ABAIXO</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill-warn">HÁ PONTOS DE ATENÇÃO — CONFIRA ABAIXO</span>',
                    unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if problemas:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🚨 Quem deu problema")
        st.dataframe(pd.DataFrame(problemas), use_container_width=True,
                     hide_index=True, height=min(60 + 35 * len(problemas), 400))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👁️ Pré-visualização (células coloridas = verificar)")
    st.dataframe(estilizar(df_atual, flags), use_container_width=True, height=380)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("✏️ Precisa editar alguma informação? Clique aqui (edição manual antes de baixar)"):
        st.caption("Edite as células diretamente na grade abaixo. As cores e o relatório "
                   "de problemas são recalculados automaticamente após a edição.")
        editado = st.data_editor(
            df_atual, num_rows="dynamic", use_container_width=True, height=420,
            key="editor_admissao",
        )
        col_a, col_b = st.columns([1, 4])
        if col_a.button("💾 Salvar edições", type="primary"):
            st.session_state["df_editado"] = editado
            st.success("Edições salvas! A pré-visualização e os problemas foram atualizados.")
            st.rerun()
        if col_b.button("↩️ Descartar edições e voltar ao processamento original"):
            st.session_state["df_editado"] = st.session_state["df_original"].copy()
            st.rerun()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3️⃣ Baixar o CSV para o Kesh Bank")
    enc = st.selectbox("Codificação do arquivo", ["utf-8", "latin-1"], index=0,
                       help="Se o banco não reconhecer o arquivo, tente latin-1.")
    csv_bytes = gerar_csv(df_atual, enc)
    st.download_button(
        "⬇️ BAIXAR CSV DE ADMISSÃO — KESH BANK",
        data=csv_bytes,
        file_name="admissao_kesh_bank.csv",
        mime="text/csv",
        type="primary",
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# ABA 2 — CONVERSOR PARA CSV
# ----------------------------------------------------------------------------
def aba_conversor():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔄 Conversor de arquivos para CSV")
    st.caption("Converta XLS, XLSX, TXT, DAT e outros formatos para CSV.")
    upload = st.file_uploader(
        "Arquivo para converter",
        type=["xls", "xlsx", "csv", "txt", "dat", "tsv"],
        key="conv_upload",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if upload is None:
        st.info("👆 Envie um arquivo para converter em CSV.")
        return

    nome = upload.name.lower()
    try:
        if nome.endswith((".xls", ".xlsx")):
            xls = pd.ExcelFile(upload)
            aba = st.selectbox("Planilha (aba)", xls.sheet_names) if len(xls.sheet_names) > 1 else xls.sheet_names[0]
            df = xls.parse(aba, dtype=str)
        else:
            bruto = upload.read()
            enc = st.selectbox("Codificação de origem", ["utf-8", "latin-1", "cp1252"], index=0)
            try:
                texto_bruto = bruto.decode(enc)
            except UnicodeDecodeError:
                texto_bruto = bruto.decode("latin-1", errors="replace")
                st.warning("Codificação incompatível — lido como `latin-1`.")
            sep = st.selectbox("Separador de origem",
                               ["Detectar automaticamente", ";", ",", "Tab", "|"])
            if sep == "Detectar automaticamente":
                amostra = texto_bruto[:4096]
                sep = max([";", ",", "\t", "|"], key=lambda s: amostra.count(s))
            elif sep == "Tab":
                sep = "\t"
            df = pd.read_csv(io.StringIO(texto_bruto), sep=sep, dtype=str)
    except Exception as e:
        st.error(f"Não foi possível ler o arquivo: `{e}`")
        return

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Pré-visualização")
    c1, c2 = st.columns(2)
    c1.metric("Linhas", len(df))
    c2.metric("Colunas", len(df.columns))
    st.dataframe(df, use_container_width=True, height=360)

    sep_out = st.selectbox("Separador do CSV de saída", [";", ",", "Tab"], index=0)
    sep_out = "\t" if sep_out == "Tab" else sep_out
    enc_out = st.selectbox("Codificação do CSV de saída", ["utf-8", "latin-1"], index=0)
    nome_saida = re.sub(r"\.[^.]+$", "", upload.name) + ".csv"
    st.download_button(
        "⬇️ BAIXAR CSV CONVERTIDO",
        data=df.to_csv(sep=sep_out, index=False, lineterminator="\r\n").encode(enc_out),
        file_name=nome_saida,
        mime="text/csv",
        type="primary",
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    hero()
    with st.sidebar:
        st.image("logo.png", width=140)
        st.markdown("## Admissão Kesh Bank")
        st.markdown("**Lider Limpe** · RH / DP")
        st.markdown("---")
        st.markdown(
            "**Como usar**\n"
            "1. Exporte os empregados do Domínio (.xls)\n"
            "2. Envie na aba **Admissão**\n"
            "3. Confira os alertas em vermelho/amarelo\n"
            "4. Edite se precisar e baixe o CSV\n\n"
            "Use a aba **Conversor** para transformar qualquer XLS/TXT/DAT em CSV."
        )
        st.markdown("---")
        st.caption("CEPs consultados automaticamente via ViaCEP.")

    aba1, aba2 = st.tabs(["📋 Admissão — Domínio → Kesh Bank", "🔄 Conversor para CSV"])
    with aba1:
        aba_admissao()
    with aba2:
        aba_conversor()


if __name__ == "__main__":
    main()
