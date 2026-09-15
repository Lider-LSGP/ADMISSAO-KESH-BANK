# Admissão Kesh Bank — Lider Limpe

App Streamlit para gerar automaticamente o **CSV de cadastro de novos colaboradores admitidos no banco Kesh Bank** a partir da planilha de empregados exportada do sistema **Domínio**.

## Funcionalidades

### 📋 Aba Admissão (Domínio → Kesh Bank)
- Lê a planilha `.xls` exportada do Domínio (Empregados em Excel)
- Gera as 18 colunas do layout Kesh Bank, em ordem:

| Coluna Kesh Bank | Origem |
|---|---|
| OPERACAO | Valor fixo `NOVO` |
| NOME | Coluna `Nome` (vermelho ⚠ se faltar) |
| CPF/CNPJ | Coluna `CPF` — 11 dígitos com zeros à esquerda (vermelho ⚠ se faltar) |
| DATA_ADMISSAO | Coluna `Admissão` (vermelho ⚠ se faltar) |
| NOME_MAE | Coluna `Nome Mãe` (vermelho ⚠ se faltar) |
| DATA_NASCIMENTO | Coluna `Data nascimento` (vermelho ⚠ se faltar) |
| E-MAIL | Coluna `Email` — se vazio, usa `naoexiste@naoexiste.com.br` (amarelo) |
| CELULAR | Coluna `Celular` — 11 dígitos, remove o 0 antes do DDD; se vazio, usa `27999153249` (vermelho) |
| SALARIO | Coluna `Salário` — ex.: `1682.700000` → `1682,70` |
| LOTACAO | Coluna `Descrição Ccusto` |
| CEP | Coluna `Cep` — se vazio, usa o CEP da empresa `29108-375` (amarelo) |
| PAIS | Valor fixo `BRASIL` |
| ESTADO / CIDADE / BAIRRO / RUA / COMPLEMENTO | Consulta automática via **ViaCEP**; se não houver retorno, usa as colunas `Cidade`, `Bairro`, `Endereço`, `Complemento` da planilha |
| NUMERO | Coluna `Numero` da planilha |

- Tudo em **letras maiúsculas**, sem acentos e sem ç — exceto o e-mail (minúsculas)
- **Painel de problemas**: lista quem deu problema, campo a campo
- **Pré-visualização colorida**: vermelho = crítico, amarelo = atenção
- **Tela de edição manual** antes de baixar (cores e problemas recalculados ao salvar)
- Download do CSV final (`;` separador, pronto para o Kesh Bank)

### 🔄 Aba Conversor
Converte **XLS, XLSX, TXT, DAT, CSV, TSV** em CSV, com escolha de separador e codificação.

## Deploy no Streamlit Community Cloud (via GitHub)

1. Crie um repositório no GitHub e suba **todos os arquivos desta pasta**:
   - `app.py`
   - `logo.png`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
2. Acesse [share.streamlit.io](https://share.streamlit.io) e entre com sua conta GitHub
3. Clique em **New app** → escolha o repositório, branch `main` e o arquivo `app.py`
4. Clique em **Deploy** — em ~2 minutos o app estará no ar com um link público

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Observações
- A consulta de CEP usa a API pública do [ViaCEP](https://viacep.com.br) (necessário acesso à internet).
- Nenhum dado é armazenado: o processamento acontece apenas em memória durante a sessão.
