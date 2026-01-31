import streamlit as st
from supabase import create_client
import time
import random

# --- 1. 接続設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets設定を確認してください。")
    st.stop()

# --- 2. データベース操作関数 ---
def get_game(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

# ログとメッセージを追加する関数
def add_msg(rid, current_chat, sender, text, is_log=False):
    chat = current_chat if current_chat else []
    prefix = "📢 [LOG]:" if is_log else f"💬 [{sender}]:"
    chat.append(f"{prefix} {text}")
    # 直近8件に絞って同期
    sync(rid, {"chat": chat[-8:]})

# --- 3. UI/レイアウト設定 ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #FFF; overflow: hidden; }
    .enemy-banner { background-color: #111; border-bottom: 1px solid #00f2ff; padding: 5px; text-align: center; margin: -60px -15px 10px -15px; }
    .enemy-text { color: #00f2ff; font-weight: bold; font-size: 0.9rem; }
    .stat-card { background: #0a0a0a; border: 1px solid #333; padding: 8px; border-radius: 4px; }
    .bar-label { font-size: 0.7rem; color: #AAA; margin-bottom: 2px; display: flex; justify-content: space-between; }
    .hp-bar-bg { background: #222; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    /* ボタンをコンパクトに */
    div[data-testid="column"] button { height: 35px !important; font-size: 0.75rem !important; }
    /* チャットログエリア */
    .chat-box { background: #050505; border: 1px solid #444; padding: 8px; height: 140px; overflow-y: auto; font-family: monospace; font-size: 0.8rem; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. メインロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("担当", ["p1", "p2"], horizontal=True)
    if st.button("戦域接続"):
        data = get_game(rid)
        if not data:
            supabase.table("games").insert({"id": rid, "p1_hp": 150, "p2_hp": 150, "turn": "p1", "ap": 2, "chat": ["📢 [LOG]: 作戦開始"]}).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【バトル】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("陣営選択", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    # --- UI表示 ---
    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">第 {data.get("turn_count", 1)} ターン | {me.upper()} OPERATION</span></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自国本土</span><span>{data[f'{me}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝地帯</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {data[f'{me}_colony']}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>敵軍核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.5;"></div></div>
        </div>""", unsafe_allow_html=True)

    # 操作
    if data['turn'] == me:
        st.info(f"あなたの指揮権 (AP: {data['ap']})")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🛠軍拡"):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + 20, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"{me.upper()}が軍備を拡張しました", True)
            st.rerun()
        if c2.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 30, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"{me.upper()}が防衛線を強化しました", True)
            st.rerun()
        if c3.button("⚔️進軍"):
            dmg = data[f"{me}_mil"] * 0.5 + 20
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"{me.upper()}が総攻撃を仕掛けました", True)
            st.rerun()
        if c4.button("🕵️スパイ"):
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-40), "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"{me.upper()}のスパイが敵核施設を破壊", True)
            st.rerun()
        
        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵軍の行動を待機中...")
        time.sleep(3)
        st.rerun()

    # --- チャット & 戦況ログ ---
    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
    
    msg_input = st.text_input("通信送信 (Enterで送信)", key="chat_input")
    if st.button("送信"):
        if msg_input:
            add_msg(st.session_state.room_id, data['chat'], me, msg_input)
            st.rerun()
