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
    st.error("Secrets設定(SUPABASE_URL, SUPABASE_KEY)を確認してください。")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒のタクティカルUI ---
st.set_page_config(page_title="DEUS ONLINE: FINAL", layout="centered")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #00ffcc !important;
        font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif;
    }
    .stButton > button { 
        background-color: #000000 !important; color: #00ffcc !important; 
        border: 2px solid #00ffcc !important; width: 100% !important; font-weight: bold !important;
        transition: 0.3s;
    }
    .stButton > button:hover { background-color: #003322 !important; border-color: #ffffff !important; }
    .status-row { display: flex; align-items: center; margin-bottom: 6px; }
    .status-label { width: 100px; font-size: 0.75rem; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 14px; border: 1px solid #333; overflow: hidden; border-radius: 2px; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    .fill-enemy { background: #ff4b4b; height: 100%; }
    .log-box { background: #050505; padding: 10px; border: 1px solid #222; height: 100px; font-size: 0.8rem; overflow-y: auto; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 3. 接続・ブリーフィング ---
if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コードを入力", "7777")
    role = st.radio("役割を選択", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名を入力", "帝國")
    if st.button("サーバーへ接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 通信確立。システムオンライン。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield_count": 0, "p2_nuke_shield_count": 0,
                "neutral_owner": "none"
            }
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        sync(rid, {f"{role}_country": c_name})
        st.session_state.room_id, st.session_state.role = rid, role
        st.session_state.briefing = True
        st.rerun()

elif st.session_state.briefing:
    st.header("🪖 最終ブリーフィング")
    st.markdown("""
    - **勝利条件**: 敵の**本土HPを0**にすること。植民地は本土へのダメージを肩代わりします。
    - **中立地帯**: 占領中、毎ターン核ptが**+15自動増加**します。
    - **神風**: 本土20%以下で解放。植民地全損・本土HP90%消失の代償で、盾貫通の**400ダメージ**。
    - **核兵器**: 200ptで発動。全戦力を20%まで削減。対核盾で防御可能。
    """)
    if st.button("戦地へ展開する"):
        st.session_state.briefing = False
        st.rerun()

# --- 4. メインゲーム ---
else:
    data = get_game(st.session_state.room_id)
    if not data: st.warning("データを待機中..."); time.sleep(1); st.rerun()
    
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    my_name, enemy_name = data.get(f'{me}_country', '自国'), data.get(f'{opp}_country', '敵国')
    
    # 勝敗判定
    if data[f"{me}_hp"] <= 0: st.error(f"【 敗北 】 {my_name}の本土が陥落しました。"); st.stop()
    if data[f"{opp}_hp"] <= 0: st.success(f"【 勝利 】 {enemy_name}の本土を制圧しました！"); st.stop()

    # --- 敵軍インテリジェンス ---
    st.subheader(f"🚩 ENEMY: {enemy_name}")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">敵本土HP</div><div class="bar-bg"><div class="fill-enemy" style="width:{data[f'{opp}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">敵核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{data[f'{opp}_nuke']/2}%"></div></div></div>
    """, unsafe_allow_html=True)
    st.caption(f"🛡️ 通常盾: {data[f'{opp}_shield']} | ☢️ 対核盾: {data[f'{opp}_nuke_shield_count']} | 🌾 植民地: {data[f'{opp}_colony']:.0f}")

    st.divider()

    # --- 自軍ステータス ---
    n_owner = data.get('neutral_owner', 'none')
    n_disp = "🏳️ 中立地帯: 未占領" if n_owner == 'none' else (f"🏳️ 中立地帯: {my_name} 支配中" if n_owner == me else f"🏳️ 中立地帯: {enemy_name} 支配中")
    st.markdown(f"**{n_disp}**")
    
    st.subheader(f"🛡️ SELF: {my_name}")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">自軍本土HP</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{data[f'{me}_nuke']/2}%"></div></div></div>
    """, unsafe_allow_html=True)
    st.caption(f"🛡️ 通常盾: {data[f'{me}_shield']} | ☢️ 対核盾: {data[f'{me}_nuke_shield_count']}")

    # 作戦ログ
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-4:]])
    st.markdown(f'<div class="log-box">{logs}</div>', unsafe_allow_html=True)

    # アクション
    if data['turn'] == me:
        # 中立地帯ボーナス
        if n_owner == me and data['ap'] == 2:
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, data[f'{me}_nuke'] + 15)})

        st.markdown(f"**あなたのターン (残りAP: {data['ap']})**")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1: 
            if st.button("🛠️軍拡"):
                sync(st.session_state.room_id, {f"{me}_nuke": min(200, data[f'{me}_nuke']+40), "ap": data['ap']-1, "chat": data.get('chat', [])+[f"🛠️ {my_name}: 軍事拡張"]}); st.rerun()
        with c2: 
            if st.button("🛡️防衛"):
                if data[f'{me}_colony'] >= 20:
                    s1, s2 = (1 if random.random() < 0.25 else 0), (1 if random.random() < 0.066 else 0)
                    sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']-20, f"{me}_shield": data[f"{me}_shield"]+s1, f"{me}_nuke_shield_count": data[f"{me}_nuke_shield_count"]+s2, "ap": data['ap']-1, "chat": data.get('chat', [])+[f"🛡️ {my_name}: 防衛構築"]}); st.rerun()
                else: st.warning("植民地不足")
        with c3:
            if st.button("🕵️工作"):
                sn, ss = (random.random() < 0.5), (random.random() < 0.2)
                up = {"ap": data['ap']-1, "chat": data.get('chat', [])+[f"🕵️ {my_name}: 特殊工作"]}
                if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
                if ss: up[f"{opp}_nuke_shield_count"] = max(0, data[f"{opp}_nuke_shield_count"]-1)
                sync(st.session_state.room_id, up); st.rerun()
        with c4:
            target = st.radio("ターゲット", ["敵国", "中立地帯"], horizontal=True, label_visibility="collapsed")
            if st.button("⚔️進軍"):
                if target == "中立地帯":
                    sync(st.session_state.room_id, {"neutral_owner": me, "ap": data['ap']-1, "chat": data.get('chat', [])+[f"🏳️ {my_name}: 中立地帯制圧"]}); st.rerun()
                else:
                    if data[f"{opp}_shield"] > 0:
                        sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data.get('chat', [])+[f"🛡️ {enemy_name}: 防御に成功"]}); st.rerun()
                    else:
                        dmg = (45 + (data[f'{me}_nuke']*0.53)) + random.randint(-5, 5)
                        rem_col = data[f'{opp}_colony']
                        new_col = max(0, rem_col - dmg)
                        hp_dmg = max(0, dmg - rem_col) if dmg > rem_col else 0
                        sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f'{opp}_hp'] - hp_dmg), "ap": data['ap']-1, "chat": data.get('chat', [])+[f"⚔️ {my_name}: 本土攻撃"]}); st.rerun()
        with c5:
            if st.button("🚩占領"):
                rebel = random.random() < 0.33
                sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']+55, f"{me}_nuke": max(0, data[f'{me}_nuke']-(30 if rebel else 0)), "ap": data['ap']-1, "chat": data.get('chat', [])+[f"🚩 {my_name}: 植民地占領"]}); st.rerun()

        # 特殊攻撃ボタン
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if data[f"{me}_hp"] <= 200:
                if st.button("🏮 神風 (KAMIKAZE) 実行", type="primary"):
                    sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-400), f"{me}_colony": 0, f"{me}_hp": data[f"{me}_hp"]*0.1, "ap": 0, "chat": data.get('chat', [])+[f"🏮 {my_name}: 神風特攻！"]}); st.rerun()
        with col_s2:
            if data[f'{me}_nuke'] >= 200:
                if st.button("🚨 核兵器 投下", type="primary"):
                    if data[f"{opp}_nuke_shield_count"] > 0:
                        sync(st.session_state.room_id, {f"{opp}_nuke_shield_count": data[f"{opp}_nuke_shield_count"]-1, f"{me}_nuke": 0, "ap": 0, "chat": data.get('chat', [])+[f"☢️ {enemy_name}: 核を迎撃"]}); st.rerun()
                    else:
                        sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data.get('chat', [])+[f"☢️ {my_name}: 核爆発"]}); st.rerun()

        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.info(f"{enemy_name}の作戦行動を分析中...")
        time.sleep(4); st.rerun()

    # 暗号通信送信
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("暗号通信文", label_visibility="collapsed", placeholder="通信文を入力...")
        if st.form_submit_button("暗号送信"):
            c_data = get_game(st.session_state.room_id)
            sync(st.session_state.room_id, {"chat": c_data['chat'] + [f"💬 {my_name}: {msg}"]}); st.rerun()
