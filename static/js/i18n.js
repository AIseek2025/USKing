/** Normalize stored / URL language so `t()` always gets `zh` or `en`. */
function normalizeI18nLang(v) {
  const s = String(v == null ? '' : v).trim().toLowerCase();
  if (!s) return 'zh';
  if (s === 'en' || s.startsWith('en-') || s === 'english') return 'en';
  return 'zh';
}

const I18N = {
  _lang: normalizeI18nLang(typeof localStorage !== 'undefined' ? localStorage.getItem('lang') : null),

  dict: {
    // === Nav ===
    'nav.home': { zh: '首页', en: 'Home' },
    'nav.about': { zh: '平台介绍', en: 'About' },
    'nav.member': { zh: '会员', en: 'Membership' },
    'nav.dashboard': { zh: '直播后台', en: 'Studio' },
    'nav.login': { zh: '登录', en: 'Login' },
    'nav.register': { zh: '注册', en: 'Sign Up' },
    'nav.logout': { zh: '退出', en: 'Logout' },
    'nav.admin': { zh: '管理', en: 'Admin' },
    'nav.studio': { zh: '直播后台', en: 'Studio' },
    'nav.profile': { zh: '个人主页', en: 'Profile' },
    'nav.member_badge': { zh: '年度会员', en: 'VIP' },

    // === Homepage ===
    'home.title': { zh: '美股王 · 交易直播平台', en: 'USKing · Trading Live' },
    'home.sub': { zh: '实时交易直播 · 多平台同步 · 十年美股培训教育品牌', en: 'Real-time Trading Streams · Multi-platform Sync · 10 Years of US Stock Education' },
    'home.register': { zh: '免费注册', en: 'Sign Up Free' },
    'home.learn': { zh: '了解平台', en: 'Learn More' },
    'home.stat_years': { zh: '年教育品牌', en: 'Years of Education' },
    'home.stat_winrate': { zh: '赢率提升', en: 'Win Rate Boost' },
    'home.stat_price': { zh: '年度会员', en: 'Annual Member' },
    'home.stat_live': { zh: '实时直播', en: 'Live Streaming' },
    'home.pill_about': { zh: '平台介绍', en: 'About Us' },
    'home.pill_member': { zh: '年度会员 $200/年', en: 'Annual Membership $200/yr' },
    'home.pill_stream': { zh: '开始直播', en: 'Go Live' },
    'home.pill_site': { zh: '官方网站', en: 'Official Site' },
    'home.live_now': { zh: '正在直播', en: 'Live Now' },
    'home.no_stream': { zh: '暂无直播，成为第一个开播的人！', en: 'No live streams yet. Be the first to go live!' },
    'home.go_studio': { zh: '进入直播后台', en: 'Go to Studio' },
    'nav.explore': { zh: '🔥 动态', en: '🔥 Explore' },
    'nav.recommend': { zh: '推荐', en: 'For You' },
    'nav.featured': { zh: '精选', en: 'Featured' },
    'nav.live': { zh: '直播', en: 'Live' },
    'nav.courses': { zh: '课程', en: 'Courses' },
    'nav.my': { zh: '我的', en: 'Me' },
    'nav.more': { zh: '更多', en: 'More' },
    'nav.software': { zh: '软件下载', en: 'Software' },
    'nav.ai_spa': { zh: 'AI投资家', en: 'AI Investor' },
    'nav.us_data': { zh: '美股数据', en: 'U.S. Data' },
    'nav.research': { zh: '公司投研', en: 'Research' },
    'nav.settings': { zh: '设置', en: 'Settings' },
    'nav.brand': { zh: '美股王', en: 'USKing' },
    'nav.search_ph': { zh: '搜索课程、直播、动态...', en: 'Search courses, streams, posts…' },
    'nav.publish': { zh: '+ 投稿', en: '+ Post' },
    'nav.lang_title': { zh: '切换语言', en: 'Switch language' },
    'home.feed_title': { zh: '动态', en: 'Feed' },
    'home.publish': { zh: '发布动态', en: 'New Post' },
    'home.publish_title': { zh: '发布动态', en: 'New Post' },
    'home.publish_submit': { zh: '发布', en: 'Post' },
    'home.no_feed': { zh: '暂无动态，发布第一条动态吧！', en: 'No posts yet. Share your first post!' },

    // === Login ===
    'login.title': { zh: '登录', en: 'Login' },
    'login.tab_user': { zh: '用户名登录', en: 'Username Login' },
    'login.tab_email': { zh: '邮箱登录', en: 'Email Login' },
    'login.username': { zh: '用户名', en: 'Username' },
    'login.email': { zh: '邮箱', en: 'Email' },
    'login.password': { zh: '密码', en: 'Password' },
    'login.ph_user': { zh: '输入用户名', en: 'Enter username' },
    'login.ph_email': { zh: '输入邮箱', en: 'Enter email' },
    'login.ph_pass': { zh: '输入密码', en: 'Enter password' },
    'login.submit': { zh: '登录', en: 'Login' },
    'login.no_account': { zh: '还没有账户？', en: "Don't have an account? " },
    'login.go_register': { zh: '立即注册', en: 'Sign up now' },

    // === Register ===
    'reg.title': { zh: '创建账户', en: 'Create Account' },
    'reg.tab_simple': { zh: '用户名注册', en: 'Username' },
    'reg.tab_email': { zh: '邮箱注册', en: 'Email' },
    'reg.username': { zh: '用户名', en: 'Username' },
    'reg.user_hint': { zh: '（登录用，至少3个字符）', en: '(for login, min 3 chars)' },
    'reg.password': { zh: '密码', en: 'Password' },
    'reg.pass_hint': { zh: '（至少6个字符）', en: '(min 6 chars)' },
    'reg.email': { zh: '邮箱', en: 'Email' },
    'reg.send_code': { zh: '发送验证码', en: 'Send Code' },
    'reg.code': { zh: '验证码', en: 'Verification Code' },
    'reg.ph_user': { zh: '输入用户名', en: 'Enter username' },
    'reg.ph_pass': { zh: '输入密码', en: 'Enter password' },
    'reg.ph_email': { zh: '输入邮箱', en: 'Enter email' },
    'reg.ph_code': { zh: '输入6位验证码', en: 'Enter 6-digit code' },
    'reg.submit': { zh: '注册', en: 'Sign Up' },
    'reg.has_account': { zh: '已有账户？', en: 'Already have an account? ' },
    'reg.go_login': { zh: '立即登录', en: 'Login now' },

    // === Dashboard ===
    'dash.title': { zh: '直播后台', en: 'Streaming Studio' },
    'dash.login_first': { zh: '请先登录后使用直播功能', en: 'Please login to use streaming features' },
    'dash.start': { zh: '开始直播', en: 'Go Live' },
    'dash.stream_link': { zh: '你的直播链接：', en: 'Your stream link: ' },
    'dash.stream_title': { zh: '直播标题', en: 'Stream Title' },
    'dash.ph_title': { zh: '输入直播标题', en: 'Enter stream title' },
    'dash.btn_start': { zh: '开始直播', en: 'Go Live' },
    'dash.btn_stop': { zh: '停止直播', en: 'Stop Stream' },
    'dash.btn_capture': { zh: '打开采集页面 ↗', en: 'Open Capture Page ↗' },
    'dash.share': { zh: '分享链接', en: 'Share Link' },
    'dash.copy': { zh: '复制链接', en: 'Copy Link' },
    'dash.status_off': { zh: '未开播', en: 'Offline' },
    'dash.status_on': { zh: '直播中', en: 'Live' },
    'dash.preview_label': { zh: '合成画面预览', en: 'Composite preview' },
    'dash.no_capture': { zh: '还没有添加采集窗口', en: 'No capture window yet' },
    'dash.add_window': { zh: '+ 添加窗口', en: '+ Add window' },
    'dash.pick_window_hint': { zh: '选择你想要直播的应用窗口', en: 'Pick the app window to stream' },
    'dash.sources_h': { zh: '采集窗口', en: 'Sources' },
    'dash.layout_h': { zh: '布局', en: 'Layout' },
    'dash.restream_h': { zh: '多平台推流', en: 'Restream' },
    'dash.add_platform': { zh: '+ 添加平台', en: '+ Platform' },
    'dash.encoder_h': { zh: '推流设置', en: 'Encoder' },
    'dash.resolution': { zh: '分辨率', en: 'Resolution' },
    'dash.framerate': { zh: '帧率', en: 'Frame rate' },
    'dash.bitrate': { zh: '码率', en: 'Bitrate' },
    'dash.stream_url_label': { zh: '直播链接', en: 'Stream URL' },
    'dash.viewer_video_note': {
      zh: '说明：站内观众在 /live 链接观看的是「直播采集」页推送的画面（JPEG 约 10fps）。请保持采集页打开；若仅在后台点了开始直播而未开采集页，观众会看到等待画面。大并发或高清建议后续改用 HLS/CDN。',
      en: 'In-site viewers see frames from the capture tab (~10 fps JPEG). Keep that tab open. For scale/HD, plan HLS or a CDN later.',
    },
    'dash.copy_btn': { zh: '复制', en: 'Copy' },
    'dash.layout_auto': { zh: '自动', en: 'Auto' },
    'dash.layout_side': { zh: '左右', en: 'Side by side' },
    'dash.layout_pip': { zh: '画中画', en: 'PiP' },
    'dash.layout_grid': { zh: '网格', en: 'Grid' },
    'dash.plat_custom': { zh: '自定义', en: 'Custom' },
    'dash.fps_label': { zh: ' fps', en: ' fps' },

    // === Watch ===
    'watch.loading': { zh: '暂无实时播放画面', en: 'No live video feed yet' },
    'watch.webrtc_hint': {
      zh: '观看页尚未连接主播音视频流（未实现 WebRTC / HLS 等播放链路）。主播请在「直播采集」页点击「添加窗口」授权屏幕后，仅能在本机预览；观众端要看到画面需后续接入流媒体服务。',
      en: 'This page is not wired to a video pipeline yet (no WebRTC/HLS). The capture page can preview locally after you pick a window; viewers need a future streaming backend.',
    },
    'watch.connecting': { zh: '正在连接直播画面…', en: 'Connecting to live feed…' },
    'watch.wait_capture': {
      zh: '若长时间无画面：请主播打开「直播采集」页，添加窗口后点击「开始直播」，并保持该页不要关闭。',
      en: 'If this stays blank: the streamer must open the capture page, add a window, click Start live, and keep that tab open.',
    },
    'watch.stream_ended': { zh: '直播已结束或未推流', en: 'Stream ended or not publishing' },
    'watch.ws_failed': {
      zh: '无法连接直播画面',
      en: 'Could not connect to the live feed',
    },
    'watch.chat_title': { zh: '聊天（即将上线）', en: 'Chat (Coming Soon)' },
    'watch.chat_dev': { zh: '直播聊天功能开发中', en: 'Live chat feature in development' },
    'watch.offline': { zh: '当前没有在直播', en: 'Currently not streaming' },
    'watch.view_profile': { zh: '查看个人主页', en: 'View Profile' },
    'watch.viewers': { zh: '人观看', en: ' viewers' },

    // === Profile ===
    'profile.posts': { zh: '作品集', en: 'Portfolio' },
    'profile.bookmarks': { zh: '我的收藏', en: 'Bookmarks' },
    'profile.edit': { zh: '编辑资料', en: 'Edit Profile' },
    'profile.no_posts': { zh: '还没有发布动态', en: 'No posts yet' },
    'profile.no_posts_other': { zh: '暂无动态', en: 'No posts' },
    'profile.post_ph': { zh: '分享你的交易心得...', en: 'Share your trading insights...' },
    'profile.publish': { zh: '发布', en: 'Post' },
    'profile.delete': { zh: '删除', en: 'Delete' },
    'profile.joined': { zh: '加入于', en: 'Joined' },
    'profile.save': { zh: '保存', en: 'Save' },
    'profile.saved': { zh: '已保存', en: 'Saved' },
    'profile.avatar': { zh: '头像', en: 'Avatar' },
    'profile.nickname': { zh: '昵称', en: 'Display Name' },
    'profile.bio': { zh: '个人简介', en: 'Bio' },
    'profile.location': { zh: '所在地', en: 'Location' },
    'profile.website': { zh: '个人网站', en: 'Website' },
    'profile.bind_email': { zh: '绑定邮箱', en: 'Bind Email' },
    'profile.bind_btn': { zh: '绑定', en: 'Bind' },

    // === Membership ===
    'member.title': { zh: '美股王年度会员', en: 'USKing Annual Membership' },
    'member.sub': { zh: '解锁全部功能，加入数万投资者的交易社区', en: 'Unlock all features, join a community of thousands of investors' },
    'member.annual': { zh: '年度会员', en: 'Annual Member' },
    'member.per_year': { zh: '每年', en: 'per year' },
    'member.buy': { zh: '立即购买', en: 'Buy Now' },
    'member.is_member': { zh: '你已是年度会员，有效期至', en: 'You are a VIP member, valid until' },
    'member.why_title': { zh: '为什么选择美股王？', en: 'Why Choose USKing?' },
    'member.why_sub': { zh: '核心价值：低风险 × 高收益 × 轻松操作', en: 'Core Value: Low Risk × High Return × Easy Operation' },
    'member.course_title': { zh: '完整课程体系', en: 'Complete Course System' },
    'member.roadmap': { zh: '三个月学习路线', en: '3-Month Learning Path' },
    'member.roadmap_sub': { zh: '快的一个月学会，慢的两到三个月学会', en: 'Fast learners: 1 month. Average: 2-3 months.' },
    'member.testimonials': { zh: '学员见证', en: 'Testimonials' },
    'member.cta_title': { zh: '准备好开始了吗？', en: 'Ready to Get Started?' },
    'member.cta_sub': { zh: '加入美股王，掌握终生赚美金的能力', en: 'Join USKing, master the ability to earn USD for life' },
    'member.confirm': { zh: '确认购买年度会员？($200/年)\n\n（演示环境：点击确认将直接开通会员）', en: 'Confirm annual membership purchase? ($200/yr)\n\n(Demo: Click OK to activate directly)' },
    'member.success': { zh: '购买成功！你已成为年度会员。', en: 'Purchase successful! You are now a VIP member.' },
    'member.already': { zh: '你已是年度会员！', en: 'You are already a VIP member!' },
    'member.feat1': { zh: '美股王投资家智能交易分析软件使用权', en: 'USKing Investor Smart Trading Analysis Software Access' },
    'member.feat2': { zh: '独创趋势交易法 + 51%法则完整教学', en: 'Proprietary Trend Trading + 51% Rule Complete Training' },
    'member.feat3': { zh: '专属VIP点评与实盘分析', en: 'Exclusive VIP Reviews & Live Market Analysis' },
    'member.feat4': { zh: '全部进阶课程（波段交易、风控、选股等）', en: 'All Advanced Courses (Swing Trading, Risk Control, Stock Picking)' },
    'member.feat5': { zh: '实时交易直播功能', en: 'Real-time Trading Live Streaming' },
    'member.feat6': { zh: '多平台同步推流（YouTube/TikTok/Bilibili）', en: 'Multi-platform Streaming (YouTube/TikTok/Bilibili)' },
    'member.feat7': { zh: '每周多次王老师盘后分享视频', en: 'Weekly Post-market Analysis Videos by Teacher Wang' },
    'member.feat8': { zh: '线下培训课程参与资格', en: 'Offline Training Course Access' },
    'member.feat9': { zh: '优先客服支持', en: 'Priority Customer Support' },
    'member.why1_t': { zh: '独创趋势交易法', en: 'Proprietary Trend Trading Method' },
    'member.why1_d': { zh: '日大趋势看清方向，赢率从50%提升到70%。配合51法则进一步提升到75%。告别盲猜，科学交易。', en: 'Daily mega-trend reveals direction, boosting win rate from 50% to 70%. Combined with 51% Rule, up to 75%. Scientific trading, no guessing.' },
    'member.why2_t': { zh: '智能交易分析软件', en: 'Smart Trading Analysis Software' },
    'member.why2_d': { zh: '美股王投资家软件：支持日大小趋势图、操盘线、51法则、中轴线系统、多屏联动、自定义扫描器等强大功能。', en: 'USKing Investor software: daily mega/mini trend charts, VWAP, 51% Rule, pivot system, multi-screen sync, custom scanners.' },
    'member.why3_t': { zh: '可复制的成功', en: 'Replicable Success' },
    'member.why3_d': { zh: '女神Judy从零基础到95%赢率、平均日赚$5,000。三个月学习方法已被证实有效，1万美金日赚$300~$500。', en: 'Judy went from zero to 95% win rate, avg $5,000/day. 3-month method proven effective — $10K capital earning $300-$500/day.' },
    'member.why4_t': { zh: '20年投资经验', en: '20 Years of Investment Experience' },
    'member.why4_d': { zh: '创始人王维拥有基金经理和操盘手经验，十年教育品牌，服务上万学员。一年顶十年。', en: 'Founder Wang Wei: fund manager & trader experience, 10-year education brand, 10,000+ students served.' },
    'member.c1_t': { zh: '入门课程', en: 'Beginner Course' },
    'member.c1_d': { zh: '华尔街投资分享课 — 美股交易基础及准备，帮助零基础投资者快速入门美股市场。', en: 'Wall Street Investment Seminar — US stock trading basics, helping beginners enter the market quickly.' },
    'member.c2_t': { zh: '当日交易宝典', en: 'Day Trading Bible' },
    'member.c2_d': { zh: 'V4.0 完整版 — 当日交易基本概念、可复制技巧、三种基础交易策略、选股方法、操盘线运用。', en: 'V4.0 — Day trading basics, replicable techniques, 3 core strategies, stock selection, VWAP usage.' },
    'member.c3_t': { zh: '技术分析大全', en: 'Technical Analysis Guide' },
    'member.c3_d': { zh: 'K线图基础、日大小趋势图、移动平均线、中轴线系统、操盘线、报价表与扫描器。', en: 'Candlestick basics, daily mega/mini trend charts, moving averages, pivot system, VWAP, scanners.' },
    'member.c4_t': { zh: '波段交易', en: 'Swing Trading' },
    'member.c4_d': { zh: '美股王波段交易大赢家 — 51法则精准识别强支撑强阻力，简单安全，赚钱效应好。', en: 'USKing Swing Trading — 51% Rule identifies strong support/resistance. Simple, safe, profitable.' },
    'member.c5_t': { zh: '风险控制', en: 'Risk Management' },
    'member.c5_d': { zh: '交易是概率的游戏 — 最大1%止损纪律，情绪与决策偏差管理，自律守率交易心理。', en: 'Trading is a probability game — max 1% stop-loss discipline, emotion & bias management, disciplined trading psychology.' },
    'member.c6_t': { zh: '软件教学', en: 'Software Training' },
    'member.c6_d': { zh: '投资家软件4.2完整教学 — 界面布局、窗口联动、多层分布、快速调用、扫描过滤器。', en: 'Investor Software 4.2 full tutorial — layout, window linking, multi-layer display, quick access, scan filters.' },
    'member.step1_t': { zh: '学会工具', en: 'Master Tools' },
    'member.step1_d': { zh: '掌握美股王投资家软件操作', en: 'Master USKing Investor software operations' },
    'member.step2_t': { zh: '学会布局', en: 'Setup Layout' },
    'member.step2_d': { zh: '单屏/多屏交易界面设置', en: 'Single/multi-screen trading interface setup' },
    'member.step3_t': { zh: '了解指标', en: 'Learn Indicators' },
    'member.step3_d': { zh: '看懂趋势图、操盘线、51法则', en: 'Understand trend charts, VWAP, 51% Rule' },
    'member.step4_t': { zh: '刻意练习', en: 'Deliberate Practice' },
    'member.step4_d': { zh: '小量资金每天交易，坚持两个月', en: 'Trade daily with small capital, persist for 2 months' },
    'member.step5_t': { zh: '加大仓位', en: 'Scale Up' },
    'member.step5_d': { zh: '赢率提高后逐步增加交易规模', en: 'Gradually increase trading size as win rate improves' },
    'member.judy_desc': { zh: '19年硅谷线下培训班学员', en: "2019 Silicon Valley training class graduate" },
    'member.judy_quote': { zh: '从广东移民到美国，关掉超市全职炒美股。学习美股王波段交易后，95%赢率，正常市场平均日赚$5,000，波动大的市场日赚$20,000-$80,000。', en: 'Immigrated from Guangdong to the US, closed her supermarket for full-time trading. After learning USKing swing trading: 95% win rate, avg $5,000/day, up to $20K-$80K/day in volatile markets.' },
    'member.judy_tip': { zh: '六字真言：支撑买，阻力卖', en: 'Golden Rule: Buy at support, sell at resistance' },
    'member.wang_name': { zh: '王维老师', en: 'Teacher Wang Wei' },
    'member.wang_desc': { zh: '美股王创始人', en: 'USKing Founder' },
    'member.wang_quote': { zh: '"经过2-3个月刻意练习，专注提升规律识别力，打磨2-3种适合自身的高胜率策略。聚焦方法、淬炼识别规律、守株待兔、打磨高赢率策略。"', en: '"After 2-3 months of deliberate practice, focus on pattern recognition, refine 2-3 high win-rate strategies. Focus on method, sharpen pattern recognition, be patient, polish strategies."' },

    // === Admin ===
    'admin.title': { zh: '管理后台', en: 'Admin Panel' },
    'admin.banners': { zh: '海报管理', en: 'Banners' },
    'admin.users': { zh: '用户管理', en: 'Users' },
    'admin.streams': { zh: '直播管理', en: 'Streams' },
    'admin.posts_tab': { zh: '动态管理', en: 'Posts' },
    'admin.payments': { zh: '会员记录', en: 'Payments' },
    'admin.no_perm': { zh: '需要管理员权限', en: 'Admin access required' },
    'admin.upload_banner': { zh: '上传新海报', en: 'Upload New Banner' },
    'admin.banner_img': { zh: '海报图片', en: 'Banner Image' },
    'admin.banner_title': { zh: '标题（选填）', en: 'Title (optional)' },
    'admin.banner_link': { zh: '链接（选填）', en: 'Link (optional)' },
    'admin.banner_sort': { zh: '排序', en: 'Sort' },
    'admin.upload': { zh: '上传', en: 'Upload' },
    'admin.no_banners': { zh: '暂无海报，请上传', en: 'No banners. Upload one.' },
    'admin.enable': { zh: '启用', en: 'Enable' },
    'admin.disable': { zh: '禁用', en: 'Disable' },

    // === AI Chat ===
    'ai.title': { zh: '美股王 AI 客服', en: 'USKing AI Support' },
    'ai.welcome': { zh: '您好！我是美股王AI客服，可以为您解答关于美股投资、会员权益、课程内容、直播功能等问题。请问有什么可以帮您？', en: "Hi! I'm USKing AI assistant. I can help with US stock investing, membership, courses, and streaming. How can I help?" },
    'ai.ph': { zh: '输入您的问题...', en: 'Type your question...' },
    'ai.send': { zh: '发送', en: 'Send' },
    'ai.thinking': { zh: '正在思考...', en: 'Thinking...' },
    'ai.error': { zh: '抱歉，暂时无法回复，请稍后再试。', en: 'Sorry, unable to reply now. Please try again later.' },

    // === About Page ===
    'about.hero_title': { zh: '美股王 · 重新定义美股当日交易', en: 'USKing · Redefining US Stock Day Trading' },
    'about.hero_sub': { zh: '十年教育品牌 · 独创趋势交易法 · 智能交易分析软件', en: '10-Year Education Brand · Proprietary Trend Trading · Smart Analysis Software' },
    'about.become_member': { zh: '成为会员 $200/年', en: 'Join Now $200/yr' },
    'about.years_exp': { zh: '年投资经验', en: 'Years Experience' },

    // === Common ===
    'common.confirm_delete': { zh: '确定删除？', en: 'Confirm delete?' },
    'common.copied': { zh: '已复制', en: 'Copied' },
    'common.loading': { zh: '加载中...', en: 'Loading...' },
    'common.year_member': { zh: '年度会员', en: 'VIP' },
    'common.verified': { zh: '已验证', en: 'Verified' },
    'common.enabled': { zh: '已开启', en: 'Enabled' },
    'common.disabled': { zh: '已关闭', en: 'Disabled' },
    'common.normal': { zh: '正常', en: 'Active' },
    'common.banned': { zh: '禁用', en: 'Banned' },
    'common.live': { zh: '直播中', en: 'Live' },
    'common.ended': { zh: '已结束', en: 'Ended' },
    'common.visible': { zh: '可见', en: 'Visible' },
    'common.hidden': { zh: '已隐藏', en: 'Hidden' },
    'common.paid': { zh: '已支付', en: 'Paid' },
    'common.pending': { zh: '待支付', en: 'Pending' },
    'common.link_copied': { zh: '链接已复制', en: 'Link copied' },
    'common.login_first_alert': { zh: '请先登录', en: 'Please sign in first' },
    'common.send_failed': { zh: '发送失败', en: 'Send failed' },

    'dm.title': { zh: '私信', en: 'Messages' },
    'dm.search_ph': { zh: '搜索用户名 / ID...', en: 'Search username / ID…' },
    'dm.empty': { zh: '暂无私信\n搜索用户发起对话', en: 'No messages yet.\nSearch a user to start.' },
    'dm.pick_conv': { zh: '选择对话开始聊天', en: 'Pick a conversation' },
    'dm.input_ph': { zh: '输入消息...', en: 'Type a message…' },
    'dm.start_chat': { zh: '开始对话吧', en: 'Say hello to start' },
    'dm.user_not_found': { zh: '未找到用户', en: 'No users found' },
    'dm.history': { zh: '搜索历史', en: 'History' },
    'dm.clear': { zh: '清除', en: 'Clear' },

    'spa.doc_title': { zh: '美股王 · 交易直播平台', en: 'USKing · Trading Live' },
    'spa.dy_loading': { zh: '加载中...', en: 'Loading…' },
    'spa.dy_load_fail': { zh: '加载失败', en: 'Failed to load' },
    'spa.dy_empty': { zh: '暂无动态，快去发布吧！', en: 'No videos yet. Be the first to post!' },
    'spa.dy_play_pause': { zh: '播放/暂停', en: 'Play / Pause' },
    'spa.dy_danmaku': { zh: '弹幕', en: 'Danmaku' },
    'spa.dy_speed': { zh: '倍速', en: 'Speed' },
    'spa.dy_volume': { zh: '音量', en: 'Volume' },
    'spa.dy_clean': { zh: '清屏', en: 'Clean mode' },
    'spa.dy_quality': { zh: '清晰度', en: 'Quality' },
    'spa.dy_fullscreen': { zh: '全屏', en: 'Fullscreen' },
    'spa.quality_sd': { zh: '标清', en: 'SD' },
    'spa.quality_hd': { zh: '高清', en: 'HD' },
    'spa.quality_uhd': { zh: '超高清', en: 'UHD' },
    'spa.comments': { zh: '评论', en: 'Comments' },
    'spa.cmt_empty': { zh: '暂无评论，快来抢沙发吧', en: 'No comments yet. Start the thread!' },
    'spa.cmt_ph': { zh: '写评论...', en: 'Write a comment…' },
    'spa.cmt_count': { zh: '{n} 条评论', en: '{n} comments' },
    'spa.cmt_loading': { zh: '加载中...', en: 'Loading…' },
    'spa.cmt_fail': { zh: '加载失败', en: 'Failed to load' },
    'spa.cmt_reply': { zh: '回复', en: 'Reply' },
    'spa.cmt_reply_ph': { zh: '回复 @{name}...', en: 'Reply to @{name}…' },
    'spa.cmt_view_replies': { zh: '查看全部 {n} 条回复', en: 'View all {n} replies' },
    'spa.ft_all': { zh: '全部', en: 'All' },
    'spa.ft_strategy': { zh: '交易策略', en: 'Strategies' },
    'spa.ft_tech': { zh: '技术分析', en: 'Technical' },
    'spa.ft_market': { zh: '市场观点', en: 'Market views' },
    'spa.ft_course': { zh: '投资课程', en: 'Courses' },
    'spa.ft_share': { zh: '实盘分享', en: 'Live trading' },
    'spa.ft_intro': { zh: '美股入门', en: 'U.S. market 101' },
    'spa.load_more': { zh: '加载更多', en: 'Load more' },
    'spa.no_more': { zh: '没有更多了', en: 'No more' },
    'spa.live_title': { zh: '正在直播', en: 'Live now' },
    'spa.live_empty': { zh: '暂无直播', en: 'No live streams' },
    'spa.go_live': { zh: '开始直播', en: 'Go live' },
    'spa.streaming': { zh: '直播中', en: 'Live' },
    'spa.courses_title': { zh: '精选课程视频', en: 'Featured course videos' },
    'spa.no_courses': { zh: '暂无课程', en: 'No courses yet' },
    'spa.course_badge': { zh: '课程', en: 'Course' },
    'spa.panel_loading': { zh: '加载中...', en: 'Loading…' },
    'spa.dash_login': { zh: '请先登录后使用直播功能', en: 'Sign in to use streaming' },
    'spa.search_results': { zh: '搜索结果：', en: 'Results:' },
    'spa.sr_all': { zh: '全部', en: 'All' },
    'spa.sr_courses': { zh: '课程', en: 'Courses' },
    'spa.sr_streams': { zh: '直播', en: 'Live' },
    'spa.sr_posts': { zh: '动态', en: 'Posts' },
    'spa.sr_hint': { zh: '输入关键词搜索课程、直播和动态', en: 'Search courses, streams, and posts' },
    'spa.sr_none': { zh: '未找到相关内容', en: 'No results' },
    'spa.settings_login': { zh: '请先登录', en: 'Please sign in' },
    'spa.ai_title': { zh: 'AI 投资家', en: 'AI Investor' },
    'spa.ai_sub': { zh: '您的智能美股投资助手，可以为您解答美股交易策略、技术分析、会员权益、课程内容等问题。', en: 'Your AI assistant for U.S. stock strategies, technical analysis, membership, and courses.' },
    'spa.ai_ph': { zh: '向 AI 投资家提问...', en: 'Ask AI Investor…' },
    'spa.ai_disclaimer': { zh: 'AI 投资家可能会产生不准确的信息，投资有风险，请谨慎决策', en: 'AI may be inaccurate. Investing involves risk.' },
    'spa.ai_s1': { zh: '美股王软件有什么优势？', en: 'What are USKing software advantages?' },
    'spa.ai_s2': { zh: '如何成为年度会员？', en: 'How do I become an annual member?' },
    'spa.ai_s3': { zh: '推荐适合新手的课程', en: 'Beginner-friendly courses?' },
    'spa.ai_s4': { zh: '短线交易有哪些技巧？', en: 'Day trading tips?' },
    'spa.us_title': { zh: '美股数据与研究', en: 'U.S. market data' },
    'spa.us_sub': {
      zh: '整合宏观指标（FRED）、个股行情（yfinance）、SEC 公告与合规资讯源。数据仅供参考，不构成投资建议。',
      en: 'Macro (FRED), quotes (yfinance), SEC filings, and compliant news sources. Not investment advice.',
    },
    'spa.us_tab_macro': { zh: '宏观 FRED', en: 'Macro (FRED)' },
    'spa.us_tab_quote': { zh: '个股行情', en: 'Quote' },
    'spa.us_tab_sec': { zh: 'SEC 公告', en: 'SEC filings' },
    'spa.us_tab_news': { zh: '资讯', en: 'News' },
    'spa.us_tab_about': { zh: '开源与合规', en: 'Open source' },
    'spa.us_fred_hint': {
      zh: '未配置 FRED_API_KEY 时将使用 FRED 官网公开 CSV（无需注册）。配置 Key 后走官方 API，元数据更完整。常用序列：UNRATE、CPIAUCSL、FEDFUNDS、DGS10。',
      en: 'Without FRED_API_KEY, data comes from FRED public graph CSV (no signup). With a key, the official API is used. Try UNRATE, CPIAUCSL, FEDFUNDS, DGS10.',
    },
    'spa.us_fred_mode_api': { zh: '官方 API（已配 Key）', en: 'FRED API (key set)' },
    'spa.us_fred_mode_csv': { zh: '公开 CSV（未配 Key）', en: 'Public CSV (no key)' },
    'spa.us_fred_csv_badge': { zh: '公开 CSV', en: 'Public CSV' },
    'spa.us_fred_series_link': {
      zh: 'FRED 系列页（单位与频率）',
      en: 'FRED series (units & frequency)',
    },
    'spa.us_fred_csv_note': {
      zh: '数值来自 FRED 官网公开 CSV。配置 FRED_API_KEY 后将显示完整标题、单位与频率。',
      en: 'Values from FRED’s public graph CSV. Set FRED_API_KEY for full title, units, and frequency from the API.',
    },
    'spa.us_series_id': { zh: '序列 ID', en: 'Series ID' },
    'spa.us_limit': { zh: '条数', en: 'Limit' },
    'spa.us_load': { zh: '加载', en: 'Load' },
    'spa.us_load_news': { zh: '刷新资讯', en: 'Refresh news' },
    'spa.us_quote_hint': {
      zh: '基于 yfinance 拉取雅虎财经公开数据（非官方），适合快速查看报价与近期收盘价。',
      en: 'yfinance / Yahoo Finance (unofficial). Quick quote and recent closes.',
    },
    'spa.us_sec_hint': {
      zh: '使用 SEC data.sec.gov 官方 JSON。请把 SEC_HTTP_USER_AGENT 设为含联系方式的合法标识。',
      en: 'SEC official JSON. Set SEC_HTTP_USER_AGENT with contact info per SEC policy.',
    },
    'spa.us_news_hint': {
      zh: '未配置 NewsAPI 与自定义 RSS 时，自动使用 SEC 新闻稿官方 RSS。也可设置 NEWSAPI_KEY 或 NEWS_RSS_URLS。须遵守各来源 ToS。',
      en: 'With no NewsAPI key and no custom RSS, SEC official press RSS is used. You may set NEWSAPI_KEY or NEWS_RSS_URLS. Respect each source’s terms.',
    },
    'spa.us_news_empty': {
      zh: '未拉到资讯。请检查网络与 SEC_HTTP_USER_AGENT；或在 .env 配置 NEWSAPI_KEY / NEWS_RSS_URLS。若已启用内置 SEC RSS 仍为空，请查看服务器日志。',
      en: 'No headlines. Check network and SEC_HTTP_USER_AGENT, or set NEWSAPI_KEY / NEWS_RSS_URLS. If built-in SEC RSS is on but empty, see server logs.',
    },
    'spa.us_fail': { zh: '加载失败', en: 'Load failed' },
    'spa.us_on': { zh: '已配置', en: 'configured' },
    'spa.us_off': { zh: '未配置', en: 'not set' },
    'spa.us_meta': {
      zh: '数据通道：FRED {fred}；NewsAPI {news}；RSS {n} 路{suffix}',
      en: 'Data feeds: FRED — {fred}; NewsAPI — {news}; RSS — {n}{suffix}',
    },
    'spa.us_meta_builtin_suffix': {
      zh: '（已启用内置 SEC 新闻稿 RSS）',
      en: ' — built-in SEC press RSS',
    },
    'spa.us_col_date': { zh: '日期', en: 'Date' },
    'spa.us_col_value': { zh: '数值', en: 'Value' },
    'spa.us_col_close': { zh: '收盘', en: 'Close' },
    'spa.us_sec_date': { zh: '披露日', en: 'Filed' },
    'spa.us_sec_link': { zh: '链接', en: 'Link' },
    'spa.us_about_sae': {
      zh: '独立队列型数据后台，适合单独部署后与站内 API 对接；未整仓嵌入以避免与当前站点强耦合。',
      en: 'Separate data stack; deploy alongside this app rather than vendoring into the repo.',
    },
    'spa.us_about_fred': { zh: '已在服务端用于宏观序列；需圣路易斯联储 API Key。', en: 'Used server-side for macro series; FRED API key required.' },
    'spa.us_about_sec': {
      zh: '本站优先使用 SEC 官方 JSON 列公告；批量下载可再集成 sec-edgar 等库。',
      en: 'We use SEC JSON for listings; add sec-edgar for bulk downloads if needed.',
    },
    'spa.us_about_yf': { zh: '已用于个股行情与历史收盘价序列。', en: 'Used for quotes and recent daily closes.' },
    'spa.us_about_np': {
      zh: '通用新闻抽取框架；未随站打包。可在后端对合规 URL 做正文清洗与入库。',
      en: 'Article extraction framework; not bundled. Pipe compliant URLs through it on the server.',
    },
    'spa.research_title': { zh: '公司投研与资讯', en: 'Company research & news' },
    'spa.research_sub': {
      zh: '按股票代码聚合公开新闻与 SEC 披露。免费层使用 Finnhub、Alpha Vantage 官方 API（需免费注册 Key）。非卖方深度研报。',
      en: 'By ticker: public headlines plus SEC filings. Free tier uses Finnhub and Alpha Vantage (free API keys). Not sell-side research.',
    },
    'spa.research_ticker_ph': { zh: '股票代码，如 AAPL', en: 'Ticker, e.g. AAPL' },
    'spa.research_load': { zh: '加载', en: 'Load' },
    'spa.research_news_h': { zh: '新闻与资讯', en: 'News & headlines' },
    'spa.research_sec_h': { zh: 'SEC 监管披露（最近）', en: 'SEC filings (recent)' },
    'spa.research_api_status': {
      zh: '免费接口：Finnhub {fh} · Alpha Vantage {av}（官网注册后即可使用）',
      en: 'Free APIs: Finnhub {fh} · Alpha Vantage {av} (sign up on their sites)',
    },
    'spa.research_disclaimer': {
      zh: '以下为第三方免费接口提供的公开摘要与外链，非美股王投研结论，不构成投资建议。',
      en: 'Headlines and links come from third-party free APIs, not USKing research, and are not investment advice.',
    },
    'spa.research_news_empty': {
      zh: '暂无新闻条目：请先配置 FINNHUB_API_KEY 或 ALPHA_VANTAGE_API_KEY（见上方说明），或稍后重试。',
      en: 'No items yet: set FINNHUB_API_KEY or ALPHA_VANTAGE_API_KEY (see above), or try again later.',
    },
    'spa.publish_title': { zh: '发布动态', en: 'New post' },
    'spa.publish_ph': { zh: '分享你的交易心得、市场观点...', en: 'Share your trading notes or views…' },
    'spa.publish_media': { zh: '📷 图片/视频', en: '📷 Photo / video' },
    'spa.publish_btn': { zh: '发布', en: 'Post' },
    'spa.publish_need': { zh: '请输入内容或上传媒体', en: 'Add text or upload media' },
    'spa.publishing': { zh: '发布中...', en: 'Posting…' },
    'spa.profile_login': { zh: '请先登录查看个人主页', en: 'Sign in to view your profile' },
    'spa.register': { zh: '注册', en: 'Sign up' },
    'spa.user_fail': { zh: '用户不存在或加载失败', en: 'User not found or load failed' },
    'spa.works': { zh: '作品', en: 'Posts' },
    'spa.no_works': { zh: '暂无作品', en: 'No posts yet' },
    'spa.member_badge': { zh: '会员', en: 'VIP' },
    'spa.follow': { zh: '关注', en: 'Follow' },
    'spa.followed': { zh: '已关注', en: 'Following' },
    'spa.following_n': { zh: '关注', en: 'Following' },
    'spa.followers_n': { zh: '粉丝', en: 'Followers' },
    'spa.dm': { zh: '私信', en: 'Message' },
    'spa.share': { zh: '分享', en: 'Share' },
    'spa.collect': { zh: '收藏', en: 'Save' },
    'spa.collected': { zh: '已收藏', en: 'Saved' },
    'spa.home': { zh: '主页', en: 'Profile' },
    'spa.cover_change': { zh: '更换封面', en: 'Change cover' },
    'spa.avatar_change': { zh: '更换', en: 'Change' },
    'spa.post_work': { zh: '+ 投稿', en: '+ Post' },
    'spa.gender_m': { zh: '男', en: 'M' },
    'spa.gender_f': { zh: '女', en: 'F' },
    'spa.gender_o': { zh: '其他', en: 'Other' },
    'spa.joined': { zh: '加入于', en: 'Joined' },
    'spa.ft_work_fallback': { zh: '作品', en: 'Post' },
    'spa.ft_play': { zh: '播放/暂停', en: 'Play / Pause' },
    'spa.ft_mute': { zh: '静音', en: 'Mute' },
    'spa.num_wan': { zh: '万', en: 'w' },

    'dash.watermark': { zh: '美股王 · 交易直播', en: 'USKing · Live' },
    'dash.plat_configured': { zh: '✓ 已配置', en: '✓ Set' },
    'dash.plat_not_configured': { zh: '未配置', en: 'Not set' },
    'dash.rtmp_server': { zh: '推流地址 (RTMP Server)', en: 'RTMP server' },
    'dash.stream_key': { zh: '推流密钥 (Stream Key)', en: 'Stream key' },
    'dash.show_hide': { zh: '显示/隐藏', en: 'Show / hide' },
    'dash.test_conn': { zh: '测试连接', en: 'Test connection' },
    'dash.remove_plat': { zh: '删除', en: 'Remove' },
    'dash.fill_rtmp': { zh: '请填写推流地址和密钥', en: 'Enter RTMP URL and stream key' },
    'dash.testing': { zh: '⏳ 测试中...', en: '⏳ Testing…' },
    'dash.test_ok': { zh: '✓ 配置格式正确，开播后将自动推流', en: '✓ Valid; will auto-push when live' },
    'dash.all_plats': { zh: '已添加所有平台', en: 'All platforms added' },
    'dash.window_n': { zh: '窗口 ', en: 'Window ' },
    'dash.capturing': { zh: '采集中', en: 'Capturing' },
    'dash.stop_src': { zh: '停止', en: 'Stop' },

    'spa.grid_no_title': { zh: '（无标题）', en: '(No title)' },
    'spa.grid_video': { zh: '视频', en: 'Video' },
    'spa.my_save_ok': { zh: '保存成功', en: 'Saved' },
    'spa.no_followers': { zh: '暂无粉丝', en: 'No followers yet' },
    'spa.no_following': { zh: '暂未关注任何人', en: 'Not following anyone yet' },
    'spa.no_bookmarks_yet': { zh: '还没有收藏', en: 'No bookmarks yet' },
    'spa.posts_empty_hint': { zh: '还没有作品，去发布第一条吧', en: 'No posts yet. Share your first!' },
    'spa.profile_edit_btn': { zh: '编辑资料', en: 'Edit profile' },
    'spa.edit_tab': { zh: '编辑', en: 'Edit' },
    'profile.save_btn': { zh: '保存资料', en: 'Save profile' },
    'profile.gender_unset': { zh: '未设置', en: 'Unset' },
    'profile.birthday': { zh: '出生日期', en: 'Birthday' },
    'profile.gender_field': { zh: '性别', en: 'Gender' },
    'spa.avatar_up_fail': { zh: '头像上传失败', en: 'Avatar upload failed' },
    'spa.cover_up_fail': { zh: '封面上传失败', en: 'Cover upload failed' },
    'spa.delete_work': { zh: '删除作品', en: 'Delete post' },
    'spa.sr_searching': { zh: '搜索中...', en: 'Searching…' },
    'spa.sr_fail': { zh: '搜索失败', en: 'Search failed' },
    'spa.sr_section_course': { zh: '📚 课程', en: '📚 Courses' },
    'spa.sr_section_live': { zh: '🔴 直播', en: '🔴 Live' },
    'spa.sr_section_posts': { zh: '📝 动态', en: '📝 Posts' },
    'spa.ai_thinking_inline': { zh: '思考中...', en: 'Thinking…' },
    'spa.ai_unavailable': { zh: '抱歉，服务暂不可用，请稍后再试', en: 'Service unavailable. Try again later.' },
    'set.title': { zh: '设置', en: 'Settings' },
    'set.change_pwd': { zh: '修改密码', en: 'Change password' },
    'set.cur_pwd_label': { zh: '当前密码', en: 'Current password' },
    'set.new_pwd_label': { zh: '新密码', en: 'New password' },
    'set.conf_pwd_label': { zh: '确认新密码', en: 'Confirm new password' },
    'set.ph_cur': { zh: '输入当前密码', en: 'Current password' },
    'set.ph_new': { zh: '输入新密码（至少6位）', en: 'New password (min 6 characters)' },
    'set.ph_conf': { zh: '再次输入新密码', en: 'Confirm new password' },
    'set.update_btn': { zh: '更新密码', en: 'Update password' },
    'set.account': { zh: '账户信息', en: 'Account' },
    'set.user_label': { zh: '用户名：', en: 'Username:' },
    'set.reg_label': { zh: '注册时间：', en: 'Registered:' },
    'set.mem_label': { zh: '会员状态：', en: 'Membership:' },
    'set.mem_vip': { zh: '年度会员', en: 'Annual member' },
    'set.mem_free': { zh: '普通用户', en: 'Standard' },
    'set.danger': { zh: '危险操作', en: 'Danger zone' },
    'set.logout_confirm': { zh: '确定要退出登录？', en: 'Log out?' },

    'moment.user': { zh: '用户', en: 'User' },
    'moment.posted': { zh: '发布于', en: 'Posted' },
    'moment.media_count': { zh: '共 {n} 张图片/视频', en: '{n} photos / videos' },
    'moment.no_caption': { zh: '（无文字说明）', en: '(No caption)' },
    'moment.no_media': { zh: '本条动态暂无图片/视频', en: 'No images or videos' },
    'moment.cover': { zh: '封面', en: 'Cover' },
    'moment.delete': { zh: '删除', en: 'Delete' },
    'moment.set_cover': { zh: '设封面', en: 'Set cover' },
    'moment.delete_post': { zh: '删除整条作品（含全部图片/视频）', en: 'Delete entire post (all media)' },
    'moment.confirm_del_media': { zh: '确定删除这张图片/视频？不可恢复。', en: 'Delete this photo/video? This cannot be undone.' },
    'moment.confirm_del_post': { zh: '确定删除整条作品？其中所有图片、视频与文字将一并删除，且不可恢复。', en: 'Delete this entire post and all media? This cannot be undone.' },
    'moment.del_fail': { zh: '删除失败', en: 'Delete failed' },
    'moment.cover_fail': { zh: '设置失败', en: 'Update failed' },
    'moment.load_fail': { zh: '加载失败', en: 'Load failed' },

    'set.fill_all': { zh: '请填写所有字段', en: 'Fill in all fields' },
    'set.pwd_short': { zh: '新密码至少6位', en: 'New password at least 6 characters' },
    'set.pwd_mismatch': { zh: '两次输入的密码不一致', en: 'Passwords do not match' },
    'set.pwd_ok': { zh: '密码修改成功', en: 'Password updated' },
  },

  get lang() { return this._lang; },

  set lang(v) {
    this._lang = normalizeI18nLang(v);
    localStorage.setItem('lang', this._lang);
    document.documentElement.lang = this._lang === 'zh' ? 'zh-CN' : 'en';
    this.apply();
    this._updateToggle();
    this._syncDocTitle();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('i18n-changed', { detail: { lang: v } }));
    }
  },

  t(key) {
    const entry = this.dict[key];
    if (!entry) return key;
    return entry[this._lang] || entry.zh || key;
  },

  /** Replace {name}, {n}, … in translated string */
  fmt(key, vars) {
    let s = this.t(key);
    if (vars && typeof vars === 'object') {
      Object.keys(vars).forEach(k => {
        s = s.split(`{${k}}`).join(String(vars[k]));
      });
    }
    return s;
  },

  _syncDocTitle() {
    if (typeof document === 'undefined') return;
    const el = document.querySelector('[data-title-i18n]');
    const k = el && el.getAttribute('data-title-i18n');
    if (k) document.title = this.t(k);
  },

  apply() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const text = this.t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = text;
      } else {
        el.textContent = text;
      }
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
      el.placeholder = this.t(el.getAttribute('data-i18n-ph'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = this.t(el.getAttribute('data-i18n-title'));
    });
  },

  _updateToggle() {
    const btn = document.getElementById('langToggle');
    if (btn) btn.textContent = this._lang === 'zh' ? 'EN' : '中';
  },

  init() {
    this._lang = normalizeI18nLang(
      typeof localStorage !== 'undefined' ? localStorage.getItem('lang') : this._lang
    );
    localStorage.setItem('lang', this._lang);
    document.documentElement.lang = this._lang === 'zh' ? 'zh-CN' : 'en';
    this.apply();
    this._updateToggle();
    this._syncDocTitle();
  },

  toggle() {
    this.lang = this._lang === 'zh' ? 'en' : 'zh';
  }
};

/* Top-level const/let are not on `window` — inline onclick must use window.I18N */
if (typeof window !== 'undefined') window.I18N = I18N;
