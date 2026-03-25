import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uid():
    return uuid.uuid4().hex[:16]


class User(Base):
    __tablename__ = "users"
    id = Column(String(16), primary_key=True, default=new_uid)
    display_id = Column(Integer, unique=True, nullable=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    email_verified = Column(Boolean, default=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    avatar_url = Column(String(512), default="")
    bio = Column(Text, default="")
    gender = Column(String(10), default="")
    birthday = Column(String(10), default="")
    cover_url = Column(String(512), default="")
    location = Column(String(100), default="")
    website = Column(String(255), default="")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_member = Column(Boolean, default=False)
    member_until = Column(DateTime, nullable=True)
    live_enabled = Column(Boolean, default=True)
    live_key = Column(String(32), default=lambda: uuid.uuid4().hex[:16])
    created_at = Column(DateTime, default=utcnow)

    posts = relationship("Post", back_populates="author", cascade="all,delete-orphan")
    streams = relationship("LiveStream", back_populates="user", cascade="all,delete-orphan")


class EmailCode(Base):
    __tablename__ = "email_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(8), nullable=False)
    purpose = Column(String(20), default="register")  # register / bind / login
    created_at = Column(DateTime, default=utcnow)
    used = Column(Boolean, default=False)


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    media_urls = Column(Text, default="")  # JSON array of URLs
    hidden = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    author = relationship("User", back_populates="posts")
    bookmarks = relationship("Bookmark", back_populates="post", cascade="all,delete-orphan")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="bookmarks")


class LiveStream(Base):
    __tablename__ = "live_streams"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="")
    is_live = Column(Boolean, default=False)
    viewer_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="streams")


class LiveChatMessage(Base):
    """直播间公屏留言（仅关联当前 live_streams 行，下播后历史仍可按 stream_id 查询）。"""
    __tablename__ = "live_chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stream_id = Column(Integer, ForeignKey("live_streams.id"), nullable=False, index=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Banner(Base):
    __tablename__ = "banners"
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_url = Column(String(512), nullable=False)
    link_url = Column(String(512), default="")
    title = Column(String(255), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class Album(Base):
    __tablename__ = "albums"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    cover_url = Column(String(512), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    videos = relationship("AlbumVideo", back_populates="album", cascade="all,delete-orphan",
                          order_by="AlbumVideo.sort_order")


class AlbumVideo(Base):
    __tablename__ = "album_videos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False)
    title = Column(String(255), nullable=False)
    video_url = Column(String(1024), nullable=False)
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    album = relationship("Album", back_populates="videos")


class SiteSetting(Base):
    __tablename__ = "site_settings"
    key = Column(String(64), primary_key=True)
    value = Column(String(255), nullable=False, default="")


class MediaItem(Base):
    """Each image/video from a Post, split out for individual recommendation tracking."""
    __tablename__ = "media_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    media_url = Column(String(1024), nullable=False)
    media_type = Column(String(10), default="image")  # image / video
    caption = Column(Text, default="")
    impressions = Column(Integer, default=0)
    total_watch_ms = Column(Integer, default=0)
    completions = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)


class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)


class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, autoincrement=True)
    follower_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    following_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_a = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    user_b = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    last_message = Column(Text, default="")
    last_at = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)
    messages = relationship("DirectMessage", back_populates="conversation", cascade="all,delete-orphan",
                            order_by="DirectMessage.created_at")


class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    conversation = relationship("Conversation", back_populates="messages")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False)
    stripe_session_id = Column(String(255), default="")
    amount_cents = Column(Integer, default=0)
    currency = Column(String(10), default="usd")
    status = Column(String(20), default="pending")  # pending / paid / failed
    membership_start = Column(DateTime, nullable=True)
    membership_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
