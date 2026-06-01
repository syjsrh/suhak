import streamlit as st
from openai import OpenAI
import PyPDF2
import sqlite3
import hashlib
import os

# ---------------------------------------------------------
# 1. 환경 설정 및 API 클라이언트 초기화
# ---------------------------------------------------------
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.error("⚠️ Streamlit Secrets에 OPENAI_API_KEY가 설정되어 있지 않습니다.")
    st.stop()

client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# 2. 로컬 데이터베이스(DB) 설정 및 유저 관리 함수
# ---------------------------------------------------------
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, tier TEXT, usage_count INTEGER, wrong_notes TEXT)''')
    
    # 마스터 계정 자동 생성
    c.execute("SELECT * FROM users WHERE username='master'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, 'paid', 0, '아직 기록된 오답 내용이 없습니다.')", 
                  ('master', make_hash('1234')))
        
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, 'free', 0, '아직 기록된 오답 내용이 없습니다.')", 
                  (username, make_hash(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, make_hash(password)))
    user = c.fetchone()
    conn.close()
    return user

def get_user_data(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT tier, usage_count, wrong_notes FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    return data

def update_user_usage(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET usage_count = usage_count + 1 WHERE username=?", (username,))
    conn.commit()
    conn.close()

def save_user_wrong_note(username, new_note):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT wrong_notes FROM users WHERE username=?", (username,))
    current_notes = c.fetchone()[0]
    if "아직 기록된" in current_notes:
        current_notes = ""
    updated_notes = current_notes + new_note + "\n"
    c.execute("UPDATE users SET wrong_notes=? WHERE username=?", (updated_notes, username))
    conn.commit()
    conn.close()

def clear_user_wrong_notes(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET wrong_notes='아직 기록된 오답 내용이 없습니다.' WHERE username=?", (username,))
    conn.commit()
    conn.close()

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    extracted_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text + "\n"
    return extracted_text

init_db()

# ---------------------------------------------------------
# 3. 로그인 / 회원가입 화면 UI
# ---------------------------------------------------------
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if st.session_state.logged_in_user is None:
    st.set_page_config(page_title="형이야", page_icon="🧌", layout="centered")
    st.title("👌저메추 해주세요")
    st.subheader("전과목 질문 가능")
    
    menu = ["로그인", "회원가입"]
    choice = st.tabs(menu)
    
    with choice[0]:
        username = st.text_input("이메일 아이디", key="login_user")
        password = st.text_input("비밀번호", type="password", key="login_pass")
        if st.button("로그인하기"):
            user = login_user(username, password)
            if user:
                st.session_state.logged_in_user = username
                st.success(f"👋 {username}님 환영합니다! 형이랑 공부하자.")
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")
        
        st.markdown("---")
        st.info("🛠️ 관리자 전용: 버튼 한 번으로 마스터(프리미엄) 계정에 즉시 접속합니다.")
        if st.button("👑 마스터 계정으로 바로 시작 (로그인 저장)"):
            st.session_state.logged_in_user = "master"
            st.rerun()
                
    with choice[1]:
        new_user = st.text_input("사용할 이메일 아이디", key="reg_user")
        new_password = st.text_input("비밀번호 설정", type="password", key="reg_pass")
        if st.button("가입하고 무료 체험하기"):
            if new_user and new_password:
                if register_user(new_user, new_password):
                    st.success("🎉 회원가입 성공! 로그인 탭에서 로그인해 주세요.")
                else:
                    st.error("⚠️ 이미 존재하는 아이디입니다.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해 주세요.")
    st.stop()

# ---------------------------------------------------------
# 4. 로그인 성공 후 메인 앱 화면
# ---------------------------------------------------------
current_user = st.session_state.logged_in_user
user_tier, user_usage, past_notes = get_user_data(current_user)

st.set_page_config(page_title="참 다행이야", page_icon="🧌", layout="centered")
st.title("📚 sPapa")

# ---------------------------------------------------------
# 5. 사이드바 - 유저 정보, 등급 제한, 오답노트
# ---------------------------------------------------------
with st.sidebar:
    st.write(f"👤 **접속 계정:** {current_user}")
    
    if user_tier == "free":
        st.error(f"⚠️ 등급: 무료 회원 ({user_usage}/3회 사용)")
        st.markdown("---")
        st.info("🔥 **[첫 달 4,900원 한정 이벤트!]**\n지금 프리미엄으로 업그레이드하고 **질문 무제한 + 교재 업로드 + 평생 오답노트**를 잠금해제 하세요!")
        st.link_button("💳 첫 달 4,900원에 결제하기", "https://your-stripe-checkout-url-here.com")
        st.markdown("---")
    else:
        st.success("👑 등급: 프리미엄 회원 (무제한)")
        st.markdown("---")
        
    st.header("📄 교재 파일 업로드")
    if user_tier == "free":
        st.warning("🔒 PDF 업로드는 프리미엄 회원만 가능합니다.")
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader("PDF 형식의 문제집을 업로드하세요.", type=["pdf"])
        if uploaded_file is not None:
            if "uploaded_filename" not in st.session_state or st.session_state.uploaded_filename != uploaded_file.name:
                with st.spinner("형이 PDF 교재 분석하는 중..."):
                    pdf_text = extract_text_from_pdf(uploaded_file)
                    st.session_state.messages.append({"role": "system", "content": f"[시스템: 유저가 PDF 업로드함]\n{pdf_text}"})
                    st.session_state.uploaded_filename = uploaded_file.name
                st.success("✅ 교재 분석 완료! 질문해봐.")

    st.markdown("---")
    st.header("📝 나의 오답 기록")
    st.text_area("영구 저장된 취약 유형", past_notes, height=150, disabled=True)
    if st.button("🗑️ 오답 기록 초기화"):
        clear_user_wrong_notes(current_user)
        st.success("오답노트가 비워졌어!")
        st.rerun()
        
    if st.button("로그아웃"):
        st.session_state.logged_in_user = None
        st.rerun()

# ---------------------------------------------------------
# 6. 메인 대화창 및 비즈니스 로직 적용
# ---------------------------------------------------------
if "messages" not in st.session_state:
    # 💡 잃어버렸던 디테일 프롬프트 완벽 복구
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
       - 국어/영어: 지문의 핵심 맥락, 주제, 또는 문법적 포인트가 무엇인지 파악하도록 유도합니다. 또한 국어부분에서 시 혹은 고전 시가의 해석 또한 알려줍니다.
       - 사회/역사: 해당 사건이나 개념의 배경지식을 가볍게 설명해 줍니다.
       
    2. 단계별 접근 및 힌트 제공:
       - 한 번에 풀이를 다 보여주지 말고, "1단계로 무엇부터 생각해보면 좋을까?"라며 풀이나 분석의 '첫 단추'를 끼울 수 있는 방향과 힌트만 제시합니다.
       
    3. 복잡한 내용 단순화:
       - 복잡한 지문이나 조건, 긴 공식이 얽혀 있다면 이해하기 쉽게 핵심 케이스나 요약 단계를 나누어 생각할 수 있도록 브레이크다운(쪼개기) 해줍니다.
       
    4. 자기주도적 질문으로 마무리:
       - 항상 "이 힌트를 바탕으로 직접 해보면 어떨까?", "방금 말한 단어를 지문에서 찾아볼 수 있겠니?" 등 학생이 직접 행동하고 생각하게 만드는 유도 질문으로 답변을 끝마치세요.
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if user_input := st.chat_input("눈치보지 말고 공부하다 막힌 내용을 질문해 봐!"):
    if user_tier == "free" and user_usage >= 3:
        st.error("🚨 무료 체험 질문 3회를 모두 사용하셨습니다! 계속 공부하려면 프리미엄 등급으로 업그레이드해 주세요.")
    else:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        if user_tier == "free":
            update_user_usage(current_user)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                # 모델 gpt-5.4-mini 적용 완료
                response = client.chat.completions.create(
                    model="gpt-5.4-mini", 
                    messages=st.session_state.messages,
                    temperature=0.6
                )
                bot_reply = response.choices[0].message.content
                message_placeholder.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
                # 오답노트 요약용 모델도 gpt-5.4-mini 적용 완료
                summary_prompt = [
                    {"role": "system", "content": "학생과 튜터 형의 대화를 보고 학생이 해맨 취약 유형을 [과목] 유형 - 내용 형태로 딱 한 줄 요약해줘. 없으면 '없음'이라고 해."},
                    {"role": "user", "content": f"질문: {user_input}\n답변: {bot_reply}"}
                ]
                summary_res = client.chat.completions.create(
                    model="gpt-5.4-mini", 
                    messages=summary_prompt, 
                    temperature=0.3
                )
                analysis = summary_res.choices[0].message.content.strip()
                
                if analysis and "없음" not in analysis:
                    save_user_wrong_note(current_user, analysis)
                    
            except Exception as e:
                st.error(f"🚨 오류 발생: {e}")
