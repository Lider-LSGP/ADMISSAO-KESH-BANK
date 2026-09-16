# -*- coding: utf-8 -*-
"""
ADMISSÃO KESH BANK — Lider Limpe
App Streamlit para gerar o CSV de cadastro de novos colaboradores admitidos
no banco Kesh Bank, a partir da planilha do sistema Domínio ou da planilha
do Sistema Interno de Admissão (AppLider / "Importar Layout").
Os resultados são separados por empresa: ATIVA, LIDER LIMPE,
LIDER MULTISSERVIÇOS e VSP.
"""

import io
import re
import unicodedata
import zipfile

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

EMPRESAS = ["ATIVA", "LIDER LIMPE", "LIDER MULTISSERVIÇOS", "VSP"]

# Sugestão de empresa por código do Domínio (Cód Emp) — ajustável na tela
MAPA_DOMINIO_PADRAO = {1: "VSP", 2: "ATIVA", 3: "LIDER MULTISSERVIÇOS", 4: "LIDER LIMPE"}

# Mapeamento: coluna de saída -> coluna de origem (endereço = fallback quando o CEP não responde)
MAPA_DOMINIO = {
    "NOME": "Nome", "CPF/CNPJ": "CPF", "DATA_ADMISSAO": "Admissão",
    "NOME_MAE": "Nome Mãe", "DATA_NASCIMENTO": "Data nascimento",
    "E-MAIL": "Email", "CELULAR": "Celular", "SALARIO": "Salário",
    "LOTACAO": "Descrição Ccusto", "CEP": "Cep", "ESTADO": "UF End", "CIDADE": "Cidade",
    "BAIRRO": "Bairro", "RUA": "Endereço", "NUMERO": "Numero",
    "COMPLEMENTO": "Complemento", "_EMPRESA": "Cód Emp",
}
MAPA_INTERNO = {
    "NOME": "nome", "CPF/CNPJ": "cnpj_cpf", "DATA_ADMISSAO": "dataadmissao",
    "NOME_MAE": "nomemae", "DATA_NASCIMENTO": "datanascimento",
    "E-MAIL": "email", "CELULAR": "celular", "SALARIO": "salariobase",
    "LOTACAO": "nomepostotrabalho", "CEP": "cep", "ESTADO": "uf", "CIDADE": "cidadeparceiro",
    "BAIRRO": "bairro", "RUA": "rua", "NUMERO": "numero",
    "COMPLEMENTO": "complemento", "_EMPRESA": "nomeempresa",
}

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
    /* Tema forçado para claro: evita letra branca em fundo branco em outros PCs */
    .stApp { background: linear-gradient(180deg, #f4f6fb 0%, #ffffff 40%) !important; color: #1a1a2e; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span,
    .stApp label, .stApp li, .stApp td, .stApp th, .stApp div { color: #1a1a2e; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #001975 0%, #00289e 100%) !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #1a1a2e !important; }
    [data-testid="stTabs"] button p { color: #1a1a2e !important; }
    [data-testid="stTabs"] button[aria-selected="true"] p { color: #ff5500 !important; }
    [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] * { color: #1a1a2e; }
    .hero {
        background: linear-gradient(120deg, #001975 0%, #003ba1 70%, #0a4fc4 100%);
        border-radius: 18px; padding: 26px 32px; margin-bottom: 18px;
        display: flex; align-items: center; gap: 22px;
        box-shadow: 0 8px 24px rgba(0, 25, 117, .25);
    }
    .hero h1 { color: #ffffff !important; margin: 0; font-size: 2rem; font-weight: 800; }
    .hero p { color: #ffd9c7 !important; margin: 4px 0 0 0; font-size: 1.02rem; }
    .hero img { border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,.35); }
    .card {
        background: #ffffff; border: 1px solid #e6eaf5; border-radius: 14px;
        padding: 18px 22px; margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0, 25, 117, .06);
    }
    .card, .card p, .card span, .card label, .card h1, .card h2, .card h3, .card li { color: #1a1a2e !important; }
    .pill-ok  { background:#e6f9ed; color:#0c7a3d !important; border-radius:20px; padding:4px 14px; font-weight:700; }
    .pill-warn{ background:#fff3bf; color:#9a6b00 !important; border-radius:20px; padding:4px 14px; font-weight:700; }
    .pill-err { background:#ffd7d7; color:#b30000 !important; border-radius:20px; padding:4px 14px; font-weight:700; }
    div[data-testid="stDownloadButton"] button, .stButton > button {
        background: linear-gradient(120deg, #ff5500, #ff7733); color: #fff !important;
        border: none; border-radius: 10px; font-weight: 700; padding: .55rem 1.4rem;
    }
    div[data-testid="stDownloadButton"] button *, .stButton > button * { color: #fff !important; }
    div[data-testid="stDownloadButton"] button:hover, .stButton > button:hover {
        background: linear-gradient(120deg, #e04b00, #ff5500);
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
                <p>Lider Limpe · Geração automática do CSV de cadastro de novos colaboradores (Domínio ou Sistema Interno), separado por empresa</p>
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


def limpar_especiais(s: str, manter: str = "") -> str:
    """Remove caracteres especiais, mantendo apenas letras, números, espaço
    e os caracteres informados em `manter` (ex.: '/' nas datas)."""
    s = re.sub(r"\s+", " ", s).strip()
    return "".join(c for c in s if c.isalnum() or c == " " or c in manter)


def texto(v, maiusculo=True) -> str:
    s = num_str(v)
    s = sem_acentos(s)
    s = limpar_especiais(s)
    return s.upper() if maiusculo else s.lower()


def fmt_email(v) -> str:
    s = sem_acentos(num_str(v)).lower()
    s = re.sub(r"[^a-z0-9@.\-_]", "", s)
    return s


def fmt_cpf(v) -> str:
    d = so_digitos(num_str(v))
    return d.zfill(11) if d else ""


def fmt_celular(v):
    """Retorna (celular, status). Qualquer erro (vazio, nº de dígitos
    diferente de 11) -> número padrão. Status: ok | padrao."""
    d = so_digitos(num_str(v))
    if not d:
        return CELULAR_PADRAO, "padrao"
    while len(d) > 11 and d.startswith("0"):
        d = d[1:]
    if len(d) == 12 and d.startswith("0"):
        d = d[1:]
    if len(d) != 11:
        return CELULAR_PADRAO, "padrao"
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
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return ""
    # Aceita DD/MM/AAAA e AAAA-MM-DD
    ts = pd.to_datetime(s, dayfirst=("-" not in s[:5]), errors="coerce")
    return ts.strftime("%d/%m/%Y") if pd.notna(ts) else ""


def limpar_caracteres(s: str, permitidos: str = "") -> str:
    """Remove qualquer caractere especial, mantendo letras, números, espaço
    e os caracteres extras informados em `permitidos`."""
    if not s:
        return s
    return re.sub(r"[^A-Za-z0-9 " + re.escape(permitidos) + "]", "", s)


def fmt_lotacao(v) -> str:
    """Mantém apenas a parte antes do '-' (ex.: 'SUZANO - PORTARIA' -> 'SUZANO')."""
    s = texto(v)
    return s.split("-")[0].strip() if s else ""


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
# EMPRESAS
# ----------------------------------------------------------------------------
def sugerir_empresa(valor, origem: str) -> str:
    """Sugere a empresa a partir do Cód Emp (Domínio) ou nomeempresa (Sistema Interno)."""
    if origem == "dominio":
        try:
            cod = int(float(num_str(valor)))
            return MAPA_DOMINIO_PADRAO.get(cod, "LIDER LIMPE")
        except Exception:
            return "LIDER LIMPE"
    t = sem_acentos(str(valor)).upper()
    if "MULTISERVICO" in t:
        return "LIDER MULTISSERVIÇOS"
    if "ATIVA" in t:
        return "ATIVA"
    if "VSP" in t:
        return "VSP"
    if "LIDER" in t or "LIMPE" in t:
        return "LIDER LIMPE"
    return "LIDER LIMPE"


# ----------------------------------------------------------------------------
# PROCESSAMENTO PRINCIPAL (serve para Domínio e Sistema Interno)
# ----------------------------------------------------------------------------
def processar(df: pd.DataFrame, mapa: dict, mapa_emp: dict) -> pd.DataFrame:
    """Gera o dataframe de saída no layout do Kesh Bank + coluna _EMPRESA."""
    df.columns = [str(c).strip() for c in df.columns]
    col_emp = mapa["_EMPRESA"]

    def campo(row, saida):
        col = mapa.get(saida)
        return row.get(col) if col in df.columns else None

    # Pré-busca dos CEPs (com barra de progresso)
    ceps = []
    for _, row in df.iterrows():
        cep = fmt_cep(campo(row, "CEP")) or CEP_EMPRESA
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
        cep = fmt_cep(campo(row, "CEP"))
        via = info_cep.get(cep) if cep else None
        if not cep:
            # Sem CEP na planilha: usa o CEP da empresa e o endereço dele
            cep_final = CEP_EMPRESA
            via_final = info_cep.get(CEP_EMPRESA) or {}
        elif via is None:
            # CEP informado mas não localizado no ViaCEP: mantém o CEP do
            # colaborador e usa os dados de endereço da própria planilha
            cep_final, via_final = cep, {}
        else:
            cep_final, via_final = cep, via

        celular, _status_cel = fmt_celular(campo(row, "CELULAR"))
        empresa = mapa_emp.get(num_str(row.get(col_emp)), mapa_emp.get(str(row.get(col_emp)), "LIDER LIMPE"))

        reg = {
            "_EMPRESA": empresa,
            "OPERACAO": "NOVO",
            "NOME": texto(campo(row, "NOME")),
            "CPF/CNPJ": fmt_cpf(campo(row, "CPF/CNPJ")),
            "DATA_ADMISSAO": fmt_data(campo(row, "DATA_ADMISSAO")),
            "NOME_MAE": texto(campo(row, "NOME_MAE")),
            "DATA_NASCIMENTO": fmt_data(campo(row, "DATA_NASCIMENTO")),
            "E-MAIL": fmt_email(campo(row, "E-MAIL")) or EMAIL_PADRAO,
            "CELULAR": celular,
            "SALARIO": fmt_salario(campo(row, "SALARIO")),
            "LOTACAO": fmt_lotacao(campo(row, "LOTACAO")),
            "CEP": cep_final,
            "PAIS": "BRASIL",
            "ESTADO": texto(via_final.get("uf", "")) or texto(campo(row, "ESTADO")),
            "CIDADE": texto(via_final.get("localidade", "")) or texto(campo(row, "CIDADE")),
            "BAIRRO": texto(via_final.get("bairro", "")) or texto(campo(row, "BAIRRO")),
            "RUA": texto(via_final.get("logradouro", "")) or texto(campo(row, "RUA")),
            "NUMERO": texto(via_final.get("numero", "")) or num_str(campo(row, "NUMERO")) or "SN",
            "COMPLEMENTO": texto(via_final.get("complemento", "")) or texto(campo(row, "COMPLEMENTO")),
        }
        registros.append(reg)

    return sanitizar_df(pd.DataFrame(registros, columns=["_EMPRESA"] + COLS_SAIDA))


# ----------------------------------------------------------------------------
# VALIDAÇÃO / ESTILO / CSV
# ----------------------------------------------------------------------------
def sanitizar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o tratamento padrão (maiúsculas, sem acentos, sem caracteres
    especiais, formatos) — usado no processamento e nas edições manuais."""
    df = df.copy()
    for col in df.columns:
        if col == "_EMPRESA":
            df[col] = df[col].apply(lambda v: limpar_caracteres(texto(v)))
        elif col == "E-MAIL":
            df[col] = df[col].apply(fmt_email)
        elif col == "CPF/CNPJ":
            df[col] = df[col].apply(fmt_cpf)
        elif col == "CELULAR":
            df[col] = df[col].apply(lambda v: fmt_celular(v)[0])
        elif col == "SALARIO":
            df[col] = df[col].apply(fmt_salario)
        elif col == "LOTACAO":
            df[col] = df[col].apply(lambda v: limpar_caracteres(fmt_lotacao(v)))
        elif col == "CEP":
            df[col] = df[col].apply(fmt_cep)
        elif col in ("DATA_ADMISSAO", "DATA_NASCIMENTO"):
            df[col] = df[col].apply(fmt_data)
        else:
            df[col] = df[col].apply(lambda v: limpar_caracteres(texto(v)))
    if "OPERACAO" in df.columns:
        df["OPERACAO"] = "NOVO"
    if "PAIS" in df.columns:
        df["PAIS"] = "BRASIL"
    if "NUMERO" in df.columns:
        df["NUMERO"] = df["NUMERO"].apply(lambda v: v if str(v).strip() else "SN")
    return df


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
                problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": col,
                                  "Situação": "⚠ FALTANDO INFORMAÇÃO", "Gravidade": "Crítico"})
        if row["CPF/CNPJ"] and len(so_digitos(row["CPF/CNPJ"])) != 11:
            flags[(i, "CPF/CNPJ")] = "vermelho"
            problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": "CPF/CNPJ",
                              "Situação": "⚠ CPF NÃO TEM 11 DÍGITOS", "Gravidade": "Crítico"})
        if row["CELULAR"] == CELULAR_PADRAO:
            flags[(i, "CELULAR")] = "vermelho"
            problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": "CELULAR",
                              "Situação": "⚠ CELULAR NÃO INFORMADO — USADO NÚMERO PADRÃO", "Gravidade": "Crítico"})
        # Amarelo — valores padrão assumidos
        if row["E-MAIL"] == EMAIL_PADRAO or not str(row["E-MAIL"]).strip():
            flags[(i, "E-MAIL")] = "amarelo"
            problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": "E-MAIL",
                              "Situação": "E-MAIL NÃO INFORMADO — USADO E-MAIL PADRÃO", "Gravidade": "Atenção"})
        if row["CEP"] == CEP_EMPRESA:
            flags[(i, "CEP")] = "amarelo"
            problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": "CEP",
                              "Situação": "CEP NÃO LOCALIZADO — USADO CEP DA EMPRESA", "Gravidade": "Atenção"})
        for col in ["ESTADO", "CIDADE", "BAIRRO", "RUA", "NUMERO", "SALARIO"]:
            if not str(row[col]).strip():
                flags[(i, col)] = "amarelo"
                problemas.append({"Empresa": row["_EMPRESA"], "Colaborador": nome, "Campo": col,
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
    """CSV final no layout Kesh Bank (sem a coluna interna _EMPRESA)."""
    saida = df.drop(columns=["_EMPRESA"], errors="ignore")
    return saida.to_csv(sep=";", index=False, lineterminator="\r\n").encode(encoding)


def nome_arquivo(empresa: str) -> str:
    return f"admissao_kesh_bank_{sem_acentos(empresa).replace(' ', '_')}.csv"


def gerar_zip(df: pd.DataFrame, encoding: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for empresa in df["_EMPRESA"].unique():
            sub = df[df["_EMPRESA"] == empresa]
            z.writestr(nome_arquivo(empresa), gerar_csv(sub, encoding))
    return buf.getvalue()


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
    st.subheader("1️⃣ Escolha a origem e envie a planilha")
    origem_rotulo = st.radio(
        "De onde vem a planilha?",
        ["📊 Domínio (Arquivo Domínio)", "🖥️ Sistema Interno — AppLider (Importar Layout)"],
        horizontal=True,
    )
    origem = "dominio" if origem_rotulo.startswith("📊") else "interno"
    upload = st.file_uploader(
        "Planilha de empregados" if origem == "dominio" else "Planilha Importar Layout (AppLider)",
        type=["xls", "xlsx", "csv", "txt", "dat"],
        help="Domínio: arquivo .xls 'Empregados em Excel'. Sistema Interno: .xlsx 'Importar Layout'.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if upload is None:
        st.info("👆 Envie a planilha para gerar o cadastro automaticamente.")
        return

    try:
        df_in = ler_planilha(upload)
    except Exception as e:
        st.error(f"Não foi possível ler o arquivo: `{e}`")
        return
    df_in.columns = [str(c).strip() for c in df_in.columns]

    mapa = MAPA_DOMINIO if origem == "dominio" else MAPA_INTERNO
    obrig_origem = [mapa[c] for c in ["NOME", "CPF/CNPJ", "DATA_ADMISSAO", "NOME_MAE",
                                      "DATA_NASCIMENTO", "E-MAIL", "CELULAR", "SALARIO",
                                      "LOTACAO", "CEP"]]
    faltando = [c for c in obrig_origem if c not in df_in.columns]
    if faltando:
        st.warning(f"Colunas não encontradas na planilha: `{', '.join(faltando)}` — "
                   "esses campos sairão com os valores padrão.")

    # ---------------- Identificação das empresas ----------------
    col_emp = mapa["_EMPRESA"]
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2️⃣ Confirme a empresa de cada grupo")
    if col_emp in df_in.columns:
        chaves = df_in[col_emp].apply(num_str).unique().tolist()
        st.caption("Empresas detectadas na planilha — confira e ajuste se necessário:")
        mapa_emp = {}
        cols = st.columns(min(len(chaves), 4) or 1)
        for i, chave in enumerate(chaves):
            sugestao = sugerir_empresa(chave, origem)
            idx = EMPRESAS.index(sugestao) if sugestao in EMPRESAS else 0
            rotulo = (f"Cód Emp {chave}" if origem == "dominio" else chave) or "(vazio)"
            mapa_emp[chave] = cols[i % len(cols)].selectbox(rotulo, EMPRESAS, index=idx,
                                                            key=f"emp_{origem}_{i}")
    else:
        st.caption("A planilha não tem identificação de empresa — escolha para qual empresa vai este lote:")
        escolha = st.selectbox("Empresa do lote", EMPRESAS, key="emp_unica")
        mapa_emp = {num_str(v): escolha for v in df_in.iloc[:, 0]}
        mapa_emp[""] = escolha
        col_emp = df_in.columns[0]
        mapa = dict(mapa)
        mapa["_EMPRESA"] = col_emp
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- Processamento ----------------
    chave_fonte = f"{origem}|{upload.name}|{tuple(sorted(mapa_emp.items()))}"
    if st.session_state.get("fonte") != chave_fonte:
        with st.spinner("Processando colaboradores..."):
            df_out = processar(df_in, mapa, mapa_emp)
        st.session_state["df_original"] = df_out
        st.session_state["df_editado"] = df_out.copy()
        st.session_state["fonte"] = chave_fonte
        st.session_state["editor_v"] = st.session_state.get("editor_v", 0) + 1

    df_atual = st.session_state["df_editado"]
    flags, problemas = validar(df_atual)
    n_crit = sum(1 for p in problemas if p["Gravidade"] == "Crítico")
    n_aten = sum(1 for p in problemas if p["Gravidade"] == "Atenção")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3️⃣ Resultado do processamento")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Colaboradores", len(df_atual))
    c2.metric("Empresas no lote", df_atual["_EMPRESA"].nunique())
    c3.metric("⚠ Críticos (vermelho)", n_crit)
    c4.metric("Atenção (amarelo)", n_aten)
    contagem = df_atual["_EMPRESA"].value_counts()
    st.markdown("**Por empresa:** " + " · ".join(f"`{e}`: **{n}**" for e, n in contagem.items()))
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
        st.caption("Edite as células diretamente na grade abaixo. Ao salvar, tudo passa pelo "
                   "tratamento padrão (maiúsculas, sem acentos, formatos) e as cores e o "
                   "relatório de problemas são recalculados automaticamente.")
        editado = st.data_editor(
            df_atual, num_rows="dynamic", use_container_width=True, height=420,
            disabled=["_EMPRESA"],
            key=f"editor_admissao_{st.session_state.get('editor_v', 0)}",
        )
        col_a, col_b = st.columns([1, 4])
        if col_a.button("💾 Salvar edições", type="primary"):
            st.session_state["df_editado"] = sanitizar_df(editado)
            st.session_state["editor_v"] = st.session_state.get("editor_v", 0) + 1
            st.success("Edições salvas com o tratamento padrão (maiúsculas, sem acentos, "
                       "formatos de CPF/celular/CEP/salário). Pré-visualização atualizada!")
            st.rerun()
        if col_b.button("↩️ Descartar edições e voltar ao processamento original"):
            st.session_state["df_editado"] = st.session_state["df_original"].copy()
            st.session_state["editor_v"] = st.session_state.get("editor_v", 0) + 1
            st.rerun()

    # ---------------- Downloads por empresa ----------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4️⃣ Baixar os CSVs — separados por empresa")
    enc = st.selectbox("Codificação do arquivo", ["utf-8", "latin-1"], index=0,
                       help="Se o banco não reconhecer o arquivo, tente latin-1.")
    empresas_lote = df_atual["_EMPRESA"].unique().tolist()
    cols_dl = st.columns(min(len(empresas_lote), 4) or 1)
    for i, empresa in enumerate(empresas_lote):
        sub = df_atual[df_atual["_EMPRESA"] == empresa]
        cols_dl[i % len(cols_dl)].download_button(
            f"⬇️ {empresa} ({len(sub)})",
            data=gerar_csv(sub, enc),
            file_name=nome_arquivo(empresa),
            mime="text/csv",
            type="primary",
            key=f"dl_{empresa}",
        )
    if len(empresas_lote) > 1:
        st.download_button(
            "📦 BAIXAR TODOS (ZIP com um CSV por empresa)",
            data=gerar_zip(df_atual, enc),
            file_name="admissao_kesh_bank_todas_empresas.zip",
            mime="application/zip",
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
            "1. Escolha a origem: **Domínio** ou **Sistema Interno**\n"
            "2. Envie a planilha e confirme as empresas\n"
            "3. Confira os alertas em vermelho/amarelo\n"
            "4. Edite se precisar e baixe **um CSV por empresa**\n\n"
            "Empresas: **ATIVA · LIDER LIMPE · LIDER MULTISSERVIÇOS · VSP**\n\n"
            "Use a aba **Conversor** para transformar qualquer XLS/TXT/DAT em CSV."
        )
        st.markdown("---")
        st.caption("CEPs consultados automaticamente via ViaCEP.")

    aba1, aba2 = st.tabs(["📋 Admissão → Kesh Bank", "🔄 Conversor para CSV"])
    with aba1:
        aba_admissao()
    with aba2:
        aba_conversor()


if __name__ == "__main__":
    main()
