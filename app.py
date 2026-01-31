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

# --- 2. 漆黒・非明滅UI (一画面固定) ---
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
    .dmg-text { color: #ff4b4b; font-weight: bold; }
    .rebel-text { color: #ffa500; font-weight: bold; }
    .victory-screen { text-align: center; color: #d4af37; font-size: 2rem; margin-top: 20%; font-weight: bold; border: 2px solid #d4af37; padding: 20px; background: #111; }
    .defeat-screen { text-align: center; color: #ff4b4b; font-size: 2rem; margin-top: 20%; font-weight: bold; border: 2px solid #ff4b4b; padding: 20px; background: #111; }
    
    .self-hud {
        background: #050505; border: 1px solid #d4af37;
        padding: 8px; margin-bottom: 5px; border-radius: 8px;
    }
    .bar-bg { background: #111; width: 100%; height: 8px; border-radius: 4px; margin: 3px 0; border: 1px solid #222; overflow: hidden; }
    .fill-hp { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .fill-sh { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .fill-nk { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    
    /* ボタンデザイン */
    .stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #ff0000, #990000) !important;
        color: white !important; border: 2px solid #ffffff !important;
        height: 60px !important; margin-top: 5px; font-size: 1.2rem !important;
    }
    button {
        background-color: #111 !important; color: #d4af37 !important;
        border: 1px solid #d4af37 !important; height: 45px !important;
        font-size: 0.7rem !important; transition: none !important; padding: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインシステム ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝国")
    if st.button("戦域接続 (DEPLOY)"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0,
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システムオンライン。"]
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
    my_name = data.get(f'{me}_country', '自国')
    enemy_name = data.get(f'{opp}_country', '敵国')
    my_nuke = data.get(f'{me}_nuke', 0)

    # --- 勝敗判定 ---
    if data[f"{me}_colony"] <= 0 or data[f"{me}_hp"] <= 0:
        st.markdown(f'<div class="defeat-screen">【敗北】<br>{my_name} 崩壊</div>', unsafe_allow_html=True)
        if st.button("ロビーに戻る"): st.session_state.room_id = None; st.rerun()
        st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.markdown(f'<div class="victory-screen">【勝利】<br>{enemy_name} 征服完了</div>', unsafe_allow_html=True)
        if st.button("ロビーに戻る"): st.session_state.room_id = None; st.rerun()
        st.stop()

    # --- 1. 敵軍HUD ---
    st.markdown(f'<div class="enemy-mini-hud"><div>敵: {enemy_name}</div><div>本土: {data.get(f"{opp}_hp",0):.0f}</div><div>領土: {data.get(f"{opp}_colony",0):.0f}</div></div>', unsafe_allow_html=True)

    # --- 2. 実況ログ ---
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # --- 3. 自軍HUD ---
    current_atk = 45 + (my_nuke * 0.53)
    st.markdown(f"""<div class="self-hud">
        <div style="font-size:1rem; color:#d4af37; font-weight:bold;">{my_name} <span style="font-size:0.6rem; color:#ff4b4b;">(ATK: {current_atk:.0f})</span></div>
        <div class="bar-bg"><div class="fill-hp" style="width:{data.get(f'{me}_hp',0)/10}%"></div></div>
        <div class="bar-bg"><div class="fill-sh" style="width:{data.get(f'{me}_colony',0)}%"></div></div>
        <div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div>
    </div>""", unsafe_allow_html=True)

    # --- 4. アクション & いつでもチャット ---
    pref = f"[{my_name}]"
    
    # 【核ボタン】(自ターンのみ出現)
    if data['turn'] == me and my_nuke >= 200:
        if st.button("🚨 核兵器発射 (NUKE)", type="primary", use_container_width=True):
            new_opp_hp, new_opp_col = max(1, data[f"{opp}_hp"] * 0.2), data[f"{opp}_colony"] * 0.2
            report = f"☢️ {my_name}が核を使用した！"
            sync(st.session_state.room_id, {f"{opp}_hp": new_opp_hp, f"{opp}_colony": new_opp_col, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[report]})
            st.rerun()

    # 【アクションボタン】(自ターンのみ有効)
    if data['turn'] == me:
        st.write(f"あなたのターン (AP: {data['ap']})")
        c1, c2, c3, c4, c5 = st.columns(5)
        conf = {"use_container_width": True}
        if c1.button("🛠️\n軍拡", **conf):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {pref} 軍備強化。"]})
            st.rerun()
        if c2.button("🛡️\n防衛", **conf):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {pref} 防衛網。"]})
            st.rerun()
        if c3.button("🕵️\n工作", **conf):
            success = random.random() < 0.5
            loss = 100 if success else 0
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"] - loss), "ap": data['ap']-1, "chat": data['chat']+[f"🕵️ {pref} 工作{'成功' if success else '失敗'}。"]})
            st.rerun()
        if c4.button("⚔️\n進軍", **conf):
            dmg = current_atk + random.randint(-5, 5)
            new_col = max(0, data[f"{opp}_colony"] - dmg); new_hp = max(0, data[f"{opp}_hp"] - (dmg - data[f"{opp}_colony"] if dmg > data[f"{opp}_colony"] else 0))
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": new_hp, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {pref} {dmg:.0f}ダメ！"]})
            st.rerun()
        if c5.button("🚩\n占領", **conf):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {pref} {'反乱発生' if rebel else '占領拡大'}。"]})
            st.rerun()
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning(f"{enemy_name} の行動を待機中...")

    # --- 【重要】いつでもチャット機能 (ターンの外側に配置) ---
    st.markdown("---")
    t_msg = st.text_input("", key="chat_input", placeholder="敵国への通信を入力...", label_visibility="collapsed")
    if st.button("通信送信 (SEND)", use_container_width=True) and t_msg:
        # 常に最新のchatデータを再取得して送信
        current_data = get_game(st.session_state.room_id)
        sync(st.session_state.room_id, {"chat": current_data['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()

    # 敵ターン時は3秒ごとに自動更新
    if data['turn'] != me:
        time.sleep(3)
        st.rerun()
