import os

VERSION = "1.3.0"
APP_NAME = "LOLauncher"
REPO_NAME = "ChenglongMa/LOLauncher"

SUPPORTED_PATCH_LINES = ("live", "pbe")

GAME_NAMES = {
    "League of Legends": "league_of_legends",
    "Teamfight Tactics": "teamfighttactics",
    "VALORANT": "valorant",
    "Legends of Runeterra": "bacon",
}

LANGUAGE_PRODUCTS = (GAME_NAMES["League of Legends"], GAME_NAMES["Teamfight Tactics"])

RIOT_DATA_DIR = os.path.join(
    os.environ.get("ProgramData") or os.path.join(os.environ.get("SystemDrive", "C:") + os.sep, "ProgramData"),
    "Riot Games",
)
DEFAULT_METADATA_DIR = os.path.join(RIOT_DATA_DIR, "Metadata")
METADATA_RELATIVE_DIR = os.path.join("ProgramData", "Riot Games", "Metadata")
PRODUCT_SETTINGS_SUFFIX = ".product_settings.yaml"

LOCALE_CODES = {
    "zh_CN": "简体中文（国服）",
    "zh_MY": "简体中文（马来西亚）",
    "zh_TW": "繁体中文",
    "en_US": "英语（美国）",
    "en_GB": "英语（英国）",
    "en_AU": "英语（澳大利亚）",
    "en_PH": "英语（菲律宾）",
    "en_SG": "英语（新加坡）",
    "ja_JP": "日语",
    "ko_KR": "韩语",
    "cs_CZ": "捷克语",
    "de_DE": "德语",
    "el_GR": "希腊语",
    "es_AR": "西班牙语（阿根廷）",
    "es_ES": "西班牙语（西班牙）",
    "es_MX": "西班牙语（墨西哥）",
    "fr_FR": "法语（法国）",
    "hu_HU": "匈牙利语",
    "it_IT": "意大利语",
    "pl_PL": "波兰语",
    "pt_BR": "葡萄牙语（巴西）",
    "ro_RO": "罗马尼亚语",
    "ru_RU": "俄语",
    "th_TH": "泰语",
    "tr_TR": "土耳其语",
    "vi_VN": "越南语",
}

COMMENT_PREFIX = "#"
DEFAULT_QUICK_CHATS = [
    "Hello!",
    "/all press d to see your latency",
    "/all glhf",
    "/all gg",
    "/muteself",
    "/mute all",
    "/remake",
]
QUICK_CHAT_DOC = r"https://www.bilibili.com/read/cv35772066"

HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".lolauncher")
CONFIG_FILENAME = os.path.join(CONFIG_DIR, "config.json")
GUI_CONFIG_FILENAME = os.path.join(CONFIG_DIR, "gui_config.json")
QUICK_CHAT_FILENAME = os.path.join(CONFIG_DIR, "quick_chat.txt")

HOST = "127.0.0.1"
PORT = 65432

