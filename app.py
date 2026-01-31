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
    st.error("Secrets設定が未完了です。")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒のUI設定 (明滅・白ボタンを物理封殺) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 1. ローディング表示と背景の完全固定 */
    [data-testid="stStatusWidget"] { display: none !important; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    
    /* 2. アニメーションとトランジションを削除（チカチカ防止） */
    * { 
        animation: none !important; 
        transition: none !important; 
        text-decoration: none !important;
    }

    /* 3. ボタンの白色化を徹底修正 */
    button, div[data-testid="stButton"] > button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        border-radius: 4px !important;
    }
    button:hover, button:active, button:focus {
        background-color: #222 !important;
        color: #f1c40f !important;
        border-color: #f1c40f !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* 4. 各種パーツ */
    .enemy-banner { background-color: #0a0a0a; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin: -60px -15px 15px -15px; }
    .stat-card { background: #050505; border: 1px solid #222; padding: 12px; border-radius: 4px; }
    .bar-label { font-size: 0.75rem; color: #AAA; margin-bottom: 3px; display: flex; justify-content: space-between; font-family: monospace; }
    .hp-bar-bg { background: #111; width: 100%; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; border: 1px solid #333; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; }
    .chat-box { background: #000; border: 1px solid #333; padding: 10px; height: 100px; overflow-y: auto; font-family: monospace; font-size: 0.8rem; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインシステム ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー：再入場時リセット】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    
    if st.button("戦域接続 (リセット開始)"):
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_max": 1000.0, "p2_max": 1000.0, 
            "p1_colony": 50.0, "p2_colony": 50.0, "p1_nuke": 0.0, "p2_nuke": 0.0, 
            "p1_mil": 0.0, "p2_mil": 0.0, "p1_faction": None, "p2_faction": None,
            "turn": "p1", "ap": 2, "chat": ["📢 SYSTEM REBOOTED."]
        }
        # エラー回避のため upsert ではなく delete -> insert の確実なリセットを採用
        try:
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
            st.session_state.room_id, st.session_state.role = rid, role
            st.rerun()
        except Exception as e:
            st.error(f"接続エラー: {e}")

# 【ゲーム中】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.session_state.room_id = None; st.rerun()
    
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("陣営選択", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">UNIT: {me.upper()} | {data["turn"].upper()} PHASE</span></div>', unsafe_allow_html=True)
    
    # --- HUD表示 ---
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>本土耐久</span><span>{data[f'{me}_hp']:.0f}/1000</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/1000)*100}%;"></div></div>
            <div class="bar-label"><span>核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/1000)*100}%;"></div></div>
            <div class="bar-label"><span>敵・核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.4;"></div></div>
        </div>""", unsafe_allow_html=True)

    # ターン操作
    if data['turn'] == me:
        st.success(f"あなたのターン (AP: {data['ap']})")
        fac = data[f"{me}_faction"]
        c1, c2, c3 = st.columns(3)
        if c1.button("🛠軍拡"):
            n_v = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_v, "ap": data['ap']-1})
            st.rerun()
        if c2.button("⚔️進軍"):
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"] - dmg), "ap": data['ap']-1})
            st.rerun()
        if c3.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 35, "ap": data['ap']-1})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("待機中...")
        time.sleep(2); st.rerun()

    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
