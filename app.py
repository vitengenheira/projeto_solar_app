import streamlit as st
import pandas as pd

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

# Título
st.title("⚡ Calculadora de Projeto Solar — VSS Energia")

# Carregar dados
df_tensao = pd.read_csv("municipios_tensao.csv")
df_disjuntor = pd.read_csv("tabela_disjuntores.csv")
df_potencia = pd.read_csv("tabela_potencia_maxima.csv")

# Corrigir nomes de colunas (sem alterar arquivos)
df_disjuntor.columns = [col.strip() for col in df_disjuntor.columns]
df_potencia.columns = [col.strip() for col in df_potencia.columns]
df_tensao.columns = [col.strip() for col in df_tensao.columns]

# Sidebar
st.sidebar.image("imagens/logo.png", width=200)
st.sidebar.header("Parâmetros do Projeto")

cidade = st.sidebar.selectbox("Selecione a cidade:", sorted(df_tensao["Municipio"].unique()))
tensao = df_tensao.loc[df_tensao["Municipio"] == cidade, "Tensao"].values[0]

st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1)
ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

# Validação solar
if "220/127" in tensao and ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Inversor solar exige no mínimo ligação bifásica em 220/127 V.")

# Cálculo da faixa conforme disjuntor
df_filtro = df_disjuntor[
    (df_disjuntor["Tensao"] == tensao) &
    (df_disjuntor["Ligacao"] == ligacao) &
    (df_disjuntor["Carga_Min_kW"] <= carga) &
    (df_disjuntor["Carga_Max_kW"] >= carga)
]

if not df_filtro.empty:
    faixa = df_filtro.iloc[0]["Faixa"]
    disjuntor = df_filtro.iloc[0]["Disjuntor_A"]
else:
    faixa = "Não encontrada"
    disjuntor = "N/A"

# Buscar potência máxima de geração
df_pot = df_potencia[df_potencia["Faixa"] == faixa]

if not df_pot.empty:
    potencia_max = df_pot.iloc[0]["Potencia_Max_kWp"]
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
