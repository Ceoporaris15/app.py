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

# --- 2. UIスタイル ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")
st.markdown("""
    <style>
    div[data-testid="stStatusWidget"], 
    div[data-testid="stAppViewBlockContainer"] > div:first-child { 
        visibility: hidden !important; display: none !important; opacity: 0 !important;
    }
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #ffffff !important;
        overflow: hidden !important; height: 100vh;
    }
    .status-row { display: flex; align-items: center; margin-bottom: 4px; }
    .status-label { width: 65px; font-size: 0.65rem; color: #aaa; font-weight: bold; }
    .bar-container { flex-grow: 1; }
    .enemy-mini-hud {
        background: #0a0a0a; border: 1px solid #441111;
        padding: 5px; margin-bottom: 5px; border-radius: 4px;
        display: flex; justify-content: space-around; font-size: 0.6rem;
    }
    .live-log {
        background: #080808; border-left: 2px solid #00ffcc;
        padding: 5px; margin-bottom: 5px; font-family: monospace;
        font-size: 0.7rem; color: #00ffcc; height: 65px; overflow-y: auto;
    }
    .shield-text { color: #3498db; font-weight: bold; }
    .self-hud {
        background: #050505; border: 1px solid #d4af37;
        padding: 10px; margin-bottom: 8px; border-radius: 8px;
    }
    .bar-bg { background: #111; width: 100%; height: 10px; border-radius: 5px; border: 1px solid #222; overflow: hidden; }
    .fill-hp { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .fill-sh { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .fill-nk { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    button {
        background-color: #111 !important; color: #d4af37 !important;
        border: 1px solid #d4af37 !important; height: 45px !important;
        font-size: 0.7rem !important; transition: none !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #ff0000, #990000) !important;
        color: white !important; border: 2px solid #ffffff !important;
        height: 50px !important; font-size: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名を入力", "帝国")
    if st.button("DEPLOY"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 通信確立。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield": False, "p2_nuke_shield": False
            }
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        sync(rid, {f"{role}_country": c_name})
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    my_name, enemy_name = data.get(f'{me}_country', '自国'), data.get(f'{opp}_country', '敵国')
    my_nuke = data.get(f'{me}_nuke', 0)

    # 勝敗判定
    if data[f"{me}_colony"] <= 0 or data[f"{me}_hp"] <= 0:
        st.error(f"敗北: {my_name}崩壊"); st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.success(f"勝利: {enemy_name}征服"); st.stop()

    # 1. 敵軍HUD
    st.markdown(f'<div class="enemy-mini-hud"><div>敵: {enemy_name}</div><div>本土: {data.get(f"{opp}_hp",0):.0f}</div><div>植民地: {data.get(f"{opp}_colony",0):.0f}</div></div>', unsafe_allow_html=True)

    # 2. ログ
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # 3. 自軍HUD
    current_atk = 45 + (my_nuke * 0.53)
    s_count = data.get(f'{me}_shield', 0)
    n_shield = "【核防壁稼働中】" if data.get(f'{me}_nuke_shield') else ""
    st.markdown(f"""
    <div class="self-hud">
        <div style="font-size:0.9rem; color:#d4af37; font-weight:bold; margin-bottom:5px;">{my_name} <span style="font-size:0.6rem; color:#3498db;">🛡️x{s_count} {n_shield}</span></div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-container"><div class="bar-bg"><div class="fill-hp" style="width:{data.get(f'{me}_hp',0)/10}%"></div></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-container"><div class="bar-bg"><div class="fill-sh" style="width:{data.get(f'{me}_colony',0)}%"></div></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-container"><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    # 4. アクション
    if data['turn'] == me:
        pref = f"[{my_name}]"
        if my_nuke >= 200:
            if st.button("🚨 核兵器発射 (NUKE)", type="primary", use_container_width=True):
                if data.get(f'{opp}_nuke_shield'):
                    msg = f"☢️ {my_name}の核を{enemy_name}が完全に無効化した！"
                    sync(st.session_state.room_id, {f"{me}_nuke": 0, f"{opp}_nuke_shield": False, "ap": 0, "chat": data['chat']+[msg]})
                else:
                    sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {my_name}の核投下。"]})
                st.rerun()

        c1, c2, c3, c4, c5 = st.columns(5)
        conf = {"use_container_width": True}
        if c1.button("🛠️\n軍拡", **conf):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {pref} 軍拡。"]})
            st.rerun()
        if c2.button("🛡️\n防衛", **conf):
            # 1/4の確率で進軍2回無効(Shield+2), 1/10の確率で核無効(NukeShield)
            s_add = 2 if random.random() < 0.25 else 0
            ns_active = True if random.random() < 0.10 else data.get(f'{me}_nuke_shield', False)
            msg = f"🛡️ {pref} 防衛網強化"
            if s_add: msg += "【迎撃体制】"
            if ns_active and not data.get(f'{me}_nuke_shield'): msg += "【対核防壁】"
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, f"{me}_shield": data[f"{me}_shield"]+s_add, f"{me}_nuke_shield": ns_active, "ap": data['ap']-1, "chat": data['chat']+[msg]})
            st.rerun()
        if c3.button("🕵️\n工作", **conf):
            success = random.random() < 0.5
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"] - (100 if success else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🕵️ {pref} 工作{'成功' if success else '失敗'}。"]})
            st.rerun()
        if c4.button("⚔️\n進軍", **conf):
            if data.get(f'{opp}_shield', 0) > 0:
                msg = f"⚔️ {pref}の進軍を{enemy_name}が迎撃！"
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[msg]})
            else:
                dmg = current_atk + random.randint(-5, 5)
                new_col = max(0, data[f"{opp}_colony"] - dmg); new_hp = max(0, data[f"{opp}_hp"] - (dmg - data[f"{opp}_colony"] if dmg > data[f"{opp}_colony"] else 0))
                sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": new_hp, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {pref} {dmg:.0f}ダメ！"]})
            st.rerun()
        if c5.button("🚩\n占領", **conf):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {pref} {'反乱' if rebel else '占領'}。"]})
            st.rerun()
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning(f"{enemy_name} 行動中...")

    # 通信
    st.markdown("---")
    t_msg = st.text_input("", key="chat_input", placeholder="通信...", label_visibility="collapsed")
    if st.button("SEND", use_container_width=True) and t_msg:
        sync(st.session_state.room_id, {"chat": get_game(st.session_state.room_id)['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()
    
    if data['turn'] != me: time.sleep(3); st.rerun()
