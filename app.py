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

def add_msg(rid, current_chat, sender, text, is_log=False):
    chat = current_chat if current_chat else []
    prefix = "📢" if is_log else f"💬[{sender}]"
    chat.append(f"{prefix} {text}")
    sync(rid, {"chat": chat[-6:]})

# --- 3. UI/スタイル設定 (点滅防止 & AI戦デザイン) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 画面の白飛び防止 */
    html, body, [data-testid="stAppViewContainer"] { background-color: #000 !important; color: #FFF; overflow: hidden; }
    /* ヘッダー */
    .enemy-banner { background-color: #111; border-bottom: 1px solid #d4af37; padding: 5px; text-align: center; margin: -60px -15px 10px -15px; }
    .enemy-text { color: #d4af37; font-weight: bold; font-size: 0.9rem; }
    /* ステータスカード */
    .stat-card { background: #0a0a0a; border: 1px solid #333; padding: 10px; border-radius: 4px; }
    .bar-label { font-size: 0.75rem; color: #AAA; margin-bottom: 2px; display: flex; justify-content: space-between; }
    /* ゲージ類 */
    .hp-bar-bg { background: #222; width: 100%; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 6px; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; transition: width 0.3s; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; transition: width 0.3s; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; transition: width 0.3s; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; transition: width 0.3s; }
    /* ログ */
    .chat-box { background: #000; border: 1px solid #444; padding: 10px; height: 120px; overflow-y: auto; font-family: monospace; font-size: 0.85rem; margin-top: 10px; color: #00ffcc; }
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
            supabase.table("games").insert({"id": rid, "p1_hp": 150, "p2_hp": 150, "turn": "p1", "ap": 2, "p1_colony": 50, "p2_colony": 50, "chat": ["作戦開始"]}).execute()
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
    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">TURN: {data["turn"].upper()} | UNIT: {me.upper()}</span></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自軍本土</span><span>{data[f'{me}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝地帯(占領)</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{me}_colony'], 100)}%"></div></div>
            <div class="bar-label"><span>自軍核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>敵軍核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.5;"></div></div>
        </div>""", unsafe_allow_html=True)

    # 勝利判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.error(f"GAME OVER - {'勝利' if data[opp+'_hp']<=0 else '敗北'}")
        if st.button("REBOOT"): sync(st.session_state.room_id, {"p1_hp": 150, "p2_hp": 150, "p1_nuke": 0, "p2_nuke": 0, "turn": "p1"}); st.rerun()
        st.stop()

    # 操作パネル
    if data['turn'] == me:
        st.success(f"指揮権発動中 (AP: {data['ap']})")
        fac = data[f"{me}_faction"]
        
        c1, c2, c3 = st.columns(3)
        if c1.button("🛠軍拡"):
            n_val = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_val, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"軍備と核開発を推進", True)
            st.rerun()
        if c2.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 30, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"防衛ラインを構築", True)
            st.rerun()
        if c3.button("⚔️進軍"):
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"敵陣地へ攻撃を敢行", True)
            st.rerun()
            
        c4, c5 = st.columns(2)
        if c4.button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 40, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"緩衝地帯を拡大", True)
            st.rerun()
        if c5.button("☢️ 核発射", disabled=data[f"{me}_nuke"] < 200):
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.15, f"{me}_nuke": 0, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"核兵器が使用された！", True)
            st.rerun()
        
        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵軍の行動を待機中...")
        time.sleep(2)
        st.rerun()

    # チャット & ログ
    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
    msg = st.text_input("通信入力", key="comms")
    if st.button("送信"):
        if msg: add_msg(st.session_state.room_id, data['chat'], me, msg); st.rerun()
