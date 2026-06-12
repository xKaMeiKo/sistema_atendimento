import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController
from datetime import datetime
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CondoTickets SaaS", layout="wide", page_icon="🏢")

# --- CONEXÃO SUPABASE ---
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "sb_publishable_EFjZ74m8m8bxBFYiNhvjaA_aIyGzRS8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GERENCIAMENTO DE COOKIES E ESTADO ---
controller = CookieController()

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
        
        # Salva no Cookie para persistência (expira em 7 dias)
        controller.set("condo_user_id", res.user.id)
        controller.set("condo_user_email", email)
        
        st.session_state.logged_in = True
        st.session_state.user_info = profile.data
        st.rerun()
    except Exception as e:
        st.error("Erro ao fazer login. Verifique suas credenciais.")

def logout():
    controller.remove("condo_user_id")
    controller.remove("condo_user_email")
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.rerun()

def check_auth():
    # Tenta ler cookies se não estiver logado na sessão
    if not st.session_state.logged_in:
        cookie_id = controller.get("condo_user_id")
        if cookie_id:
            try:
                profile = supabase.table("perfis").select("*").eq("id", cookie_id).single().execute()
                if profile.data:
                    st.session_state.user_info = profile.data
                    st.session_state.logged_in = True
                    st.rerun()
            except:
                pass

# --- INTERFACE DE LOGIN ---
check_auth()

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

# --- SIDEBAR (DINÂMICA) ---
with st.sidebar:
    st.title(f"Olá, {user['email'].split('@')[0]}")
    st.info(f"Nível: {user['nivel_acesso']}")
    
    if st.button("Sair"):
        logout()
    
    st.divider()
    
    if user['nivel_acesso'] == 'Atendente':
        st.subheader("📌 Chamados Ativos")
        res_ativos = supabase.table("atendimentos").select("id, morador, solicitacao").eq("etapa", "Em andamento").execute()
        
        if st.button("➕ Novo Atendimento", use_container_width=True):
            st.session_state.view_modo = "Novo"
            st.session_state.ticket_selecionado = None
            st.rerun()

        for t in res_ativos.data:
            resumo = f"{t['morador']} - {t['solicitacao'][:20]}..."
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
            morador = c1.text_input("Nome do Morador")
            meio = c2.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
            solicitacao = st.text_area("Descrição da Solicitação")
            
            if st.form_submit_button("Registrar Chamado"):
                if morador and solicitacao:
                    data = {
                        "usuario_id": user['id'],
                        "morador": morador,
                        "meio_contato": meio,
                        "solicitacao": solicitacao,
                        "etapa": "Em andamento"
                    }
                    supabase.table("atendimentos").insert(data).execute()
                    st.success("Chamado registrado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Preencha todos os campos.")

    elif st.session_state.view_modo == "Atualizar":
        st.title("🔄 Atualizar Chamado")
        tid = st.session_state.ticket_selecionado
        res = supabase.table("atendimentos").select("*").eq("id", tid).single().execute()
        chamado = res.data
        
        col_inf1, col_inf2 = st.columns(2)
        col_inf1.metric("Morador", chamado['morador'])
        col_inf2.metric("Abertura", datetime.fromisoformat(chamado['data_hora']).strftime("%d/%m/%Y %H:%M"))
        
        st.markdown("**Histórico Atual:**")
        st.info(chamado['solicitacao'])
        
        with st.form("form_update"):
            nova_att = st.text_area("Nova Atualização / Andamento")
            nova_etapa = st.selectbox("Status", ["Em andamento", "Concluído"])
            
            if st.form_submit_button("Salvar Alterações"):
                historico_atualizado = f"{chamado['solicitacao']}\n\n--- Atualização ({datetime.now().strftime('%d/%m %H:%M')}) ---\n{nova_att}"
                supabase.table("atendimentos").update({
                    "solicitacao": historico_atualizado,
                    "etapa": nova_etapa
                }).eq("id", tid).execute()
                
                st.success("Chamado atualizado!")
                time.sleep(1)
                st.session_state.view_modo = "Novo"
                st.rerun()

# --- VISÃO: SUPERVISOR (DASHBOARD) ---
elif user['nivel_acesso'] == 'Supervisor':
    st.title("📊 Dashboard Executivo")
    
    # Busca dados
    res_all = supabase.table("atendimentos").select("*, perfis(email)").execute()
    df = pd.DataFrame(res_all.data)
    
    if not df.empty:
        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Atendimentos", len(df))
        m2.metric("Em Andamento", len(df[df['etapa'] == 'Em andamento']))
        m3.metric("Concluídos", len(df[df['etapa'] == 'Concluído']))
        
        st.divider()
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Atendimentos por Colaborador")
            # Extrai e-mail do objeto aninhado vindo do join
            df['atendente'] = df['perfis'].apply(lambda x: x['email'] if x else 'N/A')
            chart_colab = df['atendente'].value_counts()
            st.bar_chart(chart_colab)
            
        with c2:
            st.subheader("Meio de Contato")
            chart_meio = df['meio_contato'].value_counts()
            st.bar_chart(chart_meio)
            
        st.subheader("Evolução Diária")
        df['data'] = pd.to_datetime(df['data_hora']).dt.date
        chart_evolucao = df.groupby('data').size()
        st.line_chart(chart_evolucao)
        
        st.subheader("📋 Histórico Completo (Auditoria)")
        st.dataframe(df[['id', 'data_hora', 'atendente', 'morador', 'meio_contato', 'etapa']], use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para gerar o dashboard.")
