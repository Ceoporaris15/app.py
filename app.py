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

# --- 2. 漆黒・非明滅UI (1画面・スクロール/暗転封殺) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 【最重要】画面更新時の「暗転マスク」を完全透明化して消去 */
    div[data-testid="stStatusWidget"], 
    div[data-testid="stAppViewBlockContainer"] > div:first-child { 
        visibility: hidden !important; display: none !important; opacity: 0 !important;
    }

    /* 背景固定・スクロール禁止 */
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important;
        color: #ffffff !important;
        overflow: hidden !important;
        height: 100vh;
    }

    /* 敵軍情報（上部・相手設定の名前を表示） */
    .enemy-mini-hud {
        background: #0a0a0a; border: 1px solid #441111;
        padding: 5px; margin-bottom: 5px; border-radius: 4px;
        display: flex; justify-content: space-around; font-size: 0.6rem;
    }
    .enemy-val { color: #ff4b4b; font-weight: bold; }

    /* 実況ログ */
    .live-log {
        background: #080808; border-left: 2px solid #00ffcc;
        padding: 5px; margin-bottom: 5px; font-family: monospace;
        font-size: 0.75rem; color: #00ffcc; height: 60px; overflow-y: auto;
    }
    .dmg-text { color: #ff4b4b; font-weight: bold; }

    /* 自軍情報（中央・大きく表示） */
    .self-hud {
        background: #050505; border: 1px solid #d4af37;
        padding: 8px; margin-bottom: 8px; border-radius: 8px;
    }
    .bar-bg { background: #111; width: 100%; height: 10px; border-radius: 5px; margin: 4px 0; border: 1px solid #222; overflow: hidden; }
    .fill-hp { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .fill-sh { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .fill-nk { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }

    /* ボタン */
    button {
        background-color: #111 !important; color: #d4af37 !important;
        border: 1px solid #d4af37 !important; height: 48px !important;
        font-size: 0.7rem !important; transition: none !important;
        padding: 0px !important;
    }
    button:active { background-color: #333 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. メインシステム ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

if not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("あなたの国名", "帝国")
    c_cap = st.text_input("首都名", "第一枢軸")
    f_select = st.selectbox("軍事陣営", ["連合国", "枢軸國", "社会主義国"])

    if st.button("戦域接続 (DEPLOY)"):
        # 初期化（P1がリセット、P2は既存データ読み込み）
        current_data = get_game(rid)
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0,
                "p1_nuke": 0.0, "p2_nuke": 0.0, "p1_mil": 0.0, "p2_mil": 0.0, 
                "p1_country": c_name, "p2_country": "待機中...", # 初期化時に自分の名前を登録
                "turn": "p1", "ap": 2, "chat": ["🛰️ 通信確立。戦域をスキャン中..."]
            }
            supabase.table("games").delete().eq("id", rid).execute()
            supabase.table("games").insert(init_data).execute()
        else:
            # P2として参加する場合、自分の国名を更新
            sync(rid, {f"{role}_country": c_name, f"{role}_capital": c_cap, f"{role}_faction": f_select})
        
        # 共通の初期登録（首都・陣営など）
        sync(rid, {f"{role}_capital": c_cap, f"{role}_faction": f_select, f"{role}_country": c_name})
        st.session_state.room_id, st.session_state.role = rid, role
        st.rerun()

else:
    data = get_game(st.session_state.room_id)
    if not data: st.rerun()
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")

    # 動的な名前の取得
    my_name = data.get(f'{me}_country', '自国')
    enemy_name = data.get(f'{opp}_country', '不明な敵国')

    # --- 1. 敵軍情報（相手が決めた国名を表示） ---
    st.markdown(f"""
    <div class="enemy-mini-hud">
        <div>敵国: <span class="enemy-val">{enemy_name}</span></div>
        <div>本土: <span class="enemy-val">{data.get(f'{opp}_hp',0):.0f}</span></div>
        <div>占領地: <span class="enemy-val">{data.get(f'{opp}_colony',0):.0f}</span></div>
        <div>核: <span class="enemy-val">{data.get(f'{opp}_nuke',0):.0f}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # --- 2. 戦況実況 ---
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    # --- 3. 自軍情報 ---
    st.markdown(f"""
    <div class="self-hud">
        <div style="font-size:1.1rem; color:#d4af37; font-weight:bold;">{my_name}</div>
        <div style="font-size:0.6rem; color:#aaa;">本土耐久</div>
        <div class="bar-bg"><div class="fill-hp" style="width:{data.get(f'{me}_hp',0)/10}%"></div></div>
        <div style="font-size:0.6rem; color:#aaa;">占領範囲</div>
        <div class="bar-bg"><div class="fill-sh" style="width:{data.get(f'{me}_colony',0)}%"></div></div>
        <div style="font-size:0.6rem; color:#aaa;">核開発</div>
        <div class="bar-bg"><div class="fill-nk" style="width:{data.get(f'{me}_nuke',0)/2}%"></div></div>
    </div>
    """, unsafe_allow_html=True)

    # --- 4. アクションボタン ---
    if data['turn'] == me:
        st.success(f"行動待機中... (AP:{data['ap']})")
        pref = f"[{my_name}]"
        c1, c2, c3, c4, c5 = st.columns(5)
        conf = {"use_container_width": True}
        
        if c1.button("🛠️\n軍拡", **conf):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"]+25, f"{me}_nuke": data[f"{me}_nuke"]+20, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 軍備を増強。"]})
            st.rerun()
        if c2.button("🛡️\n防衛", **conf):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 防衛網を展開。"]})
            st.rerun()
        if c3.button("🕵️\nスパイ", **conf):
            success = random.random() < 0.5
            msg = f"{pref} 工作に成功。" if success else f"{pref} 諜報員が未帰還。"
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-45) if success else data[f"{opp}_nuke"], "ap": data['ap']-1, "chat": data['chat']+[msg]})
            st.rerun()
        if c4.button("⚔️\n進軍", **conf):
            dmg = (data[f"{me}_mil"]*0.4 + 40)
            t_col = data[f"{opp}_colony"]
            new_col = max(0, t_col - dmg)
            new_hp = max(0, data[f"{opp}_hp"] - (dmg - t_col if dmg > t_col else 0))
            report = f"{pref} {enemy_name}へ <span class='dmg-text'>{dmg:.0f}</span> のダメージ！"
            sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": new_hp, "ap": data['ap']-1, "chat": data['chat']+[report]})
            st.rerun()
        if c5.button("🚩\n占領", **conf):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, "ap": data['ap']-1, "chat": data['chat']+[f"{pref} 占領地を併合。"]})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
            
        t_msg = st.text_input("通信", key="c_in", label_visibility="collapsed", placeholder="メッセージ...")
        if st.button("通信送信", use_container_width=True) and t_msg:
            sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬{my_name}: {t_msg}"]})
            st.rerun()
    else:
        st.warning(f"{enemy_name} の行動を監視中...")
        time.sleep(3); st.rerun()
