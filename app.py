# (Cole todo aquele código em Python que te passei na resposta anterior bem aqui embaixo)

import streamlit as st
from supabase import create_client, Client

# 1. Configuração da página e conexão com o Banco de Dados
st.set_page_config(page_title="Sistema de Atendimentos", page_icon="📋", layout="centered")

# SUBSTITUA PELOS SEUS DADOS DO SUPABASE DO PASSO 1
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzbm9qcG12a3ZpamdlZmxrbHRuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExNzkzNTUsImV4cCI6MjA5Njc1NTM1NX0.2rSHSW8PfmjX-ujaZqHHEIWk8tTe1Kc5dveRwYwoM4g"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# 2. Inicialização do estado da sessão (Login)
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""  # 'Atendente' ou 'Supervisor'
    st.session_state.user_id = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema")
    
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar", use_container_width=True):
        try:
            # Autenticação direta no Supabase
            auth_response = supabase.auth.sign_in_with_password({"email": email, "password": senha})
            
            # Busca o nível de acesso do usuário na tabela customizada do banco
            user_data = supabase.table("perfis").select("nivel_acesso").eq("id", auth_response.user.id).execute()
            
            if user_data.data:
                st.session_state.logado = True
                st.session_state.user_email = auth_response.user.email
                st.session_state.user_id = auth_response.user.id
                st.session_state.user_role = user_data.data[0]["nivel_acesso"]
                st.rerun()
            else:
                st.error("Erro ao carregar perfil do usuário. Contate o administrador.")
        except Exception as e:
            st.error("Usuário ou senha incorretos.")

# --- SISTEMA APÓS LOGIN ---
else:
    # Barra Lateral com Informações do Usuário e Logout
    with st.sidebar:
        st.write(f"👤 **Usuário:** {st.session_state.user_email}")
        st.write(f"🛡️ **Nível:** {st.session_state.user_role}")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    # Painel Principal baseado no Nível de Acesso
    st.title("📋 Painel de Atendimentos")
    
    # VISÃO DO ATENDENTE
    if st.session_state.user_role == "Atendente":
        st.subheader("📝 Registrar Novo Atendimento")
        
        # Campos do formulário básico
        cliente = st.text_input("Nome do Cliente/Morador")
        tipo_atendimento = st.selectbox("Tipo de Ocorrência", ["Dúvida", "Reclamação", "Solicitação", "Outros"])
        detalhes = st.text_area("Descrição do Atendimento")
        
        if st.button("Salvar Atendimento"):
            if cliente and detalhes:
                dados_atendimento = {
                    "usuario_id": st.session_state.user_id,
                    "cliente": cliente,
                    "tipo": tipo_atendimento,
                    "descricao": detalhes
                }
                # Salva no banco de dados
                supabase.table("atendimentos").insert(dados_atendimento).execute()
                st.success("Atendimento registrado com sucesso!")
            else:
                st.warning("Por favor, preencha todos os campos.")

    # VISÃO DO SUPERVISOR
    elif st.session_state.user_role == "Supervisor":
        st.subheader("📊 Relatório Geral (Visão do Supervisor)")
        st.info("Aqui você tem acesso a todos os registros da equipe.")
        
        # Busca TODOS os atendimentos no banco de dados
        try:
            resposta = supabase.table("atendimentos").select("*, perfis(email)").execute()
            if resposta.data:
                st.dataframe(resposta.data)
                
                # Botão para exportar dados (MUITO útil para supervisão)
                st.download_button(
                    label="📥 Baixar Relatório em CSV",
                    data="Exemplo de conteúdo", # Ajustaremos para os dados reais no próximo passo
                    file_name="relatorio_atendimentos.csv",
                    mime="text/csv",
                )
            else:
                st.write("Nenhum atendimento registrado no sistema ainda.")
        except Exception as e:
            st.write("Aguardando configuração final das tabelas no banco de dados.")
