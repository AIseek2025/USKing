from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
    is_body_allowed_for_status_code,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
import logging
import os

from .config import DEV_MODE, assert_production_config, UPLOAD_DIR

from .database import engine, Base
from .models import User, Album, AlbumVideo, SiteSetting, Bookmark, MediaItem, Like, Follow, Comment, Conversation, DirectMessage
from .auth import get_current_user, hash_password
from .database import SessionLocal
from .api import router as api_router

logger = logging.getLogger("meiguwang")

assert_production_config()

Base.metadata.create_all(bind=engine)

# Migrate: add new columns if they don't exist (SQLite dev mode)
def _migrate():
    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("users")}
        for col, default in [("gender", "''"), ("birthday", "''"), ("cover_url", "''")]:
            if col not in cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(512) DEFAULT {default}"))
        if "display_id" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN display_id INTEGER"))
        tables = insp.get_table_names()
        if "posts" in tables:
            pcols = {c["name"] for c in insp.get_columns("posts")}
            if "like_count" not in pcols:
                conn.execute(text("ALTER TABLE posts ADD COLUMN like_count INTEGER DEFAULT 0"))
            if "comment_count" not in pcols:
                conn.execute(text("ALTER TABLE posts ADD COLUMN comment_count INTEGER DEFAULT 0"))
        conn.commit()

try:
    _migrate()
except Exception:
    logger.exception("数据库迁移失败（可忽略若已是最新结构）")

def _backfill_display_id():
    db = SessionLocal()
    try:
        users_without = db.query(User).filter(User.display_id == None).order_by(User.created_at).all()
        if not users_without:
            return
        from sqlalchemy import func
        max_id = db.query(func.max(User.display_id)).scalar() or 0
        for u in users_without:
            max_id += 1
            u.display_id = max_id
        db.commit()
    finally:
        db.close()

try:
    _backfill_display_id()
except Exception:
    logger.exception("display_id 回填失败")

app = FastAPI(title="美股王交易直播平台")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


@app.get("/static/uploads/{filename}")
async def serve_static_upload(filename: str):
    """上传文件在 UPLOAD_DIR（如 Docker 的 /data/uploads），须在 mount /static 之前注册，避免被 /app/static 空目录抢先匹配导致 404。"""
    if len(filename) > 255 or "/" in filename or "\\" in filename or "\x00" in filename:
        raise HTTPException(status_code=404, detail="Not Found")
    path = os.path.join(UPLOAD_DIR, filename)
    real_root = os.path.realpath(UPLOAD_DIR)
    real_file = os.path.realpath(path)
    if not real_file.startswith(real_root + os.sep) and real_file != real_root:
        raise HTTPException(status_code=404, detail="Not Found")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path)


app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
# Serve the live.html capture page
app.mount("/app", StaticFiles(directory=os.path.join(BASE_DIR, "app"), html=True), name="app_static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(api_router)


async def _safe_http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """避免 HTTPException.detail 不可 JSON 序列化时，默认 handler 抛错并回落为纯文本 500。"""
    headers = getattr(exc, "headers", None)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    try:
        return await http_exception_handler(request, exc)
    except (TypeError, ValueError):
        logger.warning("HTTPException.detail 无法序列化为 JSON，已降级为字符串: %r", exc.detail)
        return JSONResponse(
            {"detail": str(exc.detail) if exc.detail is not None else "请求错误"},
            status_code=exc.status_code,
            headers=headers,
        )


async def _safe_request_validation_handler(request: Request, exc: RequestValidationError) -> Response:
    try:
        return await request_validation_exception_handler(request, exc)
    except (TypeError, ValueError):
        logger.exception("RequestValidationError 响应构造失败")
        return JSONResponse(
            status_code=422,
            content={"detail": "请求参数校验失败"},
        )


@app.exception_handler(Exception)
async def _json_exception_handler(request: Request, exc: Exception):
    """避免未捕获异常返回纯文本/HTML，导致前端 JSON.parse 报错。"""
    try:
        if isinstance(exc, StarletteHTTPException):
            return await _safe_http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await _safe_request_validation_handler(request, exc)
        logger.exception("未处理的异常")
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"},
        )
    except Exception:
        logger.exception("异常处理器自身失败")
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"},
        )


def _ensure_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            pw = os.getenv("MEIGUWANG_ADMIN_PASSWORD")
            if not pw and DEV_MODE:
                pw = "admin123"
            if not pw:
                logger.warning(
                    "未创建默认 admin：请设置环境变量 MEIGUWANG_ADMIN_PASSWORD，"
                    "或开发环境设置 DEV_MODE=true（默认）以使用 admin123"
                )
                return
            admin = User(
                username="admin",
                hashed_password=hash_password(pw),
                display_name="管理员",
                is_admin=True,
                email="admin@meiguwang.com",
                email_verified=True,
            )
            db.add(admin)
            db.commit()
            if DEV_MODE and pw == "admin123":
                logger.warning("已创建默认管理员 admin / admin123，切勿用于生产环境")
    finally:
        db.close()


_ensure_admin()


def _ensure_settings():
    db = SessionLocal()
    try:
        if not db.query(SiteSetting).filter(SiteSetting.key == "new_user_live_default").first():
            db.add(SiteSetting(key="new_user_live_default", value="true"))
            db.commit()
    finally:
        db.close()


_ensure_settings()


def _seed_albums():
    db = SessionLocal()
    try:
        if db.query(Album).count() > 0:
            return
        a1 = Album(
            title="美股王核心课程：美股交易策略",
            description="主讲人：王维 老师\n课程章节\n一、美股交易基础及准备\n二、美股王交易技术分析\n三、美股王中长期投资策略\n四、美股王智能短线交易策略",
            sort_order=1,
        )
        db.add(a1)
        db.flush()
        for i, (t, u) in enumerate([
            ("美股王核心课程第一节：美股交易基础及准备",
             "http://v.meigu18.com/video_watch.html?id=a7cf951536194725bfe7e06ff615ea80&index=0"),
            ("美股王核心课程第二节：美股王交易技术分析",
             "http://v.meigu18.com/video_watch.html?id=a7cf951536194725bfe7e06ff615ea80&index=1"),
            ("美股王核心课程第三节：美股王中长期投资策略",
             "http://v.meigu18.com/video_watch.html?id=a7cf951536194725bfe7e06ff615ea80&index=2"),
            ("美股王核心课程第四节：美股王智能短线交易策略",
             "http://v.meigu18.com/video_watch.html?id=a7cf951536194725bfe7e06ff615ea80&index=3"),
        ], 1):
            db.add(AlbumVideo(album_id=a1.id, title=t, video_url=u, sort_order=i))

        a2 = Album(
            title="美股王进阶课程：交易是概率的游戏",
            description="主讲人：王维 老师\n课程章节：\n一、交易是概率的游戏\n二、51法则的原理和应用\n三、不赌季报，久赌必输\n四、风险控制及交易心理\n五、选股 进场 出场技巧",
            sort_order=2,
        )
        db.add(a2)
        db.flush()
        for i, (t, u) in enumerate([
            ("美股王进阶课程第一节：交易是概率的游戏",
             "http://v.meigu18.com/video_watch.html?id=4212514b1f1b42ab8bb1b9de5fe8806e&index=0"),
            ("美股王进阶课程第二节：51法则的原理和应用",
             "http://v.meigu18.com/video_watch.html?id=4212514b1f1b42ab8bb1b9de5fe8806e&index=1"),
            ("美股王进阶课程第三节：不赌季报，久赌必输",
             "http://v.meigu18.com/video_watch.html?id=4212514b1f1b42ab8bb1b9de5fe8806e&index=2"),
            ("美股王进阶课程第四节：风险控制及交易心理",
             "http://v.meigu18.com/video_watch.html?id=4212514b1f1b42ab8bb1b9de5fe8806e&index=3"),
            ("美股王进阶课程第五节：选股 进场 出场技巧",
             "http://v.meigu18.com/video_watch.html?id=4212514b1f1b42ab8bb1b9de5fe8806e&index=4"),
        ], 1):
            db.add(AlbumVideo(album_id=a2.id, title=t, video_url=u, sort_order=i))

        db.commit()
    finally:
        db.close()


_seed_albums()


# --------------- Page Routes ---------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")

@app.get("/u/{username}", response_class=HTMLResponse)
async def user_profile_page(request: Request, username: str):
    return templates.TemplateResponse("profile.html", {"request": request, "username": username})

@app.get("/live/{username}", response_class=HTMLResponse)
async def watch_live(request: Request, username: str):
    return templates.TemplateResponse("watch.html", {"request": request, "username": username})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@app.get("/membership", response_class=HTMLResponse)
async def membership_page(request: Request):
    return templates.TemplateResponse(request, "membership.html")

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(request, "about.html")

@app.get("/software", response_class=HTMLResponse)
async def software_page(request: Request):
    return templates.TemplateResponse(request, "software.html")

@app.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request):
    return templates.TemplateResponse(request, "courses.html")

@app.get("/explore", response_class=HTMLResponse)
async def explore_page(request: Request):
    return templates.TemplateResponse(request, "explore.html")

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse(request, "search.html")

# Partial content routes for SPA panels
@app.get("/partial/about", response_class=HTMLResponse)
async def partial_about(request: Request):
    return templates.TemplateResponse(request, "partials/about_content.html")

@app.get("/partial/member", response_class=HTMLResponse)
async def partial_member(request: Request):
    return templates.TemplateResponse(request, "partials/member_content.html")

@app.get("/partial/software", response_class=HTMLResponse)
async def partial_software(request: Request):
    return templates.TemplateResponse(request, "partials/software_content.html")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html")
