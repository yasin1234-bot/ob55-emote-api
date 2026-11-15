# ═══════════════════════════════════════════════════════════════
# app.py — YASIN × BHAI EMOTE API (Silent Monitor & Auto-Reconnect)
# ═══════════════════════════════════════════════════════════════

import asyncio
import threading
import time
import json
import traceback
import sys
import os

import httpx
from flask import Flask, request, jsonify
from flask_cors import CORS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import login_engine
import bot_uid_pass
from xC4 import Emote_k, JoinSquadByTeamCode, ExiT

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════
# ★ HELPER: Online Auth Builder
# ═══════════════════════════════════════════════════════════════
def build_ob55_online_auth(account_uid, token, kts, key, iv):
    token_bytes = token.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc_token = cipher.encrypt(pad(token_bytes, 16))
    opcode = bytes.fromhex("830c")
    uid_bytes  = int(account_uid).to_bytes(8, byteorder="big")
    kts_bytes  = int(kts).to_bytes(4, byteorder="big")
    len_bytes  = len(enc_token).to_bytes(8, byteorder="big")
    return opcode + uid_bytes + kts_bytes + len_bytes + enc_token, enc_token

# ═══════════════════════════════════════════════════════════════
# ★ GLOBAL BOT STATE
# ═══════════════════════════════════════════════════════════════
BOT_STATE = {}  
RECONNECTING = set() 

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════════════════════════════
# ★ ASYNC LOOP
# ═══════════════════════════════════════════════════════════════
def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

MAIN_LOOP = None
def run_async(coro):
    fut = asyncio.run_coroutine_threadsafe(coro, MAIN_LOOP)
    return fut.result(timeout=60)

# ═══════════════════════════════════════════════════════════════
# ★ LOGIN & CONNECTOR
# ═══════════════════════════════════════════════════════════════
async def _login_region(region_code, uid, pw):
    print(f"🔐 Logging in {region_code} bot UID={uid} ...")
    
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client_http:
                vc = await login_engine.version_config(client_http, region_code)
                if not vc: raise RuntimeError("Version config failed")
                release_version, client_version, server_url = vc

                tg = await login_engine.get_access_token(client_http, uid, pw)
                if not tg: raise RuntimeError("Invalid UID/password")
                open_id, access_token, platform = tg

                payload = await login_engine.build_majorlogin_payload(
                    open_id, access_token, platform, client_version
                )
                major_res = await login_engine.send_majorlogin(
                    client_http, payload, release_version, server_url
                )
                if not major_res or not major_res.account_uid:
                    raise RuntimeError("MajorLogin rejected")

                gl = await login_engine.send_getlogin(
                    client_http, payload, major_res.url,
                    major_res.token, release_version
                )
                if not gl: raise RuntimeError("GetLoginData failed")
                res_proto, dict_res = gl

                key = major_res.key or login_engine.AES_KEY
                iv  = major_res.iv  or login_engine.AES_IV
                actual_region = major_res.region or region_code

                online_addr = res_proto.Online_IP_Port or "0.0.0.0:0"
                online_ip, online_port = (
                    online_addr.split(":") if ":" in online_addr else ("0.0.0.0", "0")
                )

                online_token_bytes, _ = build_ob55_online_auth(
                    int(major_res.account_uid),
                    major_res.token,
                    int(major_res.timestamp or time.time()),
                    key, iv,
                )

                # নতুন কানেকশন তৈরি
                reader, writer = await asyncio.open_connection(online_ip, int(online_port))
                writer.write(online_token_bytes)
                await writer.drain()

                # পুরানো কানেকশন ক্লোজ
                if BOT_STATE.get(region_code, {}).get("writer"):
                    try:
                        BOT_STATE[region_code]["writer"].close()
                    except:
                        pass

                BOT_STATE[region_code] = {
                    "logged_in":   True,
                    "bot_uid":     str(major_res.account_uid),
                    "key":         key,
                    "iv":          iv,
                    "region":      actual_region,
                    "writer":      writer,
                    "lock":        asyncio.Lock(),
                }
                print(f"✅ {region_code} Bot online → {online_ip}:{online_port} | UID={major_res.account_uid}")
                return

        except Exception as e:
            print(f"⚠️ {region_code} Attempt {attempt+1} failed: {e}")
            if attempt < 1:
                await asyncio.sleep(1)
            else:
                BOT_STATE[region_code] = {"logged_in": False}
                print(f"❌ {region_code} Bot failed.")

# ═══════════════════════════════════════════════════════════════
# ★ SEND ACTIONS (প্যাকেট পাঠানোর সময় কানেকশন চেক)
# ═══════════════════════════════════════════════════════════════
async def _send_packet(region_code, pkt):
    state = BOT_STATE.get(region_code, {})
    
    # ১. কানেকশন ডেড থাকলে আগে রি-কানেক্ট করো
    if not state.get("logged_in") or not state.get("writer") or state["writer"].is_closing():
        print(f"⚠️ {region_code} Connection dead during send. Reconnecting...")
        creds = bot_uid_pass.REGION_BOTS.get(region_code)
        if creds:
            await _login_region(region_code, creds["uid"], creds["password"])
            state = BOT_STATE.get(region_code, {})
            if not state.get("logged_in"):
                raise RuntimeError(f"{region_code} failed to reconnect")

    # ২. প্যাকেট পাঠাও
    try:
        state["writer"].write(pkt)
        await state["writer"].drain()
    except Exception as e:
        # পাঠানোর সময় হঠাৎ কেটে গেলে আবার রি-কানেক্ট করে পাঠাও
        print(f"⚠️ {region_code} Send failed: {e}. Reconnecting and retrying...")
        creds = bot_uid_pass.REGION_BOTS.get(region_code)
        if creds:
            await _login_region(region_code, creds["uid"], creds["password"])
            state = BOT_STATE.get(region_code, {})
            if state.get("logged_in") and state.get("writer"):
                state["writer"].write(pkt)
                await state["writer"].drain()

async def _send_emote_async(region_code, target_uid, emote_id):
    state = BOT_STATE[region_code]
    pkt = await Emote_k(int(target_uid), int(emote_id), state["key"], state["iv"], state["region"])
    await _send_packet(region_code, pkt)

# ═══════════════════════════════════════════════════════════════
# ★ FLASK ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def root():
    online_bots = {r: s.get("logged_in", False) for r, s in BOT_STATE.items()}
    return jsonify({"api": "YASIN × BHAI Emote API", "online_bots": online_bots})

@app.route("/health", methods=["GET"])
def health():
    status = {r: "healthy" if s.get("logged_in") else "degraded" for r, s in BOT_STATE.items()}
    return jsonify({"status": status})

@app.route("/emote", methods=["GET", "POST"])
def emote():
    try:
        args = request.args.to_dict()
        emote_id_str = args.get("emote_id") or args.get("emote") or ""
        server_name  = (args.get("server_name") or args.get("region") or "").upper()
        team_code    = args.get("team_code") or args.get("teamcode") or ""

        if not emote_id_str.isdigit() or not server_name or not team_code:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        emote_id = int(emote_id_str)
        targets = []
        if args.get("uid") and str(args["uid"]).isdigit():
            targets.append(str(args["uid"]))
        for i in range(1, bot_uid_pass.MAX_UIDS + 1):
            k = f"uid{i}"
            if args.get(k) and str(args[k]).isdigit():
                targets.append(str(args[k]))

        seen = set()
        targets = [u for u in targets if not (u in seen or seen.add(u))]
        if not targets: return jsonify({"success": False, "error": "No valid uid"}), 400
        
        if not BOT_STATE.get(server_name, {}).get("logged_in"):
            return jsonify({"success": False, "error": f"{server_name} bot is offline"}), 503

        results = []
        started = time.time()

        async def _run():
            # এখানে সরাসরি BOT_STATE থেকে ডাটা নেওয়া হচ্ছে, কারণ _send_packet নিজেই রি-কানেক্ট হ্যান্ডেল করে
            lock = BOT_STATE[server_name]["lock"]
            async with lock:
                state = BOT_STATE[server_name]
                
                try:
                    join_pkt = await JoinSquadByTeamCode(team_code, state["key"], state["iv"], state["region"])
                    await _send_packet(server_name, join_pkt)
                    await asyncio.sleep(1.5) 
                except Exception as e:
                    print(f"❌ {server_name} Failed to join squad: {e}")

                for uid in targets:
                    try:
                        # _send_emote_async ভেতরে _send_packet কল করবে, যা দরকার হলে রি-কানেক্ট করবে
                        await _send_emote_async(server_name, uid, emote_id)
                        results.append({"uid": uid, "sent": True})
                    except Exception as e:
                        results.append({"uid": uid, "sent": False, "error": str(e)[:120]})
                    await asyncio.sleep(0.3) 
                
                try:
                    state = BOT_STATE[server_name]
                    exit_pkt = await ExiT(int(state["bot_uid"]), state["key"], state["iv"])
                    await _send_packet(server_name, exit_pkt)
                except Exception:
                    pass

        run_async(_run())

        ok_count = sum(1 for r in results if r["sent"])
        return jsonify({"success": ok_count > 0, "sent": ok_count, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:200]}), 500

# ═══════════════════════════════════════════════════════════════
# ★ SILENT BACKGROUND MONITOR (কোনো প্যাকেট পাঠাবে না)
# ═══════════════════════════════════════════════════════════════
async def _silent_connection_monitor():
    """প্রতি ৫ সেকেন্ড পর পর চেক করবে writer মৃত কিনা, কোনো প্যাকেট পাঠাবে না"""
    while True:
        await asyncio.sleep(5) 
        
        for region, state in BOT_STATE.items():
            if region in RECONNECTING:
                continue

            # শুধু is_closing() চেক করবে, কোনো প্যাকেট পাঠাবে না
            if not state.get("logged_in") or not state.get("writer") or state["writer"].is_closing():
                RECONNECTING.add(region)
                print(f"🔄 {region} silently detected dead. Reconnecting...")
                creds = bot_uid_pass.REGION_BOTS.get(region)
                if creds and creds.get("uid") and creds.get("password"):
                    await _login_region(region, creds["uid"], creds["password"])
                    await asyncio.sleep(2) 
                RECONNECTING.discard(region)

# ═══════════════════════════════════════════════════════════════
# ★ BOOT LOGIC
# ═══════════════════════════════════════════════════════════════
def _bg_boot():
    global MAIN_LOOP
    MAIN_LOOP = start_async_loop()
    
    async def _init_all_bots():
        print("🚀 Starting Multi-Region Bot Initialization...")
        for region, creds in bot_uid_pass.REGION_BOTS.items():
            if creds["uid"] and creds["password"]:
                try:
                    await _login_region(region, creds["uid"], creds["password"])
                    await asyncio.sleep(1.0) 
                except Exception as e:
                    print(f"❌ {region} Bot failed during init: {e}")
        
        # সাইলেন্ট মনিটর চালু
        asyncio.create_task(_silent_connection_monitor())

    asyncio.run_coroutine_threadsafe(_init_all_bots(), MAIN_LOOP)
    MAIN_LOOP.run_forever()

if __name__ == "__main__":
    print("═" * 60)
    print("   YASIN × BHAI — MULTI-REGION EMOTE API")
    print("═" * 60)
    threading.Thread(target=_bg_boot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)