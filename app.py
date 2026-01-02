import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from docx import Document
from io import BytesIO
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import time

# Tenta importar a biblioteca legislativa local
try:
    import legislacao
except ImportError:
    st.error("⚠️ Ficheiro 'legislacao.py' não encontrado. Cria-o na mesma pasta do app.py.")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Auditor de Políticas Públicas & Compliance",
    page_icon="⚖️",
    layout="wide"
)

# --- ESTILO CSS ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%; 
        border-radius: 8px; 
        height: 3em;
        font-weight: bold;
    }
    .reportview-container { margin-top: -2em; }
    h1 { color: #2c3e50; }
    .stExpander { border: 1px solid #ddd; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.markdown("# ⚖️")
with col2:
    st.title("Análise Ambiental")
    st.caption("Protocolo PATE v4.0 | Biblioteca Legislativa Residente & Pesquisa Web")

# --- SIDEBAR: CONFIGURAÇÃO ---
with st.sidebar:
    st.header("⚙️ 1. Motor de IA")
    api_key = st.text_input("Google Gemini API Key", type="password")
    if not api_key:
        st.warning("Insere a chave para iniciar.")
        st.markdown("[Obter chave gratuita](https://aistudio.google.com/)")
    
    st.divider()
    
    # --- BIBLIOTECA LEGISLATIVA DINÂMICA ---
    st.header("📚 2. Biblioteca Legislativa")
    st.info("Ativa os regimes legais aplicáveis à análise:")
    
    library = legislacao.get_library()
    library_context = ""
    active_laws_count = 0
    
    # Gerar Checkboxes dinâmicos baseados no ficheiro legislacao.py
    for category, laws in library.items():
        with st.expander(f"📂 {category}", expanded=False):
            for law_name, details in laws.items():
                if st.checkbox(law_name, value=False, key=law_name):
                    active_laws_count += 1
                    library_context += f"- [ATIVA] {law_name} ({details['nivel']})\n"
                    library_context += f"  MANDATO: {details['mandato']}\n"
                    library_context += f"  LINK: {details['link']}\n\n"
    
    if active_laws_count > 0:
        st.success(f"✅ {active_laws_count} diplomas ativados.")

    st.divider()
    
    st.header("🌐 3. Fontes Externas")
    # Upload Manual
    uploaded_legal_docs = st.file_uploader("Upload PDFs Adicionais", type="pdf", accept_multiple_files=True)
    
    # Pesquisa Web
    search_query = st.text_input("Pesquisa Web Adicional", placeholder="Ex: Portaria n.º 123/2024")
    use_web_search = st.checkbox("Ativar Pesquisa Online", value=True)

# --- FUNÇÕES ---

def get_pdf_text(pdf_file):
    """Extrai texto de PDF com tratamento de erros."""
    text = ""
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        st.error(f"Erro ao ler {pdf_file.name}: {e}")
    return text

def search_online(query):
    """Pesquisa no DuckDuckGo e extrai conteúdo."""
    if not query: return ""
    results_text = ""
    status = st.empty()
    status.info(f"🔎 A pesquisar: '{query}'...")
    
    try:
        with DDGS() as ddgs:
            # Pesquisa focada em documentos legais
            results = list(ddgs.text(f"{query} legislação texto oficial", max_results=2))
        
        for r in results:
            try:
                # Timeout curto para não bloquear a app
                page = requests.get(r['href'], timeout=4)
                soup = BeautifulSoup(page.content, 'html.parser')
                # Extrair parágrafos
                text = "\n".join([p.text for p in soup.find_all('p')])[:3000]
                results_text += f"\n>>> FONTE ONLINE: {r['title']} ({r['href']}) <<<\n{text}\n"
            except:
                continue
        
        status.empty()
        return results_text
    except Exception as e:
        status.warning(f"Erro na pesquisa web: {e}")
        return ""

def create_docx(markdown_text):
    """Gera ficheiro Word formatado."""
    doc = Document()
    doc.add_heading('Relatório de Auditoria de Compliance', 0)
    
    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('# '): doc.add_heading(line[2:], 1)
        elif line.startswith('## '): doc.add_heading(line[3:], 2)
        elif line.startswith('### '): doc.add_heading(line[4:], 3)
        elif line.startswith('- ') or line.startswith('* '): 
            doc.add_paragraph(line[2:], style='List Bullet')
        else:
            clean_text = line.replace('**', '').replace('__', '')
            doc.add_paragraph(clean_text)
            
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def run_pate_audit(target_text, lib_ctx, manual_ctx, web_ctx, api_key):
    """Executa o Protocolo PATE via Gemini."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Construção do Contexto Legal Combinado
    full_legal_context = ""
    if lib_ctx:
        full_legal_context += f"\n=== BIBLIOTECA LEGISLATIVA ATIVADA ===\n{lib_ctx}"
    if manual_ctx:
        full_legal_context += f"\n=== LEGISLAÇÃO CARREGADA MANUALMENTE ===\n{manual_ctx[:20000]}"
    if web_ctx:
        full_legal_context += f"\n=== PESQUISA WEB ===\n{web_ctx}"

    prompt = f"""
    Atua como um **Consultor Sénior em Políticas Públicas e Jurídico**.
    Realiza uma AUDITORIA DE COMPLIANCE E ESTRATÉGIA ao documento fornecido.

    --- BASE DE CONFORMIDADE LEGAL (A TUA "VERDADE") ---
    {full_legal_context}
    ----------------------------------------------------

    Executa estritamente o PROTOCOLO PATE (v4.0):

    ## 1. RESUMO EXECUTIVO
    * Enquadramento do documento alvo (Objetivos, Autores, Data).
    * Estatuto de maturidade (Draft vs Final).

    ## 2. CHECK-UP DE CONFORMIDADE (CRUCIAL)
    * Cruza as medidas propostas no documento alvo com os mandatos da 'Biblioteca Legislativa'.
    * Identifica explicitamente: **"A medida X alinha-se com a Lei Y"** ou **"A medida Z parece violar o Regulamento W"**.
    * Se não houver legislação ativada, foca-te na consistência interna.

    ## 3. AUDITORIA DE EXEQUIBILIDADE
    * Avalia a robustez dos dados (ex: uso de proxies vs dados reais).
    * Avalia a segurança do financiamento e a capacidade operacional (recursos humanos).

    ## 4. ANÁLISE DE RISCO
    * Riscos Regionais (ex: assimetrias Ilhas/Continente).
    * Riscos Jurídicos (ex: litigância potencial).

    ## 5. RECOMENDAÇÕES (ACTIONABLE INSIGHTS)
    * 3 a 5 medidas corretivas concretas, baseadas na melhor técnica e na lei.

    --- DOCUMENTO ALVO ---
    {target_text}
    """
    
    return model.generate_content(prompt).text

# --- ÁREA PRINCIPAL ---
st.subheader("📄 Documento Alvo")
uploaded_target = st.file_uploader("Carrega o Relatório/Plano para análise", type="pdf")

if uploaded_target and api_key:
    if st.button("🚀 EXECUTAR AUDITORIA", type="primary"):
        with st.spinner("A processar documentos e a cruzar dados..."):
            try:
                # 1. Ler Documento Alvo
                target_txt = get_pdf_text(uploaded_target)
                
                # 2. Ler Uploads Manuais
                manual_ctx = ""
                if uploaded_legal_docs:
                    for f in uploaded_legal_docs:
                        manual_ctx += get_pdf_text(f)
                
                # 3. Pesquisa Web
                web_ctx = ""
                if use_web_search and search_query:
                    web_ctx = search_online(search_query)
                
                # 4. Executar IA
                result = run_pate_audit(target_txt, library_context, manual_ctx, web_ctx, api_key)
                
                # 5. Apresentar Resultados
                st.success("Análise Concluída.")
                
                tab1, tab2 = st.tabs(["📝 Relatório Visual", "💾 Exportar"])
                
                with tab1:
                    st.markdown(result)
                
                with tab2:
                    st.info("Descarrega o relatório editável.")
                    docx = create_docx(result)
                    st.download_button(
                        label="📄 Descarregar Word (.docx)",
                        data=docx,
                        file_name=f"Auditoria_{uploaded_target.name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    
                    st.download_button(
                        label="📥 Descarregar Markdown (.md)",
                        data=result,
                        file_name=f"Auditoria_{uploaded_target.name}.md"
                    )

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")

elif not uploaded_target:

    st.info("A aguardar documento...")
