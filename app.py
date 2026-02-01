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
    .brief-container { border: 2px solid #00ffcc; padding: 20px; background: #050505; margin-bottom: 20px; }
    .action-box { border-left: 4px solid #00ffcc; padding-left: 15px; margin-bottom: 12px; background: #0a0a0a; }
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
    st.markdown('<div class="brief-container">', unsafe_allow_html=True)
    st.header("🪖 最終決戦・タクティカルガイド")
    st.markdown("""
    - **⚔️ 進軍(選択式)**: 敵への直接攻撃か、中立地帯の制圧かを選べます。
    - **🏳️ 中立地帯**: 占領中、ターン開始時に**核ptが+15**されます。
    - **🏮 神風**: 領土20%以下で解放。植民地全喪失＋領土90%消失で敵に**固定400ダメージ**。
    - **🚨 核兵器**: 核pt 200で解放。敵の全戦力を現在の20%まで破壊。
    """)
    if st.button("全戦術を了解した"):
        st.session_state.briefing = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 4. 接続画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE: FINAL")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝國")
    if st.button("サーバー接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 最終プロトコル展開。"],
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

    # 敗北判定
    if my_colony <= 0 and data[f"{me}_hp"] <= 10:
         st.error(f"【 滅亡 】 {my_name}は沈みました。"); st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.success(f"【 勝利 】 {enemy_name}を制圧。"); st.stop()

    # ステータス表示
    n_owner = data.get('neutral_owner', 'none')
    n_text = "未占領" if n_owner == 'none' else (my_name if n_owner == me else enemy_name)
    st.write(f"🏳️ **中立地帯支配:** {n_text}")
    st.write(f"⚔️ **敵国 {enemy_name}:** 領土 {data[f'{opp}_hp']:.0f} / 植民地 {data[f'{opp}_colony']:.0f}")
    
    # ログ
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f"<div style='background:#050505; padding:8px; border:1px solid #333; height:80px; font-size:0.8rem;'>{logs}</div>", unsafe_allow_html=True)

    # 自軍
    st.markdown(f"**{my_name}** [通常盾:{data[f'{me}_shield']} / 対核盾:{data[f'{me}_nuke_shield_count']}]")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{my_colony}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    """, unsafe_allow_html=True)

    if data['turn'] == me:
        # ターン開始ボーナス
        if n_owner == me and data['ap'] == 2:
            my_nuke = min(200, my_nuke + 15)
            sync(st.session_state.room_id, {f"{me}_nuke": my_nuke})

        st.subheader("フェーズ選択")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1: st.button("🛠️軍拡", on_click=sync, args=(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke+40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍拡"]} ))
            
        with c2: 
            if st.button("🛡️防衛"):
                if my_colony >= 20:
                    s1, s2 = (1 if random.random() < 0.25 else 0), (1 if random.random() < 0.066 else 0)
                    sync(st.session_state.room_id, {f"{me}_colony": my_colony-20, f"{me}_shield": data[f"{me}_shield"]+s1, f"{me}_nuke_shield_count": data[f"{me}_nuke_shield_count"]+s2, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {my_name}: 防衛構築"]})
                    st.rerun()

        with c3:
            if st.button("🕵️工作"):
                sn, ss = (random.random() < 0.5), (random.random() < 0.2)
                up = {"ap": data['ap']-1, "chat": data['chat']+[f"🕵️ {my_name}: 工作"]}
                if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
                if ss: up[f"{opp}_nuke_shield_count"] = max(0, data[f"{opp}_nuke_shield_count"]-1)
                sync(st.session_state.room_id, up); st.rerun()

        with c4:
            # 進軍ターゲットの選択
            target = st.radio("進軍先", ["敵国", "中立地帯"], horizontal=True, label_visibility="collapsed")
            if st.button("⚔️進軍開始"):
                if target == "中立地帯":
                    if n_owner == me: st.info("既に占領済みです")
                    else:
                        sync(st.session_state.room_id, {"neutral_owner": me, "ap": data['ap']-1, "chat": data['chat']+[f"🏳️ {my_name}: 中立地帯を制圧"]})
                        st.rerun()
                else: # 敵国攻撃
                    if data[f"{opp}_shield"] > 0:
                        sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が盾を使用"]}); st.rerun()
                    else:
                        dmg = (45 + (my_nuke*0.53)) + random.randint(-5, 5)
                        new_col = max(0, data[f'{opp}_colony']-dmg)
                        hp_dmg = max(0, dmg - data[f'{opp}_colony']) if dmg > data[f'{opp}_colony'] else 0
                        sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f'{opp}_hp']-hp_dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 本土攻撃"]}); st.rerun()

        with c5:
            if st.button("🚩占領"):
                rebel = random.random() < 0.33
                sync(st.session_state.room_id, {f"{me}_colony": my_colony+55, f"{me}_nuke": max(0, my_nuke-(30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 植民地拡大"]}); st.rerun()

        # 神風 & 核
        if data[f"{me}_hp"] <= 200:
            if st.button("🏮 神風 (KAMIKAZE) 実行", type="primary"):
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-400), f"{me}_colony": 0, f"{me}_hp": data[f"{me}_hp"]*0.1, "ap": 0, "chat": data['chat']+[f"🏮 {my_name}: 神風特攻！"]}); st.rerun()

        if my_nuke >= 200:
            if st.button("🚨 核兵器投下", type="primary"):
                if data[f"{opp}_nuke_shield_count"] > 0:
                    sync(st.session_state.room_id, {f"{opp}_nuke_shield_count": data[f"{opp}_nuke_shield_count"]-1, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {enemy_name}が核を防御"]}); st.rerun()
                else:
                    sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {my_name}の核が直撃"]}); st.rerun()

        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.info("敵国の作戦行動を待機しています...")
        time.sleep(4); st.rerun()

    # チャット
    with st.form("chat", clear_on_submit=True):
        msg = st.text_input("通信文", label_visibility="collapsed")
        if st.form_submit_button("送信"):
            c_data = get_game(st.session_state.room_id)
            sync(st.session_state.room_id, {"chat": c_data['chat'] + [f"💬 {my_name}: {msg}"]}); st.rerun()
