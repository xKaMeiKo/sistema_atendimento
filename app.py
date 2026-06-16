import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone
import time
import base64
from streamlit_autorefresh import st_autorefresh

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

# Conversor de Imagem para Base64
def converter_para_base64(arquivo_upload):
    if arquivo_upload is not None:
        bytes_data = arquivo_upload.getvalue()
        extensao = arquivo_upload.name.split(".")[-1].lower()
        if extensao == "jpg": extensao = "jpeg"
        base64_texto = base64.b64encode(bytes_data).decode("utf-8")
        return f"data:image/{extensao};base64,{base64_texto}"
    return None

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
    
    st.subheader("📁 Navegação")
    menu_foco = st.radio("Exibir chamados:", ["Operação (Ativos)", "Histórico (Concluídos)"], key="menu_lateral_navegacao")
    
    st.divider()
    
    if cargo in ['Atendente', 'Manutenção', 'Financeiro']:
        if st.button("➕ Novo Atendimento", use_container_width=True, type="primary"):
            st.session_state.view_modo = "Novo"
            st.session_state.ticket_selecionado = None
            st.rerun()

# --- FLUXO 1: VISÃO OPERACIONAL (CHAMADOS ATIVOS COM BUSCA LATERAL) ---
if menu_foco == "Operação (Ativos)" and cargo in ['Atendente', 'Manutenção', 'Financeiro']:
    
    col_esquerda, col_direita = st.columns([1, 3])
    
    # COLUNA ESQUERDA: LISTA DE CHAMADOS FILTRADA
    with col_esquerda:
        sub_c1, sub_c2 = st.columns([3, 1])
        sub_c1.subheader("📌 Chamados")
        if sub_c2.button("🔄", key="btn_refresh_ativos"):
            st.rerun()
        
        # --- ADICIONADO: BARRA DE PESQUISA PARA FILTRAR OS CHAMADOS ATIVOS ---
        busca_ativo = st.text_input("🔍 Buscar ativo:", placeholder="Nº, nome ou unidade...", key="txt_busca_ativos_lateral")
        
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
            # Lógica de filtragem em tempo real na lista lateral
            if busca_ativo:
                dados_ativos_filtrados = []
                for t in dados_ativos:
                    termo_lateral = busca_ativo.lower().strip()
                    id_txt = str(t['id'])
                    pessoa_txt = t['pessoa'].lower() if t['pessoa'] else ""
                    setor_txt = t['categoria_solicitacao'].lower() if t['categoria_solicitacao'] else ""
                    
                    if termo_lateral in id_txt or termo_lateral in pessoa_txt or termo_lateral in setor_txt:
                        dados_ativos_filtrados = dados_ativos_filtrados + [t]
            else:
                dados_ativos_filtrados = dados_ativos

            # Renderização dos botões com base na busca
            if dados_ativos_filtrados:
                for t in dados_ativos_filtrados:
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
                st.info("Nenhum ativo encontrado.")
        else:
            st.info("Nenhum chamado pendente.")
            
    with col_direita:
        st.title("📋 Painel de Controle de Atendimentos")
        st.divider()
        
        if st.session_state.view_modo == "Aguardando":
            st.info("💡 Selecione um chamado na lista ao lado para tratar ou clique em '➕ Novo Atendimento'.")

        elif st.session_state.view_modo == "Novo":
            st.subheader("📝 Registrar Novo Atendimento")
            
            c1, c2 = st.columns(2)
            pessoa_input = c1.text_input("Pessoa (Nome)", value=st.session_state.form_pessoa, key="txt_pessoa")
            tipo_persona = c2.selectbox("Tipo de Pessoa", ["Morador", "Prestador", "Hóspede", "Visitante"])
            
            unidade_info = ""
            if tipo_persona == "Morador":
                unidade = st.text_input("Unidade (Ex: B402)", key="txt_unidade", max_chars=10)
                if unidade:
                    unidade_info = f" [{unidade.upper().strip()}]"
            
            c3, c4 = st.columns(2)
            meio = c3.selectbox("Meio de Contato", ["WhatsApp", "Telefone", "Pessoalmente"])
            
            indice_padrao_categoria = 0
            if cargo == "Manutenção": indice_padrao_categoria = 2
            elif cargo == "Financeiro": indice_padrao_categoria = 3
            
            categoria_solicitacao = c4.selectbox("Tipo de Solicitação", ["Liberação", "Informação", "Manutenção", "Financeiro"], index=indice_padrao_categoria)
            etapa_inicial = st.selectbox("Status Inicial", ["Em andamento", "Concluído"])
            solicitacao_detalhe = st.text_area("Descrição Detalhada da Solicitação", value=st.session_state.form_solicitacao, key="txt_solicitacao")
            
            foto_anexa = st.file_uploader("📸 Deseja anexar uma foto da ocorrência? (Opcional)", type=["png", "jpg", "jpeg"], key="upload_novo")
            
            if st.button("Registrar Chamado", type="primary", use_container_width=True):
                if pessoa_input and solicitacao_detalhe:
                    base64_foto = converter_para_base64(foto_anexa)
                    url_foto_final = None
                    
                    if base64_foto:
                        data_hora_criacao = datetime.now().strftime('%d/%m às %Hh%M')
                        url_foto_final = f"{base64_foto}::{nome_usuario_limpo}::{data_hora_criacao}"
                    
                    nome_final_banco = f"{pessoa_input}{unidade_info}"
                    
                    data = {
                        "usuario_id": user['id'],
                        "pessoa": nome_final_banco,
                        "tipo_pessoa": tipo_persona,
                        "meio_contato": meio,
                        "categoria_solicitacao": categoria_solicitacao,
                        "solicitacao": solicitacao_detalhe,
                        "etapa": etapa_inicial,
                        "url_imagem": url_foto_final
                    }
                    
                    try:
                        supabase.table("atendimentos").insert(data).execute()
                        st.session_state.form_pessoa = ""
                        st.session_state.form_solicitacao = ""
                        st.success("Chamado registrado com sucesso!")
                        time.sleep(1)
                        st.session_state.view_modo = "Novo" if cargo == "Atendente" else "Aguardando"
                        st.rerun()
                    except Exception as e:
                        st.error("🚨 Erro ao salvar no banco:")
                        st.code(str(e))
                else:
                    st.warning("Preencha os campos obrigatórios (Nome e Descrição).")

        elif st.session_state.view_modo == "Atualizar":
            tid = st.session_state.ticket_selecionado
            
            if tid:
                res = supabase.table("atendimentos").select("*").eq("id", tid).single().execute()
                chamado = res.data
                
                try:
                    dt_abertura = datetime.fromisoformat(chamado['data_hora'].replace("Z", "+00:00"))
                    data_texto = dt_abertura.strftime("%d/%m")
                    hora_texto = dt_abertura.strftime("%Hh%M")
                    
                    agora = datetime.now(timezone.utc)
                    horas_passadas = (agora - dt_abertura).total_seconds() / 3600
                    
                    if horas_passadas >= 4: status_cor = "🔴"
                    elif horas_passadas >= 2: status_cor = "🟠"
                    else: status_cor = "🟢"
                except:
                    data_texto, hora_texto, status_cor = "--/--", "--h--", "⚪"
                
                titulo_dinamico_chamado = f"{status_cor} Nº {chamado['id']} - {chamado['pessoa']} ({chamado.get('categoria_solicitacao', 'Geral')}) [{data_texto} - {hora_texto}]"
                st.subheader(titulo_dinamico_chamado)
                
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
                
                if chamado.get('url_imagem'):
                    st.markdown("**📸 Fotos do Histórico:**")
                    blocos_fotos = chamado['url_imagem'].split("||")
                    for idx, bloco in enumerate(blocos_fotos):
                        partes = bloco.split("::")
                        if len(partes) == 3:
                            string_foto, usuario_upload, data_upload = partes
                            titulo_expander = f"🖼️ Anexo por [{usuario_upload}] em ({data_upload})"
                        else:
                            string_foto = bloco
                            titulo_expander = f"🖼️ Anexo Antigo #{idx + 1}"
                            
                        with st.expander(titulo_expander):
                            st.image(string_foto, width=600, use_container_width=False)
                
                foto_atualizacao = st.file_uploader("📸 Deseja anexar mais uma foto a este chamado? (Histórico)", type=["png", "jpg", "jpeg"], key="upload_att")
                
                with st.form("form_update"):
                    nova_att = st.text_area("Descreva o andamento:")
                    nova_etapa = st.selectbox("Status Atual", ["Em andamento", "Concluído"])
                    
                    if st.form_submit_button("Gravar Alterações", type="primary"):
                        if nova_att:
                            historico_antigo = chamado['solicitacao']
                            numero_atualizacao = historico_antigo.count("Atualização") + 1
                            data_hora_agora = datetime.now().strftime('%d/%m às %Hh%M')
                            
                            nova_linha_historico = f"\n\n{numero_atualizacao}º Atualização - {data_hora_agora} - {nome_usuario_limpo} - {nova_att}"
                            historico_updated = f"{historico_antigo}{nova_linha_historico}"
                            
                            url_foto_existente = chamado.get('url_imagem')
                            base64_nova_foto = converter_para_base64(foto_atualizacao)
                            
                            if base64_nova_foto:
                                novo_bloco = f"{base64_nova_foto}::{nome_usuario_limpo}::{data_hora_agora}"
                                if url_foto_existente:
                                    url_foto_final = f"{url_foto_existente}||{novo_bloco}"
                                else:
                                    url_foto_final = novo_bloco
                            else:
                                url_foto_final = url_foto_existente
                            
                            supabase.table("atendimentos").update({
                                "solicitacao": historico_updated,
                                "etapa": nova_etapa,
                                "url_imagem": url_foto_final
                            }).eq("id", tid).execute()
                            
                            st.success("Atualizado!")
                            time.sleep(1)
                            st.session_state.ticket_selecionado = None
                            st.session_state.view_modo = "Aguardando"
                            st.rerun()
                        else:
                            st.warning("Insira uma descrição.")
            else:
                st.info("Selecione um chamado na lista lateral.")

# --- FLUXO 2: HISTÓRICO DE CONCLUÍDOS ---
elif menu_foco == "Histórico (Concluídos)" and cargo in ['Atendente', 'Manutenção', 'Financeiro']:
    st.title("🗃️ Arquivo Geral de Chamados Concluídos")
    st.markdown("Veja abaixo todos os atendimentos finalizados. Use o campo de busca para filtrar por nome, unidade, setor ou número.")
    
    busca = st.text_input("🔍 Pesquisar por Nome/Unidade, Setor ou Número do Chamado:", placeholder="Digite para buscar (Ex: B402, Hidráulica, 12)...")
    st.divider()

    try:
        query_f = supabase.table("atendimentos").select("*").eq("etapa", "Concluído")
        if cargo == "Manutenção":
            query_f = query_f.eq("categoria_solicitacao", "Manutenção")
        elif cargo == "Financeiro":
            query_f = query_f.eq("categoria_solicitacao", "Financeiro")
            
        res_concluidos = query_f.order("id", desc=True).execute()
        dados_concluidos = res_concluidos.data
    except Exception:
        dados_concluidos = []

    if dados_concluidos:
        if busca:
            dados_filtrados = []
            for item in dados_concluidos:
                termo = busca.lower().strip()
                id_texto = str(item['id'])
                nome_texto = item['pessoa'].lower() if item['pessoa'] else ""
                setor_texto = item['categoria_solicitacao'].lower() if item['categoria_solicitacao'] else ""
                
                if termo in id_texto or termo in nome_texto or termo in setor_texto:
                    dados_filtrados = dados_filtrados + [item]
        else:
            dados_filtrados = dados_concluidos

        if dados_filtrados:
            num_colunas = 3
            colunas_grade = st.columns(num_colunas)
            
            for idx, c in enumerate(dados_filtrados):
                with colunas_grade[idx % num_colunas]:
                    with st.container(border=True):
                        st.markdown(f"### ✅ Chamado Nº {c['id']}")
                        st.markdown(f"**Pessoa:** {c['pessoa']} ({c.get('tipo_pessoa', 'N/A')})")
                        st.markdown(f"**Setor:** `{c['categoria_solicitacao']}` | **Via:** {c.get('meio_contato', 'N/A')}")
                        
                        try:
                            dt_ab = datetime.fromisoformat(c['data_hora'].replace("Z", "+00:00")).strftime("%d/%m %H:%M")
                            st.markdown(f"📅 *Aberto em: {dt_ab}*")
                        except:
                            pass
                        
                        with st.expander("📝 Ver Histórico Textual"):
                            st.text(c['solicitacao'])
                        
                        if c.get('url_imagem'):
                            with st.expander("📸 Ver Imagens Anexadas"):
                                blocos_f = c['url_imagem'].split("||")
                                for sub_bloco in blocos_f:
                                    partes = sub_bloco.split("::")
                                    img_src = partes[0] if len(partes) == 3 else sub_bloco
                                    st.image(img_src, use_container_width=True)
                        
                        if st.button("🔄 Reabrir Chamado", key=f"reabrir_{c['id']}", use_container_width=True):
                            supabase.table("atendimentos").update({"etapa": "Em andamento"}).eq("id", c['id']).execute()
                            st.success(f"Nº {c['id']} reaberto!")
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.warning("Nenhum chamado corresponde aos critérios da sua pesquisa.")
    else:
        st.info("Nenhum chamado concluído encontrado para o seu setor.")

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
        st.info("Nenhum dado encontrado no banco.")
