import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CondoTickets SaaS", layout="wide", page_icon="🏢")

# --- CONEXÃO SUPABASE ---
SUPABASE_URL = "SUA_URL_AQUI"
SUPABASE_KEY = "SUA_KEY_AQUI"

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
        st.rerun()
    except Exception:
        st.error("Erro ao fazer login. Verifique suas credenciais.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
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
nome_usuario_limpo = user['email'].split('@')[0] # Extrai o início do e-mail (ex: sac)

# --- SIDEBAR (DINÂMICA) ---
with st.sidebar:
    st.title(f"Olá, {nome_usuario_limpo}")
    st.info(f"Nível: {user['nivel_acesso']}")
    
    if st.button("Sair", use_container_width=True):
        logout()
    
    st.divider()
    
    if user['nivel_acesso'] == 'Atendente':
        st.subheader("📌 Chamados Ativos")
        try:
            res_ativos = supabase.table("atendimentos").select("id, pessoa, solicitacao").eq("etapa", "Em andamento").execute()
            dados_ativos = res_ativos.data
        except:
            dados_ativos = []
        
        if st.button("➕ Novo Atendimento", use_container_width=True):
            st.session_state.view_modo = "Novo"
            st.session_state.ticket_selecionado = None
            st.rerun()

        for t in dados_ativos:
            resumo = f"Nº {t['id']} - {t['pessoa']}"
            if st.button(resumo, key=f"btn_{t['id']}", use_container_width=True):
                st.session_state.ticket_selecionado = t['id']
                st.session_state.view_modo = "Atualizar"
                st.rerun()

# --- VISÃO: ATENDENTE ---
if user['nivel_acesso'] == 'Atendente':
    
    if st.session_state.view_modo == "Novo":
        st.title("📝 Novo Atendimento")
        
        with st.form("form_novo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            pessoa = c1.text_input("Pessoa (Nome)")
            tipo_persona = c2.selectbox("Tipo de Pessoa", ["Morador", "Prestador", "Hóspede", "Visitante"])
            
            c3, c4 = st.columns(2)
            meio = c3.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
            categoria_solicitacao = c4.selectbox("Tipo de Solicitação", ["Liberação", "Informação", "Manutenção", "Financeiro"])
            
            etapa_inicial = st.selectbox("Status Inicial", ["Em andamento", "Concluído"])
            solicitacao_detalhe = st.text_area("Descrição Detalhada da Solicitação")
            
            if st.form_submit_button("Registrar Chamado", type="primary"):
                if "t_etapa" in locals():
                    status_final = t_etapa
                else:
                    status_final = etapa_inicial
                if pessoa and solicitacao_detalhe:
                    data = {
                        "usuario_id": user['id'],
                        "pessoa": pessoa,
                        "tipo_pessoa": tipo_persona,
                        "meio_contato": meio,
                        "categoria_solicitacao": categoria_solicitacao,
                        "solicitacao": solicitacao_detalhe,
                        "etapa": status_final
                    }
                    supabase.table("atendimentos").insert(data).execute()
                    st.success("Chamado registrado com sucesso!")
                    time.sleep()
