# ═══════════════════════════════════════════════════════════════
# bot_uid_pass.py — Multi-Region Bot Config
# ═══════════════════════════════════════════════════════════════

# ★ All Supported Regions
SUPPORTED_REGIONS = {
    "BD":  "Bangladesh",
    "IND": "India",
    "PK":  "Pakistan",
    "SG":  "Singapore",
    "ID":  "Indonesia",
    "ME":  "Middle East",
    "VN":  "Vietnam",
    "TW":  "Taiwan",
    "CIS": "CIS",
    "TH":  "Thailand",
    "EU":  "Europe",
    "US":  "United States",
    "NA":  "North America",
    "BR":  "Brazil",
    "SAC": "South America",
    "LK":  "Sri Lanka",
    "RU":  "Russia",
}

# ★ Region → packet type map (xC4.Emote_k অনুযায়ী)
REGION_PACKET_TYPE = {
    "IND": "0514",
    "BD":  "0519",
}
# বাকি সব region = "0515" (default)

# ★ Max UID per request
MAX_UIDS = 4

# ★ Rate limit: এক UID প্রতি কত সেকেন্ড পর পর emote যাবে
EMOTE_COOLDOWN_SEC = 0.15


# ═══════════════════════════════════════════════════════════════
# ★ REGION BOTS (আপনার দেওয়া সব দেশের আইডি এখানে বসানো হলো)
# ═══════════════════════════════════════════════════════════════
REGION_BOTS = {
    "BD": {
        "uid": "8452467687",
        "password": "yasin-bhai-emote-bot"
    },
    "IND": {
        "uid": "8452473786",
        "password": "yasin-bhai-emote-bot"
    },
    "PK": {
        "uid": "8452481328",
        "password": "yasin-bhai-emote-bot"
    },
    "SG": {
        "uid": "8452500922",
        "password": "yasin-bhai-emote-bot"
    },
    "ID": {
        "uid": "8452464187",
        "password": "yasin-bhai-emote-bot"
    },
    "ME": {
        "uid": "8452476131",
        "password": "yasin-bhai-emote-bot"
    },
    "VN": {
        "uid": "8452478696",
        "password": "yasin-bhai-emote-bot"
    },
    "TW": {
        "uid": "8452483492",
        "password": "yasin-bhai-emote-bot"
    },
    "CIS": {
        "uid": "8452588695",
        "password": "3BA408E53E9E14B4414812A0F0634D7AE7D5F14EBA2E3389CC7BBCCDEBF1B6FA"
    },
    "TH": {
        "uid": "8452480008",
        "password": "yasin-bhai-emote-bot"
    },
    "US": {
        "uid": "8452503191",
        "password": "yasin-bhai-emote-bot"
    },
    "NA": {
        "uid": "8452498496",
        "password": "yasin-bhai-emote-bot"
    },
    "BR": {
        "uid": "8452620114",
        "password": "4C4E770DCB6AECEF241B085F7EA7C3C386F3A5E1955A126EBE548C37CFF6177A"
    },
    "SAC": {
        "uid": "8452490326",
        "password": "yasin-bhai-emote-bot"
    },
    "RU": {
        "uid": "8452486739",
        "password": "yasin-bhai-emote-bot"
    }
}