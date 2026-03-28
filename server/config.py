import json
import os
import secrets

_DEFAULT_SECRET = "meiguwang-dev-secret-key-2026-fixed"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
# 生产环境务必设置 SECRET_KEY 与 DEV_MODE=false
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ("1", "true", "yes")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meiguwang.db")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
MEMBERSHIP_PRICE_CENTS = 20000  # $200

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 美股数据面板：FRED / NewsAPI / SEC 请求头 / 自选 RSS（逗号分隔 URL）
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "").strip()
_rss = os.getenv("NEWS_RSS_URLS", "").strip()
NEWS_RSS_URLS = [u.strip() for u in _rss.split(",") if u.strip()]
# 未配置 NewsAPI 且未配置 RSS 时，是否启用内置官方源（SEC 新闻稿 RSS）。设 NEWS_RSS_DISABLE_BUILTIN=1 可关闭。
NEWS_RSS_BUILTIN_DISABLED = os.getenv("NEWS_RSS_DISABLE_BUILTIN", "").lower() in ("1", "true", "yes")
NEWS_RSS_BUILTIN_URLS = (
    ()
    if NEWS_RSS_BUILTIN_DISABLED
    else ("https://www.sec.gov/news/pressreleases.rss",)
)


def effective_news_rss_urls() -> list[str]:
    """已配置自定义 RSS 时仅用自定义；否则若有 NewsAPI 则不拉 RSS；再否则使用内置官方 RSS（如 SEC 新闻稿）。"""
    if NEWS_RSS_URLS:
        return NEWS_RSS_URLS[:8]
    if NEWSAPI_KEY:
        return []
    return list(NEWS_RSS_BUILTIN_URLS)[:8]
# SEC 对 User-Agent 较敏感：勿在默认值中使用 https:// 等易被拦截的片段；生产请改为真实联系邮箱。
SEC_HTTP_USER_AGENT = os.getenv(
    "SEC_HTTP_USER_AGENT",
    "USKing/1.0 (USKing-Data-Panel contact@example.com)",
).strip()

# 免费层公司资讯（需在各官网注册 API Key，零月费；有调用频率限制）
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()

# 直播媒体平面：legacy_jpeg 仅用于 fallback / 诊断；正式方案建议 livekit/agora 等实时媒体后端
LIVE_MEDIA_BACKEND = os.getenv("LIVE_MEDIA_BACKEND", "legacy_jpeg").strip().lower()
LIVE_PUBLISH_MODE = os.getenv("LIVE_PUBLISH_MODE", "legacy_jpeg").strip().lower()
LIVE_PLAYBACK_MODE = os.getenv("LIVE_PLAYBACK_MODE", "legacy_jpeg").strip().lower()
LIVE_FALLBACK_ENABLED = os.getenv("LIVE_FALLBACK_ENABLED", "true").lower() in ("1", "true", "yes")
LIVE_FALLBACK_MODE = os.getenv("LIVE_FALLBACK_MODE", "legacy_jpeg").strip().lower()
LIVE_SIGNALING_URL = os.getenv("LIVE_SIGNALING_URL", "").strip()
LIVE_HLS_BASE_URL = os.getenv("LIVE_HLS_BASE_URL", "").strip()
LIVE_EGRESS_WEBHOOK_SECRET = os.getenv("LIVE_EGRESS_WEBHOOK_SECRET", "").strip()
LIVE_TURN_URLS = [
    u.strip() for u in os.getenv("LIVE_TURN_URLS", "").split(",") if u.strip()
]
# 独立 coturn（TURN REST + static-auth-secret），与 LIVE_TURN_URLS 并存；会话接口会签发 ice_servers
TURN_ENABLED = os.getenv("TURN_ENABLED", "false").lower() in ("1", "true", "yes")
TURN_REALM = os.getenv("TURN_REALM", "").strip()
TURN_SHARED_SECRET = os.getenv("TURN_SHARED_SECRET", "").strip()
TURN_UDP_URL = os.getenv("TURN_UDP_URL", "").strip()
TURN_TLS_URL = os.getenv("TURN_TLS_URL", "").strip()
TURN_CREDENTIAL_TTL_SECONDS = int(os.getenv("TURN_CREDENTIAL_TTL_SECONDS", "86400"))
_turn_stun = os.getenv("TURN_STUN_URLS", "").strip()
TURN_STUN_URLS = [u.strip() for u in _turn_stun.split(",") if u.strip()]
LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "").strip()
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "").strip()
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "").strip()
LIVE_VENDOR_STACK = os.getenv("LIVE_VENDOR_STACK", "livekit_cloud_mux").strip().lower()
LIVE_INTERACTIVE_VENDOR = os.getenv("LIVE_INTERACTIVE_VENDOR", "livekit_cloud").strip().lower()
LIVE_BROADCAST_VENDOR = os.getenv("LIVE_BROADCAST_VENDOR", "global_hls_cdn").strip().lower()
LIVE_RECORDING_VENDOR = os.getenv("LIVE_RECORDING_VENDOR", "mux").strip().lower()
LIVE_DEFAULT_VIEWER_INTENT = os.getenv("LIVE_DEFAULT_VIEWER_INTENT", "auto").strip().lower()
LIVE_MIGRATION_MODE = os.getenv("LIVE_MIGRATION_MODE", "managed_hybrid").strip().lower()
LIVE_INTERACTIVE_ROLLOUT_PERCENT = max(
    0,
    min(100, int(os.getenv("LIVE_INTERACTIVE_ROLLOUT_PERCENT", "100") or "100")),
)
LIVE_INTERACTIVE_AUTHENTICATED_ONLY = os.getenv(
    "LIVE_INTERACTIVE_AUTHENTICATED_ONLY", "false"
).lower() in ("1", "true", "yes")


def _csv_env(name: str) -> list[str]:
    return [u.strip() for u in os.getenv(name, "").split(",") if u.strip()]


def _json_env(name: str) -> dict[str, object]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


LIVE_CANARY_USERS = _csv_env("LIVE_CANARY_USERS")
LIVE_FORCE_INTERACTIVE_USERS = _csv_env("LIVE_FORCE_INTERACTIVE_USERS")
LIVE_FORCE_BROADCAST_COUNTRIES = [c.upper() for c in _csv_env("LIVE_FORCE_BROADCAST_COUNTRIES")]
LIVE_CANARY_COUNTRIES = [c.upper() for c in _csv_env("LIVE_CANARY_COUNTRIES")]
LIVE_RTC_REGION_WS_URLS = _json_env("LIVE_RTC_REGION_WS_URLS")
LIVE_HLS_REGION_BASE_URLS = _json_env("LIVE_HLS_REGION_BASE_URLS")
LIVE_TURN_REGION_URLS = _json_env("LIVE_TURN_REGION_URLS")
LIVE_REGION_HINT_MAP = _json_env("LIVE_REGION_HINT_MAP")
REDIS_URL = os.getenv("REDIS_URL", "").strip()

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# 生产可挂载卷并设置 UPLOAD_DIR=/data/uploads（须为绝对路径）
_UP = os.getenv("UPLOAD_DIR", "").strip()
UPLOAD_DIR = _UP if _UP else os.path.join(_BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024
ALLOWED_IMAGE_EXT = frozenset({
    "jpg", "jpeg", "png", "gif", "webp", "jfif", "pjpeg", "pjp",
    "heic", "heif", "bmp", "avif",
})
ALLOWED_MEDIA_EXT = frozenset(
    {"jpg", "jpeg", "png", "gif", "webp", "jfif", "pjpeg", "pjp", "heic", "heif", "bmp", "avif", "mp4", "mov", "webm"}
)


def assert_production_config() -> None:
    """生产环境启动前校验，避免误用默认密钥。"""
    if DEV_MODE:
        return
    if SECRET_KEY == _DEFAULT_SECRET:
        raise RuntimeError(
            "生产环境必须设置环境变量 SECRET_KEY（勿使用仓库默认值）。"
            "示例: export SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")"
        )
