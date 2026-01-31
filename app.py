import streamlit as st
import time
import base64
import random

# --- 1. システム設定 ---
st.set_page_config(page_title="DEUS: ONLINE CUSTOM", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #FFF; }
    .vs-banner { background-color: #001; border-bottom: 2px solid #00F; padding: 10px; text-align: center; margin-bottom: 20px; }
    .vs-text { color: #00F; font-weight: bold; font-size: 1.2rem; text-shadow: 0 0 10px #00F; }
    .stat-card { background: #111; border: 1px solid #333; padding: 10px; border-radius: 5px; }
    .active-p { border: 1px solid #00F; box-shadow: 0 0 15px #00F5; }
    .hp-bar-bg { background: #222; width: 100%; height: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #444; }
    .p1-bar { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .p2-bar { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    .chat-box { background: #050505; border: 1px solid #222; height: 150px; overflow-y: scroll; padding: 10px; font-size: 0.8rem; color: #0F0; font-family: monospace; margin-bottom: 10px; }
    /* ボタン装飾 */
    div[data-testid="column"] button { background: #000 !important; color: #00F !important; border: 1px solid #00F !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. データベース（共有ステート） ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "settings": {"max_hp": 500, "turn_sec": 30},
        "p1": {"hp": 500, "nuke": 0, "military": 20},
        "p2": {"hp": 500, "nuke": 0, "military": 20},
        "turn_owner": "p1", "turn_start_time": time.time(),
        "chat": ["システム：戦域オンライン。クリックして同期。"]
    }

db = st.session_state.db

# --- 3. 音響エンジン (JS) ---
def play_se(freq):
    st.components.v1.html(f"""
        <script>
        (function() {{
            const c = new (window.AudioContext || window.webkitAudioContext)();
            const o = c.createOscillator();
            const g = c.createGain();
            o.frequency.value = {freq};
            g.gain.setValueAtTime(0.1, c.currentTime);
            g.gain.exponentialRampToValueAtTime(0.01, c.currentTime + 0.2);
            o.connect(g); g.connect(c.destination);
            o.start(); o.stop(c.currentTime + 0.2);
        }})();
        </script>
    """, height=0)

# --- 4. サイドバー設定 ---
st.sidebar.title("🛠 DEUS コマンド")
my_role = st.sidebar.radio("デバイス登録:", ["観戦中", "p1", "p2"])

st.sidebar.markdown("---")
st.sidebar.subheader("戦域カスタム")
new_hp = st.sidebar.number_input("初期領土", 100, 2000, db["settings"]["max_hp"])
new_sec = st.sidebar.number_input("制限時間(秒)", 5, 120, db["settings"]["turn_sec"])

if st.sidebar.button("リセットして反映"):
    db["settings"]["max_hp"] = new_hp
    db["settings"]["turn_sec"] = new_sec
    db["p1"] = {"hp": new_hp, "nuke": 0, "military": 20}
    db["p2"] = {"hp": new_hp, "nuke": 0, "military": 20}
    db["chat"].append("システム：設定変更と戦域再構成。")
    st.rerun()

# --- 5. ゲームロジック ---
# 時間切れ判定
elapsed = time.time() - db["turn_start_time"]
time_left = max(0, db["settings"]["turn_sec"] - int(elapsed))

if time_left == 0 and my_role != "観戦中":
    db["turn_owner"] = "p2" if db["turn_owner"] == "p1" else "p1"
    db["turn_start_time"] = time.time()
    db["chat"].append(f"システム：時間切れ。交代。")
    st.rerun()

def handle_action(action, actor):
    target = "p2" if actor == "p1" else "p1"
    if action == "ATTACK":
        dmg = db[actor]["military"] + random.randint(10, 30)
        db[target]["hp"] -= dmg
        db["chat"].append(f"戦報：{actor.upper()}の攻撃。敵領土を破壊。")
    elif action == "EXP":
        db[actor]["military"] += 15
        db[actor]["nuke"] += 25
        db["chat"].append(f"戦報：{actor.upper()}が軍備を増強。")
    
    db["turn_owner"] = target
    db["turn_start_time"] = time.time()
    play_se(400)
    st.rerun()

# --- 6. メイン画面 ---
st.markdown('<div class="vs-banner"><span class="vs-text">DEUS: ONLINE PROTOCOL</span></div>', unsafe_allow_html=True)

# 領土と核
c1, c2 = st.columns(2)
with c1:
    st.markdown(f'<div class="stat-card {"active-p" if db["turn_owner"]=="p1" else ""}"><b>PLAYER 1</b><br>領土: {db["p1"]["hp"]}<div class="hp-bar-bg"><div class="p1-bar" style="width:{db["p1"]["hp"]/db["settings"]["max_hp"]*100}%"></div></div>核開発: {db["p1"]["nuke"]}/200<div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(db["p1"]["nuke"]/2, 100)}%"></div></div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-card {"active-p" if db["turn_owner"]=="p2" else ""}"><b>PLAYER 2</b><br>領土: {db["p2"]["hp"]}<div class="hp-bar-bg"><div class="p2-bar" style="width:{db["p2"]["hp"]/db["settings"]["max_hp"]*100}%"></div></div>核開発: {db["p2"]["nuke"]}/200<div class="hp-bar-bg"><div class="nuke-bar" style="width:{min(db["p2"]["nuke"]/2, 100)}%"></div></div></div>', unsafe_allow_html=True)

st.write(f"### 残り時間: {time_left}s")

if my_role == db["turn_owner"]:
    st.success("あなたのターンです")
    ca, cb = st.columns(2)
    if ca.button("⚔️ 進軍執行", use_container_width=True): handle_action("ATTACK", my_role)
    if cb.button("🛠 軍備拡張", use_container_width=True): handle_action("EXP", my_role)
else:
    st.info("待機中...")
    if st.button("🔄 同期・更新"): st.rerun()

# チャット
st.write("---")
st.markdown(f'<div class="chat-box">{"".join([f"<div>{m}</div>" for m in db["chat"][-5:]])}</div>', unsafe_allow_html=True)
msg = st.text_input("通信内容:", key="chat_input")
if st.button("送信"):
    if msg:
        db["chat"].append(f"{my_role.upper()}: {msg}")
        st.rerun()
