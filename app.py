import streamlit as st
import time
import random
import base64

# --- 1. システム・デザイン設定 ---
st.set_page_config(page_title="DEUS: ONLINE TERMINAL", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #000000 !important; color: #d4af37 !important; 
    }
    .main-title { font-size: 3.5rem; text-align: center; font-weight: bold; text-shadow: 0 0 20px #d4af37; margin-bottom: 10px; }
    .lobby-card { background: #111; border: 2px solid #333; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .stat-card { background: #111; border: 1px solid #333; padding: 15px; border-radius: 8px; }
    .active-p { border: 2px solid #d4af37 !important; box-shadow: 0 0 15px #d4af3744; }
    .hp-bar-bg { background: #222; width: 100%; height: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #444; overflow: hidden; }
    .p1-bar { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .p2-bar { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    
    div.stButton > button {
        background-color: #1a1a1a !important; color: #d4af37 !important;
        border: 2px solid #d4af37 !important; height: 50px !important; width: 100% !important;
        font-weight: bold !important; font-size: 1rem !important;
    }
    div.stButton > button:hover { background-color: #d4af37 !important; color: #000 !important; }
    .chat-box { background: #050505; border: 1px solid #222; height: 80px; overflow-y: scroll; padding: 8px; font-size: 0.8rem; color: #0F0; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- 2. BGMエンジン ---
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

def play_se(freq):
    st.components.v1.html(f"<script>const c=new AudioContext();const o=c.createOscillator();const g=c.createGain();o.frequency.value={freq};g.gain.setValueAtTime(0.1,c.currentTime);o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+0.2);</script>", height=0)

# --- 3. セッション管理 ---
if 'page' not in st.session_state:
    st.session_state.page = "HOME"

# 共有データベースの初期化
if 'db' not in st.session_state:
    st.session_state.db = {
        "room_id": None,
        "settings": {"max_hp": 500, "turn_sec": 30},
        "p1": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "p2": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "turn_owner": "p1", "turn_start_time": time.time(), "ap": 2,
        "chat": ["SYSTEM: 戦域接続待機中..."]
    }

db = st.session_state.db
setup_bgm()

# --- 4. ページ遷移ロジック ---

# [HOME]
if st.session_state.page == "HOME":
    st.markdown('<div class="main-title">DEUS: ONLINE</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="lobby-card"><h3>公開マッチ</h3><p>新しい戦場を作成します</p></div>', unsafe_allow_html=True)
        if st.button("新規作成"):
            st.session_state.page = "CONFIG"
            st.rerun()
    with col2:
        st.markdown('<div class="lobby-card"><h3>参戦</h3><p>コードを入力して合流</p></div>', unsafe_allow_html=True)
        code = st.text_input("ROOM CODE", placeholder="例: 1234")
        if st.button("戦域へ急行"):
            db["room_id"] = code
            st.session_state.page = "GAME"
            st.rerun()

# [CONFIG]
elif st.session_state.page == "CONFIG":
    st.markdown('<div class="main-title">SETTING</div>', unsafe_allow_html=True)
    with st.container():
        hp = st.number_input("初期本土領土 (100-2000)", 100, 2000, 500)
        sec = st.number_input("制限時間 (5-120秒)", 5, 120, 30)
        code = str(random.randint(1000, 9999))
        st.info(f"この戦域のコード: {code} (相手に伝えてください)")
        
        if st.button("戦域を確立する"):
            db["room_id"] = code
            db["settings"]["max_hp"] = hp
            db["settings"]["turn_sec"] = sec
            db["p1"]["hp"] = db["p2"]["hp"] = hp
            st.session_state.page = "GAME"
            st.rerun()

# [GAME]
elif st.session_state.page == "GAME":
    # 陣営選択チェック
    my_role = st.sidebar.radio("あなたのデバイス:", ["観戦中", "p1", "p2"])
    
    if my_role != "観戦中" and db[my_role]["faction"] is None:
        st.markdown('<div class="main-title">FACTION SELECT</div>', unsafe_allow_html=True)
        fac = st.selectbox("陣営を選択してください", ["連合国", "枢軸國", "社会主義国"])
        if st.button("この陣営で戦う"):
            db[my_role]["faction"] = fac
            if fac == "社会主義国": db["ap"] = 3
            db["chat"].append(f"LOG: {my_role.upper()}が{fac}として着任。")
            st.rerun()
    else:
        # メイン対戦画面
        st.markdown(f'<div class="vs-banner"><span class="vs-text">ROOM: {db["room_id"]}</span></div>', unsafe_allow_html=True)
        
        # ステータス表示
        c1, c2 = st.columns(2)
        for i, p_key in enumerate(["p1", "p2"]):
            p = db[p_key]
            with [c1, c2][i]:
                active = "active-p" if db["turn_owner"] == p_key else ""
                st.markdown(f"""
                    <div class="stat-card {active}">
                        <b>{p_key.upper()} ({p['faction'] or 'Wait...'})</b><br>
                        本土: {p['hp']:.0f}<div class="hp-bar-bg"><div class="{'p1-bar' if i==0 else 'p2-bar'}" style="width:{p['hp']/db['settings']['max_hp']*100}%"></div></div>
                        核: {p['nuke']:.0f}/200<div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(p['nuke']/2, 100)}%"></div></div>
                    </div>
                """, unsafe_allow_html=True)

        # ターン管理
        elapsed = time.time() - db["turn_start_time"]
        time_left = max(0, db["settings"]["turn_sec"] - int(elapsed))
        st.write(f"### ターン：{db['turn_owner'].upper()} (残り {time_left}s / AP:{db['ap']})")

        if time_left == 0 and my_role != "観戦中":
            db["turn_owner"] = "p2" if db["turn_owner"] == "p1" else "p1"
            db["ap"] = 2; db["turn_start_time"] = time.time(); st.rerun()

        # アクション
        if my_role == db["turn_owner"]:
            col_a, col_b, col_c = st.columns(3)
            if col_a.button("🛠軍拡"): 
                db[my_role]["military"] += 20; db[my_role]["nuke"] += 25
                db["ap"] -= 1; play_se(400); st.rerun()
            if col_b.button("🛡防衛"):
                db[my_role]["shield"] = True
                db["ap"] -= 1; play_se(300); st.rerun()
            if col_c.button("🕵️スパイ"):
                if random.random() < 0.4: db["p2" if my_role=="p1" else "p1"]["nuke"] -= 50
                db["ap"] -= 1; play_se(500); st.rerun()
            
            col_d, col_e, col_f = st.columns(3)
            if col_d.button("⚔️進軍"):
                target = "p2" if my_role == "p1" else "p1"
                dmg = db[my_role]["military"] * 0.5 + 20
                if db[target]["shield"]: dmg *= 0.5
                db[target]["hp"] -= dmg
                db["ap"] -= 1; play_se(600); st.rerun()
            if col_e.button("🚩占領"):
                db[my_role]["colony"] += 40
                db["ap"] -= 1; play_se(350); st.rerun()
            if col_f.button("☢️核兵器", disabled=db[my_role]["nuke"]<200):
                db["p2" if my_role=="p1" else "p1"]["hp"] *= 0.2
                db[my_role]["nuke"] = 0; db["ap"] -= 1; play_se(200); st.rerun()
            
            if db["ap"] <= 0:
                db[my_role]["shield"] = False
                db["turn_owner"] = "p2" if my_role == "p1" else "p1"
                db["ap"] = 2; db["turn_start_time"] = time.time(); st.rerun()
        else:
            st.info("通信待機中...")
            if st.button("🔄 同期"): st.rerun()

        # チャット
        st.markdown(f'<div class="chat-box">{"".join([f"<div>{m}</div>" for m in db["chat"][-3:]])}</div>', unsafe_allow_html=True)
        msg = st.text_input("通信:", key="chat_input")
        if st.button("送信"):
            if msg: db["chat"].append(f"{my_role.upper()}: {msg}"); st.rerun()

        if st.sidebar.button("タイトルへ戻る"):
            st.session_state.page = "HOME"
            st.rerun()
