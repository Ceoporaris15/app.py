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

# --- 2. UIデザイン (視認性重視・ノイズなし) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #ffffff !important;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }
    div[data-testid="stStatusWidget"] { display: none; }
    
    /* 説明画面用：見やすさ重視 */
    .brief-container {
        border: 2px solid #00ffcc; padding: 25px; border-radius: 10px;
        background: #0a0a0a; margin-bottom: 20px;
    }
    .brief-h1 { color: #00ffcc; font-size: 1.8rem; font-weight: bold; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #00ffcc; padding-bottom: 10px;}
    .brief-section { margin-bottom: 15px; padding: 10px; border-left: 4px solid #00ffcc; background: #111; }
    .prob-box {
        display: inline-block; background: #004433; color: #00ffcc; 
        padding: 2px 8px; border-radius: 4px; font-weight: bold; font-family: monospace;
    }
    .warning-text { color: #ff4b4b; font-weight: bold; }

    /* ゲーム画面HUD */
    .status-row { display: flex; align-items: center; margin-bottom: 5px; }
    .status-label { width: 80px; font-size: 0.8rem; color: #00ffcc; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 12px; border: 1px solid #333; border-radius: 6px; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }

    /* ボタン */
    button { height: 50px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. セッション管理 ---
if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 4. ブリーフィング画面 ---
if st.session_state.briefing:
    st.markdown("""
    <div class="brief-container">
        <div class="brief-h1">COMMAND BRIEFING</div>
        
        <div class="brief-section">
            <b>1. 勝利条件</b><br>
            敵の「領土」または「植民地」を <span class="warning-text">0</span> にすれば勝利。自軍が <span class="warning-text">0</span> になれば敗北。
        </div>

        <div class="brief-section">
            <b>2. 防衛システム (確率発生)</b><br>
            ・進軍を2回無効化：<span class="prob-box">確率 25%</span><br>
            ・核兵器を無効化：<span class="prob-box">確率 10%</span><br>
            <small>※失敗時はログに何も表示されず、植民地回復のみ行われます。</small>
        </div>

        <div class="brief-section">
            <b>3. スパイ工作 (確率発生)</b><br>
            ・敵の核ポイント-100：<span class="prob-box">確率 50%</span><br>
            ・敵の核シールド解除：<span class="prob-box">確率 20%</span>
        </div>

        <div class="brief-section">
            <b>4. 占領と反乱</b><br>
            ・反乱発生（核pt -30）：<span class="prob-box">確率 33%</span><br>
            <small>※占領自体は回数無制限で行えますが、常にリスクが伴います。</small>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("了解。作戦を開始する", use_container_width=True):
        st.session_state.briefing = False
        st.rerun()

# --- 5. 初期設定画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("アクセスコード", "7777")
    role = st.radio("役割を選択", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝國")
    if st.button("戦域へ展開 (DEPLOY)"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システムオンライン。"],
                "p1_shield": 0, "p2_shield": 0, "p1_nuke_shield": False, "p2_nuke_shield": False
            }
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        sync(rid, {f"{role}_country": c_name})
        st.session_state.room_id, st.session_state.role = rid, role
        st.session_state.briefing = True
        st.rerun()

# --- 6. ゲーム本編 ---
else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    my_name, enemy_name = data.get(f'{me}_country', '自国'), data.get(f'{opp}_country', '敵国')
    my_nuke = data.get(f'{me}_nuke', 0)

    # 勝敗ストーリー
    if data[f"{me}_colony"] <= 0 or data[f"{me}_hp"] <= 0:
        st.markdown(f'<div class="brief-container" style="border-color:#ff4b4b"><h2>敗北</h2><p>{my_name}の歴史はここで途絶えた。後世に残るのは沈黙のみである。</p></div>', unsafe_allow_html=True)
        if st.button("終了"): st.session_state.room_id = None; st.rerun()
        st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.markdown(f'<div class="brief-container"><h2>勝利</h2><p>{my_name}は頂点に立った。世界に新たな秩序が刻まれるだろう。</p></div>', unsafe_allow_html=True)
        if st.button("次へ"): st.session_state.room_id = None; st.rerun()
        st.stop()

    # ゲーム画面表示
    st.write(f"敵: {enemy_name} | 本土: {data[f'{opp}_hp']:.0f} | 植民地: {data[f'{opp}_colony']:.0f}")
    
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div style="background:#111; padding:5px; height:70px; font-size:0.8rem; border-left:2px solid #00ffcc; margin-bottom:10px;">{logs}</div>', unsafe_allow_html=True)

    current_atk = 45 + (my_nuke * 0.53)
    s_count = data.get(f'{me}_shield', 0)
    n_shield = "【対核防壁】" if data.get(f'{me}_nuke_shield') else ""
    
    st.markdown(f"""
    <div style="background:#0a0a0a; border:1px solid #333; padding:10px; border-radius:8px; margin-bottom:10px;">
        <div style="font-weight:bold; margin-bottom:5px;">{my_name} <span style="color:#3498db; font-size:0.8rem;">盾x{s_count} {n_shield}</span></div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    if data['turn'] == me:
        # アクションボタン
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠️\n軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍拡"]})
            st.rerun()
        if c2.button("🛡️\n防衛"):
            s_add = 2 if random.random() < 0.25 else 0
            ns = True if random.random() < 0.10 else data.get(f'{me}_nuke_shield', False)
            new_chat = data['chat'] + ([f"🛡️ {my_name}: 防衛成功"] if s_add or (ns and not data.get(f'{me}_nuke_shield')) else [])
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, f"{me}_shield": data[f"{me}_shield"]+s_add, f"{me}_nuke_shield": ns, "ap": data['ap']-1, "chat": new_chat})
            st.rerun()
        if c3.button("🕵️\n工作"):
            sn, ss = random.random() < 0.5, random.random() < 0.2
            updates = {"ap": data['ap']-1}
            if sn: updates[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: updates[f"{opp}_nuke_shield"] = False
            sync(st.session_state.room_id, {**updates, "chat": data['chat']+[f"🕵️ {my_name}: 潜入"]})
            st.rerun()
        if c4.button("⚔️\n進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が迎撃"]})
            else:
                dmg = current_atk + random.randint(-5, 5)
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 攻撃"]})
            st.rerun()
        if c5.button("🚩\n占領"):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 占領"]})
            st.rerun()
        
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning("待機中...")
        time.sleep(3); st.rerun()

    # チャット
    t_msg = st.text_input("", placeholder="通信...", label_visibility="collapsed")
    if st.button("SEND"):
        sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()
