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
    st.error("Secrets設定エラー")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒・固定レイアウトUI (チカチカ・スクロール封殺) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 全体：スクロール禁止・背景ブラック固定 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
        overflow: hidden !important;
        height: 100vh;
    }
    
    /* 更新時の明滅（暗転）を物理的に無効化 */
    [data-testid="stStatusWidget"], [data-testid="stAppViewBlockContainer"] > div:first-child { 
        opacity: 0 !important; 
    }
    
    /* ボタン・入力欄のスタイル固定 */
    button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        height: 38px;
    }
    button:active, button:focus { background-color: #222 !important; outline: none !important; }

    /* 実況ログ */
    .live-log {
        background: #080808;
        border-left: 3px solid #d4af37;
        padding: 6px;
        margin-bottom: 5px;
        font-family: monospace;
        font-size: 0.75rem;
        color: #00ffcc;
        height: 70px;
        overflow-y: auto;
    }

    /* HUD表示 */
    .stat-card { background: #050505; border: 1px solid #222; padding: 4px; border-radius: 4px; margin-bottom: 2px; }
    .name-tag { font-size: 0.65rem; color: #d4af37; font-weight: bold; overflow: hidden; white-space: nowrap; }
    .bar-label { font-size: 0.6rem; color: #AAA; display: flex; justify-content: space-between; }
    .hp-bar-bg { background: #111; width: 100%; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 2px; }
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
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("デバイス役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝国")
    c_cap = st.text_input("首都", "第一区")
    f_select = st.selectbox("軍事陣営", ["連合国", "枢軸國", "社会主義国"])

    if st.button("戦域接続"):
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_max": 1000.0, "p2_max": 1000.0, 
            "p1_colony": 50.0, "p2_colony": 50.0, "p1_nuke": 0.0, "p2_nuke": 0.0, 
            "p1_mil": 0.0, "p2_mil": 0.0, "turn": "p1", "ap": 2, 
            "p1_country": "準備中", "p2_country": "準備中",
            "chat": ["🛰️ 通信プロトコル確立。"]
        }
        if role == "p1":
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        
        sync(rid, {f"{role}_faction": f_select, f"{role}_country": c_name, f"{role}_capital": c_cap})
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【バトル】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    # --- 1. 戦況実況 ---
    logs = "".join([f"<div>{m}</div>" for m in data['chat'][-4:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # --- 2. HUD表示 (KeyError対策済) ---
    c_l, c_r = st.columns(2)
    for i, target in enumerate([me, opp]):
        with (c_l if i==0 else c_r):
            # .get() を使うことで、データがまだ無くてもエラーを回避
            t_name = data.get(f'{target}_country', '不明')
            t_cap = data.get(f'{target}_capital', '通信中')
            st.markdown(f"""<div class="stat-card">
                <div class="name-tag">{t_name} [{t_cap}]</div>
                <div class="bar-label"><span>HP</span><span>{data.get(f'{target}_hp', 0):.0f}</span></div>
                <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {data.get(f'{target}_hp', 0)/10}%"></div></div>
                <div class="bar-label"><span>SHIELD</span><span>{data.get(f'{target}_colony', 0):.0f}</span></div>
                <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {data.get(f'{target}_colony', 0)}%"></div></div>
            </div>""", unsafe_allow_html=True)

    # --- 3. アクション & チャット ---
    if data['turn'] == me:
        my_name = data.get(f'{me}_country', '自国')
        st.success(f"TURN: {my_name} (AP:{data['ap']})")
        
        fac = data.get(f"{me}_faction", "連合国")
        pref = f"[{my_name}]"
        
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠"):
            n_v = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"]+25, f"{me}_nuke": data[f"{me}_nuke"]+n_v, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 軍備を増強。"]})
            st.rerun()
        if c2.button("🛡"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 防衛網を展開。"]})
            st.rerun()
        if c3.button("🕵️"):
            success = random.random() < (0.6 if fac == "連合国" else 0.35)
            msg = f"{pref} 工作に成功。" if success else f"{pref} 工作員が消失。"
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50) if success else data[f"{opp}_nuke"], "ap": data['ap']-1, "chat": data['chat'] + [msg]})
            st.rerun()
        if c4.button("⚔️"):
            dmg = (data[f"{me}_mil"]*0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            t_col = data[f"{opp}_colony"]
            new_col = max(0, t_col - dmg)
            new_hp = max(0, data[f"{opp}_hp"] - (dmg - t_col if dmg > t_col else 0))
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": new_hp, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 侵攻を開始。"]})
            st.rerun()
        if c5.button("🚩"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 緩衝地帯を占拠。"]})
            st.rerun()

        # チャット機能
        with st.container():
            t_msg = st.text_input("", key="chat_in", placeholder="通信文を入力...", label_visibility="collapsed")
            if st.button("SEND", use_container_width=True):
                if t_msg:
                    sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬{my_name}: {t_msg}"]})
                    st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data.get(f"{opp}_faction") == "社会主義国" else 2})
            st.rerun()
    else:
        opp_name = data.get(f'{opp}_country', '敵国')
        st.warning(f"{opp_name} の通信を傍受中...")
        time.sleep(2); st.rerun()
