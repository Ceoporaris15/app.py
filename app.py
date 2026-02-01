import streamlit as st
from supabase import create_client
import time
import random

# --- 1. 接続・同期システム ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secretsの設定が正しくありません。")
    st.stop()

def get_game(rid):
    try:
        # キャッシュを介さず直接最新データを取りに行く
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except: return None

def sync(rid, updates):
    try:
        supabase.table("games").update(updates).eq("id", rid).execute()
    except Exception as e:
        st.error(f"同期失敗: {e}")

# --- 2. 漆黒のタクティカルUI ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #00ffcc !important;
        font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif;
    }
    /* ボタンデザイン：黒背景・緑枠・高反応 */
    .stButton > button { 
        background-color: #000000 !important; color: #00ffcc !important; 
        border: 2px solid #00ffcc !important; border-radius: 4px !important;
        height: 55px !important; width: 100% !important; font-weight: bold !important;
    }
    .stButton > button:hover { background-color: #002211 !important; border-color: #00ffcc !important; }
    
    .brief-container { border: 2px solid #00ffcc; padding: 20px; background: #050505; margin-bottom: 20px; }
    .action-box { border-left: 4px solid #00ffcc; padding-left: 15px; margin-bottom: 15px; background: #0a0a0a; padding-top: 5px; padding-bottom: 5px; }
    .prob-tag { color: #00ffcc; background: #003322; padding: 2px 8px; border-radius: 3px; font-weight: bold; border: 1px solid #00ffcc; }
    
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

# --- 3. 全アクション解説 (日本語) ---
if st.session_state.briefing:
    st.markdown('<div class="brief-container">', unsafe_allow_html=True)
    st.header("🪖 全アクション・ブリーフィング")
    
    actions = {
        "🛠️ 軍拡": "核開発ポイントを+40。ポイントが高いほど「進軍」の破壊力が上昇します。",
        "🛡️ 防衛": "<b>植民地を20消費</b>し、盾を抽選。通常盾(進軍阻止) <span class='prob-tag'>25%</span> / 対核盾(核阻止) <span class='prob-tag'>6.6%</span>",
        "🕵️ 工作": "スパイを派遣。敵の核ptを100減少 <span class='prob-tag'>50%</span> / 敵の対核盾を1つ破壊 <span class='prob-tag'>20%</span>",
        "⚔️ 進軍": "敵を攻撃。敵に「通常盾」がある場合は無効化され、盾を1枚消費させます。",
        "🚩 占領": "植民地を+55。ただし国内反乱で核ptが30減少するリスクあり <span class='prob-tag'>33%</span>",
        "🚨 核投下": "核pt 200で発動可能。敵の全戦力を現在の20%まで削る。対核盾で防御可能。"
    }
    
    for name, desc in actions.items():
        st.markdown(f'<div class="action-box"><b>{name}</b><br>{desc}</div>', unsafe_allow_html=True)
    
    if st.button("作戦開始"):
        st.session_state.briefing = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システムオンライン。"],
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

    # HUD
    st.write(f"**敵国: {enemy_name}** | 領土:{data[f'{opp}_hp']:.0f} 植民地:{data[f'{opp}_colony']:.0f}")
    
    # チャットログ (常に表示)
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-4:]])
    st.markdown(f"<div style='background:#050505; padding:10px; border:1px solid #333; height:90px; font-size:0.8rem;'>{logs}</div>", unsafe_allow_html=True)

    # ステータス
    st.markdown(f"**{my_name}** [通常盾:{data[f'{me}_shield']} / 対核盾:{data[f'{me}_nuke_shield_count']}]")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{data[f'{me}_nuke']/2}%"></div></div></div>
    """, unsafe_allow_html=True)

    # --- アクションエリア ---
    if data['turn'] == me:
        st.write(f"あなたのターン (行動残: {data['ap']})")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        if c1.button("🛠️軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, data[f'{me}_nuke']+40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍拡"]}); st.rerun()
            
        if c2.button("🛡️防衛"):
            if data[f'{me}_colony'] >= 20:
                s1 = 1 if random.random() < 0.25 else 0
                s2 = 1 if random.random() < 0.066 else 0
                sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']-20, f"{me}_shield": data[f'{me}_shield']+s1, f"{me}_nuke_shield_count": data[f'{me}_nuke_shield_count']+s2, "ap": data['ap']-1, "chat": data['chat']+[f"🛡️ {my_name}: 防衛構築"]}); st.rerun()
            else: st.warning("植民地不足")

        if c3.button("🕵️工作"):
            sn, ss = random.random() < 0.5, random.random() < 0.2
            up = {"ap": data['ap']-1, "chat": data['chat']+[f"🕵️ {my_name}: スパイ工作"]}
            if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: up[f"{opp}_nuke_shield_count"] = max(0, data[f"{opp}_nuke_shield_count"]-1)
            sync(st.session_state.room_id, up); st.rerun()

        if c4.button("⚔️進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が盾で防御"]}); st.rerun()
            else:
                dmg = (45 + (data[f'{me}_nuke']*0.53)) + random.randint(-5, 5)
                new_col = max(0, data[f'{opp}_colony']-dmg)
                hp_dmg = max(0, dmg - data[f'{opp}_colony']) if dmg > data[f'{opp}_colony'] else 0
                sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f'{opp}_hp']-hp_dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 進軍"]}); st.rerun()

        if c5.button("🚩占領"):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']+55, f"{me}_nuke": max(0, data[f'{me}_nuke']-(30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 占領"]}); st.rerun()

        if data[f'{me}_nuke'] >= 200:
            if st.button("🚨 核兵器投下", type="primary"):
                if data[f"{opp}_nuke_shield_count"] > 0:
                    sync(st.session_state.room_id, {f"{opp}_nuke_shield_count": data[f"{opp}_nuke_shield_count"]-1, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {enemy_name}が核を防御！"]}); st.rerun()
                else:
                    sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.2, f"{opp}_colony": data[f"{opp}_colony"]*0.2, f"{me}_nuke": 0, "ap": 0, "chat": data['chat']+[f"☢️ {my_name}の核が直撃！"]}); st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.info(f"{enemy_name}が作戦行動中...")
        time.sleep(4); st.rerun()

    # --- 通信システム (常時有効) ---
    st.divider()
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("通信文を入力", label_visibility="collapsed")
        if st.form_submit_button("暗号通信 送信"):
            if msg:
                # 送信の瞬間に最新ログを取得して結合
                current_data = get_game(st.session_state.room_id)
                sync(st.session_state.room_id, {"chat": current_data['chat'] + [f"💬 {my_name}: {msg}"]})
                st.rerun()
