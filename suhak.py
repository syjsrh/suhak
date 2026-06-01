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

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, tier TEXT, usage_count INTEGER, wrong_notes TEXT)''')
    
    # 💡 [보안 수정] 사장님 비밀 계정 자동 생성 (아이디: syjsrh / 비밀번호: 20260411)
    c.execute("SELECT * FROM users WHERE username='syjsrh'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, 'paid', 0, '아직 기록된 오답 내용이 없습니다.')", 
                  ('syjsrh', make_hash('20260411')))
        
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

def upgrade_user_to_paid(username):
    """(관리자용) 유저를 프리미엄으로 승급시키는 함수"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET tier='paid' WHERE username=?", (username,))
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
# UI 및 비즈니스 로직
# ---------------------------------------------------------
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if st.session_state.logged_in_user is None:
    st.set_page_config(page_title="공부하자", page_icon="🎓", layout="centered")
    st.title("🎓기말 파이팅")
    st.subheader("형이야")
    
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
current_user = st.session_state.logged_in_user
user_tier, user_usage, past_notes = get_user_data(current_user)

st.set_page_config(page_title="파이팅", page_icon="🎓", layout="centered")
st.title("📚 🧌🧌❤️❤️❤️❤️")

with st.sidebar:
    st.write(f"👤 **접속 계정:** {current_user}")
    
    if user_tier == "free":
        st.error(f"⚠️ 등급: 무료 회원 ({user_usage}/3회 사용)")
        st.markdown("---")
        st.info("🔥 **[첫 달 4,900원 이벤트!]**\n아래 버튼으로 송금 후, 카톡으로 가입하신 아이디를 알려주시면 즉시 뚫어드려요!")
        
        # 💡 사장님의 토스 링크와 카카오톡 오픈채팅 링크로 수정하세요!
        st.link_button("💸 토스로 4,900원 입금하기", "https://toss.me/여기에_사장님_토스아이디_입력")
        st.link_button("💬 입금 후 고객센터로 아이디 보내기", "https://open.kakao.com/o/여기에_오픈채팅_주소_입력")
        st.markdown("---")
    else:
        st.success("👑 등급: 프리미엄 회원 (무제한)")
        st.markdown("---")
        
    # 💡 [핵심] 사장님 전용 유저 승급 기능 (syjsrh 계정일 때만 보임)
    if current_user == "syjsrh":
        st.header("🛠️ 사장님 전용 관리자 메뉴")
        target_id = st.text_input("입금 확인된 유저 아이디 입력")
        if st.button("✨ 프리미엄으로 승급시키기"):
            if target_id:
                upgrade_user_to_paid(target_id)
                st.success(f"[{target_id}]님을 프리미엄으로 올렸습니다!")
            else:
                st.warning("아이디를 입력하세요.")
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
if "messages" not in st.session_state:
    system_prompt = f"""
    당신은 학생들이 모든 과목(수학, 과학, 영어, 국어, 사회 등)의 어려운 내용을 스스로 이해하고 해결할 수 있도록 돕는 친절하고 친근하며 마치 형 같은 논리적인 만능 전과목 공부 튜터입니다.
    
    학생의 영구 저장소에서 불러온 과거 오답 및 취약점 기록은 다음과 같습니다:
    \"\"\"
    {past_notes}
    \"\"\"
    이 과거 기록을 반드시 인지하고 대화에 임하세요. 대화 도중 과거 유형이 나오면 "야, 너 지난번에 이 유형에서 좀 해맸던 거 기억나지? 그때 형이 말해준 원리 다시 한번 떠올려보자."라고 연관 지어 설명해 주세요.
    
    1. 과목 맞춤형 핵심 짚기: 수학/과학은 공식 리마인드, 국어/영어는 맥락 및 문법, 시/고전시가 해석, 사회/역사는 배경지식 설명.
    2. 단계별 힌트 제공 ("1단계로 무엇부터 생각해보면 좋을까?")
    3. 복잡한 내용 단순화 및 브레이크다운
    4. 학생 스스로 생각하게 만드는 유도 질문으로 마무리
    
    ★ [수식 출력 절대 규칙] ★
    수학 기호나 수식을 작성할 때는 절대로 \( \) 나 \[ \] 기호를 쓰지 마세요. 웹사이트 화면이 깨집니다.
    대신 반드시 달러 기호($)를 사용하세요. 
    - 글자 사이에 들어가는 짧은 수식: $수식$ 기호로 감싸세요. (예: $\alpha < x < \beta$)
    - 줄을 바꿔서 크게 보여주는 수식: $$수식$$ 기호로 감싸세요. (예: $$x^2 - 11x + 24 < 0$$)
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if user_input := st.chat_input("공부하다 막힌 내용을 질문해 봐!"):
    if user_tier == "free" and user_usage >= 3:
        st.error("🚨 무료 체험 3회를 모두 사용하셨습니다! 계속 공부하려면 왼쪽 사이드바에서 입금 후 프리미엄을 요청해 주세요.")
    else:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        if user_tier == "free":
            update_user_usage(current_user)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                response = client.chat.completions.create(
                    model="gpt-5.4-mini", 
                    messages=st.session_state.messages,
                    temperature=0.6
                )
                bot_reply = response.choices[0].message.content
                message_placeholder.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                
                summary_prompt = [
                    {"role": "system", "content": "학생과 튜터 형의 대화를 보고 학생이 해맨 취약 유형을 [과목] 유형 - 내용 형태로 딱 한 줄 요약해줘. 없으면 '없음'이라고 해."},
                    {"role": "user", "content": f"질문: {user_input}\n답변: {bot_reply}"}
                ]
                summary_res = client.chat.completions.create(model="gpt-5.4-mini", messages=summary_prompt, temperature=0.3)
                analysis = summary_res.choices[0].message.content.strip()
                
                if analysis and "없음" not in analysis:
                    save_user_wrong_note(current_user, analysis)
                    
            except Exception as e:
                st.error(f"🚨 오류 발생: {e}")
