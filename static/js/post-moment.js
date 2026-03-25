/**
 * 个人主页作品集：点击封面进入「朋友圈」式详情；作者可删单张媒体、设封面。
 * 依赖全局 APP（app.js）。
 */
(function () {
  window._postsById = window._postsById || {};
  var _openPostId = null;

  function T(key, vars) {
    if (typeof I18N !== 'undefined' && I18N.t) {
      return vars ? I18N.fmt(key, vars) : I18N.t(key);
    }
    var fb = {
      'moment.user': '用户',
      'moment.posted': '发布于',
      'moment.media_count': '共 {n} 张图片/视频',
      'moment.no_caption': '（无文字说明）',
      'moment.no_media': '本条动态暂无图片/视频',
      'moment.cover': '封面',
      'moment.delete': '删除',
      'moment.set_cover': '设封面',
      'moment.delete_post': '删除整条作品（含全部图片/视频）',
      'moment.confirm_del_media': '确定删除这张图片/视频？不可恢复。',
      'moment.confirm_del_post': '确定删除整条作品？其中所有图片、视频与文字将一并删除，且不可恢复。',
      'moment.del_fail': '删除失败',
      'moment.cover_fail': '设置失败',
      'moment.load_fail': '加载失败',
    };
    var s = fb[key] || key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split('{' + k + '}').join(String(vars[k])); });
    return s;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escAttr(s) {
    return esc(s).replace(/'/g, '&#39;');
  }

  function mergePostsIntoCache(posts) {
    if (!posts || !posts.length) return;
    posts.forEach(function (p) {
      if (p && p.id != null) window._postsById[p.id] = p;
    });
  }

  function isVideoUrl(u) {
    return u && /\.(mp4|mov|webm)$/i.test(u);
  }

  function canEditPost(p) {
    return !!(APP.user && p && p.author && APP.user.id === p.author.id);
  }

  function reloadPortfolioGrids() {
    try {
      if (typeof loadPosts === 'function') loadPosts();
    } catch (e) {}
    try {
      if (typeof loadBookmarks === 'function') loadBookmarks();
    } catch (e) {}
    try {
      if (typeof myLoadPosts === 'function' && window._spaMyUsername) {
        myLoadPosts(window._spaMyUsername);
      }
    } catch (e) {}
    try {
      if (typeof myLoadBookmarks === 'function') myLoadBookmarks();
    } catch (e) {}
    try {
      if (typeof window._vpReloadPosts === 'function') window._vpReloadPosts();
    } catch (e) {}
  }

  function renderModal(p) {
    var head = document.getElementById('postMomentHead');
    var meta = document.getElementById('postMomentMeta');
    var text = document.getElementById('postMomentText');
    var grid = document.getElementById('postMomentGrid');
    if (!head || !meta || !text || !grid) return;

    var urls = p.media_urls || [];

    var au = p.author || {};
    var av = au.avatar_url
      ? '<img src=' + JSON.stringify(String(au.avatar_url)) + ' style="width:40px;height:40px;border-radius:50%;object-fit:cover;flex-shrink:0">'
      : '<span style="width:40px;height:40px;border-radius:50%;background:var(--bg3);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--accent);flex-shrink:0">' +
        esc((au.display_name || au.username || '?')[0]).toUpperCase() +
        '</span>';
    head.innerHTML =
      av +
      '<div style="min-width:0"><div style="font-weight:700;color:var(--white);font-size:15px">' +
      esc(au.display_name || au.username || T('moment.user')) +
      '</div><div style="font-size:12px;color:var(--text3)">@' +
      esc(au.username || '') +
      '</div></div>';

    var t = p.created_at ? new Date(p.created_at) : null;
    var parts = [];
    var loc = typeof I18N !== 'undefined' && I18N.lang === 'en' ? 'en-US' : 'zh-CN';
    if (t && !isNaN(t.getTime())) parts.push(T('moment.posted') + ' ' + t.toLocaleString(loc));
    if (urls.length) parts.push(T('moment.media_count', { n: urls.length }));
    meta.textContent = parts.join(' · ');

    var c = (p.content || '').trim();
    text.innerHTML = c ? esc(c) : '<span style="color:var(--text3)">' + esc(T('moment.no_caption')) + '</span>';
    if (!urls.length) {
      grid.innerHTML =
        '<div style="padding:24px;text-align:center;color:var(--text3);font-size:13px;background:var(--bg2);border-radius:8px">' +
        esc(T('moment.no_media')) +
        '</div>';
    } else {
    var cols = urls.length === 1 ? 1 : urls.length === 2 ? 2 : 3;
    var gap = '4px';
    var owner = canEditPost(p);

    var h =
      '<div style="display:grid;grid-template-columns:repeat(' +
      cols +
      ',1fr);gap:' +
      gap +
      '">';

    urls.forEach(function (url, idx) {
      var vid = isVideoUrl(url);
      var mediaHtml = vid
        ? '<video src=' +
          JSON.stringify(String(url)) +
          ' controls playsinline style="width:100%;height:100%;object-fit:cover;display:block;background:#000"></video>'
        : '<img src=' +
          JSON.stringify(String(url)) +
          ' alt="" style="width:100%;height:100%;object-fit:cover;display:block">';

      var badge =
        idx === 0 && urls.length > 1
          ? '<span style="position:absolute;top:6px;left:6px;font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(0,0,0,.55);color:#fff">' +
            esc(T('moment.cover')) +
            '</span>'
          : '';

      var tools = '';
      if (owner) {
        var delBtn =
          '<button type="button" class="pm-tool-btn" data-act="del" data-url=' +
          JSON.stringify(String(url)) +
          ' style="font-size:11px;padding:4px 8px;border-radius:4px;border:none;background:rgba(255,255,255,.2);color:#fff;cursor:pointer">' +
          esc(T('moment.delete')) +
          '</button>';
        var coverBtn =
          idx > 0
            ? '<button type="button" class="pm-tool-btn" data-act="cover" data-url=' +
              JSON.stringify(String(url)) +
              ' style="font-size:11px;padding:4px 8px;border-radius:4px;border:none;background:rgba(255,215,0,.35);color:#000;cursor:pointer;font-weight:600">' +
              esc(T('moment.set_cover')) +
              '</button>'
            : '';
        tools =
          '<div style="position:absolute;bottom:0;left:0;right:0;display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;padding:8px;background:linear-gradient(transparent,rgba(0,0,0,.75))">' +
          coverBtn +
          delBtn +
          '</div>';
      }

      h +=
        '<div style="position:relative;aspect-ratio:1;background:var(--bg3);border-radius:6px;overflow:hidden">' +
        badge +
        mediaHtml +
        tools +
        '</div>';
    });

    h += '</div>';
    grid.innerHTML = h;

    if (owner) {
      grid.querySelectorAll('.pm-tool-btn').forEach(function (btn) {
        btn.addEventListener('click', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          var act = btn.getAttribute('data-act');
          var url = btn.getAttribute('data-url');
          if (act === 'del') onDeleteMedia(p.id, url);
          else if (act === 'cover') onSetCover(p.id, url);
        });
      });
    }
    }

    var foot = document.getElementById('postMomentFooter');
    if (foot) {
      if (canEditPost(p)) {
        foot.style.display = 'block';
        foot.innerHTML =
          '<button type="button" onclick="PostMoment.deleteWholePost(' +
          p.id +
          ',event)" style="width:100%;padding:10px 12px;font-size:13px;border-radius:8px;border:1px solid rgba(239,68,68,.45);background:rgba(239,68,68,.08);color:#f87171;cursor:pointer;font-weight:600">' +
          esc(T('moment.delete_post')) +
          '</button>';
      } else {
        foot.style.display = 'none';
        foot.innerHTML = '';
      }
    }
  }

  async function onDeleteMedia(postId, url) {
    if (!confirm(T('moment.confirm_del_media'))) return;
    try {
      var r = await APP.api('POST', '/api/posts/' + postId + '/media/remove', { url: url });
      if (r.post) window._postsById[postId] = r.post;
      renderModal(r.post);
      reloadPortfolioGrids();
    } catch (e) {
      alert(e.message || T('moment.del_fail'));
    }
  }

  async function onSetCover(postId, url) {
    try {
      var r = await APP.api('POST', '/api/posts/' + postId + '/media/cover', { url: url });
      if (r.post) window._postsById[postId] = r.post;
      renderModal(r.post);
      reloadPortfolioGrids();
    } catch (e) {
      alert(e.message || T('moment.cover_fail'));
    }
  }

  async function open(postId) {
    var id = Number(postId);
    if (!id) return;
    var p = window._postsById[id];
    if (!p) {
      try {
        var r = await APP.api('GET', '/api/posts/' + id);
        p = r.post;
        window._postsById[id] = p;
      } catch (e) {
        alert(e.message || T('moment.load_fail'));
        return;
      }
    }
    var modal = document.getElementById('postMomentModal');
    if (!modal) return;
    _openPostId = id;
    renderModal(p);
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  async function deleteWholePost(postId, ev) {
    if (ev) {
      ev.preventDefault();
      ev.stopPropagation();
    }
    if (!confirm(T('moment.confirm_del_post'))) return;
    try {
      await APP.api('DELETE', '/api/posts/' + postId);
      delete window._postsById[postId];
      close();
      reloadPortfolioGrids();
    } catch (e) {
      alert(e.message || T('moment.del_fail'));
    }
  }

  function close() {
    _openPostId = null;
    var modal = document.getElementById('postMomentModal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
    var grid = document.getElementById('postMomentGrid');
    if (grid) {
      grid.querySelectorAll('video').forEach(function (v) {
        try {
          v.pause();
        } catch (e) {}
      });
    }
    var foot = document.getElementById('postMomentFooter');
    if (foot) {
      foot.style.display = 'none';
      foot.innerHTML = '';
    }
  }

  function onOverlayClick(ev) {
    if (ev.target.id === 'postMomentModal') close();
  }

  document.addEventListener('i18n-changed', function () {
    if (_openPostId == null) return;
    var p = window._postsById[_openPostId];
    if (p) renderModal(p);
  });

  window.PostMoment = {
    mergePosts: mergePostsIntoCache,
    open: open,
    close: close,
    onOverlayClick: onOverlayClick,
    escHtml: esc,
    escAttr: escAttr,
    deleteWholePost: deleteWholePost,
  };
})();
