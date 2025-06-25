import streamlit as st
import pandas as pd
import unicodedata
import re
import io

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
    """Normaliza um texto: remove acentos, espaços (incluindo múltiplos) e converte para minúsculas."""
    if not isinstance(texto, str):
        return texto
    # Remove parênteses e o conteúdo dentro deles, como (kW) ou (A)
    texto = re.sub(r'\s*\([^)]*\)', '', texto)
    # Normaliza, remove acentos e converte para minúsculas
    texto_normalizado = unicodedata.normalize('NFKD', texto)\
                                   .encode('ascii', 'ignore')\
                                   .decode('utf-8')\
                                   .strip()\
                                   .lower()
    # Substitui qualquer sequência de caracteres de espaço por um único sublinhado
    return re.sub(r'\s+', '_', texto_normalizado)

def parse_carga_range(range_str):
    """
    Converte uma string de faixa (ex: "5.1 - 10") em valores numéricos (min, max).
    Retorna (0, 0) se a string for inválida.
    """
    if not isinstance(range_str, str) or range_str.strip() == '-':
        return 0.0, 0.0
    try:
        # Limpa a string, troca vírgula por ponto
        range_str = range_str.replace(',', '.').strip()
        # Divide a string pelo hífen
        parts = [p.strip() for p in range_str.split('-')]
        
        if len(parts) == 2:
            min_val = float(parts[0])
            max_val = float(parts[1])
            return min_val, max_val
        elif len(parts) == 1 and parts[0]:
            # Caso haja apenas um número, considera como faixa min e max
            val = float(parts[0])
            return val, val
        else:
            return 0.0, 0.0
    except (ValueError, IndexError):
        return 0.0, 0.0

# --- Carregamento de Dados ---

@st.cache_data
def carregar_dados():
    """Carrega, processa e junta os dados dos arquivos CSV. Usa cache para performance."""
    try:
        df_tensao = pd.read_csv("municipios_tensao.csv", sep=r'\s*,\s*', engine='python')
    except FileNotFoundError:
        st.error("Erro: Arquivo 'municipios_tensao.csv' não encontrado. Verifique se o arquivo está na pasta correta.")
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

    # --- Pré-processamento e Junção ---
    
    # Padroniza nomes das colunas de todos os DataFrames
    df_tensao.columns = [padronizar_nome(col) for col in df_tensao.columns]
    df_disjuntores.columns = [padronizar_nome(col) for col in df_disjuntores.columns]
    df_potencia_max.columns = [padronizar_nome(col) for col in df_potencia_max.columns]

    # **CORREÇÃO APLICADA AQUI**
    # Normaliza a coluna de tensão para garantir correspondência (ex: remove 'V' no final)
    for df in [df_tensao, df_disjuntores, df_potencia_max]:
        if 'tensao' in df.columns:
            df['tensao'] = df['tensao'].astype(str).str.strip().str.replace('V$', '', regex=True)

    # Processa a faixa de carga para criar colunas min e max
    if 'carga_instalada' in df_disjuntores.columns:
        cargas = df_disjuntores['carga_instalada'].apply(parse_carga_range)
        df_disjuntores[['carga_min_kw', 'carga_max_kw']] = pd.DataFrame(cargas.tolist(), index=df_disjuntores.index)
    else:
        st.error("Erro Crítico: A coluna 'Carga Instalada (kW)' não foi encontrada em 'tabela_disjuntores.csv'.")
        return None, None

    # Junta as tabelas de disjuntores e de potência máxima
    # As colunas chave são 'tensao' e 'categoria'
    df_dados_tecnicos = pd.merge(
        df_disjuntores,
        df_potencia_max,
        on=['tensao', 'categoria'],
        how='left' # 'left' para manter todas as categorias da tabela de disjuntores
    )

    # Padroniza os dados da coluna 'municipio'
    df_tensao['municipio'] = df_tensao['municipio'].str.strip().apply(padronizar_nome)
    
    # Renomeia a coluna de potência para um nome padrão
    coluna_potencia_original = [col for col in df_dados_tecnicos.columns if 'potencia_maxima' in col]
    if coluna_potencia_original:
        df_dados_tecnicos.rename(columns={coluna_potencia_original[0]: 'potencia_maxima_geracao_str'}, inplace=True)
    else:
        st.error("Erro Crítico: Nenhuma coluna de potência máxima encontrada em 'tabela_potencia_maxima.csv'.")
        return None, None
        
    return df_tensao, df_dados_tecnicos

df_tensao, df_dados_tecnicos = carregar_dados()

# Interrompe a execução se os dados não puderam ser carregados
if df_tensao is None or df_dados_tecnicos is None:
    st.stop()


# --- Interface do Usuário (Sidebar) ---

try:
    st.sidebar.image("imagens/logo.png", width=200)
except Exception:
    st.sidebar.warning("Logo não encontrado em 'imagens/logo.png'.")

st.sidebar.header("Parâmetros do Projeto")

# Mapeamento para os tipos de ligação.
mapa_ligacao = {
    "Monofásico": ["M0", "M1", "M2", "M3"],
    "Bifásico": ["B0", "B1", "B2"],
    "Trifásico": [f"T{i}" for i in range(13)] # Gera T0 a T12
}

lista_cidades = sorted(df_tensao["municipio"].str.title().unique())
cidade_selecionada_fmt = st.sidebar.selectbox("Selecione a cidade:", lista_cidades)

# Padroniza a entrada do usuário
cidade_selecionada_norm = padronizar_nome(cidade_selecionada_fmt)

# Busca a tensão
tensao_info = df_tensao.loc[df_tensao["municipio"] == cidade_selecionada_norm, "tensao"]
tensao = tensao_info.values[0] if not tensao_info.empty else "Não encontrada"

st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga_instalada = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1, format="%.2f")
tipo_ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

if "220/127" in tensao and tipo_ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Para tensão 220/127V, a ligação deve ser no mínimo Bifásica para projetos solares.")

# --- Lógica Principal e Exibição de Resultados ---
st.title("⚡ Pré-Projeto Solar — VSS Energia")

if st.sidebar.button("🔍 Gerar Análise", use_container_width=True, type="primary"):
    if tensao == "Não encontrada":
        st.error(f"Não foi possível encontrar dados de tensão para a cidade '{cidade_selecionada_fmt}'.")
    else:
        with st.spinner('Analisando dados...'):
            categorias_permitidas = mapa_ligacao[tipo_ligacao]

            # Lógica de filtragem revisada
            df_faixa_encontrada = df_dados_tecnicos[
                (df_dados_tecnicos["tensao"] == tensao) &
                (df_dados_tecnicos["categoria"].isin(categorias_permitidas)) &
                (carga_instalada >= df_dados_tecnicos["carga_min_kw"]) &
                (carga_instalada <= df_dados_tecnicos["carga_max_kw"])
            ]

            # --- Exibição dos Resultados ---
            st.subheader("📋 Resumo dos Parâmetros")
            col1, col2, col3 = st.columns(3)
            col1.metric("📍 Cidade", cidade_selecionada_fmt)
            col2.metric("🔌 Tensão da Rede", tensao)
            col3.metric("🔧 Tipo de Ligação", tipo_ligacao)

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
