const APP = {
  token: localStorage.getItem('token'),
  user: null,

  async init() {
    if (this.token) {
      try {
        const r = await this.api('GET', '/api/auth/me');
        this.user = r.user;
      } catch { this.token = null; localStorage.removeItem('token'); }
    }
    this.updateNav();
  },

  _parseApiBody(text, res) {
    if (text == null || text === '') return {};
    const raw = String(text).replace(/^\uFEFF/, '').trim();
    if (!raw) return {};
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    const looksJson =
      raw.startsWith('{') ||
      raw.startsWith('[') ||
      ct.includes('application/json');
    if (!looksJson) {
      return { detail: raw.slice(0, 500) };
    }
    try {
      return JSON.parse(raw);
    } catch {
      return { detail: raw.slice(0, 500) };
    }
  },

  async api(method, url, body) {
    const opts = { method, headers: {} };
    if (this.token) opts.headers['Authorization'] = `Bearer ${this.token}`;
    if (body && !(body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (body) {
      opts.body = body;
    }
    const res = await fetch(url, opts);
    const text = await res.text();
    const data = this._parseApiBody(text, res);
    if (!res.ok) {
      const det = data.detail;
      let msg = 'Request failed';
      if (typeof det === 'string') msg = det;
      else if (Array.isArray(det))
        msg = det.map((e) => (e && (e.msg || e.message)) || JSON.stringify(e)).join('; ');
      else if (det && typeof det === 'object' && det.msg) msg = String(det.msg);
      throw new Error(msg);
    }
    return data;
  },

  setToken(token) {
    this.token = token;
    localStorage.setItem('token', token);
  },

  logout() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('token');
    location.href = '/';
  },

  updateNav() {
    const nav = document.getElementById('navUser');
    if (!nav) return;
    const pubBtn = document.getElementById('navPublishBtn');
    if (this.user) {
      if (pubBtn) pubBtn.style.display = '';
      const avatar = this.user.avatar_url || '';
      const initial = (this.user.display_name || this.user.username)[0].toUpperCase();
      const profileAction = typeof switchPanel === 'function'
        ? `javascript:switchPanel('profile',document.querySelector('[data-panel=profile]'))`
        : `/u/${this.user.username}`;
      nav.innerHTML = `
        ${this.user.is_admin ? `<a href="/admin" class="nav-link" style="font-size:11px">${I18N.t('nav.admin')}</a>` : ''}
        <a href="${profileAction}" class="nav-avatar" title="${I18N.t('nav.profile')}">
          ${avatar ? `<img src="${avatar}" alt="">` : `<span class="av-init">${initial}</span>`}
        </a>
      `;
    } else {
      if (pubBtn) pubBtn.style.display = 'none';
      nav.innerHTML = `<a href="/login" class="nav-link">${I18N.t('nav.login')}</a><a href="/register" class="btn-accent-sm">${I18N.t('nav.register')}</a>`;
    }
  },

  timeAgo(iso) {
    const d = new Date(iso);
    const s = Math.floor((Date.now() - d.getTime()) / 1000);
    const L = typeof I18N !== 'undefined' ? I18N.lang : 'zh';
    if (L === 'en') {
      if (s < 60) return 'just now';
      if (s < 3600) return Math.floor(s / 60) + 'm ago';
      if (s < 86400) return Math.floor(s / 3600) + 'h ago';
      if (s < 604800) return Math.floor(s / 86400) + 'd ago';
      return d.toLocaleDateString('en-US');
    }
    if (s < 60) return '刚刚';
    if (s < 3600) return Math.floor(s / 60) + '分钟前';
    if (s < 86400) return Math.floor(s / 3600) + '小时前';
    if (s < 604800) return Math.floor(s / 86400) + '天前';
    return d.toLocaleDateString('zh-CN');
  },
};

document.addEventListener('DOMContentLoaded', () => APP.init());
document.addEventListener('i18n-changed', () => APP.updateNav());
