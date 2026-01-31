import streamlit as st
import time
import random
import base64

# --- 1. システム・デザイン設定 ---
st.set_page_config(page_title="DEUS: FULL ONLINE", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #FFF; }
    /* ヘッダー */
    .vs-banner { background-color: #001; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin-top: -50px; }
    .vs-text { color: #d4af37; font-weight: bold; font-size: 1.2rem; }
    
    /* ステータスカード */
    .stat-card { background: #111; border: 1px solid #333; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
    .active-p { border: 2px solid #d4af37 !important; box-shadow: 0 0 15px #d4af3766; }
    
    /* ゲージ */
    .hp-bar-bg { background: #222; width: 100%; height: 10px; border-radius: 5px; margin: 4px 0; border: 1px solid #444; }
    .p1-bar { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; transition: 0.5s; }
    .p2-bar { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; transition: 0.5s; }
    .nuke-bar { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; transition: 0.5s; }
    
    /* 操作ボタンを強調 */
    div[data-testid="column"] button { 
        height: 50px !important; 
        background: #111 !important; 
        color: #d4af37 !important; 
        border: 2px solid #d4af37 !important; 
        font-weight: bold !important;
        font-size: 1rem !important;
        width: 100% !important;
    }
    div[data-testid="column"] button:hover { background: #d4af37 !important; color: #000 !important; }
    
    /* チャットエリア */
    .chat-box { background: #050505; border: 1px solid #222; height: 80px; overflow-y: scroll; padding: 8px; font-size: 0.8rem; color: #0F0; font-family: monospace; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 共有データベース管理 ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "settings": {"max_hp": 500, "turn_sec": 30},
        "p1": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "p2": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "turn_owner": "p1", "turn_start_time": time.time(), "ap": 2,
        "chat": ["システム：戦域プロトコル開始。"]
    }

db = st.session_state.db

# --- 3. 音響エンジン ---
def play_se(freq):
    st.components.v1.html(f"<script>const c=new (window.AudioContext||window.webkitAudioContext)();const o=c.createOscillator();const g=c.createGain();o.frequency.value={freq};g.gain.setValueAtTime(0.1,c.currentTime);o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+0.2);</script>", height=0)

# --- 4. サイドバー (設定・登録) ---
st.sidebar.title("🛠 DEUS MENU")
my_role = st.sidebar.radio("あなたの操作端末:", ["観戦中", "p1", "p2"])

if my_role != "観戦中" and db[my_role]["faction"] is None:
    st.sidebar.subheader("陣営選択")
    fac = st.sidebar.selectbox("陣営を選択", ["連合国", "枢軸國", "社会主義国"])
    if st.sidebar.button("陣営確定"):
        db[my_role]["faction"] = fac
        if fac == "社会主義国": db["ap"] = 3
        db["chat"].append(f"LOG: {my_role.upper()}が{fac}として参戦。")
        st.rerun()

if st.sidebar.button("全データリセット"):
    st.session_state.clear()
    st.rerun()

# --- 5. ゲームロジック ---
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
        db["chat"].append(f"COMMAND: {actor.upper()}軍拡完了")
    elif cmd == "DEF":
        db[actor]["shield"] = True
        db["chat"].append(f"COMMAND: {actor.upper()}防衛体制")
    elif cmd == "MAR":
        dmg = (db[actor]["military"] * 0.5 + 20) * a * (1/td)
        if db[target]["shield"]: dmg *= 0.5
        if db[target]["colony"] > 0:
            db[target]["colony"] = max(0, db[target]["colony"] - dmg)
        else:
            db[target]["hp"] -= dmg
        db["chat"].append(f"COMMAND: {actor.upper()}進軍({dmg:.0f}損害)")
    elif cmd == "OCC":
        steal = (30 + db[target]["hp"] * 0.1) * o
        db[actor]["colony"] += steal
        db["chat"].append(f"COMMAND: {actor.upper()}占領拡大")
    elif cmd == "SPY":
        if random.random() < (0.6 if db[actor]["faction"]=="連合国" else 0.3):
            db[target]["nuke"] = max(0, db[target]["nuke"] - 60)
            db["chat"].append(f"LOG: {actor.upper()}のスパイが成功")
        else:
            db["chat"].append(f"LOG: {actor.upper()}のスパイが失敗")
    elif cmd == "NUK":
        db[target]["hp"] *= 0.15; db[actor]["nuke"] = 0
        db["chat"].append(f"ALARM: {actor.upper()}の核が炸裂")

    play_se(400)
    db["ap"] -= 1
    if db["ap"] <= 0:
        db[actor]["shield"] = False
        db["turn_owner"] = target
        db["ap"] = 3 if db[target]["faction"] == "社会主義国" else 2
        db["turn_start_time"] = time.time()
    st.rerun()

# --- 6. メインUI ---
st.markdown('<div class="vs-banner"><span class="vs-text">DEUS: FULL COMMAND INTERFACE</span></div>', unsafe_allow_html=True)

# ステータス表示
c1, c2 = st.columns(2)
for i, p_key in enumerate(["p1", "p2"]):
    p = db[p_key]
    with [c1, c2][i]:
        active = "active-p" if db["turn_owner"] == p_key else ""
        st.markdown(f"""
            <div class="stat-card {active}">
                <b>{p_key.upper()} ({p['faction'] or 'Wait...'})</b><br>
                領土: {p['hp']:.0f}<div class="hp-bar-bg"><div class="{'p1-bar' if i==0 else 'p2-bar'}" style="width:{p['hp']/db['settings']['max_hp']*100}%"></div></div>
                核: {p['nuke']:.0f}/200<div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(p['nuke']/2, 100)}%"></div></div>
            </div>
        """, unsafe_allow_html=True)

# ターン情報
elapsed = time.time() - db["turn_start_time"]
time_left = max(0, db["settings"]["turn_sec"] - int(elapsed))
st.subheader(f"ターン：{db['turn_owner'].upper()} (残り {time_left}秒 / 行動回数:{db['ap']})")

# --- アクションコマンド（最優先表示エリア） ---
if my_role == db["turn_owner"]:
    if db[my_role]["faction"] is None:
        st.warning("サイドバーで陣営を選んでください。")
    else:
        # ボタンを大きく、押しやすく配置
        row1 = st.columns(3)
        if row1[0].button("🛠 軍拡"): handle_action("EXP", my_role)
        if row1[1].button("🛡 防衛"): handle_action("DEF", my_role)
        if row1[2].button("🕵️ スパイ"): handle_action("SPY", my_role)
        
        row2 = st.columns(3)
        if row2[0].button("⚔️ 進軍"): handle_action("MAR", my_role)
        if row2[1].button("🚩 占領"): handle_action("OCC", my_role)
        
        # 核兵器ボタン
        if db[my_role]["nuke"] >= 200:
            if row2[2].button("☢️ 核兵器", type="primary"): handle_action("NUK", my_role)
        else:
            row2[2].button(f"核({db[my_role]['nuke']:.0f})", disabled=True)
else:
    st.info("通信待機中... 相手の行動が終わるまでお待ちください。")
    if st.button("🔄 同期・最新化"): st.rerun()

# チャット・ログ（画面下部）
st.markdown(f'<div class="chat-box">{"".join([f"<div>{m}</div>" for m in db["chat"][-5:]])}</div>', unsafe_allow_html=True)
msg = st.text_input("通信送信:", key="chat_input")
if st.button("送信"):
    if msg: db["chat"].append(f"{my_role.upper()}: {msg}"); st.rerun()
