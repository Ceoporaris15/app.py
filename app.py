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

# --- 2. データベース操作関数 ---
def get_game(rid):
    res = supabase.table("games").select("*").eq("id", rid).execute()
    return res.data[0] if res.data else None

def sync(rid, updates):
    supabase.table("games").update(updates).eq("id", rid).execute()

def add_msg(rid, current_chat, sender, text, is_log=False):
    chat = current_chat if current_chat else []
    prefix = "📢" if is_log else f"💬[{sender}]"
    chat.append(f"{prefix} {text}")
    sync(rid, {"chat": chat[-6:]})

# --- 3. UI/スタイル設定 (白飛び・点滅防止) ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

st.markdown("""
    <style>
    /* 画面のリフレッシュ時に白くならないように背景色を最優先で固定 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    * { animation: none !important; transition: none !important; }
    
    .enemy-banner { background-color: #111; border-bottom: 2px solid #d4af37; padding: 10px; text-align: center; margin: -60px -15px 15px -15px; }
    .enemy-text { color: #d4af37; font-weight: bold; font-family: monospace; letter-spacing: 2px; }
    
    /* 説明用カード */
    .info-card { background: #0a0a0a; border: 1px solid #333; padding: 15px; border-radius: 5px; margin-bottom: 10px; font-size: 0.85rem; }
    .info-title { color: #d4af37; font-weight: bold; border-bottom: 1px solid #444; margin-bottom: 5px; }
    
    /* ゲージ */
    .stat-card { background: #0a0a0a; border: 1px solid #333; padding: 12px; border-radius: 4px; }
    .bar-label { font-size: 0.75rem; color: #AAA; margin-bottom: 3px; display: flex; justify-content: space-between; font-family: monospace; }
    .hp-bar-bg { background: #222; width: 100%; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; border: 1px solid #444; }
    .hp-bar-fill { background: linear-gradient(90deg, #d4af37, #f1c40f); height: 100%; }
    .shield-bar-fill { background: linear-gradient(90deg, #3498db, #2980b9); height: 100%; }
    .nuke-bar-fill { background: linear-gradient(90deg, #9b59b6, #8e44ad); height: 100%; }
    .enemy-bar-fill { background: linear-gradient(90deg, #c0392b, #e74c3c); height: 100%; }
    
    /* ログ */
    .chat-box { background: #000; border: 1px solid #444; padding: 10px; height: 120px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.85rem; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. メインロジック ---
if 'room_id' not in st.session_state:
    st.session_state.room_id = None

# 【ホーム画面：ロビー & 説明表示】
if not st.session_state.room_id:
    st.title("🛡️ DEUS: GLOBAL TERMINAL")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="info-card"><div class="info-title">【陣営特性】</div>'
                    '<b>■ 連合国</b>: 核開発速度が通常の2.0倍。スパイ成功率が高い。<br>'
                    '<b>■ 枢軸國</b>: 進軍時のダメージが1.5倍。攻撃特化型。<br>'
                    '<b>■ 社会主義国</b>: 毎ターンの行動回数(AP)が3回。</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="info-card"><div class="info-title">【アクション解説】</div>'
                    '<b>🛠軍拡</b>: 軍事力UP＋核開発P。基本行動。<br>'
                    '<b>🛡防衛</b>: 緩衝地帯を微増。本土被弾を防ぐ。<br>'
                    '<b>⚔️進軍</b>: 敵領土を直接破壊。軍事力で威力UP。<br>'
                    '<b>🚩占領</b>: 緩衝地帯を大幅拡張。防御の要。<br>'
                    '<b>🕵️スパイ</b>: 敵の核開発を妨害。一定確率で成功。</div>', unsafe_allow_html=True)

    rid = st.text_input("作戦コード(4桁)", "7777")
    role = st.radio("役割を選択", ["p1", "p2"], horizontal=True)
    if st.button("戦域へ接続 (DEPLOY)"):
        data = get_game(rid)
        if not data:
            supabase.table("games").insert({"id": rid, "p1_hp": 150, "p2_hp": 150, "turn": "p1", "ap": 2, "p1_colony": 50, "p2_colony": 50, "p1_nuke": 0, "p2_nuke": 0, "p1_mil": 0, "p2_mil": 0, "chat": ["📢 システムオンライン"]}).execute()
        st.session_state.room_id = rid
        st.session_state.role = role
        st.rerun()

# 【バトル画面】
else:
    data = get_game(st.session_state.room_id)
    me, opp = st.session_state.role, ("p2" if st.session_state.role == "p1" else "p1")
    
    if not data[f"{me}_faction"]:
        f = st.selectbox("採用する国家プロトコル", ["連合国", "枢軸國", "社会主義国"])
        if st.button("プロトコルを確定"):
            sync(st.session_state.room_id, {f"{me}_faction": f, "ap": (3 if f == "社会主義国" else 2) if me == "p1" else data['ap']})
            st.rerun()
        st.stop()

    # --- 状況表示 ---
    st.markdown(f'<div class="enemy-banner"><span class="enemy-text">OPERATOR: {me.upper()} | {data["turn"].upper()} PHASE</span></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>自軍本土</span><span>{data[f'{me}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="hp-bar-fill" style="width: {(data[f'{me}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>緩衝(占領)</span><span>{data[f'{me}_colony']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="shield-bar-fill" style="width: {min(data[f'{me}_colony'], 100)}%"></div></div>
            <div class="bar-label"><span>核開発</span><span>{data[f'{me}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="nuke-bar-fill" style="width: {min(data[f'{me}_nuke']/2, 100)}%"></div></div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-card">
            <div class="bar-label"><span>敵軍領土</span><span>{data[f'{opp}_hp']:.0f}</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {(data[f'{opp}_hp']/150)*100}%;"></div></div>
            <div class="bar-label"><span>敵・核開発</span><span>{data[f'{opp}_nuke']:.0f}/200</span></div>
            <div class="hp-bar-bg"><div class="enemy-bar-fill" style="width: {min(data[f'{opp}_nuke']/2, 100)}%; opacity: 0.4;"></div></div>
        </div>""", unsafe_allow_html=True)

    # 決着
    if data['p1_hp'] <= 0 or data['p2_hp'] <= 0:
        st.error(f"決着: {'勝利' if data[opp+'_hp']<=0 else '敗北'}")
        if st.button("再起動"):
            sync(st.session_state.room_id, {"p1_hp": 150, "p2_hp": 150, "p1_nuke": 0, "p2_nuke": 0, "p1_mil": 0, "p2_mil": 0, "p1_colony": 50, "p2_colony": 50, "turn": "p1", "chat": ["📢 システム再起動完了"]})
            st.rerun()
        st.stop()

    # コマンド
    if data['turn'] == me:
        st.success(f"あなたのターン (残りAP: {data['ap']})")
        fac = data[f"{me}_faction"]
        
        row1 = st.columns(3)
        if row1[0].button("🛠軍拡"):
            n_add = 40 if fac == "連合国" else 20
            sync(st.session_state.room_id, {f"{me}_mil": data[f"{me}_mil"] + 25, f"{me}_nuke": data[f"{me}_nuke"] + n_add, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "軍事力と核開発を進めました", True)
            st.rerun()
        if row1[1].button("🛡防衛"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 35, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "防衛ラインを構築しました", True)
            st.rerun()
        if row1[2].button("🕵️スパイ"):
            success = random.random() < (0.6 if fac == "連合国" else 0.35)
            if success:
                sync(st.session_state.room_id, {f"{opp}_nuke": max(0, data[f"{opp}_nuke"]-50), "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイが成功！敵の核施設を破壊しました", True)
            else:
                sync(st.session_state.room_id, {"ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "スパイ工作は失敗しました", True)
            st.rerun()

        row2 = st.columns(2)
        if row2[0].button("⚔️進軍"):
            dmg = (data[f"{me}_mil"] * 0.5 + 20) * (1.5 if fac == "枢軸國" else 1.0)
            sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"] - dmg, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, f"敵陣地を攻撃、{dmg:.0f}ダメージ", True)
            st.rerun()
        if row2[1].button("🚩占領"):
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"] + 45, "ap": data['ap']-1})
            add_msg(st.session_state.room_id, data['chat'], me, "緩衝地帯を拡大しました", True)
            st.rerun()
            
        if data[f"{me}_nuke"] >= 200:
            if st.button("☢️ 核ミサイル発射", type="primary", use_container_width=True):
                sync(st.session_state.room_id, {f"{opp}_hp": data[f"{opp}_hp"]*0.15, f"{me}_nuke": 0, "ap": data['ap']-1})
                add_msg(st.session_state.room_id, data['chat'], me, "☢️ 核攻撃を実行。壊滅的な被害。", True)
                st.rerun()

        if data['ap'] <= 0:
            sync(st.session_state.room_id, {"turn": opp, "ap": 3 if data[f"{opp}_faction"] == "社会主義国" else 2})
            st.rerun()
    else:
        st.warning("敵の行動を待機しています...")
        time.sleep(2)
        st.rerun()

    # チャット・ログ
    st.markdown('<div class="chat-box">' + "".join([f"<div>{m}</div>" for m in data['chat']]) + '</div>', unsafe_allow_html=True)
    msg = st.text_input("通信メッセージを入力", key="comms")
    if st.button("送信"):
        if msg: add_msg(st.session_state.room_id, data['chat'], me, msg); st.rerun()
