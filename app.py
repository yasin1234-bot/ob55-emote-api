# ═══════════════════════════════════════════════════════════════
# app.py — YASIN × BHAI EMOTE API (Multi-Region Auto Join & Leave)
# ═══════════════════════════════════════════════════════════════

import asyncio
import threading
import time
import json
import traceback

import httpx
from flask import Flask, request, jsonify
from flask_cors import CORS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import login_engine
import bot_uid_pass
from xC4 import Emote_k, JoinSquadByTeamCode, ExiT
import sys
import os
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
# ★ LOGIN FOR A SINGLE REGION (With Auto-Retry Loop)
# ═══════════════════════════════════════════════════════════════
async def _login_region(region_code, uid, pw):
    print(f"🔐 Logging in {region_code} bot UID={uid} ...")
    
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(verify=False, timeout=20.0) as client_http:
                vc = await login_engine.version_config(client_http, region_code)
                if not vc: 
                    raise RuntimeError("Version config failed")
                release_version, client_version, server_url = vc

                tg = await login_engine.get_access_token(client_http, uid, pw)
                if not tg: 
                    raise RuntimeError("Invalid UID/password")
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
                if not gl: 
                    raise RuntimeError("GetLoginData failed")
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

                reader, writer = await asyncio.open_connection(online_ip, int(online_port))
                writer.write(online_token_bytes)
                await writer.drain()

                BOT_STATE[region_code] = {
                    "logged_in":   True,
                    "bot_uid":     str(major_res.account_uid),
                    "key":         key,
                    "iv":          iv,
                    "region":      actual_region,
                    "online_ip":   online_ip,
                    "online_port": online_port,
                    "writer":      writer,
                    "lock":        asyncio.Lock(),
                    "last_error":  None,
                }
                print(f"✅ {region_code} Bot online → {online_ip}:{online_port} | UID={major_res.account_uid}")
                return  # সফল হলে লুপ থেকে বেরিয়ে যাবে

        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ {region_code} Attempt {attempt+1} failed: {err_msg}")
            if attempt < 2:
                await asyncio.sleep(2)  # পরের চেষ্টার আগে ২ সেকেন্ড অপেক্ষা
            else:
                BOT_STATE[region_code] = {"logged_in": False, "last_error": err_msg}
                print(f"❌ {region_code} Bot completely failed after 3 attempts.")

# ═══════════════════════════════════════════════════════════════
# ★ EMOTE & SQUAD ACTIONS
# ═══════════════════════════════════════════════════════════════
async def _send_packet(region_code, pkt):
    if not BOT_STATE.get(region_code, {}).get("logged_in") or not BOT_STATE[region_code].get("writer"):
        raise RuntimeError(f"{region_code} Bot offline")
    BOT_STATE[region_code]["writer"].write(pkt)
    await BOT_STATE[region_code]["writer"].drain()

async def _send_emote_async(region_code, target_uid, emote_id):
    state = BOT_STATE[region_code]
    key, iv, actual_region = state["key"], state["iv"], state["region"]
    pkt = await Emote_k(int(target_uid), int(emote_id), key, iv, actual_region)
    await _send_packet(region_code, pkt)

# ═══════════════════════════════════════════════════════════════
# ★ FLASK ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def root():
    online_bots = {r: s.get("logged_in", False) for r, s in BOT_STATE.items()}
    return jsonify({
        "api": "YASIN × BHAI Multi-Region Emote API",
        "status": "running",
        "online_bots": online_bots,
        "usage": {
            "single": "/emote?team_code=CODE&emote_id=909000063&uid=UID&server_name=BD",
            "multi":  "/emote?team_code=CODE&uid1=U1&uid2=U2&emote_id=909000063&server_name=IND"
        }
    })

@app.route("/health", methods=["GET"])
def health():
    status = {}
    for r, s in BOT_STATE.items():
        status[r] = "healthy" if s.get("logged_in") else "degraded"
    return jsonify({"status": status})

@app.route("/emote", methods=["GET", "POST"])
def emote():
    try:
        args = request.args.to_dict()

        emote_id_str = args.get("emote_id") or args.get("emote") or ""
        server_name  = (args.get("server_name") or args.get("region") or "").upper()
        team_code    = args.get("team_code") or args.get("teamcode") or ""

        if not emote_id_str.isdigit():
            return jsonify({"success": False, "error": "emote_id missing or not numeric"}), 400
        
        if not server_name or server_name not in bot_uid_pass.SUPPORTED_REGIONS:
            return jsonify({"success": False, "error": "Invalid server_name"}), 400
        
        if not team_code:
            return jsonify({"success": False, "error": "team_code is required"}), 400

        emote_id = int(emote_id_str)

        # Target UID List
        targets = []
        if args.get("uid") and str(args["uid"]).isdigit():
            targets.append(str(args["uid"]))
        for i in range(1, bot_uid_pass.MAX_UIDS + 1):
            k = f"uid{i}"
            if args.get(k) and str(args[k]).isdigit():
                targets.append(str(args[k]))

        seen = set()
        targets = [u for u in targets if not (u in seen or seen.add(u))]

        if not targets:
            return jsonify({"success": False, "error": "No valid uid provided"}), 400

        # ★ Check if the requested region's bot is online
        if not BOT_STATE.get(server_name, {}).get("logged_in"):
            return jsonify({"success": False, "error": f"{server_name} bot is offline or not configured"}), 503

        results = []
        started = time.time()
        
        key = BOT_STATE[server_name]["key"]
        iv = BOT_STATE[server_name]["iv"]
        actual_region = BOT_STATE[server_name]["region"]
        bot_uid = int(BOT_STATE[server_name]["bot_uid"])

        async def _run():
            lock = BOT_STATE[server_name]["lock"]
            async with lock:
                # ১. গ্রুপে জয়েন করা
                try:
                    join_pkt = await JoinSquadByTeamCode(team_code, key, iv, actual_region)
                    await _send_packet(server_name, join_pkt)
                    print(f"✅ {server_name} Bot joined squad: {team_code}")
                    await asyncio.sleep(1.5)
                except Exception as e:
                    print(f"❌ {server_name} Failed to join squad: {e}")

                # ২. ইমোট পাঠানো
                for uid in targets:
                    try:
                        await _send_emote_async(server_name, uid, emote_id)
                        results.append({"uid": uid, "sent": True, "error": None})
                    except Exception as e:
                        results.append({"uid": uid, "sent": False, "error": str(e)[:120]})
                    await asyncio.sleep(bot_uid_pass.EMOTE_COOLDOWN_SEC)
                
                # ৩. গ্রুপ থেকে লিভ নেওয়া
                try:
                    exit_pkt = await ExiT(bot_uid, key, iv)
                    await _send_packet(server_name, exit_pkt)
                    print(f"🚪 {server_name} Bot left the squad.")
                except Exception as e:
                    print(f"❌ {server_name} Failed to leave squad: {e}")

        run_async(_run())

        ok_count = sum(1 for r in results if r["sent"])
        return jsonify({
            "success":     ok_count == len(results),
            "emote_id":    emote_id,
            "server_name": server_name,
            "team_code":   team_code,
            "total":       len(results),
            "sent":        ok_count,
            "failed":      len(results) - ok_count,
            "results":     results,
            "elapsed_sec": round(time.time() - started, 3),
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ /emote error:\n{tb}")
        return jsonify({
            "success": False,
            "error":   str(e)[:200],
            "trace":   tb.splitlines()[-3:],
        }), 500

# ═══════════════════════════════════════════════════════════════
# ★ STARTUP
# ═══════════════════════════════════════════════════════════════
def _bg_boot():
    global MAIN_LOOP
    MAIN_LOOP = start_async_loop()
    
    async def _init_all_bots():
        for region, creds in bot_uid_pass.REGION_BOTS.items():
            if creds["uid"] and creds["password"]:
                try:
                    await _login_region(region, creds["uid"], creds["password"])
                    await asyncio.sleep(1.5) # গ্যারেনা সার্ভার সেফ রাখার জন্য
                except Exception as e:
                    print(f"❌ {region} Bot failed during init: {e}")

    # বটগুলো লগইন হতে ৫ মিনিট পর্যন্ত সময় নিতে পারে
    fut = asyncio.run_coroutine_threadsafe(_init_all_bots(), MAIN_LOOP)
    try:
        fut.result(timeout=300)  
    except Exception as e:
        print(f"❌ Startup Error: {e}")

    MAIN_LOOP.run_forever()

if __name__ == "__main__":
    print("═" * 60)
    print("   YASIN × BHAI — MULTI-REGION EMOTE API")
    print("═" * 60)
    # ⚡ এই লাইনটা মিসিং ছিল, এটা ছাড়া বট লগইন হবে না
    threading.Thread(target=_bg_boot, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)