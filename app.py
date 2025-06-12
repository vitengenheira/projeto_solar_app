import streamlit as st
import pandas as pd
import unicodedata

# Configuração da página
st.set_page_config(page_title="Calculadora Solar Inteligente", page_icon="⚡", layout="wide")

# CSS personalizado
st.markdown("""
<style>
    .main { background-color: #f7f9fb; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
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

# ✅ ALTERADO: Nova função para extrair a potência como número
def extrair_potencia(valor):
    try:
        if pd.isna(valor) or valor in ["-", ""]:
            return 0.0
        return float(valor.replace("kWp", "").replace(",", ".").strip())
    except:
        return 0.0

mapa_ligacao = {
    "Monofásico": ["M0", "M1", "M2", "M3"],
    "Bifásico": ["B0", "B1"],
    "Trifásico": ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"]
}

# Título
st.title("⚡ Calculadora de Projeto Solar — VSS Energia")

# Carregamento de dados
df_tensao = padronizar_colunas(pd.read_csv("municipios_tensao.csv"))
df_potencia = padronizar_colunas(pd.read_csv("tabela_potencia_maxima.csv"))

# ✅ ALTERADO: Corrigir nome da coluna se tiver espaços
coluna_potencia = [col for col in df_potencia.columns if "potencia" in col][0]  # encontra dinamicamente

# ✅ ALTERADO: Criar coluna numérica e faixa
df_potencia["potencia_max_kwp"] = df_potencia[coluna_potencia].apply(extrair_potencia)
df_potencia["carga_min"] = 0.0
df_potencia["carga_max"] = df_potencia["potencia_max_kwp"]

# Sidebar
st.sidebar.image("imagens/logo.png", width=200)
st.sidebar.header("Parâmetros do Projeto")

cidade = st.sidebar.selectbox("Selecione a cidade:", sorted(df_tensao["municipio"].unique()))
tensao = df_tensao.loc[df_tensao["municipio"] == cidade, "tensao"].values[0]
st.sidebar.write(f"**Tensão disponível:** {tensao}")

carga = st.sidebar.number_input("Informe a carga instalada (kW):", min_value=0.0, step=0.1)
ligacao = st.sidebar.radio("Tipo de ligação:", ["Monofásico", "Bifásico", "Trifásico"])

# Validação de tensão
if "220/127" in tensao and ligacao == "Monofásico":
    st.sidebar.warning("⚠️ Para tensão 220/127 V, use ligação Bifásica ou Trifásica.")

# 🔍 Busca da faixa
categorias = mapa_ligacao[ligacao]

df_faixa = df_potencia[
    (df_potencia["tensao"] == tensao) &
    (df_potencia["categoria"].isin(categorias)) &
    (df_potencia["carga_min"] <= carga) &
    (df_potencia["carga_max"] >= carga)
]

# 📋 Exibição de dados gerais
col1, col2, col3 = st.columns(3)
col1.metric("📍 Cidade", cidade)
col2.metric("🔌 Tensão disponível", tensao)
col3.metric("🔧 Ligação escolhida", ligacao)

st.divider()
st.subheader("📝 Resultados da Análise")
st.write(f"- **Carga instalada**: {carga:.2f} kW")

# ✅ Resultado
if not df_faixa.empty:
    faixa_nome = df_faixa.iloc[0]["categoria"]
    potencia_max = df_faixa.iloc[0][coluna_potencia]

    st.write(f"- **Faixa identificada**: {faixa_nome}")
    st.subheader("🔆 Potência máxima permitida para geração solar")
    st.success(f"{potencia_max}")
    st.success("✅ Tudo ok para continuar o projeto de energia solar.")
else:
    st.write("- **Faixa identificada**: ❌ Não encontrada")
    st.error("❌ Não foi possível determinar a faixa adequada para os parâmetros informados.")
    potencia_max = None

# Potência permitida
if potencia_max:
    st.subheader("🔆 Potência máxima permitida para geração solar")
    st.success(f"{potencia_max}")
else:
    st.subheader("🔆 Potência máxima permitida para geração solar")
    st.error("Dados não disponíveis para essa combinação.")
    
st.caption("Desenvolvido por Vitória ⚡ | VSS Energia Inteligente")
