import streamlit as st
from openai import OpenAI
import PyPDF2
import os

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

# 오답 노트를 영구 저장할 파일 경로 설정
NOTES_FILE = "wrong_notes.txt"

# ---------------------------------------------------------
# 2. 기능 함수 정의
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    extracted_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text

def load_wrong_notes():
    """저장된 오답노트 파일을 읽어오는 함수"""
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "아직 기록된 오답 내용이 없습니다."

def save_wrong_note(new_note):
    """새로운 오답 내용을 파일에 누적하여 저장하는 함수"""
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(new_note + "\n")

# ---------------------------------------------------------
# 3. 웹 UI 설정 및 봇 시스템 프롬프트 구성
# ---------------------------------------------------------
st.set_page_config(page_title="재완이형은 이렇게 풀더라고 ", page_icon="📚", layout="centered")
st.title("📚 재완이형은 이렇게 풀더라고 ")
st.caption("문제집 PDF를 업로드하고 풀이 방향을 질문해 보세요! 잘 모르겠는 유형의 변형 문제를 원하시면 요청하세요!")

# 영구 저장소에서 과거 오답 내역을 실시간으로 불러옴
past_notes = load_wrong_notes()

if "messages" not in st.session_state:
    system_prompt = f"""
    당신은 학생들이 모든 과목(수학, 과학, 영어, 국어, 사회 등)의 어려운 내용을 스스로 이해하고 해결할 수 있도록 돕는 친절하고 친근하며 마치 형 같은 논리적인 만능 전과목 공부 튜터입니다.
    
    ★ [매우 중요 - 과거 오답 및 취약점 내역 정보] ★
    학생의 영구 저장소에서 불러온 과거 오답 및 취약점 기록은 다음과 같습니다:
    \"\"\"
    {past_notes}
    \"\"\"
    이 과거 기록을 반드시 인지하고 대화에 임하세요. 대화 도중 학생이 과거에 틀렸거나 헷갈려했던 과목/유형과 비슷한 문제를 물어보면, 친근한 형처럼 "야, 너 지난번에 이 유형에서 좀 해맸던 거 기억나지? 그때 형이 말해준 원리 다시 한번 떠올려보자."와 같이 과거의 오답 기록을 적극적으로 연관 지어 설명해 주세요.
    
    학생이 직접 질문을 던지거나 교재/문제지 PDF 내용을 바탕으로 질문하면, 단순한 정답이나 최종 해설을 통째로 바로 알려주지 마세요. 
    대신 학습 효과를 극대화하기 위해 다음 가이드라인을 엄격히 따르세요:
    
    1. 과목 맞춤형 핵심 짚기:
       - 수학/과학: 문제의 핵심이 되는 원리나 공식이 무엇인지 먼저 리마인드해 줍니다.
       - 국어/영어: 지문의 핵심 맥락, 주제, 또는 문법적 포인트가 무엇인지 파악하도록 유도합니다. 또한 국어부분에서 시 혹은 고전 시가의 해석 또한 알려줍니다
       - 사회/역사: 해당 사건이나 개념의 배경지식을 가볍게 설명해 줍니다.
       
    2. 단계별 접근 및 힌트 제공:
       - 한 번에 풀이를 다 보여주지 말고, "1단계로 무엇부터 생각해보면 좋을까?"라며 풀이나 분석의 '첫 단추'를 끼울 수 있는 방향과 힌트만 제시합니다.
       
    3. 복잡한 내용 단순화:
       - 복잡한 지문이나 조건, 긴 공식이 얽혀 있다면 이해하기 쉽게 핵심 케이스나 요약 단계를 나누어 생각할 수 있도록 브레이크다운(쪼개기) 해줍니다.
       
    4. 자기주도적 질문으로 마무리:
       - 항상 "이 힌트를 바탕으로 직접 해보면 어떨까?", "방금 말한 단어를 지문에서 찾아볼 수 있겠니?" 등 학생이 직접 행동하고 생각하게 만드는 유도 질문으로 답변을 끝마치세요.
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    st.session_state.uploaded_filename = None

# ---------------------------------------------------------
# 4. 사이드바 - PDF 업로드 및 오답 기록 관리
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
            
    st.markdown("---")
    st.header("📝 저장된 오답 기록")
    st.text_area("영구 저장된 취약 유형 내역", past_notes, height=200, disabled=True)
    
    # 오답 기록 초기화 버튼
    if st.button("🗑/오답 기록 전체 삭제"):
        if os.path.exists(NOTES_FILE):
            os.remove(NOTES_FILE)
        st.success("오답 기록이 초기화되었습니다. 앱이 새로고침됩니다.")
        st.rerun()

# ---------------------------------------------------------
# 5. 메인 화면 - 챗봇 대화 및 자동 영구 저장
# ---------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if user_input := st.chat_input("늘어져"):
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
            
            # [💡 영구 오답노트 자동 추출 백그라운드 로직]
            # 대화가 끝나면 GPT가 이번 대화에서 발견된 취약점을 한 줄 요약합니다.
            summary_prompt = [
                {"role": "system", "content": "너는 학생의 대화를 분석하는 관리자 형이야. 방금 대화 내용을 바탕으로 학생이 해맸거나 틀린 문제의 '과목'과 '취약 유형'을 딱 한 줄로만 요약해줘. 예: [수학] 순열과 조합 - 이웃하는 순열 조건 헷갈려함. 만약 단순 인사거나 취약점이 없다면 '없음'이라고만 답해."},
                {"role": "user", "content": f"학생 질문: {user_input}\n튜터 답변: {bot_reply}"}
            ]
            summary_response = client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=summary_prompt,
                temperature=0.3
            )
            analysis_result = summary_response.choices[0].message.content.strip()
            
            # 분석 결과가 유효하면 wrong_notes.txt 파일에 영구 기록
            if analysis_result and "없음" not in analysis_result:
                save_wrong_note(analysis_result)
                
        except Exception as e:
            st.error(f"🚨 API 호출 중 오류가 발생했습니다: {e}")
