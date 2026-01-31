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

# --- 2. 漆黒・完全固定UI (明滅・チカチカ・スクロールを徹底排除) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 【最優先】画面更新時の「暗転マスク」を完全に透明化して消去 */
    div[data-testid="stAppViewBlockContainer"] > div:first-child,
    div[data-testid="stStatusWidget"],
    .stDeployButton {
        display: none !important;
        opacity: 0 !important;
    }

    /* 画面が計算中に「薄暗くなる」のを防ぐ魔法のCSS */
    [data-testid="stAppViewContainer"] > section:first-child > div:first-child {
        background-color: rgba(0,0,0,0) !important;
    }

    /* 背景とスクロールの固定 */
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important;
        color: #ffffff !important;
        overflow: hidden !important;
        height: 100vh;
    }

    /* ボタンの白化・明滅防止 */
    button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        height: 42px !important;
        transition: none !important; /* アニメーションによる遅延を削除 */
    }
    button:active, button:focus {
        background-color: #222 !important;
        color: #f1c40f !important;
        border-color: #f1c40f !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* HUDパーツ */
    .live-log {
        background: #080808;
        border-left: 3px solid #d4af37;
        padding: 8px;
        margin-bottom: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        color: #00ffcc;
        height: 70px;
        overflow-y: auto;
    }
    .stat-card { background: #050505; border: 1px solid #222; padding: 5px; border-radius: 4px; margin-bottom: 4px; }
    .bar-bg { background: #111; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; margin: 4px 0; border: 1px solid #222; }
    .fill-hp { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .fill-sh { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー】
if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("CODE", "7777")
    role = st.radio("ROLE", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝国")
    c_cap = st.text_input("首都", "第一区")
    f_select = st.selectbox("陣営", ["連合国", "枢軸國", "社会主義国"])

    if st.button("戦域接続"):
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0,
            "p1_nuke": 0.0, "p2_nuke": 0.0, "p1_mil": 0.0, "p2_mil": 0.0, "turn": "p1", "ap": 2,
            "p1_country": "準備中", "p2_country": "準備中", "chat": ["🛰️ システムオンライン。"]
        }
        if role == "p1":
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        
        sync(rid, {f"{role}_faction": f_select, f"{role}_country": c_name, f"{role}_capital": c_cap})
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【バトルフェーズ】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    # 戦況ログ
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-4:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # ステータス表示
    cols = st.columns(2)
    for i, t in enumerate([me, opp]):
        with cols[i]:
            t_n = data.get(f'{t}_country', '不明')
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:0.7rem; color:#d4af37; font-weight:bold;">{t_n}</div>
                <div class="bar-bg"><div class="fill-hp" style="width:{data.get(f'{t}_hp',0)/10}%"></div></div>
                <div class="bar-bg"><div class="fill-sh" style="width:{data.get(f'{t}_colony',0)}%"></div></div>
            </div>""", unsafe_allow_html=True)

    # アクション
    if data['turn'] == me:
        st.success(f"TURN: {data.get(f'{me}_country','')} (AP:{data['ap']})")
        pref = f"[{data.get(f'{me}_country','')}]"
        
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠"):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"]+25, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 軍備増強。"]})
            st.rerun()
        if c2.button("🛡"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 防衛網展開。"]})
            st.rerun()
        if c3.button("🕵️"):
            success = random.random() < 0.5
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-40) if success else data[f"{opp}_nuke"], "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 工作{'成功' if success else '失敗'}。"]})
            st.rerun()
        if c4.button("⚔️"):
            dmg = (data[f"{me}_mil"]*0.5 + 30)
            t_col = data[f"{opp}_colony"]
            new_col = max(0, t_col - dmg)
            new_hp = max(0, data[f"{opp}_hp"] - (dmg - t_col if dmg > t_col else 0))
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": new_hp, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 進軍。"]})
            st.rerun()
        if c5.button("🚩"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 占領地拡大。"]})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 2})
            st.rerun()

        # チャット
        chat_msg = st.text_input("CHAT", key="c_in", label_visibility="collapsed")
        if st.button("SEND") and chat_msg:
            sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬{data.get(f'{me}_country','')}: {chat_msg}"]})
            st.rerun()
    else:
        st.warning(f"{data.get(f'{opp}_country','敵軍')}の動向を監視中...")
        time.sleep(3)
        st.rerun()
