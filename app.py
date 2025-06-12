import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Calculadora Solar Inteligente", page_icon="⚡", layout="wide")

# Estilo premium
st.markdown("""
    <style>
    .main { background-color: #f7f9fb; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .css-18e3th9 { padding-top: 1rem; }
    .css-1d391kg { padding-top: 0rem; }
    </style>
""", unsafe_allow_html=True)

# Função para padronizar nomes de colunas
def padronizar_colunas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.normalize('NFKD')  # remove acentos
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )
    return df

# Título
st.title("⚡ Calculadora de Projeto Solar — VSS Energia")

# Carregar dados e padronizar colunas
df_tensao = padronizar_colunas(pd.read_csv("municipios_tensao.csv"))
df_disjuntor = padronizar_colunas(pd.read_csv("tabela_disjuntores.csv"))
df_potencia = padronizar_colunas(pd.read_csv("tabela_potencia_maxima.csv"))

# Sidebar
st.sidebar.image("imagens/logo.png", width=200)
st.sidebar.header("Parâmetros do Projeto")

cidade = st.sidebar.selectbox("Selecione a cidade:", sorted(df_tensao["municipio"].unique()))
tensao = df_tensao.loc[df_tensao["municipio"] == cidade, "tensao"].values[0]

st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1)
ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

# Validação solar
if "220/127" in tensao and ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Inversor solar exige no mínimo ligação bifásica em 220/127 V.")

# Cálculo da faixa conforme disjuntor
df_filtro = df_disjuntor[
    (df_disjuntor["tensao"] == tensao) &
    (df_disjuntor["ligacao"] == ligacao) &
    (df_disjuntor["carga_min_kw"] <= carga) &
    (df_disjuntor["carga_max_kw"] >= carga)
]

if not df_filtro.empty:
    faixa = df_filtro.iloc[0]["faixa"]
    disjuntor = df_filtro.iloc[0]["disjuntor_a"]
else:
    faixa = "Não encontrada"
    disjuntor = "N/A"

# Buscar potência máxima de geração
df_pot = df_potencia[df_potencia["faixa"] == faixa]

if not df_pot.empty:
    potencia_max = df_pot.iloc[0]["potencia_max_kwp"]
else:
    potencia_max = "N/A"

# Layout premium com cards
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📍 Tensão de fornecimento", tensao)

with col2:
    st.metric("📝 Faixa encontrada", faixa)

with col3:
    st.metric("🛡️ Disjuntor mínimo (A)", disjuntor)

st.divider()

st.subheader("🔆 Potência máxima permitida para geração solar:")
st.success(f"👉 {potencia_max} kWp" if potencia_max != "N/A" else "Dados não encontrados para os parâmetros informados.")

st.caption("Desenvolvido por Vitória ⚡ | VSS Energia Inteligente")

