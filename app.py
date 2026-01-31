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

# --- 2. 演出用オーディオ & CSS ---
st.set_page_config(page_title="DEUS ONLINE", layout="centered")

# 効果音を再生する関数（非表示のiframeで再生）
def play_sound(url):
    st.markdown(f'<iframe src="{url}" allow="autoplay" style="display:none"></iframe>', unsafe_allow_html=True)

st.markdown("""
    <style>
    /* 走査線・ノイズ演出 */
    .main {
        background-color: #000000 !important;
        background-image: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 2px, 3px 100%;
        color: #00ffcc !important;
    }
    div[data-testid="stStatusWidget"] { display: none; }
    
    /* 極秘資料カード */
    .briefing-card {
        background: rgba(10, 15, 10, 0.9); border: 2px solid #00ffcc; padding: 25px;
        border-radius: 5px; font-family: 'Courier New', Courier, monospace;
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.2); position: relative;
    }
    .briefing-card::before {
        content: "TOP SECRET - EYES ONLY"; position: absolute; top: -10px; right: 10px;
        background: #ff0000; color: white; padding: 2px 10px; font-size: 0.7rem;
    }
    .brief-title { color: #00ffcc; font-size: 1.8rem; text-shadow: 0 0 10px #00ffcc; margin-bottom: 15px; }
    
    /* ストーリーテキスト */
    .story-text { font-style: italic; color: #d4af37; margin: 20px 0; border-left: 3px solid #d4af37; padding-left: 10px; font-size: 0.9rem; }

    /* 各種バー */
    .status-row { display: flex; align-items: center; margin-bottom: 4px; }
    .status-label { width: 70px; font-size: 0.65rem; color: #00ffcc; font-weight: bold; }
    .bar-bg { background: #111; width: 100%; height: 10px; border-radius: 2px; border: 1px solid #00ffcc; overflow: hidden; }
    .fill-hp { background: #00ffcc; height: 100%; box-shadow: 0 0 10px #00ffcc; }
    .fill-sh { background: #3498db; height: 100%; }
    .fill-nk { background: #9b59b6; height: 100%; }
    
    button { background-color: #000 !important; color: #00ffcc !important; border: 1px solid #00ffcc !important; }
    </style>
    """, unsafe_allow_html=True)

# 音源URL (短い電子音)
BEEP = "https://www.soundjay.com/buttons/sounds/button-29.mp3"
ALERT = "https://www.soundjay.com/buttons/sounds/button-3.mp3"

# --- 3. セッション管理 ---
if 'room_id' not in st.session_state: st.session_state.room_id = None
if 'briefing' not in st.session_state: st.session_state.briefing = False

# --- 4. ブリーフィング画面 ---
if st.session_state.briefing:
    st.markdown("""
    <div class="briefing-card">
        <div class="brief-title">🛰️ 作戦概要：DEUS-VII</div>
        <p>これより貴官に本紛争の交戦規定を伝達する。</p>
        <div class="story-text">「歴史は勝者によって書かれる。敗者に残されるのは、放射能に汚染された砂漠だけだ。」</div>
        <hr style="border-color:#00ffcc">
        <b>■ 勝利条件</b>: 敵の領土または植民地を0にせよ。<br>
        <b>■ 戦術核</b>: 軍拡により威力が上昇する。発射は最大の慈悲である。<br>
        <b>■ 防衛/工作</b>: 運も実力のうちだ。沈黙こそが最大の防御となり得る。<br>
        <b>■ 反乱</b>: 無計画な占領は、自国の首を絞める結果となるだろう。
    </div>
    """, unsafe_allow_html=True)
    if st.button("全規定を承認 (UNDERSTOOD)", use_container_width=True):
        play_sound(BEEP)
        st.session_state.briefing = False
        st.rerun()

# --- 5. 初期設定画面 ---
elif not st.session_state.room_id:
    st.title("📟 DEUS TERMINAL")
    rid = st.text_input("ACCESS CODE", "7777")
    role = st.radio("SELECT ROLE", ["p1", "p2"], horizontal=True)
    c_name = st.text_input("COUNTRY NAME", "帝國")
    if st.button("CONNECTION ESTABLISH"):
        play_sound(BEEP)
        if role == "p1":
            init_data = {
                "id": rid, "p1_hp": 1000.0, "p2_hp": 1000.0, "p1_colony": 50.0, "p2_colony": 50.0, 
                "p1_nuke": 0.0, "p2_nuke": 0.0, "turn": "p1", "ap": 2, "chat": ["🛰️ システム起動。期待しているぞ。"],
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

    # --- 終戦ストーリー判定 ---
    if data[f"{me}_colony"] <= 0 or data[f"{me}_hp"] <= 0:
        st.markdown(f"""<div class="briefing-card" style="border-color:#ff0000">
            <div class="brief-title" style="color:#ff0000">【 敗 戦 】</div>
            <p>{my_name}の灯火は消えた。都市は静まり返り、かつての栄光は瓦礫の下に埋もれた。</p>
            <div class="story-text">「我々は勝利を夢見た。しかし、残されたのは静寂と、勝者が掲げる見知らぬ旗だけだった。」</div>
        </div>""", unsafe_allow_html=True)
        if st.button("ターミナルを閉じる"): st.session_state.room_id = None; st.rerun()
        st.stop()
    
    if data[f"{opp}_colony"] <= 0 or data[f"{opp}_hp"] <= 0:
        st.markdown(f"""<div class="briefing-card">
            <div class="brief-title">【 凱 旋 】</div>
            <p>世界は{my_name}の軍靴の音に震えている。敵軍は瓦解し、新たな秩序が定義された。</p>
            <div class="story-text">「平和とは、敵がいなくなった状態のことを指すのだ。貴官の功績は永遠に刻まれるだろう。」</div>
        </div>""", unsafe_allow_html=True)
        if st.button("次なる戦域へ"): st.session_state.room_id = None; st.rerun()
        st.stop()

    # --- HUD表示 ---
    st.markdown(f'<div class="enemy-mini-hud">敵: {enemy_name} | 本土: {data[f"{opp}_hp"]:.0f} | 植民地: {data[f"{opp}_colony"]:.0f}</div>', unsafe_allow_html=True)
    logs = "".join([f"<div>{m}</div>" for m in data.get('chat', [])[-3:]])
    st.markdown(f'<div class="live-log">{logs}</div>', unsafe_allow_html=True)

    current_atk = 45 + (my_nuke * 0.53)
    s_count = data.get(f'{me}_shield', 0)
    n_shield = "⚠️対核防壁" if data.get(f'{me}_nuke_shield') else ""
    st.markdown(f"""
    <div class="self-hud">
        <div style="font-size:0.9rem; margin-bottom:5px;">{my_name} <span style="font-size:0.6rem; color:#3498db;">SHIELD: {s_count} {n_shield}</span></div>
        <div class="status-row"><div class="status-label">領土</div><div class="bar-bg"><div class="fill-hp" style="width:{data[f'{me}_hp']/10}%"></div></div></div>
        <div class="status-row"><div class="status-label">植民地</div><div class="bar-bg"><div class="fill-sh" style="width:{data[f'{me}_colony']}%"></div></div></div>
        <div class="status-row"><div class="status-label">核開発</div><div class="bar-bg"><div class="fill-nk" style="width:{my_nuke/2}%"></div></div></div>
    </div>
    """, unsafe_allow_html=True)

    # --- アクション ---
    if data['turn'] == me:
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("🛠️\n軍拡"):
            play_sound(BEEP)
            sync(st.session_state.room_id, {f"{me}_nuke": min(200, my_nuke + 40), "ap": data['ap']-1, "chat": data['chat']+[f"🛠️ {my_name}: 軍拡完了。"]})
            st.rerun()
        if c2.button("🛡️\n防衛"):
            play_sound(BEEP)
            s_add = 2 if random.random() < 0.25 else 0
            ns = True if random.random() < 0.10 else data.get(f'{me}_nuke_shield', False)
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+35, f"{me}_shield": data[f"{me}_shield"]+s_add, f"{me}_nuke_shield": ns, "ap": data['ap']-1, "chat": data['chat']+( [f"🛡️ {my_name}: 防衛成功。"] if s_add or ns else [] )})
            st.rerun()
        # ... 工作・進軍・占領も同様に play_sound(BEEP) を追加 ...
        if c3.button("🕵️\n工作"):
            play_sound(BEEP)
            sn, ss = random.random() < 0.5, random.random() < 0.2
            updates = {"ap": data['ap']-1}
            if sn: updates[f"{opp}_nuke"] = max(0, data[f"{opp}_nuke"]-100)
            if ss: updates[f"{opp}_nuke_shield"] = False
            sync(st.session_state.room_id, {**updates, "chat": data['chat']+[f"🕵️ {my_name}: 潜入工作。"]})
            st.rerun()
        if c4.button("⚔️\n進軍"):
            play_sound(ALERT)
            if data[f"{opp}_shield"] > 0:
                sync(st.session_state.room_id, {f"{opp}_shield": data[f"{opp}_shield"]-1, "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {enemy_name}が迎撃！"]})
            else:
                dmg = current_atk + random.randint(-5, 5)
                sync(st.session_state.room_id, {f"{opp}_hp": max(0, data[f"{opp}_hp"]-dmg), "ap": data['ap']-1, "chat": data['chat']+[f"⚔️ {my_name}: 強襲！"]})
            st.rerun()
        if c5.button("🚩\n占領"):
            play_sound(BEEP)
            rebel = random.random() < 0.33
            sync(st.session_state.room_id, {f"{me}_colony": data[f"{me}_colony"]+55, f"{me}_nuke": max(0, my_nuke - (30 if rebel else 0)), "ap": data['ap']-1, "chat": data['chat']+[f"🚩 {my_name}: 占領。"]})
            st.rerun()
        
        if data['ap'] <= 0: sync(st.session_state.room_id, {"turn": opp, "ap": 2}); st.rerun()
    else:
        st.warning("敵の通信を傍受中...")
        time.sleep(3); st.rerun()

    # チャット
    t_msg = st.text_input("", placeholder="暗号通信...", label_visibility="collapsed")
    if st.button("SEND"):
        play_sound(BEEP)
        sync(st.session_state.room_id, {"chat": data['chat'] + [f"💬 {my_name}: {t_msg}"]})
        st.rerun()
