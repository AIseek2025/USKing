import json, logging, math, random, re, string, uuid, os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, field_validator

from sqlalchemy import or_, and_, func, cast, String
from .database import get_db, engine
from .models import User, EmailCode, Post, LiveStream, Payment, Banner, Album, AlbumVideo, SiteSetting, Bookmark, MediaItem, Like, Follow, Comment, Conversation, DirectMessage, utcnow
from .auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_user, require_admin,
)
from .config import (
    UPLOAD_DIR,
    DEV_MODE,
    MAX_UPLOAD_BYTES,
    ALLOWED_IMAGE_EXT,
    ALLOWED_MEDIA_EXT,
)
from .routes_us_market import router as _us_market_router

router = APIRouter(prefix="/api")
router.include_router(_us_market_router)
_api_log = logging.getLogger("meiguwang.api")


def _upload_ext(filename: Optional[str]) -> str:
    fn = filename or ""
    return fn.rsplit(".", 1)[-1].lower() if "." in fn else ""


def _sniff_image_ext(data: bytes) -> Optional[str]:
    """当文件名无后缀或后缀不在白名单时，用文件头判断常见图片格式。"""
    if not data:
        return None
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 2 and data[:2] == b"BM":
        return "bmp"
    if len(data) >= 32 and data[4:8] == b"ftyp":
        brands = data[8:32]
        if b"avif" in brands or b"avis" in brands:
            return "avif"
        if b"heic" in brands or b"heix" in brands or b"hevc" in brands:
            return "heic"
        if b"mif1" in brands or b"msf1" in brands:
            return "heic"
    return None


def _resolve_image_ext(filename: Optional[str], data: bytes) -> str:
    ext = _upload_ext(filename)
    if ext in ALLOWED_IMAGE_EXT:
        return ext
    sniffed = _sniff_image_ext(data)
    if sniffed and sniffed in ALLOWED_IMAGE_EXT:
        return sniffed
    raise HTTPException(
        400,
        "不支持的图片格式，请使用 jpg、png、gif、webp、heic 等常见图片",
    )


def _assert_upload_size(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(400, f"文件过大（最大 {mb}MB）")


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    return row.value if row else default


def _set_setting(db: Session, key: str, value: str):
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SiteSetting(key=key, value=value))
    db.commit()


# --------------- Schemas ---------------

class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    email_code: Optional[str] = None

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()

class LoginReq(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class EmailCodeReq(BaseModel):
    email: str
    purpose: str = "register"

class BindEmailReq(BaseModel):
    email: str
    code: str

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

class PostCreate(BaseModel):
    content: str
    media_urls: Optional[List[str]] = None


class PostMediaUrlBody(BaseModel):
    url: str

class StreamUpdate(BaseModel):
    title: Optional[str] = None
    is_live: Optional[bool] = None

class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    live_enabled: Optional[bool] = None
    is_member: Optional[bool] = None
    is_admin: Optional[bool] = None

class AIChatReq(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    lang: Optional[str] = Field(None, description="zh or en — sets assistant language")

# --------------- Auth ---------------

@router.post("/auth/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "用户名已被注册")

    email_verified = False
    email = None
    if req.email:
        if db.query(User).filter(User.email == req.email).first():
            raise HTTPException(400, "该邮箱已被注册")
        if not req.email_code:
            raise HTTPException(400, "请提供邮箱验证码")
        code_row = (db.query(EmailCode)
                    .filter(EmailCode.email == req.email, EmailCode.purpose == "register",
                            EmailCode.used == False)
                    .order_by(EmailCode.created_at.desc()).first())
        if not code_row or code_row.code != req.email_code:
            raise HTTPException(400, "验证码错误")
        age = (utcnow() - code_row.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        if age > 600:
            raise HTTPException(400, "验证码已过期")
        code_row.used = True
        email = req.email
        email_verified = True

    live_default = _get_setting(db, "new_user_live_default", "true") == "true"
    max_did = db.query(func.max(User.display_id)).scalar() or 0
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        email=email,
        email_verified=email_verified,
        display_name=req.username,
        live_enabled=live_default,
        display_id=max_did + 1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return {"token": token, "user": _user_dict(user)}


@router.post("/auth/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = None
    if req.username:
        user = db.query(User).filter(User.username == req.username).first()
    elif req.email:
        user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(400, "用户名/邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账户已被禁用")
    token = create_access_token(user.id)
    return {"token": token, "user": _user_dict(user)}


@router.post("/auth/send-code")
def send_email_code(req: EmailCodeReq, db: Session = Depends(get_db)):
    code = "".join(random.choices(string.digits, k=6))
    row = EmailCode(email=req.email, code=code, purpose=req.purpose)
    db.add(row)
    db.commit()
    # 生产环境应通过 SMTP 发送；仅在 DEV_MODE 下回传验证码便于本地调试
    out: dict = {"ok": True}
    if DEV_MODE:
        out["dev_code"] = code
    return out


@router.post("/auth/bind-email")
def bind_email(req: BindEmailReq, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email, User.id != user.id).first():
        raise HTTPException(400, "该邮箱已被其他账户绑定")
    code_row = (db.query(EmailCode)
                .filter(EmailCode.email == req.email, EmailCode.purpose == "bind",
                        EmailCode.used == False)
                .order_by(EmailCode.created_at.desc()).first())
    if not code_row or code_row.code != req.code:
        raise HTTPException(400, "验证码错误")
    code_row.used = True
    user.email = req.email
    user.email_verified = True
    db.commit()
    return {"ok": True}


class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str

@router.post("/auth/change-password")
def change_password(req: ChangePasswordReq, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not verify_password(req.old_password, user.hashed_password):
        raise HTTPException(400, "当前密码错误")
    if len(req.new_password) < 6:
        raise HTTPException(400, "新密码至少6个字符")
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"ok": True}

@router.get("/auth/me")
def get_me(user: Optional[User] = Depends(get_current_user)):
    if not user:
        return {"user": None}
    return {"user": _user_dict(user)}

# --------------- Profile ---------------

@router.get("/user/{username}")
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return {"user": _user_dict(user)}


@router.put("/user/profile")
def update_profile(req: ProfileUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    for field in ["display_name", "bio", "gender", "birthday", "location", "website"]:
        val = getattr(req, field)
        if val is not None:
            setattr(user, field, val)
    db.commit()
    return {"user": _user_dict(user)}


@router.post("/user/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        data = await file.read()
        _assert_upload_size(data)
        ext = _resolve_image_ext(file.filename, data)
        fname = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            f.write(data)
        user.avatar_url = f"/static/uploads/{fname}"
        db.commit()
        return {"avatar_url": user.avatar_url}
    except HTTPException:
        raise
    except OSError:
        _api_log.exception("avatar 写入磁盘失败")
        raise HTTPException(500, "无法保存头像，请检查服务器上传目录权限与磁盘空间")
    except Exception:
        _api_log.exception("avatar 上传异常")
        raise HTTPException(500, "头像上传失败，请稍后重试")


@router.post("/user/cover")
async def upload_cover(file: UploadFile = File(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        data = await file.read()
        _assert_upload_size(data)
        ext = _resolve_image_ext(file.filename, data)
        fname = f"cover_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            f.write(data)
        user.cover_url = f"/static/uploads/{fname}"
        db.commit()
        return {"cover_url": user.cover_url}
    except HTTPException:
        raise
    except OSError:
        _api_log.exception("cover 写入磁盘失败")
        raise HTTPException(500, "无法保存封面，请检查服务器上传目录权限与磁盘空间")
    except Exception:
        _api_log.exception("cover 上传异常")
        raise HTTPException(500, "封面上传失败，请稍后重试")

# --------------- Posts (动态) ---------------

@router.post("/posts")
def create_post(req: PostCreate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    post = Post(
        user_id=user.id,
        content=req.content,
        media_urls=json.dumps(req.media_urls or []),
    )
    db.add(post)
    db.flush()
    for url in (req.media_urls or []):
        ext = url.rsplit(".", 1)[-1].lower() if "." in url else ""
        mtype = "video" if ext in ("mp4", "mov", "webm") else "image"
        db.add(MediaItem(post_id=post.id, user_id=user.id, media_url=url,
                         media_type=mtype, caption=req.content or ""))
    db.commit()
    db.refresh(post)
    return {"post": _post_dict(post, user)}


@router.get("/posts/user/{username}")
def get_user_posts(username: str, db: Session = Depends(get_db), current: Optional[User] = Depends(get_current_user)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    posts = (db.query(Post).filter(Post.user_id == user.id, Post.hidden == False)
             .order_by(Post.created_at.desc()).limit(50).all())
    return {"posts": [_post_dict(p, user) for p in posts]}


def _delete_upload_if_local(url: str) -> None:
    if not url or not isinstance(url, str):
        return
    u = url.strip()
    if not u.startswith("/static/uploads/"):
        return
    fname = u.rsplit("/", 1)[-1]
    if not fname or ".." in fname or "/" in fname or "\\" in fname:
        return
    base = os.path.normpath(os.path.abspath(UPLOAD_DIR))
    path = os.path.normpath(os.path.join(UPLOAD_DIR, fname))
    if not path.startswith(base):
        return
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            _api_log.warning("无法删除上传文件: %s", path)


@router.get("/posts/{post_id}")
def get_single_post(post_id: int, db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p or p.hidden:
        raise HTTPException(404, "动态不存在")
    author = db.query(User).filter(User.id == p.user_id).first()
    return {"post": _post_dict(p, author)}


@router.post("/posts/{post_id}/media/remove")
def remove_post_media_item(
    post_id: int,
    body: PostMediaUrlBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "动态不存在")
    if post.user_id != user.id:
        raise HTTPException(403, "无权修改")
    urls = json.loads(post.media_urls) if post.media_urls else []
    if body.url not in urls:
        raise HTTPException(400, "该媒体不属于此动态")
    new_urls = [u for u in urls if u != body.url]
    post.media_urls = json.dumps(new_urls)
    db.query(MediaItem).filter(
        MediaItem.post_id == post.id, MediaItem.media_url == body.url
    ).delete(synchronize_session=False)
    db.commit()
    _delete_upload_if_local(body.url)
    db.refresh(post)
    author = db.query(User).filter(User.id == post.user_id).first()
    return {"post": _post_dict(post, author)}


@router.post("/posts/{post_id}/media/cover")
def set_post_media_cover(
    post_id: int,
    body: PostMediaUrlBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "动态不存在")
    if post.user_id != user.id:
        raise HTTPException(403, "无权修改")
    urls = json.loads(post.media_urls) if post.media_urls else []
    if body.url not in urls:
        raise HTTPException(400, "该媒体不属于此动态")
    new_urls = [body.url] + [u for u in urls if u != body.url]
    post.media_urls = json.dumps(new_urls)
    db.commit()
    db.refresh(post)
    author = db.query(User).filter(User.id == post.user_id).first()
    return {"post": _post_dict(post, author)}


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404)
    if post.user_id != user.id and not user.is_admin:
        raise HTTPException(403)
    urls = json.loads(post.media_urls) if post.media_urls else []
    for u in urls:
        _delete_upload_if_local(u)
    db.query(Comment).filter(Comment.post_id == post.id).delete(synchronize_session=False)
    db.query(Like).filter(Like.post_id == post.id).delete(synchronize_session=False)
    db.query(Bookmark).filter(Bookmark.post_id == post.id).delete(synchronize_session=False)
    db.query(MediaItem).filter(MediaItem.post_id == post.id).delete(synchronize_session=False)
    db.delete(post)
    db.commit()
    return {"ok": True}


@router.get("/posts/feed")
def get_feed(
    limit: int = Query(40, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Public feed of all non-hidden posts sorted by view_count desc."""
    posts = (db.query(Post).filter(Post.hidden == False)
             .order_by(Post.view_count.desc(), Post.created_at.desc())
             .limit(limit).all())
    user_ids = list({p.user_id for p in posts})
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    bookmarked = set()
    if user:
        bookmarked = {b.post_id for b in db.query(Bookmark).filter(Bookmark.user_id == user.id, Bookmark.post_id.in_([p.id for p in posts])).all()}
    return {"posts": [_post_dict(p, users_map.get(p.user_id), bookmarked=p.id in bookmarked) for p in posts]}


@router.post("/posts/{post_id}/view")
def post_view(post_id: int, db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if p:
        p.view_count = (p.view_count or 0) + 1
        db.commit()
    return {"ok": True}


@router.post("/posts/{post_id}/bookmark")
def toggle_bookmark(post_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    existing = db.query(Bookmark).filter(Bookmark.user_id == user.id, Bookmark.post_id == post_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"bookmarked": False}
    db.add(Bookmark(user_id=user.id, post_id=post_id))
    db.commit()
    return {"bookmarked": True}


@router.get("/posts/bookmarks")
def get_bookmarks(user: User = Depends(require_user), db: Session = Depends(get_db)):
    bms = db.query(Bookmark).filter(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc()).limit(100).all()
    post_ids = [b.post_id for b in bms]
    posts = db.query(Post).filter(Post.id.in_(post_ids), Post.hidden == False).all() if post_ids else []
    posts_map = {p.id: p for p in posts}
    ordered = [posts_map[pid] for pid in post_ids if pid in posts_map]
    user_ids = list({p.user_id for p in ordered})
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    return {"posts": [_post_dict(p, users_map.get(p.user_id), bookmarked=True) for p in ordered]}


# --------------- Like ---------------
@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    existing = db.query(Like).filter(Like.user_id == user.id, Like.post_id == post_id).first()
    if existing:
        db.delete(existing)
        post.like_count = max((post.like_count or 0) - 1, 0)
        db.commit()
        return {"liked": False, "like_count": post.like_count}
    db.add(Like(user_id=user.id, post_id=post_id))
    post.like_count = (post.like_count or 0) + 1
    db.commit()
    return {"liked": True, "like_count": post.like_count}


# --------------- Follow ---------------
@router.post("/user/{user_id}/follow")
def toggle_follow(user_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(400, "不能关注自己")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "用户不存在")
    existing = db.query(Follow).filter(Follow.follower_id == user.id, Follow.following_id == user_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"following": False}
    db.add(Follow(follower_id=user.id, following_id=user_id))
    db.commit()
    return {"following": True}


@router.get("/user/{username}/followers")
def get_followers(username: str, db: Session = Depends(get_db)):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, "用户不存在")
    follows = db.query(Follow).filter(Follow.following_id == target.id).order_by(Follow.created_at.desc()).limit(200).all()
    follower_ids = [f.follower_id for f in follows]
    users = db.query(User).filter(User.id.in_(follower_ids)).all() if follower_ids else []
    users_map = {u.id: u for u in users}
    return {"followers": [_user_dict(users_map[fid]) for fid in follower_ids if fid in users_map],
            "count": len(follows)}


@router.get("/user/{username}/following")
def get_following(username: str, db: Session = Depends(get_db)):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, "用户不存在")
    follows = db.query(Follow).filter(Follow.follower_id == target.id).order_by(Follow.created_at.desc()).limit(200).all()
    following_ids = [f.following_id for f in follows]
    users = db.query(User).filter(User.id.in_(following_ids)).all() if following_ids else []
    users_map = {u.id: u for u in users}
    return {"following": [_user_dict(users_map[fid]) for fid in following_ids if fid in users_map],
            "count": len(follows)}


@router.get("/user/{username}/social")
def get_social_counts(username: str, current: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(404, "用户不存在")
    followers = db.query(Follow).filter(Follow.following_id == target.id).count()
    following = db.query(Follow).filter(Follow.follower_id == target.id).count()
    is_following = False
    if current:
        is_following = db.query(Follow).filter(Follow.follower_id == current.id, Follow.following_id == target.id).first() is not None
    return {"followers": followers, "following": following, "is_following": is_following}


# --------------- Explore / Recommendation Feed ---------------

def _compute_score(m: MediaItem) -> float:
    """
    Recommendation score blending engagement quality + freshness.
    - avg_watch = total_watch_ms / max(impressions,1)
    - completion_rate = completions / max(impressions,1)
    - engagement = (avg_watch / 5000) * 0.4 + completion_rate * 0.6  (0~1 range approx)
    - freshness boost: new items (<6h) get a bonus so every post reaches users
    - decay: old low-engagement items decay over days
    """
    imp = max(m.impressions or 0, 1)
    avg_watch = (m.total_watch_ms or 0) / imp
    comp_rate = (m.completions or 0) / imp
    engagement = min(avg_watch / 5000, 1.0) * 0.4 + min(comp_rate, 1.0) * 0.6

    age_h = max((utcnow() - m.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600, 0.01)
    freshness = max(0, 1.0 - age_h / 72)

    if (m.impressions or 0) < 20:
        new_boost = 0.5 * (1.0 - (m.impressions or 0) / 20)
    else:
        new_boost = 0.0

    popularity = math.log2(max(m.impressions or 0, 1) + 1) / 15
    score = engagement * 0.45 + freshness * 0.25 + new_boost * 0.2 + popularity * 0.1
    return round(score, 6)


@router.get("/explore/feed")
def explore_feed(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=50_000),
    current: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    TikTok-style feed: video-only; each video media item is one entry (images excluded).
    """
    items = (db.query(MediaItem)
             .join(Post).filter(Post.hidden == False, MediaItem.media_type == "video")
             .order_by(MediaItem.score.desc(), MediaItem.created_at.desc())
             .offset(offset).limit(limit).all())
    user_ids = list({i.user_id for i in items})
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    post_ids = list({i.post_id for i in items})
    posts_map = {p.id: p for p in db.query(Post).filter(Post.id.in_(post_ids)).all()} if post_ids else {}
    liked_set = set()
    bookmarked_set = set()
    following_set = set()
    if current:
        liked_set = {lk.post_id for lk in db.query(Like).filter(Like.user_id == current.id, Like.post_id.in_(post_ids)).all()}
        bookmarked_set = {b.post_id for b in db.query(Bookmark).filter(Bookmark.user_id == current.id, Bookmark.post_id.in_(post_ids)).all()}
        following_set = {f.following_id for f in db.query(Follow).filter(Follow.follower_id == current.id, Follow.following_id.in_(user_ids)).all()}
    result = []
    for m in items:
        u = users_map.get(m.user_id)
        p = posts_map.get(m.post_id)
        result.append({
            "id": m.id, "post_id": m.post_id, "media_url": m.media_url,
            "media_type": m.media_type, "caption": m.caption,
            "impressions": m.impressions or 0,
            "like_count": p.like_count or 0 if p else 0,
            "comment_count": p.comment_count or 0 if p else 0,
            "liked": m.post_id in liked_set,
            "bookmarked": m.post_id in bookmarked_set,
            "author_following": m.user_id in following_set,
            "score": m.score or 0,
            "created_at": m.created_at.isoformat(),
            "author": _user_dict(u) if u else None,
        })
    return {"items": result}


@router.get("/featured/feed")
def featured_feed(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=50_000),
    db: Session = Depends(get_db),
):
    """
    Featured feed for the "精选" page (video-only user posts, no images).
    Algorithm: all new videos get exposure; high-engagement items get priority;
    the hottest recent item is marked as 'hero'.
    Returns items with a 'rank' field: 0 = hero (big video), 1+ = normal grid.
    """
    items = (db.query(MediaItem)
             .join(Post).filter(Post.hidden == False, MediaItem.media_type == "video")
             .order_by(MediaItem.score.desc(), MediaItem.created_at.desc())
             .offset(offset).limit(limit).all())
    user_ids = list({i.user_id for i in items})
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    post_ids = list({i.post_id for i in items})
    posts_map = {p.id: p for p in db.query(Post).filter(Post.id.in_(post_ids)).all()} if post_ids else {}
    result = []
    for idx, m in enumerate(items):
        u = users_map.get(m.user_id)
        p = posts_map.get(m.post_id)
        result.append({
            "id": m.id, "post_id": m.post_id, "media_url": m.media_url,
            "media_type": m.media_type, "caption": m.caption,
            "impressions": m.impressions or 0,
            "like_count": p.like_count or 0 if p else 0,
            "score": m.score or 0,
            "created_at": m.created_at.isoformat(),
            "author": _user_dict(u) if u else None,
        })
    return {"items": result}


class EngagementReport(BaseModel):
    media_id: int
    watch_ms: int = Field(0, ge=0, le=3_600_000)
    completed: bool = False


@router.post("/explore/engage")
def report_engagement(req: EngagementReport, db: Session = Depends(get_db)):
    m = db.query(MediaItem).filter(MediaItem.id == req.media_id).first()
    if not m:
        return {"ok": False}
    m.impressions = (m.impressions or 0) + 1
    m.total_watch_ms = (m.total_watch_ms or 0) + max(req.watch_ms, 0)
    if req.completed:
        m.completions = (m.completions or 0) + 1
    m.score = _compute_score(m)
    db.commit()
    return {"ok": True, "new_score": m.score}


@router.post("/upload")
async def upload_media(file: UploadFile = File(...), user: User = Depends(require_user)):
    ext = _upload_ext(file.filename)
    if not ext or ext not in ALLOWED_MEDIA_EXT:
        raise HTTPException(400, "仅支持图片或视频：jpg/png/gif/webp、mp4/mov/webm")
    fname = f"media_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    data = await file.read()
    _assert_upload_size(data)
    with open(path, "wb") as f:
        f.write(data)
    return {"url": f"/static/uploads/{fname}"}

# --------------- Live Streaming ---------------

@router.post("/live/start")
def start_stream(req: StreamUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not user.live_enabled:
        raise HTTPException(403, "直播权限已被关闭，请联系管理员")
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    if stream:
        stream.title = req.title or stream.title
        db.commit()
        return {"stream": _stream_dict(stream)}
    stream = LiveStream(user_id=user.id, title=req.title or f"{user.display_name}的直播", is_live=True, started_at=utcnow())
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return {"stream": _stream_dict(stream)}


@router.post("/live/stop")
def stop_stream(user: User = Depends(require_user), db: Session = Depends(get_db)):
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    if stream:
        stream.is_live = False
        stream.ended_at = utcnow()
        db.commit()
    return {"ok": True}


@router.post("/live/heartbeat")
def live_heartbeat(user: User = Depends(require_user), db: Session = Depends(get_db)):
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    if stream:
        stream.viewer_count = max(0, stream.viewer_count)
    return {"ok": True}


@router.get("/live/active")
def get_active_streams(db: Session = Depends(get_db)):
    streams = (db.query(LiveStream).filter(LiveStream.is_live == True)
               .order_by(LiveStream.viewer_count.desc()).limit(50).all())
    result = []
    for s in streams:
        user = db.query(User).filter(User.id == s.user_id).first()
        d = _stream_dict(s)
        d["user"] = _user_dict(user) if user else None
        result.append(d)
    return {"streams": result}


@router.get("/live/user/{username}")
def get_user_stream(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404)
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    return {"stream": _stream_dict(stream) if stream else None, "user": _user_dict(user)}


@router.post("/live/join/{username}")
def join_stream(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404)
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    if stream:
        stream.viewer_count = (stream.viewer_count or 0) + 1
        db.commit()
    return {"ok": True}


@router.post("/live/leave/{username}")
def leave_stream(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404)
    stream = db.query(LiveStream).filter(LiveStream.user_id == user.id, LiveStream.is_live == True).first()
    if stream and stream.viewer_count > 0:
        stream.viewer_count -= 1
        db.commit()
    return {"ok": True}

# --------------- Payment / Membership ---------------

@router.post("/payment/create-session")
def create_payment_session(user: User = Depends(require_user), db: Session = Depends(get_db)):
    payment = Payment(user_id=user.id, amount_cents=20000, currency="usd", status="pending")
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {"payment_id": payment.id, "message": "支付功能演示 — 生产环境将接入 Stripe Checkout"}


@router.post("/payment/demo-complete/{payment_id}")
def demo_complete_payment(payment_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.user_id == user.id).first()
    if not payment:
        raise HTTPException(404)
    now = utcnow()
    payment.status = "paid"
    payment.membership_start = now
    payment.membership_end = now + timedelta(days=365)
    user.is_member = True
    user.member_until = payment.membership_end
    db.commit()
    return {"ok": True, "member_until": payment.membership_end.isoformat()}

# --------------- Admin ---------------

@router.get("/admin/users")
def admin_list_users(page: int = 1, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return {"total": total, "page": page, "users": [_user_dict(u, admin=True) for u in users]}


@router.put("/admin/user/{user_id}")
def admin_update_user(user_id: str, req: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404)
    for field in ["is_active", "live_enabled", "is_member", "is_admin"]:
        val = getattr(req, field)
        if val is not None:
            setattr(user, field, val)
    db.commit()
    return {"user": _user_dict(user, admin=True)}


@router.get("/admin/posts")
def admin_list_posts(page: int = 1, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total = db.query(Post).count()
    posts = db.query(Post).order_by(Post.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.user_id).first()
        result.append(_post_dict(p, author, admin=True))
    return {"total": total, "page": page, "posts": result}


@router.put("/admin/post/{post_id}/hide")
def admin_hide_post(post_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404)
    post.hidden = not post.hidden
    db.commit()
    return {"hidden": post.hidden}


@router.delete("/admin/post/{post_id}")
def admin_delete_post(post_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404)
    db.delete(post)
    db.commit()
    return {"ok": True}


@router.get("/admin/streams")
def admin_list_streams(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    streams = db.query(LiveStream).order_by(LiveStream.started_at.desc()).limit(50).all()
    result = []
    for s in streams:
        user = db.query(User).filter(User.id == s.user_id).first()
        d = _stream_dict(s)
        d["user"] = _user_dict(user) if user else None
        result.append(d)
    return {"streams": result}


@router.put("/admin/stream/{stream_id}/stop")
def admin_stop_stream(stream_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(404)
    stream.is_live = False
    stream.ended_at = utcnow()
    db.commit()
    return {"ok": True}


# --------------- Admin: Live Permission Control ---------------

@router.get("/admin/live-settings")
def admin_get_live_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    new_default = _get_setting(db, "new_user_live_default", "true")
    total_users = db.query(User).filter(User.is_admin == False).count()
    enabled_count = db.query(User).filter(User.is_admin == False, User.live_enabled == True).count()
    disabled_count = total_users - enabled_count
    return {
        "new_user_live_default": new_default == "true",
        "total_users": total_users,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
    }


@router.put("/admin/live-settings/new-default")
def admin_set_new_user_default(enable: bool = True, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _set_setting(db, "new_user_live_default", "true" if enable else "false")
    return {"ok": True, "new_user_live_default": enable}


@router.put("/admin/live-settings/enable-all")
def admin_enable_all_live(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = db.query(User).filter(User.is_admin == False, User.live_enabled == False).update({"live_enabled": True})
    db.commit()
    return {"ok": True, "affected": count}


@router.put("/admin/live-settings/disable-all")
def admin_disable_all_live(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = db.query(User).filter(User.is_admin == False, User.live_enabled == True).update({"live_enabled": False})
    db.commit()
    return {"ok": True, "affected": count}


@router.get("/admin/payments")
def admin_list_payments(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(100).all()
    result = []
    for p in payments:
        user = db.query(User).filter(User.id == p.user_id).first()
        result.append({
            "id": p.id, "user": _user_dict(user) if user else None,
            "amount": p.amount_cents / 100, "currency": p.currency,
            "status": p.status,
            "membership_start": p.membership_start.isoformat() if p.membership_start else None,
            "membership_end": p.membership_end.isoformat() if p.membership_end else None,
            "created_at": p.created_at.isoformat(),
        })
    return {"payments": result}

# --------------- Banners ---------------

@router.get("/banners")
def get_banners(db: Session = Depends(get_db)):
    banners = db.query(Banner).filter(Banner.is_active == True).order_by(Banner.sort_order, Banner.id.desc()).all()
    return {"banners": [{"id": b.id, "image_url": b.image_url, "link_url": b.link_url, "title": b.title} for b in banners]}


@router.post("/admin/banners")
async def admin_upload_banner(
    file: UploadFile = File(...),
    title: str = Form(""),
    link_url: str = Form(""),
    sort_order: int = Form(0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    fname = f"banner_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    data = await file.read()
    with open(path, "wb") as f:
        f.write(data)
    banner = Banner(image_url=f"/static/uploads/{fname}", title=title, link_url=link_url, sort_order=sort_order)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return {"id": banner.id, "image_url": banner.image_url}


@router.get("/admin/banners")
def admin_list_banners(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    banners = db.query(Banner).order_by(Banner.sort_order, Banner.id.desc()).all()
    return {"banners": [{"id": b.id, "image_url": b.image_url, "link_url": b.link_url, "title": b.title, "sort_order": b.sort_order, "is_active": b.is_active} for b in banners]}


@router.put("/admin/banners/{banner_id}")
def admin_update_banner(banner_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    b = db.query(Banner).filter(Banner.id == banner_id).first()
    if not b:
        raise HTTPException(404)
    b.is_active = not b.is_active
    db.commit()
    return {"ok": True, "is_active": b.is_active}


@router.delete("/admin/banners/{banner_id}")
def admin_delete_banner(banner_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    b = db.query(Banner).filter(Banner.id == banner_id).first()
    if not b:
        raise HTTPException(404)
    db.delete(b)
    db.commit()
    return {"ok": True}


# --------------- Albums / Courses ---------------

class AlbumCreate(BaseModel):
    title: str
    description: str = ""
    cover_url: str = ""
    sort_order: int = 0

class AlbumVideoCreate(BaseModel):
    title: str
    video_url: str
    sort_order: int = 0


@router.get("/albums")
def list_albums(db: Session = Depends(get_db)):
    albums = (db.query(Album).filter(Album.is_active == True)
              .order_by(Album.sort_order, Album.id.desc()).all())
    return {"albums": [_album_dict(a) for a in albums]}


@router.get("/albums/{album_id}")
def get_album(album_id: int, db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(404)
    return {"album": _album_dict(album)}


@router.get("/videos/popular")
def get_popular_videos(limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db)):
    """All videos from active albums, sorted by view_count desc."""
    videos = (db.query(AlbumVideo)
              .join(Album).filter(Album.is_active == True)
              .order_by(AlbumVideo.view_count.desc())
              .limit(limit).all())
    return {"videos": [_video_dict(v) for v in videos]}


@router.post("/videos/{video_id}/view")
def increment_view(video_id: int, db: Session = Depends(get_db)):
    v = db.query(AlbumVideo).filter(AlbumVideo.id == video_id).first()
    if v:
        v.view_count = (v.view_count or 0) + 1
        db.commit()
    return {"ok": True}


@router.post("/admin/albums")
def admin_create_album(req: AlbumCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    album = Album(title=req.title, description=req.description, cover_url=req.cover_url, sort_order=req.sort_order)
    db.add(album)
    db.commit()
    db.refresh(album)
    return {"album": _album_dict(album)}


@router.put("/admin/albums/{album_id}")
def admin_update_album(album_id: int, req: AlbumCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(404)
    album.title = req.title
    album.description = req.description
    album.cover_url = req.cover_url
    album.sort_order = req.sort_order
    db.commit()
    return {"album": _album_dict(album)}


@router.put("/admin/albums/{album_id}/toggle")
def admin_toggle_album(album_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(404)
    album.is_active = not album.is_active
    db.commit()
    return {"ok": True, "is_active": album.is_active}


@router.delete("/admin/albums/{album_id}")
def admin_delete_album(album_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(404)
    db.delete(album)
    db.commit()
    return {"ok": True}


@router.get("/admin/albums")
def admin_list_albums(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    albums = db.query(Album).order_by(Album.sort_order, Album.id.desc()).all()
    return {"albums": [_album_dict(a) for a in albums]}


@router.post("/admin/albums/{album_id}/videos")
def admin_add_video(album_id: int, req: AlbumVideoCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(404, "专辑不存在")
    video = AlbumVideo(album_id=album_id, title=req.title, video_url=req.video_url, sort_order=req.sort_order)
    db.add(video)
    db.commit()
    db.refresh(video)
    return {"video": _video_dict(video)}


@router.delete("/admin/albums/videos/{video_id}")
def admin_delete_video(video_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    v = db.query(AlbumVideo).filter(AlbumVideo.id == video_id).first()
    if not v:
        raise HTTPException(404)
    db.delete(v)
    db.commit()
    return {"ok": True}


def _album_dict(a: Album) -> dict:
    return {
        "id": a.id, "title": a.title, "description": a.description,
        "cover_url": a.cover_url, "sort_order": a.sort_order, "is_active": a.is_active,
        "created_at": a.created_at.isoformat(),
        "videos": [_video_dict(v) for v in a.videos],
        "video_count": len(a.videos),
    }


def _video_dict(v: AlbumVideo) -> dict:
    return {
        "id": v.id, "album_id": v.album_id, "title": v.title,
        "video_url": v.video_url, "sort_order": v.sort_order,
        "view_count": v.view_count or 0,
        "album_title": v.album.title if v.album else "",
    }


# --------------- Comments ---------------

@router.get("/posts/{post_id}/comments")
def list_comments(
    post_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10_000),
    db: Session = Depends(get_db),
):
    comments = db.query(Comment).filter(Comment.post_id == post_id, Comment.parent_id == None)\
        .order_by(Comment.created_at.desc()).offset(offset).limit(limit).all()
    user_ids = list({c.user_id for c in comments})
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    total = db.query(Comment).filter(Comment.post_id == post_id).count()
    result = []
    for c in comments:
        u = users_map.get(c.user_id)
        replies = db.query(Comment).filter(Comment.parent_id == c.id).order_by(Comment.created_at.asc()).limit(3).all()
        reply_users = {r.user_id for r in replies}
        reply_users_map = {u2.id: u2 for u2 in db.query(User).filter(User.id.in_(list(reply_users))).all()} if reply_users else {}
        result.append({
            "id": c.id, "content": c.content,
            "like_count": c.like_count or 0,
            "created_at": c.created_at.isoformat(),
            "author": {"id": u.id, "username": u.username, "display_name": u.display_name, "avatar_url": u.avatar_url} if u else None,
            "reply_count": db.query(Comment).filter(Comment.parent_id == c.id).count(),
            "replies": [{
                "id": r.id, "content": r.content, "like_count": r.like_count or 0,
                "created_at": r.created_at.isoformat(),
                "author": {"id": (ru:=reply_users_map.get(r.user_id)) and ru.id, "username": ru.username if ru else '', "display_name": ru.display_name if ru else '', "avatar_url": ru.avatar_url if ru else ''} if reply_users_map.get(r.user_id) else None,
            } for r in replies],
        })
    return {"comments": result, "total": total}


@router.post("/posts/{post_id}/comments")
def create_comment(post_id: int, body: dict, user: User = Depends(require_user), db: Session = Depends(get_db)):
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "评论内容不能为空")
    if len(content) > 500:
        raise HTTPException(400, "评论不能超过500字")
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "动态不存在")
    parent_id = body.get("parent_id")
    if parent_id is not None:
        parent = db.query(Comment).filter(Comment.id == parent_id, Comment.post_id == post_id).first()
        if not parent:
            raise HTTPException(400, "父评论不存在或不属于该动态")
    c = Comment(post_id=post_id, user_id=user.id, content=content, parent_id=parent_id)
    db.add(c)
    post.comment_count = (post.comment_count or 0) + 1
    db.commit()
    db.refresh(c)
    return {
        "id": c.id, "content": c.content, "like_count": 0,
        "created_at": c.created_at.isoformat(),
        "author": {"id": user.id, "username": user.username, "display_name": user.display_name, "avatar_url": user.avatar_url},
        "comment_count": post.comment_count,
    }


# --------------- AI Chat ---------------

# --------------- Search ---------------

@router.get("/search")
def search_all(q: str = "", db: Session = Depends(get_db)):
    term = (q or "").strip()[:100].replace("%", "").replace("_", "").strip()
    if not term:
        return {"courses": [], "streams": [], "posts": []}
    kw = f"%{term}%"
    # Courses
    vids = (db.query(AlbumVideo).join(Album).filter(
        Album.is_active == True,
        (AlbumVideo.title.ilike(kw)) | (Album.title.ilike(kw))
    ).limit(20).all())
    courses = [{"id": v.id, "title": v.title, "video_url": v.video_url,
                "album_title": v.album.title if v.album else "",
                "view_count": v.view_count or 0} for v in vids]
    # Live streams
    streams_q = (db.query(LiveStream).filter(
        LiveStream.is_live == True, LiveStream.title.ilike(kw)
    ).limit(10).all())
    stream_results = []
    for s in streams_q:
        u = db.query(User).filter(User.id == s.user_id).first()
        stream_results.append({
            "id": s.id, "title": s.title, "viewer_count": s.viewer_count,
            "user": _user_dict(u) if u else None})
    # Posts
    posts_q = (db.query(Post).filter(
        Post.hidden == False, Post.content.ilike(kw)
    ).order_by(Post.view_count.desc()).limit(20).all())
    user_ids = list({p.user_id for p in posts_q})
    umap = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    post_results = [_post_dict(p, umap.get(p.user_id)) for p in posts_q]
    return {"courses": courses, "streams": stream_results, "posts": post_results}


@router.post("/ai/chat")
async def ai_chat(req: AIChatReq):
    from .config import OPENAI_API_KEY, OPENAI_MODEL
    use_en = (req.lang or "").lower().startswith("en")
    system_prompt = AI_SYSTEM_PROMPT_EN if use_en else AI_SYSTEM_PROMPT
    if not OPENAI_API_KEY:
        return {"reply": _fallback_ai(req.message, use_en)}
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": req.message},
                    ],
                    "max_tokens": 800,
                },
            )
            data = resp.json()
            return {"reply": data["choices"][0]["message"]["content"]}
        except Exception:
            return {"reply": _fallback_ai(req.message, use_en)}


AI_SYSTEM_PROMPT = """你是美股王交易直播平台的AI客服。请用中文回答。

关于美股王：
- 十年美股培训教育品牌，创始人王维，20年美股投资经验
- 提供网上课程（华尔街投资分享课）、VIP点评、智能交易分析软件
- 核心课程：美股交易基础、交易技术分析、中长期投资策略、智能短线交易策略
- 进阶课程：交易概率、风险控制、51法则阻力与支撑、选股进场出场技巧

关于会员：
- 年度会员价格：$200/年
- 会员权益：使用美股王智能交易分析软件、专属VIP点评、进阶课程
- 直播功能：注册用户可开播，通过平台分享交易画面

关于直播平台：
- 注册后可开启直播，分享交易画面给其他用户
- 支持多窗口采集（美股王软件+盈透证券等）
- 支持多平台同步推流（YouTube/TikTok/Bilibili等）

请耐心、专业地回答用户关于美股投资、会员权益、购买流程等问题。"""

AI_SYSTEM_PROMPT_EN = """You are the AI support assistant for USKing Trading Live. Answer in clear English.

About USKing:
- ~10-year U.S. stock education brand; founder Wang Wei; ~20 years of U.S. market experience
- Online courses (Wall Street intro), VIP commentary, smart trading analytics software
- Core: U.S. trading basics, technical analysis, swing/long-term strategy, systematic day trading
- Advanced: probability thinking, risk control, 51% rule for support/resistance, entry/exit selection

Membership:
- Annual price: $200/year
- Benefits: USKing analytics software, VIP commentary, advanced courses
- Live: registered users can stream and share their screens

Live platform:
- After login, users can go live and share trading screens
- Multi-window capture (USKing software, brokers, etc.)
- Multi-platform restream (YouTube, TikTok, Bilibili, etc.)

Be patient and professional on investing, membership, and how to buy."""


def _fallback_ai(msg: str, english: bool = False) -> str:
    msg_lower = msg.lower()
    if english:
        if any(w in msg_lower for w in ["member", "price", "cost", "buy", "pay", "$"]):
            return (
                "USKing annual membership is $200/year, including the smart analytics software, "
                "VIP commentary, and advanced courses. Open the Membership page and tap Buy Now. "
                "Ask if you need anything else!"
            )
        if any(w in msg_lower for w in ["live", "stream", "broadcast"]):
            return (
                "After you sign in, you can go live from the studio: add capture windows for your "
                "trading software, then start the stream. You can restream to YouTube, TikTok, and more."
            )
        if any(w in msg_lower for w in ["course", "learn", "class", "lesson"]):
            return (
                "USKing offers a full path from beginner to advanced:\n"
                "- Intro: Wall Street sharing seminar\n"
                "- Core: basics, technicals, strategy, day trading\n"
                "- Advanced: probability, risk, S/R, stock selection\n"
                "See the Courses section for details."
            )
        return (
            "Hi! I'm the USKing AI assistant. I can help with U.S. stocks, membership, courses, "
            "and live streaming. What would you like to know?"
        )
    if any(w in msg_lower for w in ["会员", "价格", "多少钱", "购买"]):
        return "美股王年度会员价格为 $200/年，包含智能交易分析软件使用权、专属VIP点评和进阶课程。您可以在会员页面点击「立即购买」完成支付。有其他问题欢迎随时咨询！"
    if any(w in msg_lower for w in ["直播", "开播"]):
        return "注册登录后即可开启直播功能。在直播页面点击「添加窗口」采集您的交易软件画面，然后点击「开始直播」即可。支持同时采集多个窗口并推流到YouTube、TikTok等平台。"
    if any(w in msg_lower for w in ["课程", "学习"]):
        return "美股王提供入门到进阶的完整课程体系：\n- 入门：华尔街投资分享课\n- 核心：美股交易基础、技术分析、投资策略、短线交易\n- 进阶：概率交易、风险控制、阻力支撑、选股技巧\n详情请查看网上课程页面。"
    return "您好！我是美股王AI客服。我可以为您解答关于美股投资、会员权益、课程内容、直播功能等问题。请问有什么可以帮您的？"


# --------------- Direct Messages ---------------

@router.get("/dm/conversations")
def dm_conversations(user: User = Depends(require_user), db: Session = Depends(get_db)):
    convos = db.query(Conversation).filter(
        or_(Conversation.user_a == user.id, Conversation.user_b == user.id)
    ).order_by(Conversation.last_at.desc()).limit(50).all()
    result = []
    for c in convos:
        peer_id = c.user_b if c.user_a == user.id else c.user_a
        peer = db.get(User, peer_id)
        if not peer:
            continue
        unread = db.query(DirectMessage).filter(
            DirectMessage.conversation_id == c.id,
            DirectMessage.sender_id != user.id,
            DirectMessage.read == False
        ).count()
        result.append({
            "id": c.id,
            "peer": {"id": peer.id, "username": peer.username,
                     "display_name": peer.display_name, "avatar_url": peer.avatar_url},
            "last_message": c.last_message or "",
            "last_at": c.last_at.isoformat() if c.last_at else None,
            "unread": unread,
        })
    total_unread = sum(r["unread"] for r in result)
    return {"conversations": result, "total_unread": total_unread}


@router.get("/dm/conversations/{conv_id}/messages")
def dm_messages(
    conv_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: int = Query(0, ge=0),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    conv = db.get(Conversation, conv_id)
    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(404, "会话不存在")
    q = db.query(DirectMessage).filter(DirectMessage.conversation_id == conv_id)
    if before_id:
        q = q.filter(DirectMessage.id < before_id)
    msgs = q.order_by(DirectMessage.id.desc()).limit(limit).all()
    msgs.reverse()
    db.query(DirectMessage).filter(
        DirectMessage.conversation_id == conv_id,
        DirectMessage.sender_id != user.id,
        DirectMessage.read == False
    ).update({"read": True})
    db.commit()
    return {"messages": [{
        "id": m.id, "sender_id": m.sender_id, "content": m.content,
        "read": m.read, "created_at": m.created_at.isoformat(),
    } for m in msgs]}


class DMSend(BaseModel):
    content: str

@router.post("/dm/conversations/{conv_id}/send")
def dm_send(conv_id: int, body: DMSend, user: User = Depends(require_user), db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if not conv or (conv.user_a != user.id and conv.user_b != user.id):
        raise HTTPException(404, "会话不存在")
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "消息不能为空")
    msg = DirectMessage(conversation_id=conv_id, sender_id=user.id, content=content[:2000])
    db.add(msg)
    conv.last_message = content[:100]
    conv.last_at = utcnow()
    db.commit()
    db.refresh(msg)
    return {"message": {"id": msg.id, "sender_id": msg.sender_id, "content": msg.content,
                        "read": msg.read, "created_at": msg.created_at.isoformat()}}


class DMStart(BaseModel):
    peer_id: str
    content: str

@router.post("/dm/start")
def dm_start(body: DMStart, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if body.peer_id == user.id:
        raise HTTPException(400, "不能给自己发私信")
    peer = db.get(User, body.peer_id)
    if not peer:
        raise HTTPException(404, "用户不存在")
    conv = db.query(Conversation).filter(
        or_(
            and_(Conversation.user_a == user.id, Conversation.user_b == body.peer_id),
            and_(Conversation.user_a == body.peer_id, Conversation.user_b == user.id),
        )
    ).first()
    if not conv:
        conv = Conversation(user_a=user.id, user_b=body.peer_id)
        db.add(conv)
        db.flush()
    content = body.content.strip()
    if content:
        msg = DirectMessage(conversation_id=conv.id, sender_id=user.id, content=content[:2000])
        db.add(msg)
        conv.last_message = content[:100]
        conv.last_at = utcnow()
    db.commit()
    db.refresh(conv)
    return {"conversation_id": conv.id}


def _normalize_dm_search_q(q: str) -> str:
    s = (q or "").strip()[:64]
    if not s:
        return ""
    m = re.match(r"^(?:id|ID)\s*[:：]\s*(.+)$", s)
    if m:
        s = m.group(1).strip()
    return s


def _is_ascii_digits_only(s: str) -> bool:
    return bool(s) and all("0" <= c <= "9" for c in s)


def _display_id_padded_sql():
    """8-digit zero-padded display_id for substring search (matches UI ID:00000012)."""
    if engine.dialect.name == "sqlite":
        return func.printf("%08d", User.display_id)
    return func.lpad(cast(User.display_id, String), 8, "0")


@router.get("/dm/search-user")
def dm_search_user(q: str = "", user: User = Depends(require_user), db: Session = Depends(get_db)):
    raw = _normalize_dm_search_q(q)
    if not raw:
        return {"users": []}
    like_term = raw.replace("%", "").replace("_", "").strip()
    results: List[User] = []
    seen = set()

    def _add(u: Optional[User]) -> None:
        if u and u.id != user.id and u.id not in seen:
            seen.add(u.id)
            results.append(u)

    uid_key = raw.lower() if re.fullmatch(r"[0-9a-fA-F]{16}", raw, flags=re.I) else None
    if uid_key:
        u = db.get(User, uid_key)
        _add(u)

    if _is_ascii_digits_only(like_term):
        pad = _display_id_padded_sql()
        id_hits = (
            db.query(User)
            .filter(
                User.id != user.id,
                User.display_id.isnot(None),
                pad.like(f"%{like_term}%"),
            )
            .limit(10)
            .all()
        )
        for u in id_hits:
            _add(u)

    need = 10 - len(results)
    if need > 0 and like_term:
        q = db.query(User).filter(
            User.id != user.id,
            or_(
                User.username.ilike(f"%{like_term}%"),
                User.display_name.ilike(f"%{like_term}%"),
            ),
        )
        if seen:
            q = q.filter(User.id.notin_(list(seen)))
        for u in q.limit(need).all():
            _add(u)
    return {"users": [{
        "id": u.id, "username": u.username,
        "display_name": u.display_name,
        "display_id": str(u.display_id).zfill(8) if u.display_id else None,
        "avatar_url": u.avatar_url,
    } for u in results]}


@router.get("/dm/unread")
def dm_unread(user: User = Depends(require_user), db: Session = Depends(get_db)):
    conv_ids = [c.id for c in db.query(Conversation).filter(
        or_(Conversation.user_a == user.id, Conversation.user_b == user.id)
    ).all()]
    if not conv_ids:
        return {"unread": 0}
    count = db.query(DirectMessage).filter(
        DirectMessage.conversation_id.in_(conv_ids),
        DirectMessage.sender_id != user.id,
        DirectMessage.read == False
    ).count()
    return {"unread": count}


# --------------- Helpers ---------------

def _dt_iso(dt) -> Optional[str]:
    """避免 SQLite/迁移导致时间为 None 或非 datetime 时 .isoformat() 抛错（直播页等接口 500）。"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _user_dict(u: User, admin: bool = False) -> dict:
    d = {
        "id": u.id, "username": u.username, "display_name": u.display_name,
        "display_id": str(u.display_id).zfill(8) if u.display_id is not None else None,
        "avatar_url": u.avatar_url, "bio": u.bio,
        "gender": u.gender or "", "birthday": u.birthday or "",
        "cover_url": u.cover_url or "",
        "location": u.location, "website": u.website, "is_member": u.is_member,
        "member_until": _dt_iso(u.member_until),
        "created_at": _dt_iso(u.created_at),
    }
    if admin:
        d.update({
            "email": u.email, "email_verified": u.email_verified,
            "is_active": u.is_active, "is_admin": u.is_admin,
            "live_enabled": u.live_enabled, "live_key": u.live_key,
        })
    return d


def _post_dict(p: Post, author: User = None, admin: bool = False, bookmarked: bool = False) -> dict:
    d = {
        "id": p.id, "content": p.content,
        "media_urls": json.loads(p.media_urls) if p.media_urls else [],
        "view_count": p.view_count or 0,
        "like_count": p.like_count or 0,
        "bookmarked": bookmarked,
        "created_at": _dt_iso(p.created_at),
        "author": _user_dict(author) if author else None,
    }
    if admin:
        d["hidden"] = p.hidden
    return d


def _stream_dict(s: LiveStream) -> dict:
    return {
        "id": s.id, "user_id": s.user_id, "title": s.title,
        "is_live": s.is_live, "viewer_count": s.viewer_count,
        "started_at": _dt_iso(s.started_at),
    }
