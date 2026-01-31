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
    .brief-container { border: 2px solid #00ffcc; padding: 25px; background: #050505; border-radius: 5px; }
    .brief-h1 { color: #00ffcc; font-size: 1.6rem; font-weight: bold; border-bottom: 2px solid #00ffcc; padding-bottom: 10px; margin-bottom: 20px; text-align: center;}
    .brief-section { margin-bottom: 15px; padding: 12px; border: 1px solid #333; background: #0a0a0a; }
    .prob-tag { background: #003322; color: #00ffcc; padding: 2px 8px; border: 1px solid #00ffcc; border-radius: 3px; font-weight: bold; }
    .stButton > button { background-color: #000000 !important; color: #00ffcc !important; border: 1px solid #00ffcc !important; }
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

# --- 3. 説明画面（再構築版） ---
if st.session_state.briefing:
    st.markdown("""
    <div class="brief-container">
        <div class="brief-h1">【 再構築・防衛プロトコル 】</div>
        
        <div class="brief-section">
            <b style="color:#ff4b4b;">🛡️ 防衛（植民地消費型）</b><br>
            実行には<b>植民地を20消費</b>する必要があります。消費後、以下の確率で防壁を展開します。<br>
            ・<b>進軍迎撃</b>：敵の進軍を2回無効化 <span class="prob-tag">25% (4分の1)</span><br>
            ・<b>対核防壁</b>：敵の核攻撃を1回無効化 <span class="prob-tag">10% (10分の1)</span><br>
            <small>※抽選に失敗した場合、植民地20が失われるだけとなります。</small>
        </div>

        <div class="brief-section">
            <b>⚔️ 進軍</b><br>
            敵の「盾」がある場合はそれを1つ破壊します。盾がない場合は、核開発状況に応じたダメージを敵の領土または植民地に与えます。
        </div>

        <div class="brief-section">
            <b>🚩 占領</b><br>
            植民地を<b>+55</b>増加させます。防衛に必要なリソースはここから確保してください。<br>
            ・<b>国内反乱</b>：核開発ポイント -30 <span class="prob-tag">33%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("新システムを承認し、戦地へ向かう"):
        st.session_state.briefing = False
        st.rerun()

# --- 4. 接続画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE: REBOOT")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝國")
    if st.button("接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システム再構築完了。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield": False, "p2_nuke_shield": False
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
    my_nuke = data.get(f'{me}_nuke', 0)
    my_colony = data.get(f'{me}_colony', 0)

    # 勝敗判定
    if my_colony <= 0 or data[f"{me}_hp"] <= 0:
        st.error(f"【 敗北 】 {my_name}は陥落しました。"); st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.success(f"【 勝利 】 {enemy_name}の制圧に成功。"); st.stop()

    # 表示
    st.markdown(f"**敵国: {enemy_name}** | 本土: {data[f'{opp}_hp']:.0f} | 植民地: {data[f'{opp}_colony']:.0f}")
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div style="background:#050505; padding:8px; height:80px; font-size:0.85rem; border:1px solid #333; margin-bottom:10px;">{logs}</div>', unsafe_allow_html=True)

    # ステータス
    current_atk = 45 + (my_nuke * 0.53)
    s_count = data.get(f'{me}_shield', 0)
    n_shield = "【対核防壁】" if data.get(f'{me}_nuke_shield') else ""
    st.markdown(f"""
    <div style="background:#050505; border:1px solid #00ffcc; padding:12px; border-radius:5px; margin-bottom:15px;">
        <div style="font-weight:bold; margin-bottom:8px;">{my_name} <span style="color:#3498db;">(迎撃盾: {s_count} {n_shield})</span></div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{my_colony}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    if data['turn'] == me:
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠️軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 兵器強化"]})
            st.rerun()
            
        if c2.button("🛡️防衛"):
            if my_colony < 20:
                st.warning("植民地が不足しています（20必要）")
            else:
                # 植民地20を即座に消費
                new_colony = my_colony - 20
                # 抽選：1/4(25%)で盾+2、1/10(10%)で対核
                s_add = 2 if random.random() < 0.25 else 0
                ns_now = data.get(f'{me}_nuke_shield', False)
                ns_new = True if random.random() < 0.10 else ns_now
                
                success_msg = []
                if s_add: success_msg.append("迎撃盾展開")
                if ns_new and not ns_now: success_msg.append("核防壁展開")
                
                msg = f"🛡️ {my_name}: 防衛（植民地-20）"
                if success_msg: msg += f" → {'・'.join(success_msg)}成功"
                
                sync(st.session_state.room_id, {
                    f"{me}_colony": new_colony,
                    f"{me}_shield": data[f"{me}_shield"] + s_add,
                    f"{me}_nuke_shield": ns_new,
                    "ap": data['ap']-1,
                    "chat": data['chat'] + [msg]
                })
                st.rerun()

        if c3.button("🕵️工作"):
            sn, ss = random.random() < 0.5, random.random() < 0.2
            up = {"ap": data['ap']-1}
            if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: up[f"{opp}_nuke_shield"] = False
            sync(st.session_state.room_id, {**up, "chat": data['chat']+[f"🕵️ {my_name}: 潜入工作"]})
            st.rerun()

        if c4.button("⚔️進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が盾で迎撃"]})
            else:
                dmg = current_atk + random.randint(-5, 5)
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 爆撃"]})
            st.rerun()

        if c5.button("🚩占領"):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": my_colony+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 占領拡大"]})
            st.rerun()
        
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning("待機中...")
        time.sleep(3); st.rerun()

    t_msg = st.text_input("", placeholder="暗号通信...", label_visibility="collapsed")
    if st.button("送信"):
        sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()
