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
    st.error("Secrets configuration missing.")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒・固定レイアウトUI (スマホ完全最適化) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 全体：スクロール禁止・背景固定 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
        overflow: hidden !important;
        height: 100vh;
    }
    
    /* チカチカ（暗転・明滅）を物理封殺 */
    [data-testid="stStatusWidget"], [data-testid="stAppViewBlockContainer"] > div:first-child { 
        opacity: 0 !important; 
    }
    * { animation: none !important; transition: none !important; }

    /* ボタン・入力欄のスタイル */
    button {
        background-color: #111 !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        height: 38px;
    }
    input { background-color: #050505 !important; color: #fff !important; border: 1px solid #333 !important; }

    /* 戦況実況 & チャット統合ボックス */
    .live-log {
        background: #080808;
        border-left: 3px solid #d4af37;
        padding: 6px;
        margin-bottom: 5px;
        font-family: monospace;
        font-size: 0.8rem;
        color: #00ffcc;
        height: 80px;
        overflow-y: auto;
    }

    /* HUD */
    .stat-card { background: #050505; border: 1px solid #222; padding: 5px; border-radius: 4px; margin-bottom: 4px; }
    .bar-label { font-size: 0.65rem; color: #AAA; display: flex; justify-content: space-between; }
    .hp-bar-bg { background: #111; width: 100%; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 3px; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインシステム ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー：国家・首都・陣営の設定】
if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("デバイス役割", ["p1", "p2"], horizontal=True)
    
    st.markdown("---")
    country = st.text_input("国名を入力", "帝国")
    capital = st.text_input("首都名を入力", "第一特別区")
    faction = st.selectbox("軍事プロトコル", ["連合国", "枢軸國", "社会主義国"])

    if st.button("戦域接続 (DEPLOY)"):
        init_data = {
            "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_max": 1000.0, "p2_max": 1000.0, 
            "p1_colony": 50.0, "p2_colony": 50.0, "p1_nuke": 0.0, "p2_nuke": 0.0, 
            "p1_mil": 0.0, "p2_mil": 0.0, "turn": "p1", "ap": 2, 
            "chat": ["🛰️ 通信プロトコル確立。両軍の入域を待機中..."]
        }
        # 初回のみリセット。2人目は既存データへ合流
        data_exists = get_game(rid)
        if not data_exists or role == "p1":
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        
        # 自分の国家情報を登録
        sync(rid, {f"{role}_faction": faction, f"{role}_country": country, f"{role}_capital": capital})
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

# 【バトルフェーズ】
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    # 戦況・チャット表示
    logs = "".join([f"<div>{m}</div>" for m in data['chat'][-5:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # 1画面HUD
    c_l, c_r = st.columns(2)
    for i, target in enumerate([me, opp]):
        with (c_l if i==0 else c_r):
            name = data.get(f'{target}_country') or "不明"
            cap = data.get(f'{target}_capital') or "待機中"
            st.markdown(f"""<div class="stat-card">
                <div style="font-size:0.7rem; color:#d4af37; font-weight:bold;">{name} [{cap}]</div>
                <div class="bar-label"><span>本土HP</span><span>{data[f'{target}_hp']:.0f}</span></div>
                <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {data[f'{target}_hp']/10}%"></div></div>
                <div class="bar-label"><span>占領地</span><span>{data[f'{target}_colony']:.0f}</span></div>
                <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {data[f'{target}_colony']}%"></div></div>
            </div>""", unsafe_allow_html=True)

    # アクション & チャット
    if data['turn'] == me:
        st.success(f"TURN: {data[f'{me}_country']} (AP:{data['ap']})")
        fac = data[f"{me}_faction"]
        c1, c2, c3, c4, c5 = st.columns(5)
        
        # 共通ログプレフィックス
        pref = f"[{data[f'{me}_country']}]"

        if c1.button("🛠"):
            n_v = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"]+25, f"{me}_nuke": data[f"{me}_nuke"]+n_v, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 軍備を拡張。"]})
            st.rerun()
        if c2.button("🛡"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 防衛線を構築。"]})
            st.rerun()
        if c3.button("🕵️"):
            success = random.random() < (0.6 if fac == "連合国" else 0.35)
            msg = f"{pref} スパイ工作に成功。" if success else f"{pref} 工作員が捕縛された。"
            new_nuke = max(0, data[f"{opp}_nuke"]-50) if success else data[f"{opp}_nuke"]
            sync(st.session_state.room_id, {f"{opp}_nuke": new_nuke, "ap": data['ap']-1, "chat": data['chat'] + [msg]})
            st.rerun()
        if c4.button("⚔️"):
            dmg = (data[f"{me}_mil"]*0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            target_col = data[f"{opp}_colony"]
            new_col = max(0, target_col - dmg)
            new_hp = data[f"{opp}_hp"] - (dmg - target_col if dmg > target_col else 0)
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, new_hp), "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 進軍を開始。{dmg:.0f}の損害。"]})
            st.rerun()
        if c5.button("🚩"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, "ap": data['ap']-1, "chat": data['chat'] + [f"{pref} 新たな領土を占領。"]})
            st.rerun()

        # チャット機能
        msg = st.text_input("通信送信", key="chat_input", placeholder="メッセージ...")
        if st.button("SEND"):
            if msg:
                sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬{data[f'{me}_country']}: {msg}"]})
                st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning(f"敵国 ({data[f'{opp}_country']}) の動向を監視中...")
        time.sleep(2); st.rerun()
