import streamlit as st
import pandas as pd
import unicodedata

# Configuração da página
st.set_page_config(page_title="Calculadora Solar Inteligente", page_icon="⚡", layout="wide")

# CSS para estilo
st.markdown("""
<style>
    .main { background-color: #f7f9fb; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .css-18e3th9 { padding-top: 1rem; }
    .css-1d391kg { padding-top: 0rem; }
</style>
""", unsafe_allow_html=True)

# Funções utilitárias
def padronizar_colunas(df):
    df.columns = (
        df.columns
          .str.strip()
          .str.lower()
          .str.normalize('NFKD')
          .str.encode('ascii', errors='ignore')
          .str.decode('utf-8')
    )
    return df

def extrair_intervalo(campo):
    if pd.isna(campo) or campo == "-" or campo == "":
        return 0.0, float('inf')
    partes = campo.replace(" ", "").split("-")
    return float(partes[0]), float(partes[1])

# Mapeamento ligação → categorias possíveis
mapa_ligacao = {
    "Monofásico": ["M0", "M1", "M2", "M3"],
    "Bifásico": ["B0", "B1"],
    "Trifásico": ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"]
}

# Título principal
st.title("⚡ Calculadora de Projeto Solar — VSS Energia")

# Carregamento dos dados
df_tensao = padronizar_colunas(pd.read_csv("municipios_tensao.csv"))
df_disjuntor = padronizar_colunas(pd.read_csv("tabela_disjuntores.csv"))
df_potencia = padronizar_colunas(pd.read_csv("tabela_potencia_maxima.csv"))

# Sidebar e logo
st.sidebar.image("imagens/logo.png", width=200)
st.sidebar.header("Parâmetros do Projeto")

cidade = st.sidebar.selectbox("Selecione a cidade:", sorted(df_tensao["municipio"].unique()))
tensao = df_tensao.loc[df_tensao["municipio"] == cidade, "tensao"].values[0]
st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1)
ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

# Validação de ligação para inversor
if "220/127" in tensao and ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Para projeto solar em 220/127 V, a ligação deve ser pelo menos Bifásica ou Trifásica.")

# Filtrar faixa e disjuntor adequados
df_disjuntor[["carga_min", "carga_max"]] = df_disjuntor["carga instalada (kw)"].map(extrair_intervalo).apply(pd.Series)
categorias = mapa_ligacao[ligacao]

df_filtro = df_disjuntor[
    (df_disjuntor["tensao"] == tensao) &
    (df_disjuntor["categoria"].isin(categorias)) &
    (df_disjuntor["carga_min"] <= carga) &
    (df_disjuntor["carga_max"] >= carga)
]

if not df_filtro.empty:
    faixa = df_filtro.iloc[0]["categoria"]
    disjuntor = int(df_filtro.iloc[0]["disjuntor(a)"])
else:
    faixa = None
    disjuntor = None

# Consultar potência máxima
pot_row = df_potencia[
    (df_potencia["tensao"] == tensao) &
    (df_potencia["categoria"] == faixa)
]

potencia_max = pot_row.iloc[0]["potência  maxima de geração"] if not pot_row.empty else None

# Exibição
col1, col2, col3 = st.columns(3)
col1.metric("📍 Cidade", cidade)
col2.metric("🔌 Tensão disponível", tensao)
col3.metric("🔧 Ligação escolhida", ligacao)

st.divider()

st.subheader("📝 Resultados da Análise")
st.write(f"- **Carga instalada**: {carga:.2f} kW")
if faixa:
    st.write(f"- **Faixa identificada**: {faixa}")
else:
    st.write("- **Faixa identificada**: ❌ Não encontrada")

if disjuntor:
    st.write(f"- **Disjuntor mínimo recomendado**: {disjuntor} A")
else:
    st.write("- **Disjuntor mínimo recomendado**: N/A")

# Validação final e mensagem
if "220/127" in tensao and ligacao == "Monofásico":
    st.error("⚠️ Em tensão 220/127 V, inversor exige ligação Bifásica ou Trifásica — ajuste necessário.")
elif faixa is None:
    st.error("❌ Não foi possível determinar a faixa adequada para os parâmetros informados.")
else:
    st.success("✅ Tudo ok para continuar o projeto de energia solar.")

# Potência permitida
if potencia_max:
    st.subheader("🔆 Potência máxima permitida para geração solar")
    st.success(f"{potencia_max}")
else:
    st.subheader("🔆 Potência máxima permitida para geração solar")
    st.error("Dados não disponíveis para essa combinação.")

st.caption("Desenvolvido por Vitória ⚡ | VSS Energia Inteligente")



