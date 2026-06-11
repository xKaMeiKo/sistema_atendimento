import streamlit as st
from supabase import create_client, Client

# 1. Configuração da página e conexão com o Banco de Dados
st.set_page_config(page_title="Sistema de Atendimentos", page_icon="📋", layout="centered")

# SUBSTITUA PELOS SEUS DADOS DO SUPABASE
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "sb_publishable_EFjZ74m8m8bxBFYiNhvjaA_aIyGzRS8"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# 2. Inicialização do estado da sessão (Login)
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
            # 1. Autentica o usuário com e-mail e senha
            auth_response = supabase.auth.sign_in_with_password({"email": email_input, "password": senha})
            user_id = auth_response.user.id
            user_email = auth_response.user.email
            
            # 2. Busca o perfil usando o cliente "admin/bypassed" ou tenta ler direto
            # Forçamos a busca limpando espaços para evitar erros
            user_data = supabase.table("perfis").select("nivel_acesso").eq("id", user_id).execute()
            
            if user_data.data:
                # Pegamos o nível de acesso e padronizamos para começar com Maiúscula
                role_banco = str(user_data.data[0]["nivel_acesso"]).strip().capitalize()
                
                st.session_state.logado = True
                st.session_state.user_email = user_email
                st.session_state.user_id = user_id
                st.session_state.user_role = role_banco
                st.rerun()
            else:
                # SE O LOGIN DEU CERTO MAS NÃO ACHOU NA TABELA, MOSTRA O ID PARA AJUDAR
                st.error(f"Usuário autenticado, mas nenhum perfil foi encontrado na tabela 'perfis' para o ID: {user_id}. Verifique no Table Editor.")
        except Exception as e:
            st.error("Usuário ou senha incorretos ou erro de conexão.")

# --- SISTEMA APÓS LOGIN ---
else:
    with st.sidebar:
        st.write(f"👤 **Usuário:** {st.session_state.user_email}")
        st.write(f"🛡️ **Nível:** {st.session_state.user_role}")
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    st.title("📋 Painel de Atendimentos")
    
    # VISÃO DO ATENDENTE (Aceita tanto 'Atendente' quanto se o banco falhar e trouxer minúsculo)
    if st.session_state.user_role == "Atendente":
        st.subheader("📝 Registrar Novo Atendimento")
        
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
                supabase.table("atendimentos").insert(dados_atendimento).execute()
                st.success("Atendimento registrado com sucesso!")
            else:
                st.warning("Por favor, preencha todos os campos.")

    # VISÃO DO SUPERVISOR
    elif st.session_state.user_role == "Supervisor":
        st.subheader("📊 Relatório Geral (Visão do Supervisor)")
        st.info("Aqui você tem acesso a todos os registros da equipe.")
        
        try:
            resposta = supabase.table("atendimentos").select("*").execute()
            if resposta.data:
                st.dataframe(resposta.data)
            else:
                st.write("Nenhum atendimento registrado no sistema ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar atendimentos: {e}")
