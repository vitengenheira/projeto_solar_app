import streamlit as st
import pandas as pd
import unicodedata
import re
import io
from fpdf import FPDF
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Pré-Projeto Solar | VSS Energia",
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
    """Normaliza um texto para ser usado em nomes de arquivos e colunas."""
    if not isinstance(texto, str):
        return texto
    texto = re.sub(r'\s*\([^)]*\)', '', texto)
    texto_normalizado = unicodedata.normalize('NFKD', texto)\
                                   .encode('ascii', 'ignore')\
                                   .decode('utf-8')\
                                   .strip()\
                                   .lower()
    return re.sub(r'[\s\W]+', '_', texto_normalizado)

def parse_carga_range(range_str):
    """Converte uma string de faixa (ex: "5.1 - 10") em valores numéricos (min, max)."""
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
        return 0.0, 0.0
    except (ValueError, IndexError):
        return 0.0, 0.0

def gerar_pdf(cliente, cidade, tensao, ligacao, carga, categoria, disjuntor, potencia_max):
    """Gera um relatório PDF com os resultados da análise."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho
    try:
        pdf.image("imagens/logo.png", x=10, y=8, w=40)
    except FileNotFoundError:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, 10, "VSS Energia")
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "Relatório de Pré-Análise Solar", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, "C")
    pdf.ln(15)
    
    # Título da Seção
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "Resumo do Projeto", 0, 1, "L", fill=True)
    pdf.ln(5)

    # Função para adicionar linha de dados
    def add_linha(label, value):
        pdf.set_font("Arial", "B", 11)
        pdf.cell(50, 8, label, 0, 0, "L")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, value, 0, 1, "L")

    add_linha("Nome do Cliente:", cliente)
    add_linha("Município:", cidade)
    add_linha("Tensão da Rede:", tensao)
    add_linha("Tipo de Ligação:", ligacao)
    add_linha("Carga Instalada:", f"{carga:.2f} kW")
    pdf.ln(10)

    # Resultados da Análise
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Análise Técnica da Concessionária", 0, 1, "L", fill=True)
    pdf.ln(5)
    add_linha("Categoria de Enquadramento:", categoria)
    add_linha("Disjuntor de Proteção Padrão:", f"{disjuntor} A")
    pdf.ln(10)

    # Potência Máxima
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Potencial de Geração Solar", 0, 1, "L", fill=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Potência máxima de geração permitida para esta categoria:", 0, 1, "L")
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(255, 99, 71) # Cor Tomato
    if pd.notna(potencia_max) and potencia_max.strip() != '-':
        pdf.cell(0, 15, f" {potencia_max}", 0, 1, "C")
    else:
        pdf.set_font("Arial", "I", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 15, "Nao aplicavel para esta categoria.", 0, 1, "C")

    # Rodapé
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, f'Página {pdf.page_no()}', 0, 0, 'C')

    return pdf.output(dest='S').encode('latin-1')


# --- Carregamento de Dados ---

@st.cache_data
def carregar_dados():
    """Carrega, processa e junta os dados dos arquivos CSV. Usa cache para performance."""
    try:
        df_tensao = pd.read_csv("municipios_tensao.csv", sep=r'\s*,\s*', engine='python')
    except FileNotFoundError:
        st.error("Erro: Arquivo 'municipios_tensao.csv' não encontrado.")
        return None, None

    try:
        df_disjuntores = pd.read_csv("tabela_disjuntores.csv", sep=r'\s*,\s*', engine='python')
    except FileNotFoundError:
        st.error("Erro: Arquivo 'tabela_disjuntores.csv' não encontrado.")
        return None, None

    try:
        df_potencia_max = pd.read_csv("tabela_potencia_maxima.csv", sep=r'\s*,\s*', engine='python')
    except FileNotFoundError:
        st.error("Erro: Arquivo 'tabela_potencia_maxima.csv' não encontrado.")
        return None, None

    df_tensao.columns = [padronizar_nome(col) for col in df_tensao.columns]
    df_disjuntores.columns = [padronizar_nome(col) for col in df_disjuntores.columns]
    df_potencia_max.columns = [padronizar_nome(col) for col in df_potencia_max.columns]

    for df in [df_tensao, df_disjuntores, df_potencia_max]:
        if 'tensao' in df.columns:
            df['tensao'] = df['tensao'].astype(str).str.strip().str.replace('V$', '', regex=True)

    if 'carga_instalada' in df_disjuntores.columns:
        cargas = df_disjuntores['carga_instalada'].apply(parse_carga_range)
        df_disjuntores[['carga_min_kw', 'carga_max_kw']] = pd.DataFrame(cargas.tolist(), index=df_disjuntores.index)
    else:
        st.error("Erro Crítico: Coluna 'Carga Instalada (kW)' não encontrada em 'tabela_disjuntores.csv'.")
        return None, None

    df_dados_tecnicos = pd.merge(df_disjuntores, df_potencia_max, on=['tensao', 'categoria'], how='left')
    df_tensao['municipio'] = df_tensao['municipio'].str.strip().apply(padronizar_nome)
    
    col_potencia = [col for col in df_dados_tecnicos.columns if 'potencia_maxima' in col]
    if col_potencia:
        df_dados_tecnicos.rename(columns={col_potencia[0]: 'potencia_maxima_geracao_str'}, inplace=True)
    else:
        st.error("Erro Crítico: Nenhuma coluna de potência máxima encontrada.")
        return None, None
        
    return df_tensao, df_dados_tecnicos

df_tensao, df_dados_tecnicos = carregar_dados()

if df_tensao is None or df_dados_tecnicos is None:
    st.stop()


# --- Interface do Usuário (Sidebar) ---

try:
    st.sidebar.image("imagens/logo.png", width=200)
except Exception:
    st.sidebar.warning("Logo não encontrado em 'imagens/logo.png'.")

st.sidebar.header("Parâmetros do Projeto")
nome_cliente = st.sidebar.text_input("Nome do Cliente:", placeholder="Digite o nome completo")
lista_cidades = sorted(df_tensao["municipio"].str.title().unique())
cidade_selecionada_fmt = st.sidebar.selectbox("Selecione a cidade:", lista_cidades)
cidade_selecionada_norm = padronizar_nome(cidade_selecionada_fmt)

tensao_info = df_tensao.loc[df_tensao["municipio"] == cidade_selecionada_norm, "tensao"]
tensao = tensao_info.values[0] if not tensao_info.empty else "Não encontrada"
st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga_instalada = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1, format="%.2f")
tipo_ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

if "220/127" in tensao and tipo_ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Para tensão 220/127V, a ligação deve ser no mínimo Bifásica.")

# --- Lógica Principal e Exibição de Resultados ---
st.title("⚡ Pré-Projeto Solar — VSS Energia")

if st.sidebar.button("🔍 Gerar Análise", use_container_width=True, type="primary"):
    if not nome_cliente:
        st.sidebar.error("Por favor, informe o nome do cliente.")
    elif tensao == "Não encontrada":
        st.error(f"Não foi possível encontrar dados de tensão para a cidade '{cidade_selecionada_fmt}'.")
    else:
        with st.spinner('Analisando dados...'):
            mapa_ligacao = {
                "Monofásico": ["M0", "M1", "M2", "M3"],
                "Bifásico": ["B0", "B1", "B2"],
                "Trifásico": [f"T{i}" for i in range(13)]
            }
            categorias_permitidas = mapa_ligacao[tipo_ligacao]

            df_faixa_encontrada = df_dados_tecnicos[
                (df_dados_tecnicos["tensao"] == tensao) &
                (df_dados_tecnicos["categoria"].isin(categorias_permitidas)) &
                (carga_instalada >= df_dados_tecnicos["carga_min_kw"]) &
                (carga_instalada <= df_dados_tecnicos["carga_max_kw"])
            ]

            st.subheader("📋 Resumo dos Parâmetros")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👤 Cliente", nome_cliente)
            col2.metric("📍 Cidade", cidade_selecionada_fmt)
            col3.metric("🔌 Tensão da Rede", tensao)
            col4.metric("🔧 Tipo de Ligação", tipo_ligacao)

            st.divider()
            st.subheader("📝 Resultados da Análise")
            st.write(f"**Carga instalada informada**: {carga_instalada:.2f} kW")

            if not df_faixa_encontrada.empty:
                resultado = df_faixa_encontrada.iloc[0]
                faixa_nome = resultado["categoria"]
                disjuntor = resultado.get("disjuntor", "N/A")
                potencia_max_str = resultado.get('potencia_maxima_geracao_str', '-')
                
                st.success("✅ Análise concluída com sucesso!")
                st.write(f"**Faixa de enquadramento (Categoria)**: `{faixa_nome}`")
                st.write(f"**Disjuntor de Proteção Recomendado**: `{disjuntor} A`")

                st.subheader("🔆 Potência Máxima Permitida para Geração")
                if pd.notna(potencia_max_str) and potencia_max_str.strip() != '-':
                    st.info(f"Para a categoria **{faixa_nome}**, a potência máxima que pode ser injetada é:")
                    st.success(f"## {potencia_max_str}")
                    st.balloons()
                else:
                    st.warning(f"Não há um limite de potência de geração definido para a categoria **{faixa_nome}**.")
                
                st.divider()

                pdf_bytes = gerar_pdf(
                    nome_cliente, cidade_selecionada_fmt, tensao, tipo_ligacao, 
                    carga_instalada, faixa_nome, disjuntor, potencia_max_str
                )
                
                st.download_button(
                    label="📄 Baixar Relatório em PDF",
                    data=pdf_bytes,
                    file_name=f"pre_projeto_{padronizar_nome(nome_cliente)}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            else:
                st.error("❌ Não foi possível encontrar uma faixa correspondente.")
                st.write(
                    "Verifique os seguintes pontos:\n"
                    "- A **Carga Instalada** pode estar fora das faixas definidas para o tipo de ligação e tensão selecionados.\n"
                    "- A combinação de **Tensão** e **Tipo de Ligação** pode não ser válida."
                )
else:
    st.info("👈 Preencha os parâmetros na barra lateral e clique em 'Gerar Análise' para começar.")

st.caption("Desenvolvido por Vitória ⚡ | VSS Energia Inteligente")
