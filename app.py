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
    st.error("Secretsの設定を確認してください。")
    st.stop()

def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try: supabase.table("games").update(updates).eq("id", rid).execute()
    except: pass

# --- 2. 漆黒のUIデザイン ---
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
    }
    .status-row { display: flex; align-items: center; margin-bottom: 8px; }
    .status-label { width: 85px; font-size: 0.8rem; }
    .bar-bg { background: #111; width: 100%; height: 12px; border: 1px solid #333; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 3. アクション解説 ---
if st.session_state.briefing:
    st.markdown("### 🪖 最終決戦・勝利条件の変更")
    st.info("勝利条件：敵の本土HPを0にすること（植民地が0になっても敗北にはなりませんが、防衛ができなくなります）")
    if st.button("戦場へ展開"):
        st.session_state.briefing = False
        st.rerun()

# --- 4. 接続画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝國")
    if st.button("接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システムオンライン。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield_count": 0, "p2_nuke_shield_count": 0,
                "neutral_owner": "none"
            }
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        sync(rid, {f"{role}_country": c_name})
        st.session_state.room_id, st.session_state.role = rid, role
        st.session_state.briefing = True
        st.rerun()

# --- 5. ゲーム本編 ---
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    my_name, enemy_name = data.get(f'{me}_country', '自国'), data.get(f'{opp}_country', '敵国')
    my_nuke, my_colony = data.get(f'{me}_nuke', 0), data.get(f'{me}_colony', 0)

    # --- 修正された勝利判定 ---
    if data[f"{me}_hp"] <= 0:
         st.error(f"【 敗北 】 {my_name}の本土が陥落しました。"); st.stop()
    if data[f"{opp}_hp"] <= 0:
        st.success(f"【 勝利 】 {enemy_name}の本土を完全制圧しました！"); st.stop()

    # 表示
    n_owner = data.get('neutral_owner', 'none')
    n_text = "未占領" if n_owner == 'none' else (my_name if n_owner == me else enemy_name)
    st.write(f"🏳️ **中立支配:** {n_text} | ⚔️ **敵国 {enemy_name}:** 領土 {data[f'{opp}_hp']:.0f} / 植民地 {data[f'{opp}_colony']:.0f}")
    
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f"<div style='background:#050505; padding:8px; border:1px solid #333; height:80px; font-size:0.8rem;'>{logs}</div>", unsafe_allow_html=True)

    st.markdown(f"**{my_name}** [通常盾:{data[f'{me}_shield']} / 対核盾:{data[f'{me}_nuke_shield_count']}]")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{my_colony}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    """, unsafe_allow_html=True)

    if data['turn'] == me:
        if n_owner == me and data['ap'] == 2:
            my_nuke = min(200, my_nuke + 15)
            sync(st.session_state.room_id, {f"{me}_nuke": my_nuke})

        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1: 
            if st.button("🛠️軍拡"):
                sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke+40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍拡"]}); st.rerun()
            
        with c2: 
            if st.button("🛡️防衛"):
                if my_colony >= 20:
                    s1, s2 = (1 if random.random() < 0.25 else 0), (1 if random.random() < 0.066 else 0)
                    sync(st.session_state.room_id, {f"{me}_colony": my_colony-20, f"{me}_shield": data[f"{me}_shield"]+s1, f"{me}_nuke_shield_count": data[f"{me}_nuke_shield_count"]+s2, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {my_name}: 防衛構築"]}); st.rerun()
                else: st.warning("植民地不足（防衛不可）")

        with c3:
            if st.button("🕵️工作"):
                sn, ss = (random.random() < 0.5), (random.random() < 0.2)
                up = {"ap": data['ap']-1, "chat": data['chat']+[f"🕵️ {my_name}: 工作員派遣"]}
                if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
                if ss: up[f"{opp}_nuke_shield_count"] = max(0, data[f"{opp}_nuke_shield_count"]-1)
                sync(st.session_state.room_id, up); st.rerun()

        with c4:
            target = st.radio("攻撃先", ["敵国", "中立地帯"], horizontal=True, label_visibility="collapsed")
            if st.button("⚔️進軍"):
                if target == "中立地帯":
                    sync(st.session_state.room_id, {"neutral_owner": me, "ap": data['ap']-1, "chat": data['chat']+[f"🏳️ {my_name}: 中立地帯を支配"]}); st.rerun()
                else:
                    if data[f"{opp}_shield"] > 0:
                        sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {enemy_name}: 盾で防御"]}); st.rerun()
                    else:
                        dmg = (45 + (my_nuke*0.53)) + random.randint(-5, 5)
                        new_col = max(0, data[f'{opp}_colony'] - dmg)
                        # 植民地を削りきった分だけ本土HPにダメージ
                        hp_dmg = max(0, dmg - data[f'{opp}_colony']) if dmg > data[f'{opp}_colony'] else 0
                        sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f'{opp}_hp'] - hp_dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 進撃"]}); st.rerun()

        with c5:
            if st.button("🚩占領"):
                rebel = random.random() < 0.33
                sync(st.session_state.room_id, {f"{me}_colony": my_colony+55, f"{me}_nuke": max(0, my_nuke-(30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 占領"]}); st.rerun()

        # 神風 & 核
        if data[f"{me}_hp"] <= 200:
            if st.button("🏮 神風 (KAMIKAZE) 実行", type="primary"):
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-400), f"{me}_colony": 0, f"{me}_hp": data[f"{me}_hp"]*0.1, "ap": 0, "chat": data['chat']+[f"🏮 {my_name}: 神風特攻！"]}); st.rerun()

        if my_nuke >= 200:
            if st.button("🚨 核兵器投下", type="primary"):
                if data[f"{opp}_nuke_shield_count"] > 0:
                    sync(st.session_state.room_id, {f"{opp}_nuke_shield_count": data[f"{opp}_nuke_shield_count"]-1, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {enemy_name}: 核を迎撃"]}); st.rerun()
                else:
                    sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {my_name}: 核爆発"]}); st.rerun()

        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.info("敵国のターンです...")
        time.sleep(4); st.rerun()

    with st.form("chat", clear_on_submit=True):
        msg = st.text_input("暗号通信文", label_visibility="collapsed")
        if st.form_submit_button("送信"):
            c_data = get_game(st.session_state.room_id)
            sync(st.session_state.room_id, {"chat": c_data['chat'] + [f"💬 {my_name}: {msg}"]}); st.rerun()
