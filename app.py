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
    st.error("接続エラー。Secretsを確認してください。")
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
st.set_page_config(page_title="DEUS ONLINE", layout="centered")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #00ffcc !important;
        font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif;
    }
    div[data-testid="stStatusWidget"] { display: none; }
    .brief-container { border: 2px solid #00ffcc; padding: 25px; background: #050505; border-radius: 5px; line-height: 1.6; }
    .brief-h1 { color: #00ffcc; font-size: 1.6rem; font-weight: bold; border-bottom: 2px solid #00ffcc; padding-bottom: 10px; margin-bottom: 20px; text-align: center;}
    .brief-section { margin-bottom: 15px; padding: 12px; border: 1px solid #333; background: #0a0a0a; }
    .prob-tag { background: #003322; color: #00ffcc; padding: 2px 8px; border: 1px solid #00ffcc; border-radius: 3px; font-weight: bold; }
    
    .stButton > button { 
        background-color: #000000 !important; color: #00ffcc !important; 
        border: 1px solid #00ffcc !important; border-radius: 4px !important;
    }
    .status-row { display: flex; align-items: center; margin-bottom: 8px; }
    .status-label { width: 85px; font-size: 0.8rem; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 12px; border: 1px solid #00ffcc; border-radius: 2px; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 3. 全アクション解説画面 ---
if st.session_state.briefing:
    st.markdown("""
    <div class="brief-container">
        <div class="brief-h1">【 全軍事アクション解説 】</div>
        
        <div class="brief-section">
            <b>🛠️ 軍拡</b><br>
            核開発ポイントを<b>+40</b>します。この値が高いほど、後述の「進軍」ダメージが増加します。
        </div>

        <div class="brief-section">
            <b style="color:#ff4b4b;">🛡️ 防衛（重要）</b><br>
            <b>植民地を20消費</b>して、2種類の独立した盾を構築します。<br>
            ・<b>通常盾</b>：敵の進軍を1回阻止 <span class="prob-tag">1/4 (25%)</span><br>
            ・<b>対核盾</b>：敵の核攻撃を1回阻止 <span class="prob-tag">1/15 (約6.6%)</span>
        </div>

        <div class="brief-section">
            <b>🕵️ 工作</b><br>
            敵の軍事設備を妨害します。<br>
            ・<b>核妨害</b>：敵の核ポイント-100 <span class="prob-tag">1/2 (50%)</span><br>
            ・<b>盾破壊</b>：敵の「対核盾」を1つ破壊 <span class="prob-tag">1/5 (20%)</span>
        </div>

        <div class="brief-section">
            <b>⚔️ 進軍</b><br>
            敵の植民地（または領土）を攻撃します。敵に「通常盾」がある場合は、ダメージを無効化され盾を1枚消費させます。
        </div>

        <div class="brief-section">
            <b>🚩 占領</b><br>
            植民地を<b>+55</b>増加させます。防衛に必要な植民地はここから調達してください。<br>
            ・<b>国内反乱</b>：核ポイント-30 <span class="prob-tag">1/3 (33%)</span>
        </div>

        <div class="brief-section">
            <b>🚨 核兵器投下</b><br>
            核ポイント200で解放。敵の本土・植民地を<b>現在の20%</b>まで破壊します。敵に「対核盾」がある場合は無効化されます。
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("全アクションを理解した"):
        st.session_state.briefing = False
        st.rerun()

# --- 4. 接続画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("あなたの国名", "帝國")
    if st.button("接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 通信オンライン。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield_count": 0, "p2_nuke_shield_count": 0
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

    # 勝敗
    if my_colony <= 0 or data[f"{me}_hp"] <= 0:
        st.error(f"【 敗北 】 {my_name}の歴史は終了しました。"); st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.success(f"【 勝利 】 {enemy_name}を制圧しました。"); st.stop()

    # HUD
    st.write(f"敵: {enemy_name} | 本土: {data[f'{opp}_hp']:.0f} | 植民地: {data[f'{opp}_colony']:.0f}")
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div style="background:#050505; padding:8px; height:80px; font-size:0.85rem; border:1px solid #333; margin-bottom:10px;">{logs}</div>', unsafe_allow_html=True)

    # ステータス
    st.markdown(f"""
    <div style="background:#050505; border:1px solid #00ffcc; padding:12px; border-radius:5px; margin-bottom:15px;">
        <div style="font-weight:bold; margin-bottom:8px;">{my_name} 
            <span style="color:#3498db; font-size:0.75rem;"> [通常盾:{data[f'{me}_shield']}]</span> 
            <span style="color:#9b59b6; font-size:0.75rem;"> [対核盾:{data[f'{me}_nuke_shield_count']}]</span>
        </div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{my_colony}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    # アクション（自分のターンのみ）
    if data['turn'] == me:
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠️軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍事力強化"]}); st.rerun()
        if c2.button("🛡️防衛"):
            if my_colony >= 20:
                n_add = 1 if random.random() < 0.25 else 0
                nk_add = 1 if random.random() < (1/15) else 0
                sync(st.session_state.room_id, {f"{me}_colony": my_colony-20, f"{me}_shield": data[f"{me}_shield"]+n_add, f"{me}_nuke_shield_count": data[f"{me}_nuke_shield_count"]+nk_add, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {my_name}: 防衛体制構築"]}); st.rerun()
        if c3.button("🕵️工作"):
            sn, ss = random.random() < 0.5, random.random() < 0.2
            up = {"ap": data['ap']-1}
            if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: up[f"{opp}_nuke_shield_count"] = max(0, data[f"{opp}_nuke_shield_count"]-1)
            sync(st.session_state.room_id, {**up, "chat": data['chat']+[f"🕵️ {my_name}: スパイ工作"]}); st.rerun()
        if c4.button("⚔️進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が盾を使用"]}); st.rerun()
            else:
                dmg = (45 + (my_nuke * 0.53)) + random.randint(-5, 5)
                new_col = max(0, data[f"{opp}_colony"] - dmg)
                hp_dmg = max(0, dmg - data[f"{opp}_colony"]) if dmg > data[f"{opp}_colony"] else 0
                sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f"{opp}_hp"]-hp_dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 強襲"]}); st.rerun()
        if c5.button("🚩占領"):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": my_colony+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 領土拡大"]}); st.rerun()

        if my_nuke >= 200:
            if st.button("🚨 核兵器投下", type="primary"):
                if data[f"{opp}_nuke_shield_count"] > 0:
                    sync(st.session_state.room_id, {f"{opp}_nuke_shield_count": data[f"{opp}_nuke_shield_count"]-1, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {enemy_name}が核を迎撃"]}); st.rerun()
                else:
                    sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {my_name}の核が直撃"]}); st.rerun()
        
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning(f"{enemy_name}のターンです...")
        time.sleep(3); st.rerun()

    # --- 共通チャット機能 (ターンの制約なし) ---
    st.divider()
    with st.container():
        t_msg = st.text_input("通信メッセージ", key="chat_input", placeholder="暗号通信文を入力...", label_visibility="collapsed")
        if st.button("送信"):
            if t_msg:
                # 常に最新のデータを取得して更新（上書き防止）
                current_data = get_game(st.session_state.room_id)
                sync(st.session_state.room_id, {"chat": current_data['chat'] + [f"💬 {my_name}: {t_msg}"]})
                st.rerun()
