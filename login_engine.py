# ═══════════════════════════════════════════════════════════════
# login.py — YASIN × BHAI | PREMIUM LOGIN ENGINE
# © 2026 YASIN × BHAI — All rights reserved
# ═══════════════════════════════════════════════════════════════

import asyncio
import random
import uuid
import time
import json
import sys
from datetime import datetime

import httpx
from google_play_scraper import app as play_scraper
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from Pb2 import MajoRLoGinrEs_pb2, PorTs_pb2


# ═══════════════════════════════════════════════════════════════
# PC LOGO (ASCII ART) — shows when login succeeds via MajorLogin
# ═══════════════════════════════════════════════════════════════
PC_LOGO = r"""
   ██████╗  ██████╗    ██╗      ██████╗  ██████╗  ██████╗  ██████╗
  ██╔═══██╗██╔════╝    ██║     ██╔═══██╗██╔════╝ ██╔═══██╗██╔════╝
  ██║   ██║██║         ██║     ██║   ██║██║  ███╗██║   ██║██║  ███╗
  ██║   ██║██║         ██║     ██║   ██║██║   ██║██║   ██║██║   ██║
  ╚██████╔╝╚██████╗    ███████╗╚██████╔╝╚██████╔╝╚██████╔╝╚██████╔╝
   ╚═════╝  ╚═════╝    ╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝  ╚═════╝
          ══════════  YASIN × BHAI  •  MAJOR LOGIN  ══════════
"""


def show_pc_logo():
    """Display the PC logo when MajorLogin succeeds."""
    try:
        print(_c(PC_LOGO, "cyan"))
    except Exception:
        print(PC_LOGO)


def _c(text, color):
    colors = {
        "cyan":    "\033[1;36m",
        "green":   "\033[1;32m",
        "yellow":  "\033[1;33m",
        "red":     "\033[1;31m",
        "magenta": "\033[1;35m",
        "white":   "\033[1;37m",
        "gray":    "\033[1;90m",
        "reset":   "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def log(level, msg):
    icons = {
        "INFO":  ("cyan",    "ℹ"),
        "OK":    ("green",   "✔"),
        "WAIT":  ("yellow",  "⏳"),
        "WARN":  ("yellow",  "⚠"),
        "ERROR": ("red",     "✘"),
        "BOT":   ("magenta", "★"),
        "NET":   ("cyan",    "⇄"),
    }
    color, icon = icons.get(level, ("white", "•"))
    ts = time.strftime("%H:%M:%S")
    print(f"{_c(f'[{ts}]', 'gray')} {_c(f'{icon} {level:<5}', color)} │ {msg}")


def print_banner():
    print("\n" + "═" * 68)
    print(_c("      ★  YASIN × BHAI  —  ELITE PREMIUM LOGIN ENGINE  ★", "magenta"))
    print(_c("             Free Fire OB55 Secure Guest Login", "cyan"))
    print("═" * 68 + "\n")


def print_box(title, pairs):
    width = 60
    print(_c(f"┌{'─' * width}┐", "magenta"))
    print(_c("│", "magenta") + _c(f" {title.center(width - 2)} ", "yellow") + _c("│", "magenta"))
    print(_c(f"├{'─' * width}┤", "magenta"))
    for k, v in pairs:
        line = f"  {_c(f'{k:<16}', 'cyan')}: {_c(str(v), 'green')}"
        pad_len = width - 4 - len(k) - len(str(v))
        print(_c("│", "magenta") + f" {line}{' ' * max(pad_len, 0)}" + _c("│", "magenta"))
    print(_c(f"└{'─' * width}┘", "magenta") + "\n")


AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV  = b'6oyZDr22E3ychjM%'

REGION_LANG = {
    "BD": "bn", "IND": "hi", "PK": "ur", "SG": "en", "ID": "id",
    "ME": "ar", "VN": "vi", "TW": "zh", "CIS": "ru", "TH": "th",
    "EU": "en", "US": "en", "SAC": "es", "LK": "en", "BR": "pt",
}

DEFAULT_HEADERS = {
    'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Expect': '100-continue',
    'X-Unity-Version': '2018.4.12f1',
    'X-GA-SV': '1789535859',
    'X-GA': 'v1 1',
    'ReleaseVersion': 'OB55',
}


def _pb_varint(n):
    if n < 0:
        n = (1 << 64) + n
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            b |= 0x80
        out.append(b)
        if not n:
            break
    return bytes(out)


def _pb_tag(f, w):
    return _pb_varint((f << 3) | w)


def _pb_field(f, v):
    if isinstance(v, bool):
        v = int(v)
    if isinstance(v, int):
        return _pb_tag(f, 0) + _pb_varint(v)
    if isinstance(v, str):
        d = v.encode('utf-8')
        return _pb_tag(f, 2) + _pb_varint(len(d)) + d
    if isinstance(v, (bytes, bytearray)):
        d = bytes(v)
        return _pb_tag(f, 2) + _pb_varint(len(d)) + d
    return b""


async def aes_encrypt(payload, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(payload, AES.block_size))


def get_proto_field(d, key, default=None):
    if not d or not isinstance(d, dict):
        return default
    if key in d:
        return d[key].get('data', default)
    if str(key) in d:
        return d[str(key)].get('data', default)
    return default


async def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {"wire_type": result.wire_type}
        if result.wire_type in ("varint", "string", "bytes"):
            field_data["data"] = result.data
        elif result.wire_type == "length_delimited":
            if hasattr(result.data, "results"):
                field_data["data"] = await parse_results(result.data.results)
            elif isinstance(result.data, list):
                field_data["data"] = await parse_results(result.data)
            else:
                field_data["data"] = str(result.data)
        result_dict[str(result.field)] = field_data
    return result_dict


async def get_playstore_version():
    loop = asyncio.get_event_loop()
    try:
        res = await loop.run_in_executor(
            None,
            lambda: play_scraper('com.dts.freefireth', lang='en', country='id'),
        )
        return res.get("version", "1.132.8")
    except Exception:
        return "1.132.8"


async def version_config(client_http, region="IND"):
    app_version = await get_playstore_version()
    lang = REGION_LANG.get(region, "en")
    api_url = (
        f"https://version.ggwhitehawk.com/live/ver.php?version={app_version}"
        f"&lang={lang}&device=android&channel=android&appstore=googleplay"
        f"&region={region}&whitelist_version=1.3.0&whitelist_sp_version=1.0.0"
    )
    try:
        res = await client_http.get(api_url)
        data = res.json()
        return (
            data.get("latest_release_version"),
            data.get("remote_version"),
            data.get("server_url"),
        )
    except Exception:
        return None


async def get_access_token(client_http, uid, password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    hdrs = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    data = {
        "uid": str(uid),
        "password": str(password),
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    for attempt in range(3):
        try:
            r = await client_http.post(url, headers=hdrs, data=data)
            if r.status_code == 200:
                rd = r.json()
                return rd.get("open_id"), rd.get("access_token"), rd.get("platform", 4)
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return None


# ═══════════════════════════════════════════════════════════════
# ★★★ MANUAL PROTOBUF BUILDER (FROM app.py) ★★★
# ═══════════════════════════════════════════════════════════════
def encode_varint(n):
    if n < 0:
        return b''
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            b |= 0x80
        out.append(b)
        if not n:
            break
    return bytes(out)


def build_proto(fields):
    parts = []
    for k, v in fields.items():
        if isinstance(v, dict):
            nested = build_proto(v)
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(nested)) + nested)
        elif isinstance(v, int):
            parts.append(encode_varint((k << 3) | 0) + encode_varint(v))
        elif isinstance(v, (str, bytes)):
            ev = v.encode() if isinstance(v, str) else v
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(ev)) + ev)
    return b''.join(parts)


def encrypt_api_bytes(plain_bytes):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(
        pad(plain_bytes, AES.block_size)
    )


# ═══════════════════════════════════════════════════════════════
# ★★★ MAJOR LOGIN PAYLOAD — FIXED TO MATCH app.py ★★★
# ═══════════════════════════════════════════════════════════════
async def build_majorlogin_payload_new(open_id, access_token, platform, client_version, device_info=None):
    try:
        if device_info is None:
            device_info = {}
            
        payload_dict = {
            3: str(datetime.now())[:-7], 4: "free fire", 5: "1",
            7: str(client_version) if client_version else "1.132.8",
            8: str(device_info.get("system_software", "Android OS 15 / API-35 (AP3A.240905.015.A2/OS2.0.202.0.VGTIDXM)")),
            9: "Handheld", 10: "Telkomsel", 11: "CarrierDataNetwork",
            12: str(device_info.get("screen_width", 1639)),
            13: str(device_info.get("screen_height", 720)),
            14: str(device_info.get("screen_dpi", 320)),
            15: str(device_info.get("processor_details", "ARM64 FP ASIMD AES | 2000 | 8")),
            16: str(device_info.get("memory", 5653)),
            17: str(device_info.get("gpu_renderer", "Mali-G52 MC2")),
            18: "OpenGL ES 3.2 v1.r49p1-03bet0.19498e0ae1d5dac223383c39a2e58f04",
            19: str(device_info.get("unique_device_id", f"Google|{uuid.uuid4()}")),
            20: str(device_info.get("client_ip", "182.5.135.225")),
            21: "en", 22: str(open_id), 23: str(platform), 24: "Handheld",
            25: str(device_info.get("model", "Xiaomi 2409BRN2CY")), 26: "ID",
            29: str(access_token), 30: "1", 41: "Telkomsel", 42: "4G",
            57: "7428b253defc164018c604a1ebbfebdf", 60: "109278", 61: "55402",
            62: "868", 64: "55927", 65: "109278", 66: "55927", 67: "109278",
            73: 2,
            74: "/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/lib/arm64",
            76: 1,
            77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/base.apk",
            78: 6, 79: 1, 81: "32", 83: "2019121229", 85: 3,
            86: "OpenGLES2", 87: 3071, 88: 4, 89: 14466, 93: "3rd_party",
            94: "KqsHTyb7yHjsAiyNWUUZa0DSOD6U0AhDQ76smAo1WeHHHpSmJ8KMRyRrxb2ttgJqO9YOqO/K6AORAvDMAX/qBS8+JahIkrM7kHfzlfULbgRAoZ9r",
            95: "111207", 96: "{\"cur_rate\":[60,90,120],\"support_etc2\":true}", 97: "1",
            98: "1", 99: str(platform), 100: str(platform), 102: "D]C\x15\x05T\x0eU3",
            103: "1", 104: "52837", 105: "1",
            106: "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|211c933168f55902c7dfbfd8c4e2957d",
            107: "1.3fb8adbf45f44ce9",
        }
        raw_proto = build_proto(payload_dict)
        return encrypt_api_bytes(raw_proto)
    except Exception as e:
        log("ERROR", f"Error building MajorLogin payload: {e}")
        return None


USE_OLD_MAJORLOGIN = False


async def build_majorlogin_payload_old(open_id, access_token):
    from Pb2 import MajoRLoGinrEq_pb2 as ML
    major_login = ML.MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire India"
    major_login.platform_id = 1
    major_login.client_version = "1.123.2"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.reg_avatar = 1
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019118695"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    return await aes_encrypt(major_login.SerializeToString(), AES_KEY, AES_IV)


async def build_majorlogin_payload(open_id, access_token, platform, client_version, device_info=None):
    if USE_OLD_MAJORLOGIN:
        try:
            return await build_majorlogin_payload_old(open_id, access_token)
        except Exception as e:
            log("ERROR", f"Old MajorLogin payload error: {e}")
            return None
    return await build_majorlogin_payload_new(open_id, access_token, platform, client_version, device_info)


async def send_majorlogin(client_http, data, release_version, server_url):
    try:
        url = f"{server_url}MajorLogin" if server_url.endswith('/') else f"{server_url}/MajorLogin"
        req_headers = DEFAULT_HEADERS.copy()
        req_headers["ReleaseVersion"] = str(release_version)

        response = await client_http.post(url, headers=req_headers, data=data)
        if response.status_code != 200 or len(response.content) < 40:
            log("WARN", f"DEBUG | URL={url}")
            log("WARN", f"DEBUG | HTTP status={response.status_code} | bytes={len(response.content)}")
            return None

        res_proto = MajoRLoGinrEs_pb2.MajorLoginRes()
        try:
            res_proto.ParseFromString(response.content)
        except Exception:
            pass

        if not (res_proto.account_uid and res_proto.token):
            for offset in range(min(128, len(response.content))):
                try:
                    c = MajoRLoGinrEs_pb2.MajorLoginRes()
                    c.ParseFromString(response.content[offset:])
                    if c.account_uid and c.token:
                        res_proto = c
                        break
                except Exception:
                    pass

        parsed = Parser().parse(response.content.hex())
        dict_res = await parse_results(parsed)

        key_val = get_proto_field(dict_res, 22) or res_proto.key or AES_KEY
        iv_val  = get_proto_field(dict_res, 23) or res_proto.iv  or AES_IV

        if isinstance(key_val, str):
            try: key_val = bytes.fromhex(key_val)
            except Exception: pass
        if isinstance(iv_val, str):
            try: iv_val = bytes.fromhex(iv_val)
            except Exception: pass

        res_proto.key = key_val
        res_proto.iv  = iv_val
        if not res_proto.url:
            res_proto.url = server_url
        return res_proto
    except Exception as e:
        log("ERROR", f"MajorLogin error: {e}")
        return None


async def send_getlogin(client_http, data, base_url, token, release_version):
    try:
        url = f"{base_url.rstrip('/')}/GetLoginData"
        req_headers = DEFAULT_HEADERS.copy()
        req_headers["ReleaseVersion"] = str(release_version)
        req_headers['Authorization'] = f"Bearer {token}"

        response = await client_http.post(url, headers=req_headers, data=data)
        if response.status_code != 200:
            return None

        res_proto = PorTs_pb2.GetLoginData()
        try:
            res_proto.ParseFromString(response.content)
        except Exception:
            pass

        parsed = Parser().parse(response.content.hex())
        dict_res = await parse_results(parsed)
        return res_proto, dict_res
    except Exception as e:
        log("ERROR", f"GetLoginData error: {e}")
        return None


async def do_login(uid, password, region_pref="IND"):
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client_http:
        log("NET", "Fetching version configuration...")
        vc = await version_config(client_http, region_pref)
        if not vc:
            log("ERROR", "Version config failed.")
            return None
        release_version, client_version, server_url = vc
        log("OK", f"Version: {client_version} │ Release: {release_version}")

        log("NET", "Fetching access token...")
        tg = await get_access_token(client_http, uid, password)
        if not tg:
            log("ERROR", "Invalid UID or password - Access token not found.")
            return None
        open_id, access_token, platform = tg
        log("OK", "Access token acquired successfully.")

        log("INFO", "Building MajorLogin payload...")
        payload = await build_majorlogin_payload(open_id, access_token, platform, client_version)
        if not payload:
            log("ERROR", "Payload creation failed.")
            return None

        log("NET", "Sending MajorLogin request...")
        major_res = await send_majorlogin(client_http, payload, release_version, server_url)
        if not major_res or not major_res.account_uid:
            log("ERROR", "MajorLogin rejected by server.")
            return None

        show_pc_logo()
        log("OK", f"MajorLogin accepted → Account UID: {major_res.account_uid}")

        log("NET", "Sending GetLoginData request...")
        gl = await send_getlogin(client_http, payload, major_res.url, major_res.token, release_version)
        if not gl:
            log("ERROR", "GetLoginData failed.")
            return None
        res_proto, dict_res = gl
        log("OK", "Login data retrieved successfully.")

        online_addr = res_proto.Online_IP_Port or get_proto_field(dict_res, 14, "0.0.0.0:0")
        if ':' in online_addr:
            online_ip, online_port = online_addr.split(":")
        else:
            online_ip, online_port = "0.0.0.0", "0"

        chat_addr = res_proto.AccountIP_Port or get_proto_field(dict_res, 32, online_addr)
        if ':' in chat_addr:
            chat_ip, chat_port = chat_addr.split(":")
        else:
            chat_ip, chat_port = online_ip, online_port

        print_box("YASIN × BHAI — LOGIN SUCCESS", [
            ("Bot UID",     major_res.account_uid),
            ("Account Name", res_proto.AccountName or "Unknown"),
            ("Region",      major_res.region or region_pref),
            ("Clan ID",     res_proto.Clan_ID or 0),
            ("Online",      f"{online_ip}:{online_port}"),
            ("Chat",        f"{chat_ip}:{chat_port}"),
            ("Server",      major_res.url),
        ])

        return {
            "bot_uid":      str(major_res.account_uid),
            "token":        major_res.token,
            "region":       major_res.region or region_pref,
            "key":          major_res.key or AES_KEY,
            "iv":           major_res.iv or AES_IV,
            "timestamp":    major_res.timestamp or int(time.time()),
            "online_ip":    online_ip,
            "online_port":  online_port,
            "chat_ip":      chat_ip,
            "chat_port":    chat_port,
            "account_name": res_proto.AccountName or "Unknown",
            "clan_id":      res_proto.Clan_ID or 0,
            "clan_data":    res_proto.Clan_Compiled_Data or "",
            "server_url":   major_res.url,
        }