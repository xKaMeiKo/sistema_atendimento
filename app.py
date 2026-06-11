import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. Configuração da página
st.set_page_config(page_title="Sistema de Chamados Inteligente", page_icon="📋", layout="wide")

# CONEXÃO COM O SUPABASE (Mantenha as suas chaves aqui)
SUPABASE_URL = "https://vsnojpmvkvijgeflkltn.supabase.co"
SUPABASE_KEY = "sb_publishable_EFjZ74m8m8bxBFYiNhvjaA_aIyGzRS8"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# Inicialização de estados da sessão importantes para a navegação e limpeza
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""  
    st.session_state.user_id = ""
if "chamado_selecionado_id" not in st.session_state:
    st.session_state.chamado_selecionado_id = None
if "tela_atual" not in st.session_state:
    st.session_state.tela_atual = "novo" # 'novo' ou 'atualizar'

# Chaves para forçar a limpeza do formulário de novos registros
if "form_morador" not in st.session_state:
    st.session_state.form_morador = ""
if "form_solicitacao" not in st.session_state:
    st.session_state.form_solicitacao = ""

# Função para resumir textos longos
def gerar_resumo(texto, max_caracteres=55):
    if len(texto) <= max_caracteres:
        return texto
    return texto[:max_caracteres].strip() + "..."

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
    # Busca os chamados abertos no início
    try:
        busca_abertos = supabase.table("atendimentos").select("id, morador, solicitacao, meio_contato").eq("etapa", "Em andamento").execute()
        chamados_abertos = busca_abertos.data
    except Exception:
        chamados_abertos = []

    # ------------------ BARRA LATERAL (MENU CLICÁVEL) ------------------
    with st.sidebar:
        st.write(f"👤 **Usuário:** {st.session_state.user_email}")
        st.write(f"🛡️ **Nível:** {st.session_state.user_role}")
        
        st.divider()
        
        # Botão dedicado para abrir a tela de Novo Registro e limpar seleções anteriores
        if st.button("➕ Criar Novo Atendimento", use_container_width=True, type="secondary"):
            st.session_state.tela_atual = "novo"
            st.session_state.chamado_selecionado_id = None
            st.rerun()
            
        st.divider()
        st.subheader("⚠️ Chamados Ativos (Clique para Tratar)")
        
        if chamados_abertos:
            for chamado in chamados_abertos:
                resumo = gerar_resumo(chamado['solicitacao'])
                label_botao = f"Nº {chamado['id']} - {chamado['morador']}\n💬 {resumo}"
                
                # Clicar aqui agora GARANTE a troca de tela sem travar no componente visual anterior
                if st.button(label_botao, key=f"btn_{chamado['id']}", use_container_width=True):
                    st.session_state.chamado_selecionado_id = chamado['id']
                    st.session_state.tela_atual = "atualizar"
                    st.rerun()
        else:
            st.info("Nenhum chamado pendente.")
            
        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()

    # ------------------ PAINEL PRINCIPAL ------------------
    st.title("📋 Painel de Controle de Atendimentos")
    st.divider()
    
    # ------------------ VISÃO DO ATENDENTE ------------------
    if st.session_state.user_role == "Atendente":

        # TELA 1: NOVO ATENDIMENTO
        if st.session_state.tela_atual == "novo":
            st.subheader("📝 Registrar Novo Atendimento")
            
            col1, col2 = st.columns(2)
            with col1:
                # Usamos a chave de sessão 'value' para conseguir zerar o campo programaticamente
                morador = st.text_input("Nome do Morador", value=st.session_state.form_morador, key="input_morador")
                meio_contato = st.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
            with col2:
                etapa = st.selectbox("Etapa Inicial", ["Em andamento", "Concluído"])
                
            solicitacao = st.text_area("Solicitação (Descreva o que foi pedido)", value=st.session_state.form_solicitacao, key="input_solicitacao")
            
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
                    
                    # SUCESSO! Agora limpamos as caixas de texto limpando o estado delas
                    st.session_state.form_morador = ""
                    st.session_state.form_solicitacao = ""
                    
                    st.success("Atendimento registrado com sucesso! O formulário foi limpo.")
                    st.rerun() # Reinicia a página com os campos limpos
                else:
                    st.warning("Por favor, preencha o nome do morador e a solicitação.")
                    
        # TELA 2: ATUALIZAR CHAMADO
        elif st.session_state.tela_atual == "atualizar":
            if chamados_abertos:
                opcoes_chamados = {f"Nº {c['id']} - {c['morador']}": c for c in chamados_abertos}
                
                index_padrao = 0
                if st.session_state.chamado_selecionado_id:
                    for i, (texto, ch) in enumerate(opcoes_chamados.items()):
                        if ch['id'] == st.session_state.chamado_selecionado_id:
                            index_padrao = i
                            break
                
                selecionado = st.selectbox("Escolha o chamado para tratar:", list(opcoes_chamados.keys()), index=index_padrao)
                chamado_atual = opcoes_chamados[selecionado]
                
                st.markdown("### 📄 Detalhes do Chamado Selecionado")
                with st.container(border=True):
                    st.markdown(f"**Morador:** {chamado_atual['morador']} | **Contato:** {chamado_atual['meio_contato']}")
                    st.write(chamado_atual['solicitacao'])
                
                nova_atualizacao = st.text_area("Descreva a atualização ou andamento da situação:")
                nova_etapa = st.selectbox("Mudar Status para:", ["Em andamento", "Concluído"], key="atualizar_status")
                
                if st.button("Gravar Atualização", type="secondary", use_container_width=True):
                    if nova_atualizacao:
                        texto_atualizado = f"{chamado_atual['solicitacao']}\n\n[Nova Atualização]: {nova_atualizacao}"
                        
                        supabase.table("atendimentos").update({
                            "solicitacao": texto_atualizado,
                            "etapa": nova_etapa
                        }).eq("id", chamado_atual['id']).execute()
                        
                        # Limpa os estados de seleção e força o retorno para a tela de novo cadastro limpo
                        st.session_state.chamado_selecionado_id = None
                        st.session_state.tela_atual = "novo"
                        st.session_state.form_morador = ""
                        st.session_state.form_solicitacao = ""
                        st.success("Chamado atualizado com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Escreva o que foi feito antes de salvar.")
            else:
                st.info("Não há chamados em andamento para atualizar no momento.")
                st.session_state.tela_atual = "novo"
                st.rerun()

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
