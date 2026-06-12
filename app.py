import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone
import time
from streamlit_autorefresh import st_autorefresh
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA (Com a nova marca) ---
st.set_page_config(page_title="Lake Side - Resident Services", layout="wide", page_icon="🏢")

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

# --- CHAVES DE MEMÓRIA PARA LIMPEZA DO FORMULÁRIO ---
if 'form_pessoa' not in st.session_state:
    st.session_state.form_pessoa = ""
if 'form_solicitacao' not in st.session_state:
    st.session_state.form_solicitacao = ""

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

def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string

# --- INTERFACE DE LOGIN (Marca Lake Side) ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        image = Image.open('lakeside_logo.png') # Carrega a logo
        st.image(image, width=150) # Exibe a logo
        st.title("Lake Side")
        st.subheader("Resident Services Platform")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            login_user(email, senha)
    st.stop()

# --- ÁREA LOGADA (Marca Lake Side) ---
user = st.session_state.user_info
nome_usuario_limpo = user['email'].split('@')[0] 
cargo = user['nivel_acesso']

# --- ATIVAÇÃO DO CRONÔMETRO AUTOMÁTICO (15 segundos) ---
st_autorefresh(interval=15000, key="lakeside_refresh")

# --- BARRA LATERAL FIXA (Marca Lake Side) ---
with st.sidebar:
    image = Image.open('lakeside_logo.png') # Carrega a logo
    st.image(image, width=75) # Exibe a logo
    st.title(f"Hello, {nome_usuario_limpo}")
    st.info(f"Level: {cargo}")
    
    if st.button("Logout", use_container_width=True):
        logout()
    
    st.divider()
    
    if cargo in ['Atendente', 'Manutenção', 'Financeiro']:
        if st.button("➕ New Service Request", use_container_width=True, type="primary"):
            st.session_state.view_modo = "Novo"
            st.session_state.ticket_selecionado = None
            st.rerun()

# --- PAINEL PRINCIPAL OPERACIONAL (Marca Lake Side) ---
if cargo in ['Atendente', 'Manutenção', 'Financeiro']:
    
    col_esquerda, col_direita = st.columns([1, 3])
    
    # COLUNA ESQUERDA: LISTA DE CHAMADOS FILTRADA
    with col_esquerda:
        sub_c1, sub_c2 = st.columns([3, 1])
        sub_c1.subheader("📌 Service Requests")
        if sub_c2.button("🔄", help="Refresh list"):
            st.rerun()
        
        try:
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
                try:
                    dt_abertura = datetime.fromisoformat(t['data_hora'].replace("Z", "+00:00"))
                    data_texto = dt_abertura.strftime("%d/%m")
                    hora_texto = dt_abertura.strftime("%Hh%M")
                    
                    agora = datetime.now(timezone.utc)
                    horas_passadas = (agora - dt_abertura).total_seconds() / 3600
                    
                    if horas_passadas >= 4: status_cor = "🔴"
                    elif horas_passadas >= 2: status_cor = "🟠"
                    else: status_cor = "🟢"
                except:
                    data_texto, hora_texto, status_cor = "--/--", "--h--", "⚪"

                label_completa = f"{status_cor} Nº {t['id']} - {t['pessoa']} ({t['categoria_solicitacao']}) [{data_texto} - {hora_texto}]"
                if st.button(label_completa, key=f"btn_{t['id']}", use_container_width=True):
                    st.session_state.ticket_selecionado = t['id']
                    st.session_state.view_modo = "Atualizar"
                    st.rerun()
        else:
            st.info("No service requests pending.")
            
    # COLUNA DIREITA: CONTEÚDO DINÂMICO
    with col_direita:
        st.title("📋 Resident Services Dashboard")
        st.divider()
        
        if st.session_state.view_modo == "Aguardando":
            st.info("💡 Select a service request on the left or click '➕ New Service Request' on the sidebar.")

        elif st.session_state.view_modo == "Novo":
            st.subheader("📝 Request New Service")
            
            with st.form("form_novo", clear_on_submit=True):
                c1, c2 = st.columns(2)
                pessoa = c1.text_input("Person (Name)", value=st.session_state.form_pessoa, key="txt_pessoa")
                tipo_persona = c2.selectbox("Person Type", ["Resident", "Staff", "Guest", "Visitor"])
                
                c3, c4 = st.columns(2)
                meio = c3.selectbox("Contact Method", ["WhatsApp", "Phone", "In Person"])
                
                indice_padrao_categoria = 0
                if cargo == "Manutenção": indice_padrao_categoria = 2
                elif cargo == "Financeiro": indice_padrao_categoria = 3
                
                categoria_solicitacao = c4.selectbox(
                    "Service Type", 
                    ["Security", "Information", "Maintenance", "Financial"],
                    index=indice_padrao_categoria
                )
                
                etapa_inicial = st.selectbox("Status", ["In Progress", "Completed"])
                solicitacao_detalhe = st.text_area("Detailed Request Description", value=st.session_state.form_solicitacao, key="txt_solicitacao")
                
                # Permissão para anexar imagem no novo chamado
                c5, c6 = st.columns(2)
                foto_anexa = c5.file_uploader("📸 Anexar foto da ocorrência?", type=["png", "jpg", "jpeg"])

                if st.form_submit_button("Submit Request", type="primary"):
                    if pessoa and solicitacao_detalhe:
                        url_foto_final = None
                        
                        if foto_anexa:
                            nome_arquivo = f"{int(time.time())}_{foto_anexa.name}"
                            bytes_data = foto_anexa.getvalue()
                            supabase.storage.from_("arquivos_chamados").upload(nome_arquivo, bytes_data)
                            url_foto_final = supabase.storage.from_("arquivos_chamados").get_public_url(nome_arquivo)
                        
                        data = {
                            "usuario_id": user['id'],
                            "pessoa": pessoa,
                            "tipo_pessoa": tipo_persona,
                            "meio_contato": meio,
                            "categoria_solicitacao": categoria_solicitacao,
                            "solicitacao": solicitacao_detalhe,
                            "etapa": etapa_inicial,
                            "url_imagem": url_foto_final
                        }
                        supabase.table("atendimentos").insert(data).execute()
                        
                        st.session_state.form_pessoa = ""
                        st.session_state.form_solicitacao = ""
                        
                        st.success("Request submitted successfully!")
                        time.sleep(1)
                        st.session_state.view_modo = "Novo" if cargo == "Atendente" else "Aguardando"
                        st.rerun()
                    else:
                        st.warning("Please fill required fields (Name and Description).")

        elif st.session_state.view_modo == "Atualizar":
            st.subheader("🔄 Update Request")
            tid = st.session_state.ticket_selecionado
            
            if tid:
                res = supabase.table("atendimentos").select("*").eq("id", tid).single().execute()
                chamado = res.data
                
                col_inf1, col_inf2, col_inf3 = st.columns(3)
                col_inf1.metric("Person", chamado['pessoa'])
                col_inf2.metric("Department", chamado.get('categoria_solicitacao', 'General'))
                try:
                    data_formatada = datetime.fromisoformat(chamado['data_hora'].replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
                except:
                    data_formatada = "Date Unavailable"
                col_inf3.metric("Opened", data_formatada)
                
                st.markdown("**Request History:**")
                st.info(chamado['solicitacao'])
                
                # Exibição de imagem se houver
                if chamado.get('url_imagem'):
                    st.markdown("**📸 Request Photo:**")
                    st.image(chamado['url_imagem'], width=450)
                
                with st.form("form_update"):
                    nova_att = st.text_area("Describe progress:")
                    nova_etapa = st.selectbox("Current Status", ["In Progress", "Completed"])
                    
                    # Permissão para anexar imagem na atualização (CORREÇÃO PEDIDA)
                    c5, c6 = st.columns(2)
                    foto_anexa = c5.file_uploader("📸 Anexar nova foto?", type=["png", "jpg", "jpeg"])
                    
                    if st.form_submit_button("Save Update", type="primary"):
                        if nova_att:
                            data_hora_agora = datetime.now().strftime('%d/%m %H:%M')
                            historico_updated = f"{chamado['solicitacao']}\n\n--- Update ({data_hora_agora}) by [{nome_usuario_limpo} - {cargo}] ---\n{nova_att}"
                            
                            url_foto_final = chamado.get('url_imagem') # Mantém a antiga se não houver nova

                            if foto_anexa:
                                nome_arquivo = f"{int(time.time())}_{foto_anexa.name}"
                                bytes_data = foto_anexa.getvalue()
                                supabase.storage.from_("arquivos_chamados").upload(nome_arquivo, bytes_data)
                                url_foto_final = supabase.storage.from_("arquivos_chamados").get_public_url(nome_arquivo)
                            
                            supabase.table("atendimentos").update({
                                "solicitacao": historico_updated,
                                "etapa": nova_etapa,
                                "url_imagem": url_foto_final
                            }).eq("id", tid).execute()
                            
                            st.success("Request updated!")
                            time.sleep(1)
                            st.session_state.ticket_selecionado = None
                            st.session_state.view_modo = "Novo" if cargo == "Atendente" else "Aguardando"
                            st.rerun()
                        else:
                            st.warning("Please enter a description.")
            else:
                st.info("Select a request on the left.")

# --- FLUXO 3: VISÃO DO SUPERVISOR (Marca Lake Side) ---
elif cargo == 'Supervisor':
    st.title("📋 Resident Services Dashboard")
    st.subheader("📊 Executive Supervision Overview")
    
    resposta_banco = supabase.table("atendimentos").select("*, perfis(email)").execute()
    df = pd.DataFrame(resposta_banco.data)
    
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Requests", len(df))
        m2.metric("In Progress", len(df[df['etapa'] == 'In Progress']))
        m3.metric("Completed", len(df[df['etapa'] == 'Completed']))
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Requests per Staff")
            df['atendente'] = df['perfis'].apply(lambda x: x['email'] if isinstance(x, dict) else 'N/A')
            st.bar_chart(df['atendente'].value_counts())
        with c2:
            st.subheader("Demands per Department")
            if 'categoria_solicitacao' in df.columns:
                st.bar_chart(df['categoria_solicitacao'].value_counts())
            
        st.subheader("Daily Request Flow")
        df['data'] = pd.to_datetime(df['data_hora']).dt.date
        st.line_chart(df.groupby('data').size())
        
        st.subheader("📋 Complete Audit History")
        df_exibicao = df.copy()
        colunas_exibir = ['id', 'data_hora', 'atendente', 'pessoa', 'meio_contato', 'categoria_solicitacao', 'etapa']
        colunas_existentes = [c for c in colunas_exibir if c in df_exibicao.columns]
        st.dataframe(df_exibicao[colunas_existentes], use_container_width=True)
    else:
        st.info("No data found.")
