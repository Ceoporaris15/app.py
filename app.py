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

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒のUI設定 (明滅・チカチカ・白ボタンを物理封殺) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 1. 画面全体の背景色を強制固定（再読込時の白飛び・暗転を防止） */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    
    /* 2. 更新中の「薄暗いマスク」とウィジェットを完全透明化（チカチカの主因を排除） */
    [data-testid="stStatusWidget"], [data-testid="stAppViewBlockContainer"] > div:first-child { 
        display: none !important; 
    }
    div[data-testid="stVerticalBlock"] > div { border: none !important; }
    
    /* 3. アニメーションを無効化 */
    * { animation: none !important; transition: none !important; }

    /* 4. ボタンの明滅修正：押した瞬間も黒と金を維持 */
    button, div[data-testid="stButton"] > button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
    }
    button:hover, button:active, button:focus {
        background-color: #222 !important;
        color: #f1c40f !important;
        border-color: #f1c40f !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* 5. HUD装飾 */
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

# 【ロビー】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    
    if st.button("戦域接続 (初期化して開始)"):
        # 初期データ：両国とも緩衝地帯（colony）を50保有してスタート
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_max": 1000.0, "p2_max": 1000.0, 
            "p1_colony": 50.0, "p2_colony": 50.0, "p1_nuke": 0.0, "p2_nuke": 0.0, 
            "p1_mil": 0.0, "p2_mil": 0.0, "p1_faction": None, "p2_faction": None,
            "turn": "p1", "ap": 2, "chat": ["📢 戦役開始。両軍、緩衝地帯を確保済み。"]
        }
        try:
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
            st.session_state.room_id, st.session_state.role = rid, role
            st.rerun()
        except:
            st.error("接続エラー。テーブル設定を確認してください。")

# 【バトルフェーズ】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.session_state.room_id = None; st.rerun()
    
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("陣営選択", ["連合国", "枢軸國", "社会主義国"])
        if st.button("確定"):
            ap_val = (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": ap_val})
            st.rerun()
        st.stop()

    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">OPERATOR: {me.upper()} | {data["turn"].upper()} PHASE</span></div>', unsafe_allow_html=True)
    
    # --- HUD表示 ---
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自軍本土</span><span>{data[f'{me}_hp']:.0f}/1000</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/1000)*100}%;"></div></div>
            <div class="bar-label"><span>占領地(緩衝)</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{me}_colony'], 100)}%"></div></div>
            <div class="bar-label"><span>核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/1000)*100}%;"></div></div>
            <div class="bar-label"><span>敵・占領地</span><span>{data[f'{opp}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{opp}_colony'], 100)}%; opacity: 0.6;"></div></div>
            <div class="bar-label"><span>敵・核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.4;"></div></div>
        </div>""", unsafe_allow_html=True)

    # アクション
    if data['turn'] == me:
        st.success(f"ACTIVE TURN (AP: {data['ap']})")
        fac = data[f"{me}_faction"]
        c1, c2, c3 = st.columns(3); c4, c5 = st.columns(2)
        
        if c1.button("🛠軍拡"):
            n_v = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_v, "ap": data['ap']-1})
            st.rerun()
        if c2.button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 35, "ap": data['ap']-1}); st.rerun()
        if c3.button("🕵️スパイ"):
            success = random.random() < (0.6 if fac == "連合国" else 0.35)
            if success:
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1})
            else:
                sync(st.session_state.room_id, {"ap": data['ap']-1})
            st.rerun()
        if c4.button("⚔️進軍"):
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            # ダメージ処理：まず敵の占領地を削り、余った分が本土へ
            if data[f"{opp}_colony"] > 0:
                new_colony = max(0, data[f"{opp}_colony"] - dmg)
                sync(st.session_state.room_id, {f"{opp}_colony": new_colony, "ap": data['ap']-1})
            else:
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"] - dmg), "ap": data['ap']-1})
            st.rerun()
        if c5.button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 55, "ap": data['ap']-1}); st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵の行動を待機中...")
        time.sleep(2); st.rerun()
