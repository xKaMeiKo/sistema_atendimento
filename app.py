import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. Configuração da página
st.set_page_config(page_title="Sistema de Chamados Pro", page_icon="📋", layout="wide")

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

# --- SESSÃO LOGADA ---
else:
    # ------------------ BARRA LATERAL (MENU ESQUERDO) ------------------
    with st.sidebar:
        st.write(f"👤 **Usuário:** {st.session_state.user_email}")
        st.write(f"🛡️ **Nível:** {st.session_state.user_role}")
        
        st.divider()
        st.subheader("⚠️ Chamados Em Andamento")
        
        # Busca os chamados abertos para exibir no menu lateral (Disponível para todos)
        try:
            busca_abertos = supabase.table("atendimentos").select("id, morador, solicitacao").eq("etapa", "Em andamento").execute()
            chamados_abertos = busca_abertos.data
        except Exception:
            chamados_abertos = []
            
        if chamados_abertos:
            for chamado in chamados_abertos:
                # Cria um pequeno card visual para cada chamado na lateral
                with st.container(border=True):
                    st.markdown(f"**Nº {chamado['id']} - Morador: {chamado['morador']}**")
                    st.caption(f"💬 {chamado['solicitacao'][:60]}...") # Mostra só o começo do texto
        else:
            st.info("Nenhum chamado pendente.")
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()

    # ------------------ PAINEL PRINCIPAL ------------------
    st.title("📋 Painel de Controle de Atendimentos")
    
    # ------------------ VISÃO DO ATENDENTE ------------------
    if st.session_state.user_role == "Atendente":
        
        # Abas para separar a criação de novos chamados da atualização dos existentes
        aba_novo, aba_atualizar = st.tabs(["📝 Registrar Novo Atendimento", "🔄 Atualizar Chamado Pendente"])
        
        with aba_novo:
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
                    st.rerun() # Recarrega a página para atualizar o menu lateral na hora
                else:
                    st.warning("Por favor, preencha o nome do morador e a solicitação.")
                    
        with aba_atualizar:
            if chamados_abertos:
                st.markdown("### Selecione o chamado para atualizar:")
                # Cria uma lista bonita para o atendente escolher qual chamado quer mexer
                opcoes_chamados = {f"Nº {c['id']} - {c['morador']}": c for c in chamados_abertos}
                selecionado = st.selectbox("Escolha o chamado:", list(opcoes_chamados.keys()))
                
                chamado_atual = opcoes_chamados[selecionado]
                
                # Mostra o problema original
                st.info(f"**Histórico Original:** {chamado_atual['solicitacao']}")
                
                # Campos para a atualização
                nova_atualizacao = st.text_area("Descreva a atualização ou andamento da situação:")
                nova_etapa = st.selectbox("Mudar Status para:", ["Em andamento", "Concluído"], key="atualizar_status")
                
                if st.button("Gravar Atualização", type="secondary", use_container_width=True):
                    if nova_atualizacao:
                        # Junta o texto antigo com o novo texto de atualização para não perder o histórico
                        texto_atualizado = f"{chamado_atual['solicitacao']}\n\n[Nova Atualização]: {nova_atualizacao}"
                        
                        supabase.table("atendimentos").update({
                            "solicitacao": texto_atualizado,
                            "etapa": nova_etapa
                        }).eq("id", chamado_atual['id']).execute()
                        
                        st.success("Chamado atualizado com sucesso!")
                        st.rerun() # Atualiza a tela para sumir da lateral se foi concluído
                    else:
                        st.warning("Escreva o que foi feito antes de salvar.")
            else:
                st.info("Não há chamados em andamento para atualizar no momento.")

    # ------------------ VISÃO DO SUPERVISOR (DASHBOARD) ------------------
    elif st.session_state.user_role == "Supervisor":
        st.subheader("📊 Dashboard Executivo de Supervisão")
        
        resposta = supabase.table("atendimentos").select("*, perfis(email)").execute()
        
        if resposta.data:
            df = pd.DataFrame(resposta.data)
            df['Colaborador'] = df['perfis'].apply(lambda x: x['email'] if isinstance(x, dict) else 'Desconhecido')
            df['Data'] = pd.to_datetime(df['data_hora']).dt.date
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Atendimentos", len(df))
            m2.metric("Atendimentos Em Andamento", len(df[df['etapa'] == 'Em andamento']))
            m3.metric("Atendimentos Concluídos", len(df[df['etapa'] == 'Concluído']))
            
            st.divider()
            
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("### 👥 Atendimentos por Colaborador")
                st.bar_chart(df['Colaborador'].value_counts())
            with g2:
                st.markdown("### 📞 Atendimentos por Meio de Contato")
                st.bar_chart(df['meio_contato'].value_counts())
                
            st.divider()
            st.markdown("### 📅 Evolução Diária de Atendimentos")
            st.line_chart(df.groupby('Data').size())
            
            st.divider()
            st.markdown("### 📑 Histórico Completo de Registros")
            df_exibicao = df[['Data', 'Colaborador', 'morador', 'meio_contato', 'solicitacao', 'etapa']]
            df_exibicao.columns = ['Data', 'Atendente', 'Morador', 'Meio de Contato', 'Histórico/Solicitação', 'Status']
            st.dataframe(df_exibicao, use_container_width=True)
            
        else:
            st.info("Nenhum atendimento registrado no sistema para gerar o dashboard.")
