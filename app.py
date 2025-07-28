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

def parse_potencia_numerica(texto_potencia):
    """Extrai um valor numérico de uma string de potência como '15 kW'."""
    if not isinstance(texto_potencia, str) or texto_potencia.strip() == '-':
        return None
    try:
        texto_limpo = re.sub(r'(?i)\s*(kw|kva)', '', texto_potencia).strip()
        texto_limpo = texto_limpo.replace(',', '.')
        return float(texto_limpo)
    except (ValueError, TypeError):
        return None

def gerar_pdf(nome_cliente, cidade, tensao, tipo_ligacao, carga, categoria, disjuntor, potencia_max):
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
        st.error(f"Erro: Arquivo '{e.filename}' não foi encontrado. Verifique se ele está na mesma pasta do seu app.py.")
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

st.sidebar.header("Dados do Sistema Solar")
potencia_kit_kwp = st.sidebar.number_input(
    "Potência do Kit Solar (kWp):",
    min_value=0.0,
    step=0.01,
    format="%.2f",
    help="Informe a potência de pico (kWp) do sistema solar que planeja instalar. Ex: 5.54"
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
            
            if not df_faixa_encontrada.empty:
                resultado = df_faixa_encontrada.iloc[0]
                
                # NOVO: BLOCO DE DEPURAÇÃO INTELIGENTE
                # Ele verifica se o merge com a tabela de potência máxima falhou para esta categoria
                if pd.isna(resultado['potencia_maxima_geracao_str']):
                    st.error(
                        f"⚠️ Erro no Cruzamento de Dados!",
                        icon="❗"
                    )
                    st.warning(
                        f"**Alerta de Depuração:** A categoria **{resultado['categoria']}** foi encontrada, mas não foi possível localizar um limite de potência correspondente no arquivo `tabela_potencia_maxima.csv`."
                        f"\n\n**Solução:** Verifique se a combinação de `tensão` ('{resultado['tensao']}') e `categoria` ('{resultado['categoria']}') existe e está escrita de forma **exatamente idêntica** nos seus dois arquivos: `tabela_disjuntores.csv` e `tabela_potencia_maxima.csv`."
                    )
                    st.stop() # Para a execução aqui para o usuário poder corrigir os dados.

                # Se o código continuar, o merge funcionou. A lógica abaixo permanece a mesma.
                faixa_nome = resultado["categoria"]
                disjuntor = resultado.get("disjuntor", "N/A")
                potencia_max_str = resultado.get('potencia_maxima_geracao_str', '-')

                st.write(f"**Carga instalada:** {carga_instalada:.2f} kW")
                st.success("✅ Análise concluída com sucesso!")
                st.write(f"**Categoria Encontrada**: `{faixa_nome}`")
                st.write(f"**Disjuntor Recomendado**: `{disjuntor} A`")
                st.divider()

                # --- LÓGICA DE EXIBIÇÃO E COMPARAÇÃO ---
                st.subheader("Limite de Geração da Categoria")
                limite_potencia_numerico = parse_potencia_numerica(potencia_max_str)

                if limite_potencia_numerico is not None:
                    st.write(f"A potência máxima de geração permitida para a categoria **{faixa_nome}** é:")
                    st.success(f"## {limite_potencia_numerico} kWp")
                else:
                    st.info(f"A categoria **{faixa_nome}** não possui um limite de geração pré-definido nos dados.")

                if potencia_kit_kwp > 0:
                    st.subheader(f"Validação do Kit de {potencia_kit_kwp:.2f} kWp")
                    if limite_potencia_numerico is not None:
                        if potencia_kit_kwp <= limite_potencia_numerico:
                            st.success(f"**APROVADO:** O kit está dentro do limite de {limite_potencia_numerico} kWp.")
                            st.balloons()
                        else:
                            st.error(f"**REPROVADO:** O kit excede o limite de {limite_potencia_numerico} kWp permitido.")
                    else:
                        st.success("**APROVADO:** Como não há limite definido para esta categoria, o kit é compatível.")
                
                st.divider()
                st.download_button(
                    label="📄 Baixar Relatório em PDF",
                    data=gerar_pdf(
                        nome_cliente, cidade_selecionada_fmt, tensao, tipo_ligacao,
                        carga_instalada, faixa_nome, disjuntor, potencia_max_str
                    ),
                    file_name=f"relatorio_{padronizar_nome(nome_cliente)}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.error("❌ Faixa não encontrada para os parâmetros informados.")
                st.markdown("- Verifique a **carga instalada**.\n- Confirme se a **tensão** e **tipo de ligação** são válidos para a cidade.")

else:
    st.info("👈 Preencha os dados na barra lateral e clique em 'Gerar Análise' para começar.")

st.caption("Desenvolvido por Vitória de Sales Sena ⚡")
