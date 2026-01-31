import streamlit as st
import time
import random
import base64
import uuid

# --- 1. デザイン・CSS設定 ---
st.set_page_config(page_title="DEUS: ONLINE LOBBY", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #d4af37; }
    .main-title { font-size: 3rem; text-align: center; font-weight: bold; text-shadow: 0 0 20px #d4af37; margin-bottom: 30px; }
    .lobby-card { background: #111; border: 2px solid #333; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    div.stButton > button {
        background-color: #1a1a1a !important; color: #d4af37 !important;
        border: 2px solid #d4af37 !important; height: 60px !important; width: 100% !important;
        font-weight: bold !important; font-size: 1.2rem !important;
    }
    div.stButton > button:hover { background-color: #d4af37 !important; color: #000 !important; }
    .status-msg { font-family: monospace; color: #00ff00; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 2. BGM設定 ---
def setup_bgm():
    try:
        with open('Vidnoz_AIMusic.mp3', 'rb') as f:
            data = base64.b64encode(f.read()).decode()
            st.components.v1.html(f"""
                <audio id="bgm" loop src="data:audio/mp3;base64,{data}"></audio>
                <script>
                const a = document.getElementById('bgm');
                window.parent.document.addEventListener('mousedown', () => a.play(), {{once: true}});
                </script>
            """, height=0)
    except: pass

setup_bgm()

# --- 3. セッション管理 ---
if 'page' not in st.session_state:
    st.session_state.page = "HOME"
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# --- 4. ホーム画面 ---
if st.session_state.page == "HOME":
    st.markdown('<div class="main-title">DEUS: ONLINE</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="lobby-card"><h3>公開マッチ</h3><p>誰でも参加可能な戦域を探します</p></div>', unsafe_allow_html=True)
        if st.button("クイックマッチ開始"):
            st.session_state.room_id = "PUBLIC_" + str(random.randint(100, 999))
            st.session_state.page = "CONFIG"
            st.rerun()

    with col2:
        st.markdown('<div class="lobby-card"><h3>フレンドマッチ</h3><p>コードを入力して合流します</p></div>', unsafe_allow_html=True)
        code = st.text_input("ルームコードを入力", placeholder="例: XJ77")
        if st.button("コードで参戦"):
            if code:
                st.session_state.room_id = code
                st.session_state.page = "GAME" # 友人の部屋へ直接入る
                st.rerun()

# --- 5. 設定画面（ホスト用） ---
elif st.session_state.page == "CONFIG":
    st.markdown(f'<div class="main-title">ROOM: {st.session_state.room_id}</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="lobby-card">', unsafe_allow_html=True)
    st.subheader("戦域パラメータ設定")
    hp = st.slider("初期本土領土", 100, 2000, 500)
    sec = st.slider("1ターンの制限時間(秒)", 5, 120, 30)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("この設定で戦域を生成"):
        # 本来ここでFirestoreに初期データを書き込む
        st.session_state.max_hp = hp
        st.session_state.turn_sec = sec
        st.session_state.page = "GAME"
        st.rerun()
    
    if st.button("キャンセル"):
        st.session_state.page = "HOME"
        st.rerun()

# --- 6. ゲーム画面（以前の全機能統合版） ---
elif st.session_state.page == "GAME":
    # ここに「全機能版」のコードを結合します
    st.markdown(f"### ROOM: {st.session_state.room_id} / 領土: {st.session_state.get('max_hp', 500)}")
    st.info("対戦相手の入室を待機中...（URLを相手に共有してください）")
    
    # 以前作成した対戦用コードの「ロジック部分」がここに繋がります
    if st.button("タイトルへ戻る"):
        st.session_state.page = "HOME"
        st.rerun()
