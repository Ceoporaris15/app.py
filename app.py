import streamlit as st
from supabase import create_client
import time
import random

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

# --- 2. UI/スタイル設定 (点滅・白飛びの完全封鎖) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 1. 背景色の強制固定：再読み込み時の白飛びを防止 */
    html, body, [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], [data-testid="stCanvas"], 
    [data-testid="stToolbar"], .main {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    
    /* 2. アニメーションの無効化：要素が出現する際のフェード(白点滅の原因)を消す */
    * {
        animation: none !important;
        transition: none !important;
        box-shadow: none !important;
    }

    /* 3. ヘッダー */
    .enemy-banner { 
        background-color: #0a0a0a; 
        border-bottom: 2px solid #d4af37; 
        padding: 10px; 
        text-align: center; 
        margin: -60px -15px 15px -15px; 
    }
    .enemy-text { color: #d4af37; font-weight: bold; font-family: monospace; letter-spacing: 2px; }
    
    /* 4. ステータスカード & ゲージ */
    .stat-card { background: #050505; border: 1px solid #222; padding: 12px; border-radius: 4px; }
    .bar-label { font-size: 0.75rem; color: #AAA; margin-bottom: 3px; display: flex; justify-content: space-between; font-family: monospace; }
    .hp-bar-bg { background: #111; width: 100%; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; border: 1px solid #333; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; }

    /* 5. 説明用カード */
    .info-card { background: #080808; border: 1px solid #333; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 0.8rem; }
    .info-title { color: #d4af37; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 5px; }
    
    /* 6. ボタンのデザイン(点滅抑制) */
    button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
    }
    
    /* 7. ログボックス */
    .chat-box { background: #000; border: 1px solid #333; padding: 10px; height: 100px; overflow-y: auto; font-family: monospace; font-size: 0.8rem; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ロジック ---
def play_sound(freq=440, type='sine', duration=0.2):
    st.components.v1.html(f"""<script>(function(){{const c=new(window.AudioContext||window.webkitAudioContext)();const o=c.createOscillator();const g=c.createGain();o.type='{type}';o.frequency.setValueAtTime({freq},c.currentTime);g.gain.setValueAtTime(0.1,c.currentTime);g.gain.exponentialRampToValueAtTime(0.01,c.currentTime+{duration});o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+{duration});}})();</script>""", height=0)

if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="info-card"><div class="info-title">【陣営特性】</div>'
                    '・連合国: 核速度2.0倍。スパイ60%成功。<br>'
                    '・枢軸國: 進軍1.5倍。攻撃特化。<br>'
                    '・社会主義国: 常に3AP。手数で圧倒。</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="info-card"><div class="info-title">【アクション】</div>'
                    '・軍拡: 軍備＋核。 | 防衛/占領: 緩衝地帯。<br>'
                    '・スパイ: 敵核妨害。 | 核: 200Pで発動。</div>', unsafe_allow_html=True)

    rid = st.text_input("作戦コード", "7777")
    role = st.radio("デバイス役割", ["p1", "p2"], horizontal=True)
    if st.button("戦域接続 (DEPLOY)"):
        data = get_game(rid)
        if not data:
            # 本土のデフォルト値を1000に設定
            supabase.table("games").insert({"id": rid, "p1_hp": 1000, "p2_hp": 1000, "p1_max": 1000, "p2_max": 1000, "p1_colony": 50, "p2_colony": 50, "turn": "p1", "ap": 2, "chat": ["📢 システム稼働"]}).execute()
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【バトル】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    max_hp = data.get('p1_max', 1000)
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("国家プロトコル選択", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">OPERATOR: {me.upper()} | {data["turn"].upper()} PHASE</span></div>', unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自軍本土</span><span>{data[f'{me}_hp']:.0f}/{max_hp}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/max_hp)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝地帯</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{me}_colony'], 100)}%"></div></div>
            <div class="bar-label"><span>核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with col_r:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/max_hp)*100}%;"></div></div>
            <div class="bar-label"><span>敵・核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.4;"></div></div>
        </div>""", unsafe_allow_html=True)

    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.error("MISSION END")
        if st.button("REBOOT"): 
            sync(st.session_state.room_id, {"p1_hp": 1000, "p2_hp": 1000, "p1_nuke": 0, "p2_nuke": 0, "p1_mil": 0, "p2_mil": 0, "p1_colony": 50, "p2_colony": 50, "turn": "p1"})
            st.rerun()
        st.stop()

    if data['turn'] == me:
        st.success(f"ACTIVE TURN (AP: {data['ap']})")
        fac = data[f"{me}_faction"]
        
        c1, c2, c3 = st.columns(3); c4, c5 = st.columns(2)
        if c1.button("🛠軍拡"):
            play_sound(300)
            n_val = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_val, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "軍備拡張及び核開発推進", True); st.rerun()
        if c2.button("🛡防衛"):
            play_sound(350)
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 35, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "防衛ライン再構築", True); st.rerun()
        if c3.button("🕵️スパイ"):
            play_sound(600, 'square')
            if random.random() < (0.6 if fac == "連合国" else 0.35):
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイ工作成功：敵核施設破壊", True)
            else:
                sync(st.session_state.room_id, {"ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイ工作失敗", True)
            st.rerun()
        if c4.button("⚔️進軍"):
            play_sound(500, 'square')
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"侵攻開始：{dmg:.0f}ダメージ", True); st.rerun()
        if c5.button("🚩占領"):
            play_sound(400)
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 45, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "緩衝地帯占領範囲拡大", True); st.rerun()

        if data[f"{me}_nuke"] >= 200:
            if st.button("☢️ 最終宣告執行", type="primary", use_container_width=True):
                sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.15, f"{me}_nuke": 0, "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "核兵器投下。", True); st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵の動向を監視中...")
        time.sleep(2); st.rerun()

    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
