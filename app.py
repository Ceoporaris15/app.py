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
    st.error("接続設定(Secrets)を確認してください。")
    st.stop()

# データを取得する関数 (キャッシュを無効化して常に最新を得る)
def get_game(rid):
    try:
        res = supabase.table("games").select("*").eq("id", rid).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return None

# データを更新する関数
def sync(rid, updates):
    try:
        supabase.table("games").update(updates).eq("id", rid).execute()
    except Exception as e:
        st.error(f"同期エラー: {e}")

# --- 2. UIデザイン (漆黒・高コントラスト) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #000000 !important; color: #00ffcc !important;
        font-family: 'Hiragino Kaku Gothic Pro', 'Meiryo', sans-serif;
    }
    /* ボタンが白くならないための設定 */
    .stButton > button { 
        background-color: #000000 !important; color: #00ffcc !important; 
        border: 2px solid #00ffcc !important; width: 100% !important;
        height: 60px !important; font-weight: bold !important;
    }
    .stButton > button:active, .stButton > button:focus {
        background-color: #003322 !important; color: #00ffcc !important;
    }
    .status-row { display: flex; align-items: center; margin-bottom: 8px; }
    .status-label { width: 85px; font-size: 0.8rem; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 12px; border: 1px solid #00ffcc; border-radius: 2px; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# セッション管理
if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 3. 説明画面 ---
if st.session_state.briefing:
    st.markdown("### 【 全軍事アクション解説 】")
    st.info("🛠️ 軍拡: 核pt+40 / 🛡️ 防衛: 植民地-20で盾抽選(通常25%/核6.6%) / 🕵️ 工作: 敵妨害 / ⚔️ 進軍: 攻撃 / 🚩 占領: 植民地+55(反乱33%) / 🚨 核: 広範囲破壊")
    if st.button("了解、戦地へ"):
        st.session_state.briefing = False
        st.rerun()

# --- 4. 接続画面 ---
elif not st.session_state.room_id:
    st.title("🛡️ DEUS ONLINE")
    rid = st.text_input("作戦コード", "7777")
    role = st.radio("役割", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("国名", "帝國")
    if st.button("接続開始"):
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ 通信確立。"],
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
    if not data: 
        st.warning("データを確認中...")
        time.sleep(1)
        st.rerun()
    
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    my_name, enemy_name = data.get(f'{me}_country', '自国'), data.get(f'{opp}_country', '敵国')

    # HUDとログの表示
    st.write(f"**敵国: {enemy_name}** | 領土:{data[f'{opp}_hp']:.0f} 植民地:{data[f'{opp}_colony']:.0f}")
    
    # チャットログ表示
    current_chat = data.get('chat', [])
    logs = "".join([f"<div style='margin-bottom:2px;'>{m}</div>" for m in current_chat[-4:]])
    st.markdown(f"<div style='background:#0a0a0a; padding:10px; border:1px solid #333; height:100px; font-size:0.8rem; overflow:hidden;'>{logs}</div>", unsafe_allow_html=True)

    # 自軍ステータス表示
    st.markdown(f"**{my_name}** [通常盾:{data[f'{me}_shield']} / 対核盾:{data[f'{me}_nuke_shield_count']}]")
    st.markdown(f"""
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{data[f'{me}_nuke']/2}%"></div></div></div>
    """, unsafe_allow_html=True)

    # --- アクション部 ---
    if data['turn'] == me:
        st.subheader("あなたのターン")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        # 処理を共通化してエラーを防ぐ
        if c1.button("🛠️軍拡"):
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, data[f'{me}_nuke']+40), "ap": data['ap']-1, "chat": current_chat+[f"🛠️ {my_name}: 軍拡"]})
            st.rerun()
        if c2.button("🛡️防衛"):
            if data[f'{me}_colony'] >= 20:
                s1 = 1 if random.random() < 0.25 else 0
                s2 = 1 if random.random() < 0.066 else 0
                sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']-20, f"{me}_shield": data[f'{me}_shield']+s1, f"{me}_nuke_shield_count": data[f'{me}_nuke_shield_count']+s2, "ap": data['ap']-1, "chat": current_chat+[f"🛡️ {my_name}: 防衛体制"]})
                st.rerun()
        if c4.button("⚔️進軍"):
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": current_chat+[f"⚔️ {enemy_name}が盾を使用"]})
            else:
                dmg = (45 + (data[f'{me}_nuke']*0.53)) + random.randint(-5, 5)
                new_col = max(0, data[f'{opp}_colony']-dmg)
                hp_dmg = max(0, dmg - data[f'{opp}_colony']) if dmg > data[f'{opp}_colony'] else 0
                sync(st.session_state.room_id, {f"{opp}_colony": new_col, f"{opp}_hp": max(0, data[f'{opp}_hp']-hp_dmg), "ap": data['ap']-1, "chat": current_chat+[f"⚔️ {my_name}: 進軍"]})
            st.rerun()
        if c5.button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f'{me}_colony']+55, "ap": data['ap']-1, "chat": current_chat+[f"🚩 {my_name}: 占領"]})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 2})
            st.rerun()
    else:
        st.info("相手の行動を待機中...")
        if st.button("🔄 画面更新"): st.rerun()
        time.sleep(4)
        st.rerun()

    # --- 共通チャットエリア ---
    st.divider()
    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_input("通信文を入力")
        submit = st.form_submit_button("通信送信")
        if submit and msg:
            # 送信直前に最新のチャット履歴を再取得して、メッセージが消えるのを防ぐ
            latest_data = get_game(st.session_state.room_id)
            latest_chat = latest_data.get('chat', [])
            sync(st.session_state.room_id, {"chat": latest_chat + [f"💬 {my_name}: {msg}"]})
            st.rerun()
