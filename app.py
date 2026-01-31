import streamlit as st
from supabase import create_client
import time
import random
import base64

# --- 1. 接続設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets設定を確認してください。")
    st.stop()

# --- 2. データベース同期関数 ---
def get_game(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

# --- 3. UI/スタイル設定 (AI戦のデザインを継承) ---
st.set_page_config(page_title="DEUS: ONLINE", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #FFF; overflow: hidden; }
    .enemy-banner { background-color: #200; border-bottom: 1px solid #F00; padding: 5px; text-align: center; margin: -60px -15px 10px -15px; }
    .enemy-text { color: #F00; font-weight: bold; font-size: 0.9rem; letter-spacing: 2px; }
    .stat-section { display: flex; gap: 8px; margin-bottom: 8px; }
    .stat-card { flex: 1; background: #111; border: 1px solid #333; padding: 6px; border-radius: 4px; }
    .bar-label { font-size: 0.7rem; color: #AAA; margin-bottom: 2px; display: flex; justify-content: space-between; }
    .hp-bar-bg { background: #222; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 4px; border: 1px solid #333; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; transition: width 0.5s; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; transition: width 0.5s; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; transition: width 0.5s; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; transition: width 0.5s; }
    div[data-testid="column"] button, div[data-testid="stVerticalBlock"] button {
        height: 38px !important; background-color: #1a1a1a !important; color: #d4af37 !important; border: 1px solid #d4af37 !important; font-size: 0.8rem !important;
    }
    .log-box { background: #000; border-top: 1px solid #333; padding: 4px 8px; height: 60px; font-size: 0.75rem; color: #CCC; margin-top: 10px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 音響エンジン (AI戦仕様) ---
def play_sound(freq=440, type='sine', duration=0.2):
    st.components.v1.html(f"""<script>(function() {{ const c = new (window.AudioContext || window.webkitAudioContext)(); const o = c.createOscillator(); const g = c.createGain(); o.type = '{type}'; o.frequency.setValueAtTime({freq}, c.currentTime); g.gain.setValueAtTime(0.1, c.currentTime); g.gain.exponentialRampToValueAtTime(0.01, c.currentTime + {duration}); o.connect(g); g.connect(c.destination); o.start(); o.stop(c.currentTime + {duration}); }})();</script>""", height=0)

# --- 5. ゲームロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー・設定フェーズ】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("担当", ["p1", "p2"], horizontal=True)
    if st.button("戦域接続 (LINK START)"):
        data = get_game(rid)
        if not data:
            supabase.table("games").insert({"id": rid, "p1_hp": 150, "p2_hp": 150, "turn": "p1", "ap": 2, "p1_mil": 0, "p2_mil": 0, "p1_colony": 50, "p2_colony": 50, "chat": ["SYSTEM ONLINE"]}).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【陣営選択・ゲームフェーズ】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        st.title("陣営プロトコル選択")
        f = st.selectbox("採用陣営", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            ap = 3 if f == "社会主義国" else 2
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": ap if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    # --- 数値計算 ---
    p1_hp_pct = (data['p1_hp'] / 150) * 100
    p2_hp_pct = (data['p2_hp'] / 150) * 100
    my_nuke_pct = min(data[f'{me}_nuke'] / 2, 100)
    opp_nuke_pct = min(data[f'{opp}_nuke'] / 2, 100)
    my_colony_pct = min(data[f'{me}_colony'], 100)

    # --- UI表示 ---
    st.markdown(f"""
    <div class="enemy-banner"><span class="enemy-text">第 {data.get('turn_count', 1)} ターン | {me.upper()} OPERATION</span></div>
    <div class="stat-section">
        <div class="stat-card">
            <div class="bar-label"><span>自国本土</span><span>{data[f'{me}_hp']}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝地帯</span><span>{data[f'{me}_colony']}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {data[f'{me}_colony']}%;"></div></div>
            <div class="bar-label"><span>自国核開発</span><span>{data[f'{me}_nuke']}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {my_nuke_pct}%;"></div></div>
        </div>
        <div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>敵軍核開発</span><span>{data[f'{opp}_nuke']}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {opp_nuke_pct}%; opacity: 0.5;"></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 勝利判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.error("作戦終了")
        if st.button("再起動"): sync(st.session_state.room_id, {"p1_hp": 150, "p2_hp": 150, "p1_nuke": 0, "p2_nuke": 0, "turn": "p1"}); st.rerun()
        st.stop()

    # コマンド
    if data['turn'] == me:
        st.info(f"あなたの指揮ターン (AP: {data['ap']})")
        # 陣営補正
        fac = data[f"{me}_faction"]
        a = 1.5 if fac == "枢軸國" else 1.0
        n_rate = 2.0 if fac == "連合国" else 1.0
        
        c1, c2, c3 = st.columns(3); c4, c5 = st.columns(2)
        if c1.button("🛠軍拡"):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25*a, f"{me}_nuke": data[f"{me}_nuke"] + 20*n_rate, "ap": data['ap']-1})
            play_sound(300); st.rerun()
        if c2.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 30, "ap": data['ap']-1})
            play_sound(350); st.rerun()
        if c3.button("🕵️スパイ"):
            if random.random() < (0.6 if fac == "連合国" else 0.33):
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1})
            else: sync(st.session_state.room_id, {"ap": data['ap']-1})
            play_sound(600); st.rerun()
        if c4.button("⚔️進軍"):
            dmg = (data[f"{me}_mil"] * 0.5 + 15) * a
            new_opp_hp = data[f"{opp}_hp"] - dmg
            sync(st.session_state.room_id, {f"{opp}_hp": new_opp_hp, "ap": data['ap']-1})
            play_sound(500, 'square'); st.rerun()
        if c5.button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 40, "ap": data['ap']-1})
            play_sound(400); st.rerun()
        
        if data[f"{me}_nuke"] >= 200:
            if st.button("☢️ 最終宣告執行", type="primary"):
                sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.15, f"{me}_nuke": 0, "ap": data['ap']-1})
                st.rerun()

        if data['ap'] <= 0:
            next_ap = 3 if data[f"{opp}_faction"] == "社会主義国" else 2
            sync(st.session_state.room_id, {"turn": opp, "ap": next_ap})
            st.rerun()
    else:
        st.warning("敵軍の行動を待機中...")
        time.sleep(2)
        st.rerun()

    # ログ
    st.markdown(f'<div class="log-box">{"".join([f"<div>>> {l}</div>" for l in data["chat"][-2:]])}</div>', unsafe_allow_html=True)
