import streamlit as st
from openai import OpenAI
import PyPDF2

# ---------------------------------------------------------
# 1. 환경 설정 및 API 클라이언트 초기화 (Streamlit Secrets만 사용)
# ---------------------------------------------------------
# Streamlit Secrets에서 API 키를 가져옵니다.
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("⚠️ Streamlit Secrets에 OPENAI_API_KEY가 설정되어 있지 않습니다.")
    st.stop()

client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# 2. PDF 텍스트 추출 함수
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    extracted_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text

# ---------------------------------------------------------
# 3. 웹 UI 설정 및 봇 시스템 프롬프트 구성
# ---------------------------------------------------------
st.set_page_config(page_title="수학 튜터 봇", page_icon="📚", layout="centered")
st.title("📚 수학 튜터 봇 (PDF 지원)")
st.caption("수학문제 PDF를 업로드하고 풀이 방향을 질문해 보세요!")

if "messages" not in st.session_state:
    system_prompt = """
    당신은 학생들이 어려운 문제를 스스로 해결할 수 있도록 돕는 친절하고 논리적인 전과목 수학 튜터입니다.
    학생이 문제를 제시하거나 업로드한 PDF 내용을 바탕으로 질문하면, 정답이나 최종 계산식을 바로 알려주지 마세요.
    대신 다음 가이드라인을 따르세요:
    1. 문제의 핵심을 파악하여 어떤 수학적 개념이나 공식(예: 방정식, 함수, 기하, 미적분, 확률 등 문제에 해당하는 개념)을 적용해야 하는지 차근차근 설명합니다.
    2. 문제를 해결하기 위해 어떤 단계로 나누어 생각해야 하는지 풀이의 '접근 방향'과 '논리적 흐름'을 제시합니다.
    3. 조건이 복잡하거나 여러 조건이 얽혀 있는 경우, 케이스를 어떻게 분류하고 단계를 어떻게 쪼개야 할지 힌트를 제공합니다.
    4. 학생이 개념을 바탕으로 스스로 식을 세우고 계산할 수 있도록 유도하는 질문으로 마무리합니다.
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    st.session_state.uploaded_filename = None
# ---------------------------------------------------------
# 4. 사이드바 - PDF 업로드
# ---------------------------------------------------------
with st.sidebar:
    st.header("📄 문제 파일 업로드")
    uploaded_file = st.file_uploader("PDF 형식의 수학 문제를 업로드하세요.", type=["pdf"])
    
    if uploaded_file is not None:
        if st.session_state.uploaded_filename != uploaded_file.name:
            with st.spinner("PDF를 분석하는 중입니다..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                context_message = f"[시스템 메시지: 학생이 다음 내용의 PDF를 업로드했습니다.]\n\n{pdf_text}"
                st.session_state.messages.append({"role": "system", "content": context_message})
                st.session_state.uploaded_filename = uploaded_file.name
                
            st.success("✅ PDF 업로드 및 분석 완료! 문제 번호나 내용을 질문해 보세요.")

# ---------------------------------------------------------
# 5. 메인 화면 - 챗봇 대화
# ---------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if user_input := st.chat_input("수학 문제에 대해 질문해 보세요. (예: 방금 올린 3번 문제 힌트 줘)"):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # 설정하신 gpt-5.4-mini 모델 사용
            response = client.chat.completions.create(
                model="gpt-5.4-mini", 
                messages=st.session_state.messages,
                temperature=0.6
            )
            bot_reply = response.choices[0].message.content
            message_placeholder.markdown(bot_reply)
            
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
        except Exception as e:
            st.error(f"🚨 API 호출 중 오류가 발생했습니다: {e}")
