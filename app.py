import streamlit as st
from supabase import create_client
import time
import random
import base64

# --- 1. 接続 & 初期設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets configuration missing.")
    st.stop()

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

# --- 2. UI/スタイル設定 (AI戦のデザインを完全継承 + 白飛び防止) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 画面の白飛びを徹底防止 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    * { animation: none !important; transition: none !important; }

    .enemy-banner { background-color: #111; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin: -60px -15px 15px -15px; }
    .enemy-text { color: #d4af37; font-weight: bold; font-family: monospace; letter-spacing: 2px; }
    
    .stat-card { background: #0a0a0a; border: 1px solid #333; padding: 12px; border-radius: 4px; }
    .bar-label { font-size: 0.75rem; color: #AAA; margin-bottom: 3px; display: flex; justify-content: space-between; font-family: monospace; }
    .hp-bar-bg { background: #222; width: 100%; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 8px; border: 1px solid #444; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; }

    .info-card { background: #0a0a0a; border: 1px solid #333; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 0.8rem; }
    .info-title { color: #d4af37; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 5px; }
    
    div[data-testid="column"] button {
        background-color: #1a1a1a !important; color: #d4af37 !important; border: 1px solid #d4af37 !important; height: 38px !important;
    }
    .chat-box { background: #000; border: 1px solid #444; padding: 10px; height: 100px; overflow-y: auto; font-family: monospace; font-size: 0.8rem; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 音響 & ロジック ---
def play_sound(freq=440, type='sine', duration=0.2):
    st.components.v1.html(f"""<script>(function(){{const c=new(window.AudioContext||window.webkitAudioContext)();const o=c.createOscillator();const g=c.createGain();o.type='{type}';o.frequency.setValueAtTime({freq},c.currentTime);g.gain.setValueAtTime(0.1,c.currentTime);g.gain.exponentialRampToValueAtTime(0.01,c.currentTime+{duration});o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+{duration});}})();</script>""", height=0)

if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【フェーズ：ロビー & 説明書】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="info-card"><div class="info-title">【陣営特性】</div>'
                    '・<b>連合国</b>: 核速度2.0倍。スパイ成功率60%。<br>'
                    '・<b>枢軸國</b>: 攻撃力1.5倍。短期決戦型。<br>'
                    '・<b>社会主義国</b>: AP(行動回数)が常に3。</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="info-card"><div class="info-title">【アクション】</div>'
                    '・<b>軍拡</b>: 軍備＋核P増加。<br>'
                    '・<b>防衛/占領</b>: 緩衝地帯を確保し本土を守る。<br>'
                    '・<b>スパイ</b>: 確率で敵の核開発を妨害。</div>', unsafe_allow_html=True)

    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    if st.button("戦域接続 (DEPLOY)"):
        data = get_game(rid)
        if not data:
            supabase.table("games").insert({"id": rid, "p1_hp": 150, "p2_hp": 150, "p1_colony": 50, "p2_colony": 50, "turn": "p1", "ap": 2, "chat": ["📢 システム稼働"]}).execute()
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【フェーズ：ゲーム本編】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("陣営プロトコル選択", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    # --- ステータスHUD ---
    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">OPERATOR: {me.upper()} | {data["turn"].upper()} PHASE</span></div>', unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自軍本土</span><span>{data[f'{me}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝地帯</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{me}_colony'], 100)}%"></div></div>
            <div class="bar-label"><span>核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with col_r:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>敵・核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.4;"></div></div>
        </div>""", unsafe_allow_html=True)

    # 勝敗判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.error("MISSION END")
        if st.button("SYSTEM REBOOT"): 
            sync(st.session_state.room_id, {"p1_hp": 150, "p2_hp": 150, "p1_nuke": 0, "p2_nuke": 0, "p1_mil": 0, "p2_mil": 0, "p1_colony": 50, "p2_colony": 50, "turn": "p1"})
            st.rerun()
        st.stop()

    # コマンド制御
    if data['turn'] == me:
        st.success(f"ACTIVE TURN (AP: {data['ap']})")
        fac = data[f"{me}_faction"]
        
        c1, c2, c3 = st.columns(3); c4, c5 = st.columns(2)
        if c1.button("🛠軍拡"):
            play_sound(300)
            n_val = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_val, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "軍備拡張及び核開発の推進", True); st.rerun()
        if c2.button("🛡防衛"):
            play_sound(350)
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 30, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "防衛ラインの再構築", True); st.rerun()
        if c3.button("🕵️スパイ"):
            play_sound(600, 'square')
            if random.random() < (0.6 if fac == "連合国" else 0.35):
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイ工作成功：敵核施設を破壊", True)
            else:
                sync(st.session_state.room_id, {"ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイ工作失敗", True)
            st.rerun()
        if c4.button("⚔️進軍"):
            play_sound(500, 'square')
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"敵軍への侵攻を開始：{dmg:.0f}ダメージ", True); st.rerun()
        if c5.button("🚩占領"):
            play_sound(400)
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 45, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "緩衝地帯の制圧範囲を拡大", True); st.rerun()

        if data[f"{me}_nuke"] >= 200:
            if st.button("☢️ 最終宣告執行", type="primary", use_container_width=True):
                sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.15, f"{me}_nuke": 0, "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "核兵器投下。世界が静まり返る。", True); st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵の動向を監視中...")
        time.sleep(2); st.rerun()

    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
    msg = st.text_input("通信送信", key="comms")
    if st.button("SEND"):
        if msg: add_msg(st.session_state.room_id, data['chat'], me, msg); st.rerun()
