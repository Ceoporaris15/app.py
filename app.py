import streamlit as st
import time
import random
import base64

# --- 1. システム・デザイン設定 ---
st.set_page_config(page_title="DEUS: ONLINE CUSTOM", layout="centered")

# CSSによる視覚補正：ボタンの白飛びを防止し、黄金の文字を維持
st.markdown("""
    <style>
    /* 全体背景 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #000000 !important; 
        color: #d4af37 !important; 
    }
    
    /* バナー */
    .vs-banner { background-color: #00051a; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin-top: -50px; margin-bottom: 20px; }
    .vs-text { color: #d4af37; font-weight: bold; font-size: 1.2rem; text-shadow: 0 0 10px #d4af37; }
    
    /* ステータスカード */
    .stat-card { background: #111111; border: 1px solid #333333; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .active-p { border: 2px solid #d4af37 !important; box-shadow: 0 0 20px #d4af3744; }
    
    /* ゲージ */
    .hp-bar-bg { background: #222; width: 100%; height: 12px; border-radius: 6px; margin: 5px 0; border: 1px solid #444; overflow: hidden; }
    .p1-bar { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; transition: 0.5s; }
    .p2-bar { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; transition: 0.5s; }
    .nuke-bar { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; transition: 0.5s; }
    
    /* 重要：ボタンの視認性改善（白飛び防止） */
    div.stButton > button {
        background-color: #1a1a1a !important;
        color: #d4af37 !important;
        border: 2px solid #d4af37 !important;
        border-radius: 5px !important;
        height: 55px !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        box-shadow: none !important;
        text-transform: uppercase;
    }
    div.stButton > button:hover {
        background-color: #d4af37 !important;
        color: #000000 !important;
    }
    
    /* サイドバーとチャット */
    section[data-testid="stSidebar"] { background-color: #0a0a0a !important; border-right: 1px solid #333; }
    .chat-box { background: #050505; border: 1px solid #222; height: 100px; overflow-y: scroll; padding: 10px; font-size: 0.85rem; color: #00ff00; font-family: 'Courier New', monospace; }
    </style>
""", unsafe_allow_html=True)

# --- 2. データベース管理 ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "settings": {"max_hp": 500, "turn_sec": 30},
        "p1": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "p2": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "turn_owner": "p1", "turn_start_time": time.time(), "ap": 2,
        "chat": ["SYSTEM: 通信確立。画面をクリックして音響を同期。"]
    }

db = st.session_state.db

# --- 3. BGM & SE 再生エンジン ---
def setup_audio():
    # BGM再生用（Vidnoz_AIMusic.mp3を想定）
    try:
        with open('Vidnoz_AIMusic.mp3', 'rb') as f:
            data = base64.b64encode(f.read()).decode()
            st.components.v1.html(f"""
                <audio id="bgm" loop src="data:audio/mp3;base64,{data}"></audio>
                <script>
                const bgm = document.getElementById('bgm');
                window.parent.document.addEventListener('mousedown', () => {{
                    bgm.play().catch(e => console.log('Audio wait...'));
                }}, {{once: true}});
                </script>
            """, height=0)
    except: pass

def play_se(freq):
    st.components.v1.html(f"""
        <script>
        (function() {{
            const c = new (window.AudioContext || window.webkitAudioContext)();
            const o = c.createOscillator();
            const g = c.createGain();
            o.frequency.setValueAtTime({freq}, c.currentTime);
            g.gain.setValueAtTime(0.1, c.currentTime);
            g.gain.exponentialRampToValueAtTime(0.01, c.currentTime + 0.3);
            o.connect(g); g.connect(c.destination);
            o.start(); o.stop(c.currentTime + 0.3);
        }})();
        </script>
    """, height=0)

setup_audio()

# --- 4. サイドバー設定 ---
st.sidebar.title("DEUS CONTROL")
my_role = st.sidebar.radio("端末登録:", ["観戦中", "p1", "p2"])

if my_role != "観戦中" and db[my_role]["faction"] is None:
    fac = st.sidebar.selectbox("陣営選択", ["連合国", "枢軸國", "社会主義国"])
    if st.sidebar.button("陣営確定"):
        db[my_role]["faction"] = fac
        if fac == "社会主義国": db["ap"] = 3
        db["chat"].append(f"LOG: {my_role.upper()} ({fac}) が着任。")
        st.rerun()

# --- 5. ゲームロジック（全AI機能） ---
def get_stats(actor):
    f = db[actor]["faction"]
    if f == "連合国": return 1.0, 1.0, 1.0, 2.0
    if f == "枢軸國": return 1.5, 0.8, 1.2, 1.0
    if f == "社会主義国": return 0.8, 1.2, 1.0, 1.0
    return 1.0, 1.0, 1.0, 1.0

def handle_action(cmd, actor):
    target = "p2" if actor == "p1" else "p1"
    a, d, o, n = get_stats(actor)
    _, td, _, _ = get_stats(target)
    
    if cmd == "EXP":
        db[actor]["military"] += 20 * a; db[actor]["nuke"] += 25 * n
        db["chat"].append(f"CMD: {actor.upper()}軍備増強")
    elif cmd == "DEF":
        db[actor]["shield"] = True
        db["chat"].append(f"CMD: {actor.upper()}防衛網構築")
    elif cmd == "MAR":
        dmg = (db[actor]["military"] * 0.5 + 20) * a * (1/td)
        if db[target]["shield"]: dmg *= 0.5
        if db[target]["colony"] > 0: db[target]["colony"] = max(0, db[target]["colony"] - dmg)
        else: db[target]["hp"] -= dmg
        db["chat"].append(f"CMD: {actor.upper()}進撃（{dmg:.0f}損害）")
    elif cmd == "OCC":
        steal = (30 + db[target]["hp"] * 0.1) * o
        db[actor]["colony"] += steal
        db["chat"].append(f"CMD: {actor.upper()}占領成功")
    elif cmd == "SPY":
        if random.random() < (0.6 if db[actor]["faction"]=="連合国" else 0.3):
            db[target]["nuke"] = max(0, db[target]["nuke"] - 60)
            db["chat"].append(f"LOG: {actor.upper()}のスパイが核工作に成功")
        else: db["chat"].append(f"LOG: {actor.upper()}のスパイが捕縛された")
    elif cmd == "NUK":
        db[target]["hp"] *= 0.15; db[actor]["nuke"] = 0
        db["chat"].append(f"CRITICAL: {actor.upper()}が核兵器を使用")

    play_se(400)
    db["ap"] -= 1
    if db["ap"] <= 0:
        db[actor]["shield"] = False
        db["turn_owner"] = target
        db["ap"] = 3 if db[target]["faction"] == "社会主義国" else 2
        db["turn_start_time"] = time.time()
    st.rerun()

# --- 6. メインUI ---
st.markdown('<div class="vs-banner"><span class="vs-text">DEUS: FULL COMMAND CONNECTED</span></div>', unsafe_allow_html=True)

# ステータス表示
c1, c2 = st.columns(2)
for i, p_key in enumerate(["p1", "p2"]):
    p = db[p_key]
    with [c1, c2][i]:
        active = "active-p" if db["turn_owner"] == p_key else ""
        st.markdown(f"""
            <div class="stat-card {active}">
                <b style='font-size:1.1rem;'>{p_key.upper()} ({p['faction'] or 'Waiting...'})</b><br>
                本土領土: {p['hp']:.0f}
                <div class="hp-bar-bg"><div class="{'p1-bar' if i==0 else 'p2-bar'}" style="width:{p['hp']/db['settings']['max_hp']*100}%"></div></div>
                核開発: {p['nuke']:.0f}/200
                <div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(p['nuke']/2, 100)}%"></div></div>
            </div>
        """, unsafe_allow_html=True)

# ターン管理
elapsed = time.time() - db["turn_start_time"]
time_left = max(0, db["settings"]["turn_sec"] - int(elapsed))
st.markdown(f"### ターン：<span style='color:#d4af37'>{db['turn_owner'].upper()}</span> (残り {time_left}秒 / AP: {db['ap']})", unsafe_allow_html=True)

# アクションコマンド
if my_role == db["turn_owner"]:
    if db[my_role]["faction"] is None:
        st.warning("サイドバーで陣営を選んでください。")
    else:
        row1 = st.columns(3)
        if row1[0].button("🛠 軍拡"): handle_action("EXP", my_role)
        if row1[1].button("🛡 防衛"): handle_action("DEF", my_role)
        if row1[2].button("🕵️ スパイ"): handle_action("SPY", my_role)
        
        row2 = st.columns(3)
        if row2[0].button("⚔️ 進軍"): handle_action("MAR", my_role)
        if row2[1].button("🚩 占領"): handle_action("OCC", my_role)
        if db[my_role]["nuke"] >= 200:
            if row2[2].button("☢️ 核兵器", type="primary"): handle_action("NUK", my_role)
        else: row2[2].button(f"核開発中", disabled=True)
else:
    st.info("通信待機中... 相手の行動を待っています。")
    if st.button("🔄 同期・画面更新"): st.rerun()

# チャット・ログ
st.markdown(f'<div class="chat-box">{"".join([f"<div>{m}</div>" for m in db["chat"][-5:]])}</div>', unsafe_allow_html=True)
msg = st.text_input("通信送信:", key="chat_input")
if st.button("送信"):
    if msg: db["chat"].append(f"{my_role.upper()}: {msg}"); st.rerun()
