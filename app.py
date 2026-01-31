import streamlit as st
from supabase import create_client
import time
import random

# --- 1. 接続 & 通信 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets missing.")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒・固定レイアウトUI (スマホ最適化) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 全体：スクロール禁止と背景固定 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
        overflow: hidden !important; /* スクロール封印 */
        height: 100vh;
    }
    
    /* 更新時のチカチカ（オーバーレイ）を完全透明化 */
    [data-testid="stStatusWidget"], [data-testid="stAppViewBlockContainer"] > div:first-child { 
        opacity: 0 !important; 
    }

    /* ボタンの白化防止 */
    button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        height: 40px; /* スマホで押しやすい高さ */
    }
    button:active, button:focus {
        background-color: #222 !important;
        color: #f1c40f !important;
        outline: none !important;
    }

    /* 戦況実況ボックス */
    .live-log {
        background: #080808;
        border-left: 3px solid #d4af37;
        padding: 8px;
        margin: 5px 0;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: #00ffcc;
        height: 60px; /* 固定高でスクロールを防ぐ */
        overflow: hidden;
    }

    /* ゲージのコンパクト化 */
    .stat-card { background: #050505; border: 1px solid #222; padding: 5px; border-radius: 4px; margin-bottom: 5px; }
    .bar-label { font-size: 0.7rem; color: #AAA; margin-bottom: 2px; display: flex; justify-content: space-between; }
    .hp-bar-bg { background: #111; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインシステム ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー】
if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("CODE", "7777")
    role = st.radio("ROLE", ["p1", "p2"], horizontal=True)
    if st.button("DEPLOY"):
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_max": 1000.0, "p2_max": 1000.0, 
            "p1_colony": 50.0, "p2_colony": 50.0, "p1_nuke": 0.0, "p2_nuke": 0.0, 
            "p1_mil": 0.0, "p2_mil": 0.0, "p1_faction": None, "p2_faction": None,
            "turn": "p1", "ap": 2, "chat": ["🛰️ 衛星軌道上で通信確立..."]
        }
        supabase.table("games").delete().eq("id", rid).execute()
        supabase.table("games").insert(init_data).execute()
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【バトル】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("FACTION", ["連合国", "枢軸國", "社会主義国"])
        if st.button("CONNECT"):
            ap_val = (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": ap_val})
            st.rerun()
        st.stop()

    # 戦況実況（最新のログを表示）
    last_msg = data['chat'][-1] if data['chat'] else "監視中..."
    st.markdown(f'<div class="live-log">⚡ LIVE: {last_msg}</div>', unsafe_allow_html=True)

    # ステータス表示
    c_l, c_r = st.columns(2)
    for i, target in enumerate([me, opp]):
        with (c_l if i==0 else c_r):
            label = "SELF" if target == me else "ENEMY"
            st.markdown(f"""<div class="stat-card">
                <div class="bar-label"><span>{label} HP</span><span>{data[f'{target}_hp']:.0f}</span></div>
                <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {data[f'{target}_hp']/10}%"></div></div>
                <div class="bar-label"><span>SHIELD</span><span>{data[f'{target}_colony']:.0f}</span></div>
                <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {data[f'{target}_colony']}%"></div></div>
            </div>""", unsafe_allow_html=True)

    # アクション
    if data['turn'] == me:
        st.success(f"YOUR TURN [AP:{data['ap']}]")
        fac = data[f"{me}_faction"]
        c1, c2, c3 = st.columns(3); c4, c5 = st.columns(2)
        
        if c1.button("🛠軍拡"):
            n_v = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"]+25, f"{me}_nuke": data[f"{me}_nuke"]+n_v, "ap": data['ap']-1, "chat": data['chat'] + ["軍備拡張、核燃料再処理を開始。"]})
            st.rerun()
        if c2.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat'] + ["防衛線を再構築、迎撃準備完了。"]})
            st.rerun()
        if c3.button("🕵️スパイ"):
            if random.random() < (0.6 if fac == "連合国" else 0.35):
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1, "chat": data['chat'] + ["スパイが潜入。敵核施設に打撃。"]})
            else:
                sync(st.session_state.room_id, {"ap": data['ap']-1, "chat": data['chat'] + ["工作員より通信途絶...失敗。"]})
            st.rerun()
        if c4.button("⚔️進軍"):
            dmg = (data[f"{me}_mil"]*0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            target_col = data[f"{opp}_colony"]
            new_col = max(0, target_col - dmg)
            new_hp = data[f"{opp}_hp"] - (dmg - target_col if dmg > target_col else 0)
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, new_hp), "ap": data['ap']-1, "chat": data['chat'] + [f"全軍進軍！敵陣地へ{dmg:.0f}の打撃。"]})
            st.rerun()
        if c5.button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, "ap": data['ap']-1, "chat": data['chat'] + ["緩衝地帯を占領、防衛域を拡大。"]})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵軍の通信を傍受中...")
        time.sleep(2); st.rerun()
