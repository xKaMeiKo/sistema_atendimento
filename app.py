import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
import time
from streamlit_autorefresh import st_autorefresh

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

# --- ATIVAÇÃO DO CRONÔMETRO AUTOMÁTICO (15 segundos) ---
st_autorefresh(interval=15000, key="condotickets_refresh")

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
    
    col_esquerda, col_direita = st.columns([1, 3])
    
    # COLUNA ESQUERDA: LISTA DE CHAMADOS FILTRADA COM CORES E HORÁRIOS
    with col_esquerda:
        sub_c1, sub_c2 = st.columns([3, 1])
        sub_c1.subheader("📌 Chamados")
        if sub_c2.button("🔄", help="Atualizar lista agora"):
            st.rerun()
        
        try:
            # Puxamos também a coluna data_hora para fazer o cálculo do tempo
            query = supabase.table("atendimentos").select("id, pessoa, solicitacao, categoria_solicitacao, data_hora").eq("etapa", "Em andamento")
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
                # 1. TRATAMENTO E FORMATAÇÃO DA DATA/HORA
                try:
                    # Converte o texto do banco para um objeto de data real em Python
                    dt_abertura = datetime.fromisoformat(t['data_hora'].replace("Z", "+00:00"))
                    
                    # Formata para os padrões exigidos: dd/mm e 01h01
                    data_texto = dt_abertura.strftime("%d/%m")
                    hora_texto = dt_abertura.strftime("%Hh%M")
                    
                    # 2. CÁLCULO DO ESPECTRO DE URGÊNCIA (TEMPO EM ABERTO)
                    agora = datetime.now(timezone.utc)
                    diferenca = agora - dt_abertura
                    horas_passadas = diferenca.total_seconds() / 3600
                    
                    # Define a cor baseado no tempo solicitado
                    if horas_passadas >= 4:
                        status_cor = "🔴" # Mais de 4 horas sem fechar
                    elif horas_passadas >= 2:
                        status_cor = "🟠" # Entre 2 e 4 horas
                    else:
                        status_cor = "🟢" # Recente (menos de 2 horas)
                except:
                    data_texto = "--/--"
                    hora_texto = "--h--"
                    status_cor = "⚪"

                # 3. MONTAGEM DA LABEL DO BOTÃO COMPLETA
                # Formato: 🟢 Nº 12 - Lucas (Manutenção) [12/06 - 13h45]
                label_completa = f"{status_cor} Nº {t['id']} - {t['pessoa']} ({t['categoria_solicitacao']}) [{data_texto} - {hora_texto}]"
                
                if st.button(label_completa, key=f"btn_{t['id']}", use_container_width=True):
                    st.session_state.ticket_selecionado = t['id']
                    st.session_state.view_modo = "Atualizar"
                    st.rerun()
        else:
            st.info("Nenhum chamado pendente para o seu setor.")
            
    # COLUNA DIREITA: CONTEÚDO DINÂMICO
    with col_direita:
        st.title("📋 Painel de Controle de Atendimentos")
        st.divider()
        
        if st.session_state.view_modo == "Aguardando":
            st.info("💡 Selecione um chamado na lista ao lado para tratar ou clique em '➕ Novo Atendimento' na barra lateral. O painel se atualiza sozinho a cada 15 segundos.")

        elif st.session_state.view_modo == "Novo":
            st.subheader("📝 Registrar Novo Atendimento")
            
            with st.form("form_novo", clear_on_submit=True):
                c1, c2 = st.columns(2)
                pessoa = c1.text_input("Pessoa (Nome)")
                tipo_persona = c2.selectbox("Tipo de Pessoa", ["Morador", "Prestador", "Hóspede", "Visitante"])
                
                c3, c4 = st.columns(2)
                meio = c3.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
                
                indice_padrao_categoria = 0
                if cargo == "Manutenção": indice_padrao_categoria = 2
                elif cargo == "Financeiro": indice_padrao_categoria = 3
                
                categoria_solicitacao = c4.selectbox(
                    "Tipo de Solicitação", 
                    ["Liberação", "Informação", "Manutenção", "Financeiro"],
                    index=indice_padrao_categoria
                )
                
                etapa_inicial = st.selectbox("Status Inicial", ["Em andamento", "Concluído"])
                solicitacao_detalhe = st.text_area("Descrição Detalhada da Solicitação")
                
                if st.form_submit_button("Registrar Chamado", type="primary"):
                    if pessoa and solicitacao_detalhe:
                        data = {
                            "usuario_id": user['id'],
                            "pessoa": pessoa,
                            "tipo_pessoa": tipo_persona,
                            "meio_contato": meio,
                            "categoria_solicitacao": categoria_solicitacao,
                            "solicitacao": solicitacao_detalhe,
                            "etapa": etapa_inicial
                        }
                        supabase.table("atendimentos").insert(data).execute()
                        st.success("Chamado registrado!")
                        time.sleep(1)
                        st.session_state.view_modo = "Novo" if cargo == "Atendente" else "Aguardando"
                        st.rerun()
                    else:
                        st.warning("Preencha os campos obrigatórios.")

        elif st.session_state.view_modo == "Atualizar":
            st.subheader("🔄 Atualizar Chamado")
            tid = st.session_state.ticket_selecionado
            
            if tid:
                res = supabase.table("atendimentos").select("*").eq("id", tid).single().execute()
                chamado = res.data
                
                col_inf1, col_inf2, col_inf3 = st.columns(3)
                col_inf1.metric("Pessoa", chamado['pessoa'])
                col_inf2.metric("Departamento", chamado.get('categoria_solicitacao', 'Geral'))
                try:
                    data_formatada = datetime.fromisoformat(chamado['data_hora'].replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
                except:
                    data_formatada = "Data indisponível"
                col_inf3.metric("Abertura", data_formatada)
                
                st.markdown("**Histórico de Ocorrências:**")
                st.info(chamado['solicitacao'])
                
                with st.form("form_update"):
                    nova_att = st.text_area("Descreva o andamento:")
                    nova_etapa = st.selectbox("Status Atual", ["Em andamento", "Concluído"])
                    
                    if st.form_submit_button("Gravar Alterações", type="primary"):
                        if nova_att:
                            data_hora_agora = datetime.now().strftime('%d/%m %H:%M')
                            historico_updated = f"{chamado['solicitacao']}\n\n--- Atualização ({data_hora_agora}) por [{nome_usuario_limpo} - {cargo}] ---\n{nova_att}"
                            
                            supabase.table("atendimentos").update({
                                "solicitacao": historico_updated,
                                "etapa": nova_etapa
                            }).eq("id", tid).execute()
                            
                            st.success("Atualizado!")
                            time.sleep(1)
                            st.session_state.ticket_selecionado = None
                            st.session_state.view_modo = "Novo" if cargo == "Atendente" else "Aguardando"
                            st.rerun()
                        else:
                            st.warning("Insira uma descrição.")
            else:
                st.info("Selecione um chamado na lista lateral.")

# --- FLUXO 3: VISÃO DO SUPERVISOR ---
elif cargo == 'Supervisor':
    st.title("📋 Painel de Controle de Atendimentos")
    st.subheader("📊 Dashboard Executivo de Supervisão Geral")
    
    resposta_banco = supabase.table("atendimentos").select("*, perfis(email)").execute()
    df = pd.DataFrame(resposta_banco.data)
    
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Atendimentos", len(df))
        m2.metric("Em Andamento", len(df[df['etapa'] == 'Em andamento']))
        m3.metric("Concluídos", len(df[df['etapa'] == 'Concluído']))
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Atendimentos por Colaborador")
            df['atendente'] = df['perfis'].apply(lambda x: x['email'] if isinstance(x, dict) else 'N/A')
            st.bar_chart(df['atendente'].value_counts())
        with c2:
            st.subheader("Demandas por Setor")
            if 'categoria_solicitacao' in df.columns:
                st.bar_chart(df['categoria_solicitacao'].value_counts())
            
        st.subheader("Evolução Diária")
        df['data'] = pd.to_datetime(df['data_hora']).dt.date
        st.line_chart(df.groupby('data').size())
        
        st.subheader("📋 Histórico Completo")
        df_exibicao = df.copy()
        colunas_exibir = ['id', 'data_hora', 'atendente', 'pessoa', 'meio_contato', 'categoria_solicitacao', 'etapa']
        colunas_existentes = [c for c in colunas_exibir if c in df_exibicao.columns]
        st.dataframe(df_exibicao[colunas_existentes], use_container_width=True)
    else:
        st.info("Nenhum dado encontrado no banco para consolidar o painel gerencial.")
