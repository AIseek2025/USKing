import os, secrets

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
