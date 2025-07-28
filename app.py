import streamlit as st
import pandas as pd
import unicodedata
import re
import io
from fpdf import FPDF
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Pré-Projeto Solar",
    page_icon="⚡",
    layout="wide"
)

# --- CSS Customizado ---
st.markdown("""
<style>
    .main { background-color: #f7f9fb; }
    .st-emotion-cache-16txtl3 { padding-top: 1.5rem; }
    h1 { color: #ff6347; }
    .st-sidebar .st-emotion-cache-1v0mbdj a { color: #ff6347; }
</style>
""", unsafe_allow_html=True)


# --- Funções Utilitárias ---

def padronizar_nome(texto):
    if not isinstance(texto, str):
        return texto
    texto = re.sub(r'\s*\([^)]*\)', '', texto)
    texto_normalizado = unicodedata.normalize('NFKD', texto)\
        .encode('ascii', 'ignore')\
        .decode('utf-8')\
        .strip().lower()
    return re.sub(r'\s+', '_', texto_normalizado)

def parse_carga_range(range_str):
    if not isinstance(range_str, str) or range_str.strip() == '-':
        return 0.0, 0.0
    try:
        range_str = range_str.replace(',', '.').strip()
        parts = [p.strip() for p in range_str.split('-')]
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
        elif len(parts) == 1 and parts[0]:
            val = float(parts[0])
            return val, val
        else:
            return 0.0, 0.0
    except:
        return 0.0, 0.0

# NOVA VERSÃO "À PROVA DE BALAS" DA FUNÇÃO
def parse_potencia_numerica(texto_potencia):
    """
    Função super robusta para extrair o primeiro número de uma string.
    Ignora letras, aspas e a maior parte do lixo.
    """
    if not isinstance(texto_potencia, str):
        return None

    # Procura por um padrão de número (dígitos com opcionalmente um ponto ou vírgula)
    match = re.search(r'[\d,.]+', texto_potencia)
    
    if match:
        try:
            # Pega o número encontrado, troca vírgula por ponto e converte para float
            numero_str = match.group(0).replace(',', '.')
            return float(numero_str)
        except (ValueError, TypeError):
            return None
    return None


def gerar_pdf(nome_cliente, cidade, tensao, tipo_ligacao, carga, categoria, disjuntor, potencia_max):
    # (Sua função de gerar PDF continua igual)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 99, 71)
    pdf.cell(0, 10, "Relatório de Pré-Projeto Solar", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0)
    pdf.ln(10)
    pdf.cell(0, 10, f"Cliente: {nome_cliente}", ln=True)
    pdf.cell(0, 10, f"Data da análise: {datetime.today().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 10, f"Cidade: {cidade}", ln=True)
    pdf.cell(0, 10, f"Tensão da rede: {tensao}", ln=True)
    pdf.cell(0, 10, f"Tipo de ligação: {tipo_ligacao}", ln=True)
    pdf.cell(0, 10, f"Carga instalada: {carga:.2f} kW", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Resultado da Análise:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Categoria: {categoria}", ln=True)
    pdf.cell(0, 10, f"Disjuntor recomendado: {disjuntor} A", ln=True)
    if potencia_max and potencia_max.strip() != "-":
        pdf.cell(0, 10, f"Potência máxima permitida para geração: {potencia_max}", ln=True)
    else:
        pdf.cell(0, 10, "Não há limite de potência definido para esta categoria.", ln=True)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# --- Carregamento de Dados ---
@st.cache_data
def carregar_dados():
    try:
        df_tensao = pd.read_csv("municipios_tensao.csv", sep=r'\s*,\s*', engine='python')
        df_disjuntores = pd.read_csv("tabela_disjuntores.csv", sep=r'\s*,\s*', engine='python')
        df_potencia_max = pd.read_csv("tabela_potencia_maxima.csv", sep=r'\s*,\s*', engine='python')
    except FileNotFoundError as e:
        st.error(f"Erro: {e}")
        return None, None

    for df in [df_tensao, df_disjuntores, df_potencia_max]:
        df.columns = [padronizar_nome(col) for col in df.columns]
        if 'tensao' in df.columns:
            df['tensao'] = df['tensao'].astype(str).str.strip().str.replace('V$', '', regex=True)

    if 'carga_instalada' in df_disjuntores.columns:
        cargas = df_disjuntores['carga_instalada'].apply(parse_carga_range)
        df_disjuntores[['carga_min_kw', 'carga_max_kw']] = pd.DataFrame(cargas.tolist(), index=df_disjuntores.index)
    else:
        st.error("Erro: Coluna 'Carga Instalada' não encontrada.")
        return None, None

    df_dados_tecnicos = pd.merge(df_disjuntores, df_potencia_max, on=['tensao', 'categoria'], how='left')
    df_tensao['municipio'] = df_tensao['municipio'].str.strip().apply(padronizar_nome)

    coluna_pot = [col for col in df_dados_tecnicos.columns if 'potencia_maxima' in col]
    if coluna_pot:
        df_dados_tecnicos.rename(columns={coluna_pot[0]: 'potencia_maxima_geracao_str'}, inplace=True)
    else:
        st.error("Erro: Coluna de potência máxima não encontrada.")
        return None, None

    return df_tensao, df_dados_tecnicos

df_tensao, df_dados_tecnicos = carregar_dados()
if df_tensao is None or df_dados_tecnicos is None:
    st.stop()

# --- Interface do Usuário ---
# (Sua interface continua a mesma)
try:
    st.sidebar.image("imagens/logo.png", width=200)
except Exception:
    st.sidebar.warning("Logo não encontrada.")

st.sidebar.header("Identificação do Cliente")
nome_cliente = st.sidebar.text_input("Digite o nome do cliente:")

st.sidebar.header("Parâmetros do Projeto")
mapa_ligacao = {
    "Monofásico": ["M0", "M1", "M2", "M3"],
    "Bifásico": ["B0", "B1", "B2"],
    "Trifásico": [f"T{i}" for i in range(13)]
}
lista_cidades = sorted(df_tensao["municipio"].str.title().unique())
cidade_selecionada_fmt = st.sidebar.selectbox("Selecione a cidade:", lista_cidades)
cidade_selecionada_norm = padronizar_nome(cidade_selecionada_fmt)
tensao_info = df_tensao.loc[df_tensao["municipio"] == cidade_selecionada_norm, "tensao"]
tensao = tensao_info.values[0] if not tensao_info.empty else "Não encontrada"
st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga_instalada = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1, format="%.2f")
tipo_ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

if "220/127" in tensao and tipo_ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Para tensão 220/127V, use pelo menos Bifásico.")

st.sidebar.header("Dados do Kit Solar")
potencia_kit_kwp = st.sidebar.number_input(
    "Potência do Kit (kWp):",
    min_value=0.0,
    step=0.01,
    format="%.2f",
    help="Informe a potência de pico do kit que planeja instalar."
)


# --- Lógica Principal ---
st.title("⚡ Pré-Projeto Solar")

if st.sidebar.button("🔍 Gerar Análise", use_container_width=True, type="primary"):
    if not nome_cliente.strip():
        st.sidebar.warning("Por favor, informe o nome do cliente.")
    elif tensao == "Não encontrada":
        st.error(f"Não foi possível encontrar dados para '{cidade_selecionada_fmt}'.")
    else:
        with st.spinner('Analisando dados...'):
            categorias_permitidas = mapa_ligacao[tipo_ligacao]
            df_faixa_encontrada = df_dados_tecnicos[
                (df_dados_tecnicos["tensao"] == tensao) &
                (df_dados_tecnicos["categoria"].isin(categorias_permitidas)) &
                (carga_instalada >= df_dados_tecnicos["carga_min_kw"]) &
                (carga_instalada <= df_dados_tecnicos["carga_max_kw"])
            ]

            st.subheader("📋 Resumo dos Parâmetros")
            col1, col2, col3 = st.columns(3)
            col1.metric("📍 Cidade", cidade_selecionada_fmt)
            col2.metric("🔌 Tensão", tensao)
            col3.metric("🔧 Ligação", tipo_ligacao)
            st.divider()

            st.subheader("📝 Resultados da Análise")
            st.write(f"**Carga instalada:** {carga_instalada:.2f} kW")

            if not df_faixa_encontrada.empty:
                resultado = df_faixa_encontrada.iloc[0]
                faixa_nome = resultado["categoria"]
                disjuntor = resultado.get("disjuntor", "N/A")
                potencia_max_str = resultado.get('potencia_maxima_geracao_str', '-')

                st.success("✅ Análise concluída com sucesso!")
                st.write(f"**Categoria**: `{faixa_nome}`")
                st.write(f"**Disjuntor recomendado**: `{disjuntor} A`")
                
                # NOVO BLOCO DE DIAGNÓSTICO FINAL
                with st.expander("🕵️‍♀️ DIAGNÓSTICO FINAL (Clique aqui) 🕵️‍♀️"):
                    valor_lido_raw = resultado.get('potencia_maxima_geracao_str', 'NÃO ENCONTRADO')
                    st.warning("Abaixo está o valor EXATO que o programa leu do seu CSV.")
                    st.code(repr(valor_lido_raw), language="python")
                    st.info(f"O tipo deste dado é: {type(valor_lido_raw)}")
                    
                    resultado_parse = parse_potencia_numerica(valor_lido_raw)
                    st.success(f"A nova função 'à prova de balas' converteu isso para o número: {resultado_parse}")


                # Bloco que mostra a potência máxima (original)
                if pd.notna(potencia_max_str) and potencia_max_str.strip() not in ('', '-'):
                    st.subheader("🔆 Potência Máxima Permitida para Geração")
                    st.info(f"Potência máxima para **{faixa_nome}**:")
                    st.success(f"## {potencia_max_str}")
                else:
                    st.warning("Não há limite de potência definido para esta categoria.")
                
                st.divider()

                # BLOCO PARA VALIDAR O KIT DO CLIENTE
                if potencia_kit_kwp > 0:
                    st.subheader("✔️ Validação do Kit do Cliente")
                    limite_numerico = parse_potencia_numerica(potencia_max_str)

                    if limite_numerico is not None:
                        if potencia_kit_kwp <= limite_numerico:
                            st.success(f"**APROVADO:** O kit de {potencia_kit_kwp:.2f} kWp está dentro do limite de {limite_numerico:.2f} kWp.")
                            st.balloons()
                        else:
                            st.error(f"**REPROVADO:** O kit de {potencia_kit_kwp:.2f} kWp excede o limite de {limite_numerico:.2f} kWp.")
                    else:
                        st.success(f"**APROVADO:** O kit de {potencia_kit_kwp:.2f} kWp é compatível, pois não há limite de potência para esta categoria.")

                # --- Download do PDF ---
                pdf_buffer = gerar_pdf(
                    nome_cliente, cidade_selecionada_fmt, tensao, tipo_ligacao,
                    carga_instalada, faixa_nome, disjuntor, potencia_max_str
                )
                st.download_button(...) # Sua função de download
            else:
                st.error("❌ Faixa não encontrada.")
                st.markdown("- Verifique a carga instalada.\n- Confirme se a tensão e tipo de ligação são válidos.")

else:
    st.info("👈 Preencha os dados e clique em 'Gerar Análise' para começar.")

st.caption("Desenvolvido por Vitória de Sales Sena ⚡")
