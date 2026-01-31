import streamlit as st
from supabase import create_client
import time

# --- 1. 接続設定 ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Secrets設定エラー: SUPABASE_URL と SUPABASE_KEY を確認してください。")
    st.stop()

# --- 2. データベース操作関数 ---
def get_data(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

# --- 3. UI/デザイン ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { background-color: #000; color: #d4af37; font-family: 'Courier New', monospace; }
    .stButton > button { background-color: #1a1a1a !important; color: #d4af37 !important; border: 2px solid #d4af37 !important; transition: 0.3s; font-weight: bold; }
    .stButton > button:hover { background-color: #d4af37 !important; color: #000 !important; }
    .stProgress > div > div > div > div { background-color: #d4af37 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. メイン・シーケンス ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【フェーズ1: ホーム画面 / 接続】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: ONLINE TERMINAL")
    st.write("--- 世界線への接続 ---")
    rid = st.text_input("ルームコードを入力", "1234")
    role = st.radio("担当デバイス", ["p1", "p2"], help="一人がP1、もう一人がP2を選んでください")
    
    if st.button("戦域接続 (CONNECT)"):
        data = get_data(rid)
        if not data:
            # 初めてのルームなら初期データを投入
            supabase.table("games").insert({
                "id": rid, "p1_hp": 500, "p2_hp": 500, 
                "turn": "p1", "ap": 2, "chat": []
            }).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【フェーズ2: ゲーム本編】
else:
    data = get_data(st.session_state.room_id)
    me = st.session_state.role
    opp = "p2" if me == "p1" else "p1"
    
    # --- 陣営選択チェック ---
    if not data[f"{me}_faction"]:
        st.title("🪖 陣営選別")
        fac = st.selectbox("国家特性を選択せよ", ["連合国 (バランス)", "枢軸國 (攻撃特化)", "社会主義国 (物量特化)"])
        if st.button("陣営確定"):
            sync(st.session_state.room_id, {f"{me}_faction": fac})
            st.rerun()
        st.stop()

    # --- バトル画面 ---
    st.title(f"DEUS: ROOM {st.session_state.room_id}")
    
    # 状況メーター
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**P1: {data['p1_faction']}**")
        st.metric("領土耐久値", f"{data['p1_hp']} HP")
        st.progress(max(0, min(data['p1_hp']/500, 1.0)))
    with c2:
        st.write(f"**P2: {data['p2_faction']}**")
        st.metric("領土耐久値", f"{data['p2_hp']} HP")
        st.progress(max(0, min(data['p2_hp']/500, 1.0)))

    st.write("---")
    
    # 勝利判定
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        winner = "P1" if data['p2_hp'] <= 0 else "P2"
        st.error(f"【終局】 勝者: {winner}")
        if st.button("再戦 (リセット)"):
            sync(st.session_state.room_id, {"p1_hp": 500, "p2_hp": 500, "turn": "p1", "ap": 2})
            st.rerun()
        st.stop()

    # ターン管理
    st.subheader(f"ターン: {data['turn'].upper()} (残りAP: {data['ap']})")
    
    if data['turn'] == me:
        st.success("あなたの指揮ターンです。行動を選択してください。")
        row1 = st.columns(3)
        
        # アクション
        if row1[0].button("⚔️ 進軍"):
            dmg = 40 if data[f"{me}_faction"] == "枢軸國" else 30
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap'] - 1})
            st.rerun()
            
        if row1[1].button("🛡️ 防衛"):
            heal = 40 if data[f"{me}_faction"] == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_hp": data[f"{me}_hp"] + heal, "ap": data['ap'] - 1})
            st.rerun()
            
        if row1[2].button("☢️ 核開発"):
            sync(st.session_state.room_id, {f"{me}_nuke": data[f"{me}_nuke"] + 50, "ap": data['ap'] - 1})
            st.rerun()

        # ターン終了処理
        if data['ap'] <= 0:
            next_ap = 3 if data[f"{opp}_faction"] == "社会主義国" else 2
            sync(st.session_state.room_id, {"turn": opp, "ap": next_ap})
            st.rerun()
    else:
        st.warning("相手の通信を待機しています...")
        time.sleep(2) # 簡易的な自動更新待機
        if st.button("🔄 戦況を強制更新"):
            st.rerun()

    # ログアウト
    if st.sidebar.button("戦域離脱"):
        st.session_state.room_id = None
        st.rerun()
