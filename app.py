# ═══════════════════════════════════════════════════════════════
# app.py — YASIN × BHAI EMOTE API (Multi-Region Fast On-Demand)
# ═══════════════════════════════════════════════════════════════

import asyncio
import time
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

app = Flask(__name__)
CORS(app)

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
# ★ CORE FUNCTION (Login -> Join -> Emote -> Leave)
# ═══════════════════════════════════════════════════════════════
async def run_live_emote(region_code, uid, pw, team_code, emote_id, targets):
    print(f"🔐 [{region_code}] Logging in bot UID={uid} ...")
    
    # ১. লগইন প্রসেস
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client_http:
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
        bot_uid = int(major_res.account_uid)

        online_addr = res_proto.Online_IP_Port or "0.0.0.0:0"
        online_ip, online_port = (
            online_addr.split(":") if ":" in online_addr else ("0.0.0.0", "0")
        )

        online_token_bytes, _ = build_ob55_online_auth(
            bot_uid, major_res.token, int(major_res.timestamp or time.time()), key, iv
        )

    # ২. TCP কানেকশন ওপেন
    reader, writer = await asyncio.open_connection(online_ip, int(online_port))
    writer.write(online_token_bytes)
    await writer.drain()
    print(f"✅ [{region_code}] Bot connected → {online_ip}:{online_port}")

    try:
        # ৩. টিমে জয়েন
        join_pkt = await JoinSquadByTeamCode(team_code, key, iv, actual_region)
        writer.write(join_pkt)
        await writer.drain()
        print(f"✅ [{region_code}] Bot joining squad: {team_code}...")
        
        # জয়েন হওয়ার জন্য ১.২ সেকেন্ড অপেক্ষা
        await asyncio.sleep(1.2) 

        # ৪. ইমোট পাঠানো
        results = []
        for target in targets:
            try:
                pkt = await Emote_k(int(target), int(emote_id), key, iv, actual_region)
                writer.write(pkt)
                await writer.drain()
                results.append({"uid": target, "sent": True})
                print(f"🎭 [{region_code}] Emote {emote_id} sent to {target}")
            except Exception as e:
                results.append({"uid": target, "sent": False, "error": str(e)})
            await asyncio.sleep(0.15)

        # ৫. ইমোট দেওয়া শেষে গ্রুপ থেকে লিভ নেওয়া
        try:
            exit_pkt = await ExiT(bot_uid, key, iv)
            writer.write(exit_pkt)
            await writer.drain()
            print(f"🚪 [{region_code}] Bot left the squad.")
        except Exception as e:
            print(f"❌ [{region_code}] Failed to leave squad: {e}")

        # এখানে কোনো writer.close() নেই, সিস্টেম নিজেই কেটে দিবে

        return results, bot_uid

    except Exception as e:
        raise RuntimeError(f"TCP Error: {e}")

# ═══════════════════════════════════════════════════════════════
# ★ FLASK ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def root():
    return jsonify({"api": "YASIN × BHAI Emote API", "status": "running", "mode": "on-demand"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})

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
        if not targets: 
            return jsonify({"success": False, "error": "No valid uid provided"}), 400
        
        creds = bot_uid_pass.REGION_BOTS.get(server_name)
        if not creds or not creds.get("uid") or not creds.get("password"):
            return jsonify({"success": False, "error": f"{server_name} bot credentials not found"}), 404

        started = time.time()
        
        results, bot_uid = asyncio.run(run_live_emote(
            server_name, creds["uid"], creds["password"], team_code, emote_id, targets
        ))

        ok_count = sum(1 for r in results if r["sent"])
        return jsonify({
            "success": ok_count > 0,
            "emote_id": emote_id,
            "server_name": server_name,
            "team_code": team_code,
            "bot_uid": bot_uid,
            "sent": ok_count,
            "results": results,
            "elapsed_sec": round(time.time() - started, 3)
        })

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ /emote error:\n{tb}")
        return jsonify({"success": False, "error": str(e)[:200]}), 500

# ═══════════════════════════════════════════════════════════════
# ★ STARTUP
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 60)
    print("   YASIN × BHAI — FAST ON-DEMAND API")
    print("═" * 60)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)