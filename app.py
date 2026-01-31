import streamlit as st
from supabase import create_client
import time

# --- 1. Supabase接続設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("接続情報(Secrets)が未設定です。")
    st.stop()

# --- 2. データベース同期関数 ---
def get_game(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

# --- 3. UI/演出設定 ---
st.set_page_config(page_title="DEUS: TOTAL ONLINE", layout="wide")

# BGM実装（ループ再生）
st.markdown("""
    <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&loop=1&playlist=dQw4w9WgXcQ" 
    width="0" height="0" frameborder="0" allow="autoplay"></iframe>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #050505; color: #d4af37; font-family: 'Courier New', monospace; }
    .stMetric { border: 1px solid #d4af37; padding: 10px; border-radius: 5px; background: #111; }
    .stButton > button { background-color: #1a1a1a !important; color: #d4af37 !important; border: 2px solid #d4af37 !important; width: 100%; height: 60px; font-weight: bold; }
    .stButton > button:hover { background-color: #d4af37 !important; color: #000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. ゲームロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【フェーズ1: ホーム画面 & ルール設定】
if not st.session_state.room_id:
    st.title("⚔️ DEUS: GLOBAL COMMAND CENTER")
    c1, c2 = st.columns(2)
    with c1:
        rid = st.text_input("ルームコード(4桁)", "7777")
        role = st.radio("担当", ["p1", "p2"])
    with c2:
        st.info("ホスト(P1)が設定を決定します")
        time_limit = st.select_slider("1ターンの持ち時間(秒)", options=[30, 60, 120, 300], value=60)
    
    if st.button("戦域へ接続 (START)"):
        data = get_game(rid)
        if not data:
            # 部屋の新規作成（AI戦の全仕様を投入）
            supabase.table("games").insert({
                "id": rid, "p1_hp": 500, "p2_hp": 500, "turn": "p1", "ap": 3,
                "p1_nuke": 0, "p2_nuke": 0, "p1_mil": 20, "p2_mil": 20,
                "time_limit": time_limit
            }).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【フェーズ2: バトル画面】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    # 陣営と本土の設定（未設定の場合）
    if not data[f"{me}_faction"]:
        st.header("🏁 国家・本土の最終決定")
        f = st.selectbox("陣営選択", ["連合国 (防衛型)", "枢軸國 (攻撃型)", "社会主義国 (物量型)"])
        h = st.text_input("本土（首都）の名称を入力", "TOKYO CITY")
        if st.button("戦略決定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, f"{me}_home": h})
            st.rerun()
        st.stop()

    # --- メインバトルインターフェース ---
    st.title(f"📡 OPERATION: {data.get('id')}")
    st.write(f"あなたの本土: **{data[f'{me}_home']}** | 陣営: **{data[f'{me}_faction']}**")

    # ステータス（AI戦の全パラメーターを可視化）
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric(f"P1: {data['p1_faction']}", f"{data['p1_hp']} HP", f"軍事力 {data['p1_mil']}")
    sc2.metric("🌏 世界情勢", f"TURN: {data['turn'].upper()}", f"残りAP: {data['ap']}")
    sc3.metric(f"P2: {data['p2_faction']}", f"{data['p2_hp']} HP", f"軍事力 {data['p2_mil']}")

    # 勝利判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.balloons()
        st.error(f"勝者: {'P1' if data['p2_hp'] <= 0 else 'P2'}")
        if st.button("ターミナルをリセット"):
            sync(st.session_state.room_id, {"p1_hp": 500, "p2_hp": 500, "turn": "p1", "ap": 3, "p1_nuke": 0, "p2_nuke": 0})
            st.rerun()
        st.stop()

    # コマンド入力
    if data['turn'] == me:
        st.markdown(f"### ⚡ YOUR TURN (持ち時間: {data['time_limit']}s)")
        row1 = st.columns(3)
        if row1[0].button("🛠 軍事力拡充"):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 20, "ap": data['ap'] - 1})
            st.rerun()
        if row1[1].button("🛡 領土防衛"):
            sync(st.session_state.room_id, {f"{me}_hp": data[f"{me}_hp"] + 30, "ap": data['ap'] - 1})
            st.rerun()
        if row1[2].button("🕵️ スパイ工作"):
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"] - 40), "ap": data['ap'] - 1})
            st.rerun()

        row2 = st.columns(3)
        if row2[0].button("⚔️ 全軍進軍"):
            dmg = data[f"{me}_mil"] + (20 if data[f"{me}_faction"] == "枢軸國" else 0)
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap'] - 1})
            st.rerun()
        if row2[1].button("☢️ 核開発"):
            sync(st.session_state.room_id, {f"{me}_nuke": data[f"{me}_nuke"] + 40, "ap": data['ap'] - 1})
            st.rerun()
        if row2[2].button("🚀 核ミサイル発射", disabled=data[f"{me}_nuke"] < 100):
            sync(st.session_state.room_id, {f"{opp}_hp": 0, f"{me}_nuke": 0, "ap": data['ap'] - 1})
            st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3})
            st.rerun()
    else:
        st.warning("敵軍の行動を待機中...")
        time.sleep(3)
        if st.button("📡 戦況同期"): st.rerun()

    
