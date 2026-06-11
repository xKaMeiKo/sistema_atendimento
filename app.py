import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. Configuração da página
st.set_page_config(page_title="Sistema de Atendimentos Pro", page_icon="📋", layout="wide")

# CONEXÃO COM O SUPABASE (Mantenha as suas chaves aqui)
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "sb_publishable_EFjZ74m8m8bxBFYiNhvjaA_aIyGzRS8"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""  
    st.session_state.user_id = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema")
    email_input = st.text_input("E-mail").strip().lower()
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar", use_container_width=True):
        try:
            auth_response = supabase.auth.sign_in_with_password({"email": email_input, "password": senha})
            user_data = supabase.table("perfis").select("nivel_acesso").eq("id", auth_response.user.id).execute()
            if user_data.data:
                st.session_state.logado = True
                st.session_state.user_email = auth_response.user.email
                st.session_state.user_id = auth_response.user.id
                st.session_state.user_role = str(user_data.data[0]["nivel_acesso"]).strip().capitalize()
                st.rerun()
        except Exception:
            st.error("Usuário ou senha incorretos.")

# --- SISTEMA APÓS LOGIN ---
else:
    with st.sidebar:
        st.write(f"👤 **Usuário:** {st.session_state.user_email}")
        st.write(f"🛡️ **Nível:** {st.session_state.user_role}")
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()

    st.title("📋 Painel de Controle de Atendimentos")
    
    # ------------------ VISÃO DO ATENDENTE ------------------
    if st.session_state.user_role == "Atendente":
        st.subheader("📝 Registrar Novo Atendimento")
        
        # Organizando os campos lado a lado para um design mais limpo
        col1, col2 = st.columns(2)
        with col1:
            morador = st.text_input("Nome do Morador")
            meio_contato = st.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
        with col2:
            etapa = st.selectbox("Etapa Inicial", ["Em andamento", "Concluído"])
            
        solicitacao = st.text_area("Solicitação (Descreva o que foi pedido)")
        
        if st.button("Salvar Registro", type="primary", use_container_width=True):
            if morador and solicitacao:
                dados = {
                    "usuario_id": st.session_state.user_id,
                    "morador": morador,
                    "meio_contato": meio_contato,
                    "etapa": etapa,
                    "solicitacao": solicitacao
                }
                supabase.table("atendimentos").insert(dados).execute()
                st.success("Atendimento registrado com sucesso!")
            else:
                st.warning("Por favor, preencha o nome do morador e a solicitação.")

    # ------------------ VISÃO DO SUPERVISOR (DASHBOARD) ------------------
    elif st.session_state.user_role == "Supervisor":
        st.subheader("📊 Dashboard Executivo de Supervisão")
        
        # Busca dados do banco trazendo junto o e-mail de quem atendeu
        resposta = supabase.table("atendimentos").select("*, perfis(email)").execute()
        
        if resposta.data:
            # Transforma os dados em uma tabela Pandas para facilitar os gráficos
            df = pd.DataFrame(resposta.data)
            # Extrai o e-mail do colaborador de dentro do relacionamento do banco
            df['Colaborador'] = df['perfis'].apply(lambda x: x['email'] if isinstance(x, dict) else 'Desconhecido')
            # Formata a data para formato legível (Ano-Mês-Dia)
            df['Data'] = pd.to_datetime(df['data_hora']).dt.date
            
            # --- CARD DE MÉTRICAS RÁPIDAS ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Atendimentos", len(df))
            m2.metric("Atendimentos Em Andamento", len(df[df['etapa'] == 'Em andamento']))
            m3.metric("Atendimentos Concluídos", len(df[df['etapa'] == 'Concluído']))
            
            st.divider()
            
            # --- BLOCO DE GRÁFICOS ---
            g1, g2 = st.columns(2)
            
            with g1:
                st.markdown("### 👥 Atendimentos por Colaborador")
                atend_por_colab = df['Colaborador'].value_counts()
                st.bar_chart(atend_por_colab)
                
            with g2:
                st.markdown("### 📞 Atendimentos por Meio de Contato")
                atend_por_meio = df['meio_contato'].value_counts()
                st.bar_chart(atend_por_meio)
                
            st.divider()
            
            st.markdown("### 📅 Evolução Diária de Atendimentos")
            atend_por_dia = df.groupby('Data').size()
            st.line_chart(atend_por_dia)
            
            st.divider()
            
            # --- TABELA DE DADOS COMPLETA ---
            st.markdown("### 📑 Histórico Completo de Registros")
            # Seleciona e organiza as colunas para exibição na tabela limpa
            df_exibicao = df[['Data', 'Colaborador', 'morador', 'meio_contato', 'solicitacao', 'etapa']]
            df_exibicao.columns = ['Data', 'Atendente', 'Morador', 'Meio de Contato', 'Solicitação', 'Status']
            st.dataframe(df_exibicao, use_container_width=True)
            
        else:
            st.info("Nenhum atendimento registrado no sistema para gerar o dashboard.")
