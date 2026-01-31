import streamlit as st
from supabase import create_client
import time

# --- 1. 接続設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets (URL/KEY) が正しく設定されていません。")
    st.stop()

# --- 2. データベース操作関数 ---
def get_game(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

# --- 3. UI/演出 ---
st.set_page_config(page_title="DEUS: 1on1 ONLINE", layout="centered")

# BGM (YouTube埋め込みによる自動再生)
st.markdown('<iframe src="https://www.youtube.com/embed/LRLhYF0C9pM?autoplay=1&loop=1&playlist=LRLhYF0C9pM" width="0" height="0" frameborder="0" allow="autoplay"></iframe>', unsafe_allow_html=True)

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #0b0d10; color: #00ffcc; font-family: 'Share Tech Mono', monospace; }
    .stMetric { border: 1px solid #00ffcc; background: #161b22; padding: 15px; border-radius: 10px; box-shadow: 0 0 10px #00ffcc; }
    .stButton > button { background: #161b22 !important; color: #00ffcc !important; border: 1px solid #00ffcc !important; height: 3em; font-size: 1.2em; transition: 0.3s; width: 100%; }
    .stButton > button:hover { background: #00ffcc !important; color: #0b0d10 !important; box-shadow: 0 0 20px #00ffcc; }
    </style>
""", unsafe_allow_html=True)

# --- 4. メイン処理 ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ロビー画面】
if not st.session_state.room_id:
    st.title("🎛️ DEUS: ONLINE TERMINAL")
    st.subheader("1vs1 遠隔作戦介入システム")
    
    col_l, col_r = st.columns(2)
    with col_l:
        rid = st.text_input("作戦コード(4桁)", "2025")
        role = st.radio("担当デバイス", ["p1", "p2"], help="一人がP1、もう一人がP2を選択")
    with col_r:
        st.write("【システム状況】")
        st.write("・オンライン同期: 有効")
        st.write("・BGMプロトコル: 実行中")
    
    if st.button("戦域へダイブ (LINK START)"):
        data = get_game(rid)
        if not data:
            # 初期化（本土名や陣営は空で作成）
            supabase.table("games").insert({
                "id": rid, "p1_hp": 500, "p2_hp": 500, "turn": "p1", "ap": 3,
                "p1_mil": 20, "p2_mil": 20, "p1_nuke": 0, "p2_nuke": 0
            }).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【バトル画面】
else:
    data = get_game(st.session_state.room_id)
    me = st.session_state.role
    opp = "p2" if me == "p1" else "p1"

    # 初期設定（陣営・本土）
    if not data[f"{me}_faction"]:
        st.title("🛰️ 初期設定プロトコル")
        f = st.selectbox("採用陣営", ["連合国", "枢軸國", "社会主義国"])
        h = st.text_input("本土拠点名", "NEW TOKYO")
        if st.button("設定確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, f"{me}_home": h})
            st.rerun()
        st.stop()

    # --- メインUI ---
    st.title(f"📡 ROOM: {st.session_state.room_id}")
    
    # 状況インジケーター
    c1, c2 = st.columns(2)
    with c1:
        st.metric(f"【自軍】 {data[f'{me}_home']}", f"{data[f'{me}_hp']} HP", f"{data[f'{me}_faction']}")
        st.progress(max(0, min(data[f'{me}_hp']/500, 1.0)))
    with c2:
        opp_home = data[f'{opp}_home'] if data[f'{opp}_home'] else "待機中..."
        st.metric(f"【敵軍】 {opp_home}", f"{data[f'{opp}_hp']} HP", f"{data[f'{opp}_faction']}")
        st.progress(max(0, min(data[f'{opp}_hp']/500, 1.0)))

    st.write("---")

    # 勝利判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        winner = "P1" if data['p2_hp'] <= 0 else "P2"
        st.error(f"⚔️ 作戦終了: 勝者 {winner}")
        if st.button("戦域リセット"):
            sync(st.session_state.room_id, {"p1_hp": 500, "p2_hp": 500, "turn": "p1", "ap": 3, "p1_nuke": 0, "p2_nuke": 0})
            st.rerun()
        st.stop()

    # ターンアクション
    if data['turn'] == me:
        st.success(f"⚡ 指揮権を掌握中 (残りAP: {data['ap']})")
        
        row1 = st.columns(3)
        if row1[0].button("🛠 軍拡"):
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 20, "ap": data['ap'] - 1})
            st.rerun()
        if row1[1].button("🛡 防衛"):
            sync(st.session_state.room_id, {f"{me}_hp": data[f"{me}_hp"] + 40, "ap": data['ap'] - 1})
            st.rerun()
        if row1[2].button("🕵️ スパイ"):
            sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"] - 50), "ap": data['ap'] - 1})
            st.rerun()

        row2 = st.columns(3)
        if row2[0].button("⚔️ 進軍"):
            # 陣営ボーナス計算
            bonus = 20 if data[f"{me}_faction"] == "枢軸國" else 0
            dmg = data[f"{me}_mil"] + bonus
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap'] - 1})
            st.rerun()
        if row2[1].button("☢️ 核開発"):
            sync(st.session_state.room_id, {f"{me}_nuke": data[f"{me}_nuke"] + 35, "ap": data['ap'] - 1})
            st.rerun()
        if row2[2].button("🚀 核発射", disabled=data[f"{me}_nuke"] < 100):
            sync(st.session_state.room_id, {f"{opp}_hp": 0, f"{me}_nuke": 0, "ap": data['ap'] - 1})
            st.rerun()

        if data['ap'] <= 0:
            # ターン交代処理
            next_ap = 4 if data[f"{opp}_faction"] == "社会主義国" else 3
            sync(st.session_state.room_id, {"turn": opp, "ap": next_ap})
            st.rerun()
    else:
        st.warning("📡 敵軍の通信を傍受中... (待機)")
        time.sleep(3) # 3秒待機して自動更新
        st.rerun()

    if st.sidebar.button("接続解除"):
        st.session_state.room_id = None
        st.rerun()
