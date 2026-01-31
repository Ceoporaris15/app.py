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

# --- 2. 漆黒のUIデザイン ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 全体背景とテキスト */
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #00ffcc !important;
        font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif;
    }
    div[data-testid="stStatusWidget"] { display: none; }
    
    /* 説明画面：日本語で見やすく */
    .brief-container {
        border: 2px solid #00ffcc; padding: 20px; border-radius: 5px;
        background: #050505; margin-bottom: 20px;
    }
    .brief-h1 { color: #00ffcc; font-size: 1.5rem; font-weight: bold; border-bottom: 1px solid #00ffcc; padding-bottom: 10px; margin-bottom: 20px;}
    .brief-section { margin-bottom: 15px; padding-left: 10px; border-left: 3px solid #00ffcc; }
    .prob-tag {
        background: #003322; color: #00ffcc; padding: 2px 6px; 
        border: 1px solid #00ffcc; border-radius: 3px; font-weight: bold;
    }

    /* ボタン：白くならないように黒背景+緑枠 */
    .stButton > button {
        background-color: #000000 !important;
        color: #00ffcc !important;
        border: 1px solid #00ffcc !important;
        border-radius: 4px !important;
        height: 50px !important;
        width: 100% !important;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #003322 !important;
        border-color: #00ffcc !important;
    }
    
    /* 入力フォームの色調整 */
    input { background-color: #111 !important; color: #00ffcc !important; border: 1px solid #333 !important; }
    
    /* ステータスバー */
    .status-row { display: flex; align-items: center; margin-bottom: 8px; }
    .status-label { width: 85px; font-size: 0.8rem; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 12px; border: 1px solid #00ffcc; border-radius: 2px; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. セッション管理 ---
if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 4. 説明画面（日本語・確率明記） ---
if st.session_state.briefing:
    st.markdown("""
    <div class="brief-container">
        <div class="brief-h1">【 作戦説明書 】</div>
        
        <div class="brief-section">
            <b>■ 勝利条件</b><br>
            敵国の「領土」または「植民地」を<b>0</b>にすれば勝利となります。自国のいずれかが<b>0</b>になった場合は即座に敗北です。
        </div>

        <div class="brief-section">
            <b>■ 防衛プロトコル (確率発生)</b><br>
            「防衛」実行時、以下の効果が抽選されます。<br>
            ・敵の進軍を2回無効化：<span class="prob-tag">25%</span><br>
            ・敵の核兵器を無効化：<span class="prob-tag">10%</span>
        </div>

        <div class="brief-section">
            <b>■ スパイ工作 (確率発生)</b><br>
            ・敵の核ポイントを100減少：<span class="prob-tag">50%</span><br>
            ・敵の核防壁を強制解除：<span class="prob-tag">20%</span>
        </div>

        <div class="brief-section">
            <b>■ 占領のリスク</b><br>
            「占領」は植民地を大きく増やしますが、リスクがあります。<br>
            ・国内反乱（核開発pt -30）：<span class="prob-tag">33%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("全内容を理解し、戦地へ赴く"):
        st.session_state.briefing = False
        st.rerun()

# --- 5. 初期設定画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コードを入力", "7777")
    role = st.radio("役割を選択", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("あなたの国名", "帝國")
    if st.button("作戦サーバーに接続"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 通信接続完了。"],
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

    # 勝敗
    if data[f"{me}_colony"] <= 0 or data[f"{me}_hp"] <= 0:
        st.error(f"【 敗北 】 {my_name}は滅亡しました。"); st.stop()
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.success(f"【 勝利 】 {enemy_name}の制圧を完了しました。"); st.stop()

    # 敵情報
    st.markdown(f"**敵国: {enemy_name}** | 本土: {data[f'{opp}_hp']:.0f} | 植民地: {data[f'{opp}_colony']:.0f}")
    
    # ログ
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div style="background:#050505; padding:8px; height:80px; font-size:0.85rem; border:1px solid #333; margin-bottom:10px;">{logs}</div>', unsafe_allow_html=True)

    # 自軍ステータス
    current_atk = 45 + (my_nuke * 0.53)
    s_count = data.get(f'{me}_shield', 0)
    n_shield = "【対核防壁】" if data.get(f'{me}_nuke_shield') else ""
    
    st.markdown(f"""
    <div style="background:#050505; border:1px solid #00ffcc; padding:12px; border-radius:5px; margin-bottom:15px;">
        <div style="font-weight:bold; margin-bottom:8px;">{my_name} <span style="color:#3498db;">(盾: {s_count} {n_shield})</span></div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    if data['turn'] == me:
        st.write(f"あなたのターン (行動可能回数: {data['ap']})")
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠️軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}：兵器開発"]})
            st.rerun()
        if c2.button("🛡️防衛"):
            s_add = 2 if random.random() < 0.25 else 0
            ns = True if random.random() < 0.10 else data.get(f'{me}_nuke_shield', False)
            chat = data['chat'] + ([f"🛡️ {my_name}：防衛成功"] if s_add or (ns and not data.get(f'{me}_nuke_shield')) else [])
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, f"{me}_shield": data[f"{me}_shield"]+s_add, f"{me}_nuke_shield": ns, "ap": data['ap']-1, "chat": chat})
            st.rerun()
        if c3.button("🕵️工作"):
            sn, ss = random.random() < 0.5, random.random() < 0.2
            up = {"ap": data['ap']-1}
            if sn: up[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: up[f"{opp}_nuke_shield"] = False
            sync(st.session_state.room_id, {**up, "chat": data['chat']+[f"🕵️ {my_name}：工作員派遣"]})
            st.rerun()
        if c4.button("⚔️進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が防衛"]})
            else:
                dmg = current_atk + random.randint(-5, 5)
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}：総攻撃"]})
            st.rerun()
        if c5.button("🚩占領"):
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}：領土拡大"]})
            st.rerun()
        
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning(f"{enemy_name}の行動を待機中...")
        time.sleep(3); st.rerun()

    # チャット送信
    t_msg = st.text_input("", placeholder="通信文を入力...", label_visibility="collapsed")
    if st.button("通信を送信"):
        sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()
