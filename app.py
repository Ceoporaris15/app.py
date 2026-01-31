import streamlit as st
import time
import random
import base64

# --- 1. デザイン設定 ---
st.set_page_config(page_title="DEUS: FULL ONLINE", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #FFF; }
    .vs-banner { background-color: #001; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin-bottom: 20px; }
    .vs-text { color: #d4af37; font-weight: bold; font-size: 1.2rem; text-shadow: 0 0 10px #d4af37; }
    .stat-card { background: #111; border: 1px solid #333; padding: 10px; border-radius: 5px; }
    .active-p { border: 1px solid #d4af37 !important; box-shadow: 0 0 15px #d4af3755; }
    .hp-bar-bg { background: #222; width: 100%; height: 8px; border-radius: 4px; margin: 4px 0; }
    .p1-bar { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; transition: 0.5s; }
    .p2-bar { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; transition: 0.5s; }
    .nuke-bar { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; transition: 0.5s; }
    .chat-box { background: #050505; border: 1px solid #222; height: 100px; overflow-y: scroll; padding: 8px; font-size: 0.75rem; color: #0F0; font-family: monospace; }
    div[data-testid="column"] button { background: #111 !important; color: #d4af37 !important; border: 1px solid #d4af37 !important; font-size: 0.7rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. データベース（共有ステート） ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "settings": {"max_hp": 500, "turn_sec": 30},
        "p1": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "p2": {"hp": 500, "colony": 0, "nuke": 0, "military": 20, "faction": None, "shield": False},
        "turn_owner": "p1", "turn_start_time": time.time(), "ap": 2,
        "chat": ["システム：戦域プロトコル待機中。"]
    }

db = st.session_state.db

# --- 3. 音響エンジン ---
def play_se(freq):
    st.components.v1.html(f"<script>const c=new AudioContext();const o=c.createOscillator();const g=c.createGain();o.frequency.value={freq};g.gain.setValueAtTime(0.1,c.currentTime);o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+0.2);</script>", height=0)

# --- 4. サイドバー：デバイス登録と陣営選択 ---
st.sidebar.title("🛠 DEUS COMMAND")
my_role = st.sidebar.radio("デバイス登録:", ["観戦中", "p1", "p2"])

if my_role != "観戦中":
    if db[my_role]["faction"] is None:
        st.sidebar.subheader(f"{my_role.upper()} 陣営選択")
        fac = st.sidebar.selectbox("陣営を選んでください", ["連合国", "枢軸國", "社会主義国"])
        if st.sidebar.button("陣営を確定"):
            db[my_role]["faction"] = fac
            if fac == "社会主義国": db["ap"] = 3
            db["chat"].append(f"システム：{my_role.upper()}が{fac}を選択。")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("戦域設定（ホスト）")
new_hp = st.sidebar.number_input("初期領土", 100, 2000, 500)
new_sec = st.sidebar.number_input("制限時間(s)", 5, 120, 30)
if st.sidebar.button("戦域リセット"):
    st.session_state.clear()
    st.rerun()

# --- 5. ゲームロジック（AI機能を対人用に移植） ---
def get_stats(actor):
    f = db[actor]["faction"]
    if f == "連合国": return 1.0, 1.0, 1.0, 2.0  # atk, def, occ, nuke_speed
    if f == "枢軸國": return 1.5, 0.8, 1.2, 1.0
    if f == "社会主義国": return 0.8, 1.2, 1.0, 1.0
    return 1.0, 1.0, 1.0, 1.0

def handle_action(cmd, actor):
    target = "p2" if actor == "p1" else "p1"
    a, d, o, n = get_stats(actor)
    _, td, _, _ = get_stats(target)
    
    if cmd == "EXP": # 軍拡
        db[actor]["military"] += 20 * a; db[actor]["nuke"] += 20 * n
        db["chat"].append(f"🛠 {actor.upper()}：軍拡。")
    elif cmd == "DEF": # 防衛
        db[actor]["shield"] = True
        db["chat"].append(f"🛡 {actor.upper()}：シールド展開。")
    elif cmd == "MAR": # 進軍
        dmg = (db[actor]["military"] * 0.5 + 15) * a * (1/td)
        if db[target]["shield"]: dmg *= 0.5
        if db[target]["colony"] > 0:
            db[target]["colony"] = max(0, db[target]["colony"] - dmg)
        else:
            db[target]["hp"] -= dmg
        db["chat"].append(f"⚔️ {actor.upper()}：進軍（{dmg:.0f}損害）。")
    elif cmd == "OCC": # 占領
        steal = (25 + db[target]["hp"] * 0.1) * o
        db[actor]["colony"] += steal
        db["chat"].append(f"🚩 {actor.upper()}：緩衝地帯を{steal:.0f}拡張。")
    elif cmd == "SPY": # スパイ
        if random.random() < (0.6 if db[actor]["faction"]=="連合国" else 0.3):
            db[target]["nuke"] = max(0, db[target]["nuke"] - 50)
            db["chat"].append(f"🕵️ {actor.upper()}：スパイ成功！敵の核開発を阻害。")
        else:
            db["chat"].append(f"🕵️ {actor.upper()}：スパイ失敗。")
    elif cmd == "NUK": # 核
        db[target]["hp"] *= 0.2; db[actor]["nuke"] = 0
        db["chat"].append(f"☢️ {actor.upper()}：最終宣告。世界が震える。")

    play_se(400)
    db["ap"] -= 1
    if db["ap"] <= 0:
        db[actor]["shield"] = False
        db["turn_owner"] = target
        db["ap"] = 3 if db[target]["faction"] == "社会主義国" else 2
        db["turn_start_time"] = time.time()
    st.rerun()

# --- 6. UI ---
st.markdown('<div class="vs-banner"><span class="vs-text">DEUS: ONLINE ADVANCED</span></div>', unsafe_allow_html=True)

# 状況表示
c1, c2 = st.columns(2)
for i, p_key in enumerate(["p1", "p2"]):
    p = db[p_key]
    with [c1, c2][i]:
        active = "active-p" if db["turn_owner"] == p_key else ""
        st.markdown(f"""
            <div class="stat-card {active}">
                <b>{p_key.upper()} [{p['faction'] or '未選択'}]</b><br>
                本土: {p['hp']:.0f}<div class="hp-bar-bg"><div class="{'p1-bar' if i==0 else 'p2-bar'}" style="width:{p['hp']/db['settings']['max_hp']*100}%"></div></div>
                緩衝: {p['colony']:.0f}<div class="hp-bar-bg"><div style="background:#444; width:{min(p['colony']/2, 100)}%; height:100%;"></div></div>
                核: {p['nuke']:.0f}/200<div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(p['nuke']/2, 100)}%"></div></div>
            </div>
        """, unsafe_allow_html=True)

# 制限時間
elapsed = time.time() - db["turn_start_time"]
time_left = max(0, db["settings"]["turn_sec"] - int(elapsed))
st.write(f"### ターン：{db['turn_owner'].upper()} (残り {time_left}s / AP:{db['ap']})")

if time_left == 0 and my_role != "観戦中":
    db["ap"] = 0; handle_action("PASS", db["turn_owner"])

# アクション
if my_role == db["turn_owner"]:
    if db[my_role]["faction"] is None:
        st.warning("サイドバーで陣営を選択してください。")
    else:
        col1, col2, col3 = st.columns(3)
        if col1.button("🛠軍拡"): handle_action("EXP", my_role)
        if col2.button("🛡防衛"): handle_action("DEF", my_role)
        if col3.button("🕵️スパイ"): handle_action("SPY", my_role)
        col4, col5, col6 = st.columns(3)
        if col4.button("⚔️進軍"): handle_action("MAR", my_role)
        if col5.button("🚩占領"): handle_action("OCC", my_role)
        if db[my_role]["nuke"] >= 200:
            if col6.button("☢️核兵器", type="primary"): handle_action("NUK", my_role)
        else: col6.button(f"核({db[my_role]['nuke']:.0f})", disabled=True)
else:
    st.info("通信待機中...")
    if st.button("🔄 同期"): st.rerun()

# チャット
st.markdown(f'<div class="chat-box">{"".join([f"<div>{m}</div>" for m in db["chat"][-4:]])}</div>', unsafe_allow_html=True)
msg = st.text_input("通信:", key="chat_input")
if st.button("送信"):
    if msg: db["chat"].append(f"{my_role.upper()}: {msg}"); st.rerun()
