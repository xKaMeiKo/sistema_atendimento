import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CondoTickets SaaS", layout="wide", page_icon="🏢")

# --- CONEXÃO SUPABASE ---
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "sb_publishable_EFjZ74m8m8bxBFYiNhvjaA_aIyGzRS8"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# --- GERENCIAMENTO DE ESTADO NATIVO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'view_modo' not in st.session_state:
    st.session_state.view_modo = "Novo"
if 'ticket_selecionado' not in st.session_state:
    st.session_state.ticket_selecionado = None

# --- FUNÇÕES DE AUXÍLIO ---
def login_user(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        profile = supabase.table("perfis").select("*").eq("id", res.user.id).single().execute()
        
        st.session_state.logged_in = True
        st.session_state.user_info = profile.data
        
        if profile.data['nivel_acesso'] in ['Manutenção', 'Financeiro']:
            st.session_state.view_modo = "Aguardando"
        else:
            st.session_state.view_modo = "Novo"
            
        st.rerun()
    except Exception:
        st.error("Erro ao fazer login. Verifique suas credenciais.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.view_modo = "Novo"
    st.session_state.ticket_selecionado = None
    st.rerun()

# --- INTERFACE DE LOGIN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🏢 CondoTickets")
        st.subheader("Login no Sistema")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            login_user(email, senha)
    st.stop()

# --- ÁREA LOGADA ---
user = st.session_state.user_info
nome_usuario_limpo = user['email'].split('@')[0] 
cargo = user['nivel_acesso']

# --- BARRA LATERAL FIXA ---
with st.sidebar:
    st.title(f"Olá, {nome_usuario_limpo}")
    st.info(f"Nível: {cargo}")
    
    if st.button("Sair", use_container_width=True):
        logout()
    
    st.divider()
    
    if cargo in ['Atendente', 'Manutenção', 'Financeiro']:
        if st.button("➕ Novo Atendimento", use_container_width=True, type="primary"):
            st.session_state.view_modo = "Novo"
            st.session_state.ticket_selecionado = None
            st.rerun()

# --- PAINEL PRINCIPAL OPERACIONAL ---
if cargo in ['Atendente', 'Manutenção', 'Financeiro']:
    
    # Criamos o layout clássico de duas colunas na tela central
    col_esquerda, col_direita = st.columns([1, 3])
    
    # COLUNA ESQUERDA: LISTA DE CHAMADOS FILTRADA
    with col_esquerda:
        sub_c1, sub_c2 = st.columns([3, 1])
        sub_c1.subheader("📌 Chamados")
        if sub_c2.button("🔄", help="Atualizar lista"):
            st.rerun()
        
        try:
            query = supabase.table("atendimentos").select("id, pessoa, solicitacao, categoria_solicitacao").eq("etapa", "Em andamento")
            if cargo == "Manutenção":
                query = query.eq("categoria_solicitacao", "Manutenção")
            elif cargo == "Financeiro":
                query = query.eq("categoria_solicitacao", "Financeiro")
                
            res_ativos = query.execute()
            dados_ativos = res_ativos.data
        except Exception:
            dados_ativos = []

        if dados_ativos:
            for t in dados_ativos:
                resumo = f"Nº {t['id']} - {t['pessoa']} ({t['categoria_solicitacao']})"
                if st.button(res
