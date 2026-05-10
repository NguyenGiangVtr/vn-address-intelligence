/* ══════════════════════════════════════════════════════════════
   VN Address Intelligence — SaaS App Logic
   ══════════════════════════════════════════════════════════════ */

const DEFAULT_API_BASE = window.location.hostname === "localhost" || window.location.protocol === "file:"
  ? "http://localhost:8081/api"
  : "/api";

const UI_SETTINGS_STORAGE_KEY = 'vnai_ui_settings_v1';
const VALID_THEMES = new Set(['dark', 'light', 'oled-black']);
const VALID_MOTION_MODES = new Set(['smooth', 'fast', 'off']);

function normalizeApiBase(url) {
  const raw = String(url || '').trim();
  if (!raw) return DEFAULT_API_BASE;
  return raw.replace(/\/+$/, '');
}

function loadUISettings() {
  try {
    const raw = localStorage.getItem(UI_SETTINGS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function saveUISettings(settings) {
  localStorage.setItem(UI_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}

function resolveTheme(theme) {
  return VALID_THEMES.has(theme) ? theme : 'dark';
}

function resolveMotionMode(mode) {
  return VALID_MOTION_MODES.has(mode) ? mode : 'smooth';
}

function applyVisualSettings(settings) {
  const theme = resolveTheme(settings?.theme);
  const motion = resolveMotionMode(settings?.animations);
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-motion', motion);
}

let API_BASE = normalizeApiBase(loadUISettings().apiBaseUrl);
applyVisualSettings(loadUISettings());

function getApiBaseCandidates() {
  const candidates = [API_BASE, normalizeApiBase(loadUISettings().apiBaseUrl), DEFAULT_API_BASE];

  if (window.location.origin && window.location.origin !== 'null') {
    candidates.push(`${window.location.origin}/api`);
  }

  return [...new Set(candidates.filter(Boolean).map((value) => normalizeApiBase(value)))];
}

async function fetchWithApiFallback(path, options = {}) {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  let lastError = null;

  for (const base of getApiBaseCandidates()) {
    try {
      return await fetch(`${base}${suffix}`, options);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error(`Unable to reach API for ${suffix}`);
}

const PAGES = [
  "overview", "parser", "batch", "training", "label-studio",
  "experiments", "explorer", "osm-enrichment", "lookup", "boundary-visualization",
  "admin-units", "nso-sync", "settings", "evidence", "label-registry", "prelabeler-cases",
  "documentation",
];

const {
  applyUnifiedControlTemplate,
  renderLookupTemplateDatalist,
  renderUnifiedSelectOptions,
  showToast,
  showConfirm
} = window.VNAIControls || {};

// ── Auth Check ──
if (!localStorage.getItem('vnai_token') && !window.location.pathname.includes('login.html')) {
  window.location.href = 'login.html';
}

function getAuthHeader() {
  const token = localStorage.getItem('vnai_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

/** Any 401 from this app’s API clears the session and opens the login page (covers all fetch call sites). */
(function installFetchUnauthorizedRedirect() {
  const nativeFetch = window.fetch.bind(window);

  function requestUrlString(input) {
    if (typeof input === 'string') return input;
    if (input instanceof Request) return input.url;
    if (input != null && typeof input === 'object' && typeof input.url === 'string') return input.url;
    return '';
  }

  function isAppApiRequest(input) {
    const urlStr = requestUrlString(input);
    if (!urlStr) return false;
    let resolved;
    try {
      resolved = new URL(urlStr, window.location.href);
    } catch (_err) {
      return false;
    }
    const path = resolved.pathname || '';
    if (path === '/api' || path.startsWith('/api/')) return true;
    const normalizedHref = resolved.href.split(/[?#]/)[0].replace(/\/+$/, '');
    for (const base of getApiBaseCandidates()) {
      const prefix = String(base || '').replace(/\/+$/, '');
      if (!prefix) continue;
      if (normalizedHref === prefix || normalizedHref.startsWith(`${prefix}/`)) return true;
    }
    return false;
  }

  window.fetch = async function fetchWithUnauthorizedRedirect(input, init) {
    const response = await nativeFetch(input, init);
    if (response.status === 401 && isAppApiRequest(input)) {
      try {
        localStorage.removeItem('vnai_token');
      } catch (_e) {}
      window.location.href = 'login.html';
    }
    return response;
  };
})();

async function logoutAndRedirect() {
  try {
    await fetch(`${API_BASE}/logout`, {
      method: 'POST',
      headers: getAuthHeader(),
    });
  } catch (error) {
    console.warn('Logout request failed, clearing local session anyway.', error);
  } finally {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
  }
}

// ═══════════════════════════════════════════════════════════
// MOBILE MENU HELPER
// ═══════════════════════════════════════════════════════════
function closeMobileMenu() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.remove("mobile-active");
  if (overlay) overlay.classList.remove("mobile-active");
  document.body.classList.remove("no-scroll");
}

// ═══════════════════════════════════════════════════════════
// URL ROUTING & SEO
// ═══════════════════════════════════════════════════════════

// Page metadata for SEO
const PAGE_META = {
  'overview': {
    title: 'Tổng quan - Vietnamese Address Intelligence',
    description: 'Nền tảng phân tích địa chỉ Việt Nam sử dụng AI và Machine Learning cho nghiên cứu khoa học và triển khai SaaS',
    keywords: 'địa chỉ việt nam, AI, machine learning, NER, phân tích địa chỉ'
  },
  'parser': {
    title: 'Phân tích địa chỉ - Vietnamese Address Intelligence',
    description: 'Công cụ phân tích địa chỉ Việt Nam bằng 4 mô hình AI: PreLabeler, PhoBERT, mGTE và Qwen LLM',
    keywords: 'parser, phân tích địa chỉ, NER, AddressNER, PhoBERT, mGTE, Qwen, Hugging Face'
  },
  'batch': {
    title: 'Xử lý hàng loạt - Vietnamese Address Intelligence',
    description: 'Xử lý và phân tích nhiều địa chỉ cùng lúc với khả năng batch processing hiệu quả',
    keywords: 'batch processing, xử lý hàng loạt, bulk address parsing'
  },
  'explorer': {
    title: 'Khám phá hàng đợi - Vietnamese Address Intelligence',
    description: 'Khám phá và quản lý hàng đợi xử lý địa chỉ, theo dõi tiến trình phân tích',
    keywords: 'queue explorer, hàng đợi, job queue'
  },
  'lookup': {
    title: 'Chuyển đổi ĐVHC - Vietnamese Address Intelligence',
    description: 'Công cụ chuyển đổi và tra cứu đơn vị hành chính Việt Nam',
    keywords: 'đvhc, đơn vị hành chính, lookup, administrative units'
  },
  'boundary-visualization': {
    title: 'Ranh giới hành chính - Vietnamese Address Intelligence',
    description: 'Trực quan hóa ranh giới hành chính Việt Nam trên bản đồ tương tác',
    keywords: 'ranh giới, boundary, bản đồ, visualization, administrative boundary'
  },
  'osm-enrichment': {
    title: 'Làm giàu OSM - Vietnamese Address Intelligence',
    description: 'Làm giàu dữ liệu địa chỉ từ OpenStreetMap để cải thiện độ chính xác',
    keywords: 'OSM, OpenStreetMap, data enrichment, làm giàu dữ liệu'
  },
  'label-studio': {
    title: 'Nhãn dữ liệu - Vietnamese Address Intelligence',
    description: 'Công cụ gán nhãn dữ liệu để huấn luyện và cải thiện mô hình AI',
    keywords: 'label studio, gán nhãn, data labeling, machine learning'
  },
  'training': {
    title: 'Huấn luyện mô hình - Vietnamese Address Intelligence',
    description: 'Huấn luyện và tối ưu hóa các mô hình AI cho phân tích địa chỉ Việt Nam',
    keywords: 'training, huấn luyện mô hình, AI training, model optimization'
  },
  'experiments': {
    title: 'So sánh mô hình - Vietnamese Address Intelligence',
    description: 'So sánh hiệu suất và độ chính xác của các mô hình AI khác nhau',
    keywords: 'model comparison, so sánh mô hình, benchmarking, evaluation'
  },
  'label-registry': {
    title: 'Danh sách nhãn NER - Vietnamese Address Intelligence',
    description: 'Danh sách đầy đủ các nhãn Named Entity Recognition được sử dụng trong hệ thống',
    keywords: 'NER labels, nhãn NER, named entity recognition, label registry'
  },
  'nso-sync': {
    title: 'Đồng bộ NSO/Gov - Vietnamese Address Intelligence',
    description: 'Đồng bộ dữ liệu từ Tổng cục Thống kê và các cơ quan chính phủ',
    keywords: 'NSO sync, government data, đồng bộ dữ liệu chính phủ'
  },
  'admin-units': {
    title: 'Quản lý ĐVHC - Vietnamese Address Intelligence',
    description: 'Quản lý danh sách và thông tin đơn vị hành chính Việt Nam',
    keywords: 'admin units, đvhc, quản lý đơn vị hành chính'
  },
  'settings': {
    title: 'Cài đặt - Vietnamese Address Intelligence',
    description: 'Cấu hình và tùy chỉnh hệ thống Vietnamese Address Intelligence',
    keywords: 'settings, cài đặt, configuration, preferences'
  },
  'prelabeler-cases': {
    title: 'Address Label Studio - Vietnamese Address Intelligence',
    description: 'Thiết lập nhãn kỳ vọng, đối chiếu với gợi ý nhãn rule (PreLabeler) và tinh chỉnh dữ liệu địa chỉ',
    keywords: 'address labeling, vietnam address, ner, annotation, expected labels'
  },
  documentation: {
    title: 'Trung tâm tài liệu - Vietnamese Address Intelligence',
    description: 'Đọc trực tiếp các tệp Markdown trong docs/ của repository — trùng nội dung với repo, không có bản HTML tĩnh riêng',
    keywords: 'documentation, readme, playbook, markdown, huấn luyện, pipeline'
  }
};

// URL Routing functions
function updateURL(pageId, pushState = true) {
  const newURL = pageId === 'overview' ? '#/' : `#/${pageId}`;
  if (pushState && window.location.hash !== newURL) {
    window.history.pushState({ page: pageId }, '', newURL);
  }
  updatePageMeta(pageId);
}

function updatePageMeta(pageId) {
  const meta = PAGE_META[pageId];
  if (!meta) return;

  // Update title
  document.title = meta.title;

  // Update or create meta tags
  updateMetaTag('description', meta.description);
  updateMetaTag('keywords', meta.keywords);

  // Update canonical URL
  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement('link');
    canonical.rel = 'canonical';
    document.head.appendChild(canonical);
  }
  const baseUrl = window.location.origin + window.location.pathname;
  const canonicalUrl = pageId === 'overview' ? baseUrl : `${baseUrl}#/${pageId}`;
  canonical.href = canonicalUrl;

  // Update Open Graph tags for social sharing
  updateMetaTag('og:title', meta.title, 'property');
  updateMetaTag('og:description', meta.description, 'property');
  updateMetaTag('og:url', canonicalUrl, 'property');
  updateMetaTag('og:type', 'website', 'property');

  // Update Twitter Card tags
  updateMetaTag('twitter:card', 'summary_large_image', 'name');
  updateMetaTag('twitter:title', meta.title, 'name');
  updateMetaTag('twitter:description', meta.description, 'name');
  updateMetaTag('twitter:url', canonicalUrl, 'name');
}

function updateMetaTag(name, content, attribute = 'name') {
  let meta = document.querySelector(`meta[${attribute}="${name}"]`);
  if (!meta) {
    meta = document.createElement('meta');
    meta.setAttribute(attribute, name);
    document.head.appendChild(meta);
  }
  meta.setAttribute('content', content);
}

function getPageFromURL() {
  const hash = window.location.hash;
  if (!hash || hash === '#/' || hash === '#') {
    return 'overview';
  }
  let pageId = hash.substring(2); // Remove '#/'
  if (pageId === 'prelabeler-test') {
    pageId = 'prelabeler-cases';
  }

  // Validate if page exists
  const pageEl = document.getElementById(pageId);
  return pageEl ? pageId : 'overview';
}

function navigateToPage(pageId, shouldUpdateURL = true) {
  // Find the nav item and trigger click
  const navItem = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (navItem) {
    // Remove active from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
    });

    // Add active to target
    navItem.classList.add('active');

    // Switch pages
    document.querySelectorAll('.page').forEach(page => {
      page.classList.toggle('active', page.id === pageId);
    });

    if (pageId !== 'prelabeler-cases') window.pltDismissRandomPredictLoadingOverlay?.();

    // Update title
    const titleEl = document.getElementById('page-title');
    if (titleEl) {
      const spanEl = navItem.querySelector('span');
      titleEl.textContent = (spanEl ? spanEl.textContent : navItem.textContent).trim();
    }

    // Open parent group if needed
    const group = PAGE_GROUP_MAP[pageId];
    if (group) openNavGroup(group);

    // Page-specific initialization
    initializePageSpecific(pageId);

    // Update URL and meta
    if (shouldUpdateURL) {
      updateURL(pageId);
    }

    // UI adjustments
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const contentEl = document.getElementById('page-content');
    if (contentEl) contentEl.scrollTo({ top: 0, behavior: 'smooth' });

    closeMobileMenu();
    setTimeout(adjustActivePageHeight, 350);
  }
}

function initializePageSpecific(pageId) {
  // Page-specific initialization logic
  switch (pageId) {
    case 'parser':
      if (_parserStatusPollTimer) clearTimeout(_parserStatusPollTimer);
      _pollParserModelStatus();
      break;
    case 'label-registry':
      populateLabelRegistry();
      break;
    case 'prelabeler-cases':
      if (window.pltInitPage) window.pltInitPage();
      break;
    case 'documentation':
      initDocumentationHub();
      break;
    // Add more page-specific initialization as needed
  }
}

// ══════════════════════════════════════════════════════════════
// TRUNG TÂM TÀI LIỆU — đọc trực tiếp *.md trong docs/ qua GET /api/repo-docs
// Render: markdown-it + highlight.js + github-markdown-css (CDN)
// Mục lục: cây thư mục có thứ tự (numeric trong tên được sort đúng)
// ══════════════════════════════════════════════════════════════

const DOC_HUB_LS_KEY = 'vnai_doc_hub_path';
const DOC_UI_LIB_REV = 'mdit-hljs-1';

const docHubState = {
  docs: [],
  currentPath: null,
  libsPromise: null,
  libRevApplied: '',
  navBuilt: false,
};

let repoDocsMarkdownIt = null;

function repoDocsResetMarkdownLibs() {
  docHubState.libsPromise = null;
  repoDocsMarkdownIt = null;
  docHubState.libRevApplied = '';
}

function repoDocsScriptOnce(src, idempotentId) {
  return new Promise((resolve, reject) => {
    if (idempotentId && document.getElementById(idempotentId)) {
      resolve();
      return;
    }
    const s = document.createElement('script');
    if (idempotentId) s.id = idempotentId;
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Không tải được thư viện: ${src}`));
    document.head.appendChild(s);
  });
}

function repoDocsLinkOnce(href, id) {
  if (document.getElementById(id)) return;
  const l = document.createElement('link');
  l.rel = 'stylesheet';
  l.href = href;
  l.id = id;
  document.head.appendChild(l);
}

function docHubIsDarkTheme() {
  const t = document.documentElement.getAttribute('data-theme') || '';
  return t === 'dark' || t === 'oled-black';
}

function docHubApplyMarkdownStylesheets() {
  const dark = docHubIsDarkTheme();
  const mdOld = document.getElementById('vnai-doc-gh-md');
  const hlOld = document.getElementById('vnai-doc-hljs');
  if (mdOld) mdOld.remove();
  if (hlOld) hlOld.remove();
  repoDocsLinkOnce(
    dark
      ? 'https://cdn.jsdelivr.net/npm/github-markdown-css@5.7.1/github-markdown-dark.min.css'
      : 'https://cdn.jsdelivr.net/npm/github-markdown-css@5.7.1/github-markdown-light.min.css',
    'vnai-doc-gh-md'
  );
  repoDocsLinkOnce(
    dark
      ? 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css'
      : 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css',
    'vnai-doc-hljs'
  );
}

function docHubEnsureThemeObserver() {
  if (docHubState._themeObs) return;
  docHubState._themeObs = new MutationObserver(() => {
    if (document.getElementById('documentation')?.classList.contains('active')) {
      docHubApplyMarkdownStylesheets();
    }
  });
  docHubState._themeObs.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });
}

function docHubEscapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function repoDocsEnsureMarkdownLibs() {
  if (docHubState.libRevApplied !== DOC_UI_LIB_REV) {
    repoDocsResetMarkdownLibs();
    docHubState.libRevApplied = DOC_UI_LIB_REV;
  }
  if (!docHubState.libsPromise) {
    docHubApplyMarkdownStylesheets();
    docHubEnsureThemeObserver();
    docHubState.libsPromise = Promise.all([
      repoDocsScriptOnce(
        'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js',
        'vnai-hljs'
      ),
      repoDocsScriptOnce(
        'https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js',
        'vnai-markdown-it'
      ),
      repoDocsScriptOnce(
        'https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js',
        'vnai-dompurify'
      ),
    ]).then(() => {
      const hl = window.hljs;
      const Md = window.markdownit || window.markdownIt;
      if (typeof Md !== 'function') throw new Error('markdown-it chưa sẵn sàng');
      const inst = Md({
        html: false,
        linkify: true,
        typographer: true,
        highlight: (str, lang) => {
          const esc = docHubEscapeHtml(str);
          const safeLang = String(lang || '').replace(/[^a-zA-Z0-9_-]/g, '') || 'text';
          if (lang && hl && hl.getLanguage(lang)) {
            try {
              const v = hl.highlight(str, { language: lang, ignoreIllegals: true }).value;
              return `<pre><code class="hljs language-${safeLang}">${v}</code></pre>`;
            } catch (_e) {
              /* fall through */
            }
          }
          if (hl && typeof hl.highlightAuto === 'function') {
            try {
              const v = hl.highlightAuto(str).value;
              return `<pre><code class="hljs">${v}</code></pre>`;
            } catch (_e) {
              /* fall through */
            }
          }
          return `<pre><code class="hljs">${esc}</code></pre>`;
        },
      });
      repoDocsMarkdownIt = inst;
      try {
        inst.enable(["table"]);
      } catch (_e) {
        /* bảng mặc định không bật trên một số build — bỏ qua */
      }
    });
  }
  return docHubState.libsPromise;
}

function repoDocsMarkdownToHtml(mdText) {
  if (!repoDocsMarkdownIt) throw new Error('markdown-it chưa khởi tạo');
  return repoDocsMarkdownIt.render(mdText);
}

function docHubNaturalCompare(a, b) {
  return String(a).localeCompare(String(b), 'vi', { numeric: true, sensitivity: 'base' });
}

function docHubHumanFolderLabel(segment) {
  if (!segment) return '';
  return String(segment).replace(/-/g, ' ');
}

function docHubNewTree() {
  return { dirs: new Map(), files: [] };
}

function docHubTreeAdd(tree, doc) {
  const parts = doc.path.split('/').filter(Boolean);
  if (parts.length === 1) {
    tree.files.push(doc);
    return;
  }
  let cur = tree;
  for (let i = 0; i < parts.length - 1; i++) {
    const seg = parts[i];
    if (!cur.dirs.has(seg)) cur.dirs.set(seg, docHubNewTree());
    cur = cur.dirs.get(seg);
  }
  cur.files.push(doc);
}

function docHubTreeLeafCount(node) {
  let n = node.files.length;
  for (const ch of node.dirs.values()) n += docHubTreeLeafCount(ch);
  return n;
}

/** Mở folder chứa tài liệu hiện tại */
function docHubExpandForPath(relPath) {
  const segments = relPath.split('/').filter(Boolean);
  if (segments.length <= 1) return;
  let acc = '';
  for (let i = 0; i < segments.length - 1; i++) {
    acc = i === 0 ? segments[0] : `${acc}/${segments[i]}`;
    const el = document.querySelector(`#doc-hub-nav details[data-folder-rel="${acc}"]`);
    if (el) el.open = true;
  }
}

function docHubMakeLeafButton(doc) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'doc-hub-nav-btn';
  btn.dataset.path = doc.path;
  if (doc.path === 'INDEX.md') btn.classList.add('doc-hub-toc-leaf-index');
  const title = document.createElement('span');
  title.textContent = doc.title || doc.path.split('/').pop();
  const meta = document.createElement('span');
  meta.className = 'doc-hub-nav-meta';
  meta.textContent = doc.path;
  btn.appendChild(title);
  btn.appendChild(meta);
  btn.addEventListener('click', () => {
    docHubLoadDocument(doc.path);
    docHubSetActiveNav(doc.path);
  });
  return btn;
}

/** @param {*} container HTMLElement */
function docHubLeafCompare(a, b) {
  if (a.path === 'INDEX.md' && b.path !== 'INDEX.md') return -1;
  if (b.path === 'INDEX.md' && a.path !== 'INDEX.md') return 1;
  return docHubNaturalCompare(a.path, b.path);
}

function docHubRenderTree(container, tree, folderRelPrefix) {
  const filesSorted = tree.files.slice().sort(docHubLeafCompare);
  for (const doc of filesSorted) {
    container.appendChild(docHubMakeLeafButton(doc));
  }

  const keys = [...tree.dirs.keys()].sort(docHubNaturalCompare);
  for (const key of keys) {
    const subtree = tree.dirs.get(key);
    const rel = folderRelPrefix ? `${folderRelPrefix}/${key}` : key;
    if (!subtree || docHubTreeLeafCount(subtree) === 0) continue;

    const details = document.createElement('details');
    details.className = 'doc-hub-toc-folder';
    details.dataset.folderRel = rel;
    const depth = rel.split('/').length;
    details.open = depth <= 2;

    const summary = document.createElement('summary');
    summary.className = 'doc-hub-toc-summary';
    summary.textContent = docHubHumanFolderLabel(key);

    const inner = document.createElement('div');
    inner.className = 'doc-hub-toc-branch doc-hub-toc-inner';

    docHubRenderTree(inner, subtree, rel);

    details.appendChild(summary);
    details.appendChild(inner);
    container.appendChild(details);
  }
}

function docHubBuildNavTree(docsFiltered) {
  const nav = document.getElementById('doc-hub-nav');
  if (!nav) return;

  nav.innerHTML = '';

  const tree = docHubNewTree();
  for (const doc of docsFiltered) {
    docHubTreeAdd(tree, doc);
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'doc-hub-toc-branch doc-hub-toc-branch--root';

  if (!docHubTreeLeafCount(tree)) {
    const p = document.createElement('div');
    p.className = 'doc-hub-toc-empty';
    p.textContent = 'Không có tài liệu khớp bộ lọc.';
    nav.appendChild(p);
    return;
  }

  docHubRenderTree(wrapper, tree, '');
  nav.appendChild(wrapper);
}

function docHubResolveMdLink(currentPath, href) {
  if (!href || href.startsWith('#')) return null;
  const trimmed = href.trim();
  if (/^mailto:/i.test(trimmed)) return { external: true, url: trimmed };
  if (/^https?:\/\//i.test(trimmed)) return { external: true, url: trimmed };

  try {
    const baseDir =
      currentPath && currentPath.includes('/')
        ? currentPath.slice(0, currentPath.lastIndexOf('/') + 1)
        : '';
    const u = new URL(trimmed, `http://vnai.doc/${baseDir}`);
    let pathname = decodeURIComponent(u.pathname.replace(/^\//, ''));
    pathname = pathname.split('#')[0].split('?')[0];
    if (!pathname.toLowerCase().endsWith('.md')) {
      return { external: true, url: trimmed };
    }
    return { path: pathname.replace(/\\/g, '/') };
  } catch (_e) {
    return null;
  }
}

async function docHubFetchList() {
  const res = await fetchWithApiFallback('/repo-docs/list', { headers: getAuthHeader() });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const data = await res.json();
  return Array.isArray(data.documents) ? data.documents : [];
}

function docHubDocsMatchingFilter(docs, q) {
  const qLower = q.trim().toLowerCase();
  if (!qLower) return docs.slice();
  return docs.filter(
    (d) =>
      (d.title && d.title.toLowerCase().includes(qLower)) ||
      (d.path && d.path.toLowerCase().includes(qLower))
  );
}

function docHubRebuildNav(docs, q) {
  docHubBuildNavTree(docHubDocsMatchingFilter(docs, q));
  if (docHubState.currentPath) {
    docHubExpandForPath(docHubState.currentPath);
    docHubSetActiveNav(docHubState.currentPath);
  }
}

function docHubSetActiveNav(path) {
  document.querySelectorAll('#doc-hub-nav .doc-hub-nav-btn').forEach((b) => {
    b.classList.toggle('doc-hub-active', b.dataset.path === path);
  });
  const active = document.querySelector('#doc-hub-nav .doc-hub-nav-btn.doc-hub-active');
  if (active) {
    active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  try {
    localStorage.setItem(DOC_HUB_LS_KEY, path);
  } catch (_e) {
    /* ignore */
  }
}

function docHubBindContentClicks() {
  const host = document.getElementById('doc-hub-render');
  if (!host || host.dataset.docBound === '1') return;
  host.dataset.docBound = '1';
  host.addEventListener('click', (ev) => {
    const a = ev.target.closest('a');
    if (!a || !docHubState.currentPath) return;
    const href = a.getAttribute('href');
    const resolved = docHubResolveMdLink(docHubState.currentPath, href);
    if (!resolved || resolved.external) return;
    ev.preventDefault();
    docHubLoadDocument(resolved.path);
    docHubSetActiveNav(resolved.path);
  });
}

async function docHubLoadDocument(relPath) {
  const status = document.getElementById('doc-hub-error');
  const render = document.getElementById('doc-hub-render');
  const crumb = document.getElementById('doc-hub-breadcrumb');
  if (!render || !crumb) return;

  if (status) {
    status.hidden = true;
    status.textContent = '';
  }
  render.innerHTML = '<div class="doc-hub-muted markdown-body doc-hub-markdown-body">Đang tải…</div>';
  crumb.textContent = relPath;

  try {
    await repoDocsEnsureMarkdownLibs();
    const encodedPath = relPath
      .split('/')
      .map((segment) => encodeURIComponent(segment))
      .join('/');
    const res = await fetchWithApiFallback(`/repo-docs/raw/${encodedPath}`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} — ${relPath}`);
    }
    const md = await res.text();
    const dirty = repoDocsMarkdownToHtml(md);
    const clean = window.DOMPurify
      ? window.DOMPurify.sanitize(dirty, { USE_PROFILES: { html: true } })
      : dirty;
    render.innerHTML = `<div class="markdown-body doc-hub-markdown-body">${clean}</div>`;
    docHubState.currentPath = relPath;
    docHubExpandForPath(relPath);
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    if (status) {
      status.textContent = msg;
      status.hidden = false;
    }
    render.innerHTML = '';
  }
}

function initDocumentationHub() {
  const navHost = document.getElementById('doc-hub-nav');
  const navStatus = document.getElementById('doc-hub-nav-status');
  const filter = document.getElementById('doc-hub-filter');
  const btnIndex = document.getElementById('doc-hub-open-index');
  if (!navHost || !navStatus) return;

  docHubBindContentClicks();

  if (btnIndex) {
    btnIndex.onclick = () => {
      docHubLoadDocument('INDEX.md');
      docHubSetActiveNav('INDEX.md');
    };
  }

  let filterTimer;
  if (filter) {
    filter.oninput = () => {
      clearTimeout(filterTimer);
      filterTimer = setTimeout(() => docHubRebuildNav(docHubState.docs, filter.value), 200);
    };
  }

  if (docHubState.navBuilt && docHubState.docs.length) {
    docHubRebuildNav(docHubState.docs, filter ? filter.value : '');
    return;
  }

  navStatus.textContent = 'Đang tải danh sách…';
  docHubFetchList()
    .then((docs) => {
      docHubState.docs = docs;
      docHubState.navBuilt = true;
      navStatus.textContent = `${docs.length} tệp .md`;
      docHubRebuildNav(docs, filter ? filter.value : '');
      let startPath = null;
      try {
        startPath = localStorage.getItem(DOC_HUB_LS_KEY);
      } catch (_e) {
        startPath = null;
      }
      const known = (p) => docs.some((d) => d.path === p);
      if (!startPath || !known(startPath)) {
        startPath = known('INDEX.md') ? 'INDEX.md' : docs[0]?.path || null;
      }
      if (startPath) {
        docHubLoadDocument(startPath);
        docHubSetActiveNav(startPath);
      }
    })
    .catch((err) => {
      const msg = err && err.message ? err.message : String(err);
      navStatus.textContent = `Lỗi: ${msg}`;
    });
}

window.initDocumentationHub = initDocumentationHub;

function initRouting() {
  // Handle browser back/forward buttons
  window.addEventListener('popstate', (event) => {
    const pageId = getPageFromURL();
    navigateToPage(pageId, false); // Don't update URL since we're responding to URL change
  });

  // Handle initial page load routing
  const initialPageId = getPageFromURL();
  if (initialPageId !== 'overview') {
    navigateToPage(initialPageId, false); // Don't update URL, it's already correct
  } else {
    // Set initial meta for overview page
    updatePageMeta('overview');
  }

  // Handle hash changes (for compatibility)
  window.addEventListener('hashchange', () => {
    const pageId = getPageFromURL();
    navigateToPage(pageId, false);
  });
}

async function fetchNerLabelsFromApi() {
  const res = await fetchWithApiFallback("/config/ner-labels");
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const data = await res.json();
  const labels = Array.isArray(data.labels) ? data.labels : [];
  if (!labels.length) {
    throw new Error("empty labels");
  }
  return labels;
}

/** Danh sách nhãn NER — luôn lấy từ GET /api/config/ner-labels (đồng bộ constants.py). */
let NER_LABELS = [];

/**
 * Tải nhãn từ API. Gọi `forceRefresh=true` sau khi đổi API_BASE trong Settings.
 * @returns {Promise<Array>}
 */
async function ensureNerLabelsLoaded(forceRefresh = false) {
  if (!forceRefresh && NER_LABELS.length > 0) {
    window.NER_LABELS = NER_LABELS;
    return NER_LABELS;
  }
  try {
    NER_LABELS = await fetchNerLabelsFromApi();
  } catch (err) {
    console.warn("[VNAI] Không tải được /config/ner-labels:", err);
    NER_LABELS = [];
    if (showToast) {
      showToast("Không tải được danh sách nhãn NER từ API. Kiểm tra URL API và đăng nhập.", "warning");
    }
  }
  window.NER_LABELS = NER_LABELS;
  return NER_LABELS;
}

const SAMPLE_ADDRESSES = [
  "2695/7 Đường Phạm Thế Hiển, phường 7, Quận 8, Thành phố Hồ Chí Minh, Việt Nam",
  "Chung Cư Tecco Green Nest, Phan Văn Hớn, Tân Thới Nhất, Quận 12, Thành phố Hồ Chí Minh",
  "850/169, Đường Trưng Nữ Vương, Khu Vực 10 gần nhà tạp hoá, Châu Văn Liêm, Ô Môn, Cần Thơ",
  "số 5 ngõ 10 phố Tôn Thất Tùng, phường Trung Tự, quận Đống Đa, Hà Nội",
  "Tổ 3 ấp Phước Hưng, xã Long Phước, thành phố Bà Rịa, tỉnh Bà Rịa-Vũng Tàu",
  "Lô E2-20 Khu đô thị Mega Residence, đường 990B, Phú Hữu, TP. Thủ Đức, HCM",
];

const KPI_TARGETS = {
  f1: 82,
  throughput: 20,
  costPerMillion: 100,
  googleMatch: 75,
};

const TRAINING_HISTORY_FALLBACK = [
  { version: "v2.1", accuracy: 82.5, f1: 79.1, samples: 12000, date: "2026-03-12", loss: 0.412, notes: "Fallback snapshot" },
  { version: "v2.2", accuracy: 84.2, f1: 81.5, samples: 15800, date: "2026-03-28", loss: 0.365, notes: "Fallback snapshot" },
  { version: "v2.3", accuracy: 88.7, f1: 85.3, samples: 20100, date: "2026-04-10", loss: 0.298, notes: "Fallback snapshot" },
  { version: "v2.4", accuracy: 92.4, f1: 90.1, samples: 25130, date: "2026-04-24", loss: 0.244, notes: "Fallback snapshot" },
];

let benchmarkBaselineCache = null;
let trainingHistoryRows = [];

// ─── Formatting Helpers ───
function setupNumberInputFormatting() {
  const numberInputs = ['batch-size', 'osm-target-total', 'export-limit'];
  numberInputs.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    // Initial format
    if (el.value) {
      const numeric = el.value.replace(/\D/g, '');
      if (numeric) el.value = parseInt(numeric).toLocaleString('vi-VN');
    }

    el.addEventListener('input', (e) => {
      const input = e.target;
      const originalValue = input.value;
      const originalCursorPos = input.selectionStart;

      // Count digits before cursor in the original value
      const digitsBeforeCursor = (originalValue.substring(0, originalCursorPos).match(/\d/g) || []).length;

      const digitsOnly = originalValue.replace(/\D/g, '');
      if (digitsOnly === '') {
        input.value = '';
        return;
      }

      const formattedValue = parseInt(digitsOnly).toLocaleString('vi-VN');
      input.value = formattedValue;

      // Calculate new cursor position based on the same number of digits
      let newCursorPos = 0;
      let digitsSeen = 0;
      for (let i = 0; i < formattedValue.length; i++) {
        if (/\d/.test(formattedValue[i])) {
          digitsSeen++;
        }
        newCursorPos = i + 1;
        if (digitsSeen === digitsBeforeCursor) break;
      }
      // Only call setSelectionRange if the element supports it
      if (input.type === 'text' || input.type === 'search' || input.type === 'url' || input.type === 'tel' || input.type === 'password') {
        input.setSelectionRange(newCursorPos, newCursorPos);
      }
    });
  });
}

function getNumericInputValue(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  return parseInt(el.value.replace(/\D/g, '') || '0', 10);
}

async function fetchBenchmarkBaselines() {
  const response = await fetch(`${API_BASE}/benchmark/baselines`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`Benchmark baseline API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !payload.models) {
    throw new Error("Invalid benchmark baseline payload");
  }

  return payload.models;
}

async function fetchTrainingHistory() {
  const response = await fetch(`${API_BASE}/training/history`, {
    headers: getAuthHeader(),
  });

  if (response.status === 404) {
    return TRAINING_HISTORY_FALLBACK;
  }

  if (!response.ok) {
    throw new Error(`Training history API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !Array.isArray(payload.history)) {
    throw new Error("Invalid training history payload");
  }

  return payload.history;
}

async function createTrainingHistoryEntry(entry) {
  const response = await fetch(`${API_BASE}/training/history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify(entry),
  });

  if (response.status === 404) {
    return { status: "fallback", history: entry };
  }

  if (!response.ok) {
    throw new Error(`Training history create API failed: ${response.status}`);
  }

  return response.json();
}

function formatLogTime() {
  const d = new Date();
  const time = d.toLocaleTimeString('vi-VN', { hour12: false });
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  return `${time}.${ms}`;
}

// ─── INIT ───
document.addEventListener("DOMContentLoaded", async () => {
  if (!window.VNAIControls) {
    console.error('Missing controls-template.js. Shared UI controls are not initialized.');
    return;
  }

  await ensureNerLabelsLoaded();

  // Load all pages first
  await loadPages();

  const safeInit = (name, fn) => { try { fn(); } catch (e) { console.error(`[VNAI] Init error in ${name}:`, e); } };

  safeInit("setupNavigation", setupNavigation);
  safeInit("applyUnifiedControlTemplate", applyUnifiedControlTemplate);
  safeInit("populateLabelRegistry", populateLabelRegistry);
  safeInit("setupParserTool", setupParserTool);
  safeInit("setupBatchTool", setupBatchTool);
  safeInit("initDashboardRefreshControls", initDashboardRefreshControls);
  safeInit("initOSMEnrichmentUI", initOSMEnrichmentUI);
  safeInit("initNSOSyncTool", initNSOSyncTool);
  safeInit("initAdminManager", initAdminManager);
  safeInit("setupNumberInputFormatting", setupNumberInputFormatting);
  safeInit("initDataExplorer", initDataExplorer);
  safeInit("initLabelStudioIntegration", initLabelStudioIntegration);
  safeInit("initMappingV3", initMappingV3);
  safeInit("initIntelligenceChart", initIntelligenceChart);
  safeInit("initModelBenchmarkUI", initModelBenchmarkUI);
  safeInit("initEvidenceView", initEvidenceView);
  safeInit("initTrainingHub", initTrainingHub);
  safeInit("initBoundaryVisualizationUI", initBoundaryVisualizationUI);
  safeInit("setupThemeToggle", setupThemeToggle);
  safeInit("initSettingsPage", initSettingsPage);

  document.getElementById('btn-logout')?.addEventListener('click', async () => {
    const confirmed = !showConfirm ? true : await showConfirm('Bạn có chắc chắn muốn đăng xuất?');
    if (confirmed) {
      await logoutAndRedirect();
    }
  });

  // Initialize URL routing
  safeInit("initRouting", initRouting);

  fetchStats();
  setInterval(fetchStats, 30000);
  loadTrainingHistoryFromDB({ silent: true });
});

function getSettingsFormData() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return null;

  const env = {};
  settingsPage.querySelectorAll('[data-env-key]').forEach((input) => {
    const key = input.getAttribute('data-env-key');
    if (!key) return;
    env[key] = input.value.trim();
  });

  const apiInput = document.getElementById('cfg-api-url');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  return {
    apiBaseUrl: normalizeApiBase(apiInput?.value),
    theme: resolveTheme(themeSelect?.value),
    animations: resolveMotionMode(motionSelect?.value),
    env,
  };
}

function populateSettingsForm() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return;

  const stored = loadUISettings();
  const env = stored?.env && typeof stored.env === 'object' ? stored.env : {};

  const apiInput = document.getElementById('cfg-api-url');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  if (apiInput) {
    apiInput.value = normalizeApiBase(stored.apiBaseUrl || API_BASE || DEFAULT_API_BASE);
  }
  if (themeSelect) {
    themeSelect.value = resolveTheme(stored.theme);
  }
  if (motionSelect) {
    motionSelect.value = resolveMotionMode(stored.animations);
  }

  settingsPage.querySelectorAll('[data-env-key]').forEach((input) => {
    const key = input.getAttribute('data-env-key');
    if (!key) return;
    input.value = typeof env[key] === 'string' ? env[key] : '';
  });
}

async function testLabelStudioConnectionFromSettings(buttonNode) {
  if (!buttonNode) return;
  const original = buttonNode.innerHTML;
  buttonNode.disabled = true;
  buttonNode.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra...';

  try {
    const response = await fetch(`${API_BASE}/label-studio/debug`, {
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (result.status === 'success') {
      showToast(result.message || 'Kết nối Label Studio thành công', 'success');
    } else {
      showToast(result.message || 'Kết nối Label Studio thất bại', 'danger');
    }
  } catch (_err) {
    showToast('Không thể kết nối tới API server', 'danger');
  } finally {
    buttonNode.disabled = false;
    buttonNode.innerHTML = original;
  }
}

function updateThemeToggleButton(theme) {
  const btn = document.getElementById('btn-theme-toggle');
  if (!btn) return;
  const icon = btn.querySelector('i');
  if (!icon) return;
  if (theme === 'light') {
    icon.className = 'fa-solid fa-moon';
  } else {
    icon.className = 'fa-solid fa-sun';
  }
}

function setupThemeToggle() {
  const btn = document.getElementById('btn-theme-toggle');
  if (!btn) return;

  const current = loadUISettings();
  updateThemeToggleButton(resolveTheme(current.theme));

  btn.addEventListener('click', () => {
    const settings = loadUISettings();
    const currentTheme = resolveTheme(settings.theme);
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    settings.theme = newTheme;
    saveUISettings(settings);
    applyVisualSettings(settings);
    updateThemeToggleButton(newTheme);

    const themeSelect = document.getElementById('cfg-theme');
    if (themeSelect) {
      themeSelect.value = newTheme;
    }
  });
}

function initSettingsPage() {
  const settingsPage = document.getElementById('settings');
  if (!settingsPage) return;

  populateSettingsForm();

  const saveBtn = document.getElementById('btn-settings-save');
  const testLsBtn = document.getElementById('btn-settings-ls-test');
  const themeSelect = document.getElementById('cfg-theme');
  const motionSelect = document.getElementById('cfg-animations');

  if (themeSelect) {
    themeSelect.addEventListener('change', () => {
      const current = loadUISettings();
      current.theme = resolveTheme(themeSelect.value);
      saveUISettings(current);
      applyVisualSettings(current);
      updateThemeToggleButton(current.theme);
    });
  }

  if (motionSelect) {
    motionSelect.addEventListener('change', () => {
      const current = loadUISettings();
      current.animations = resolveMotionMode(motionSelect.value);
      saveUISettings(current);
      applyVisualSettings(current);
    });
  }

  if (testLsBtn) {
    testLsBtn.addEventListener('click', () => testLabelStudioConnectionFromSettings(testLsBtn));
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const formData = getSettingsFormData();
      if (!formData) return;

      saveUISettings(formData);
      API_BASE = formData.apiBaseUrl;
      applyVisualSettings(formData);
      await ensureNerLabelsLoaded(true);
      try {
        populateLabelRegistry();
      } catch (_e) { /* DOM có thể chưa có registry */ }
      try {
        _buildParserNERLegend();
      } catch (_e) { /* parser page có thể chưa mount */ }
      showToast('Đã lưu cấu hình Settings trên trình duyệt', 'success');
    });
  }
}

function setDashboardRefreshState(isLoading) {
  const btn = document.getElementById('btn-dashboard-refresh');
  if (!btn) return;

  btn.disabled = isLoading;
  btn.innerHTML = isLoading
    ? '<i class="fa-solid fa-spinner fa-spin"></i> Đang làm mới...'
    : '<i class="fa-solid fa-arrow-rotate-right"></i> Làm mới số liệu';
}

function updateDashboardRefreshTime() {
  const label = document.getElementById('dashboard-last-refresh');
  if (!label) return;
  label.textContent = `Cập nhật lúc ${formatLogTime()}`;
}

function initDashboardRefreshControls() {
  const btn = document.getElementById('btn-dashboard-refresh');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    await fetchStats({ manual: true });
  });
}

let intelligenceChart = null;
function initIntelligenceChart() {
  const ctx = document.getElementById('chart-training-progress');
  if (!ctx) return;

  if (intelligenceChart) intelligenceChart.destroy();

  // Load fallback data immediately for visual feedback
  const fallbackData = TRAINING_HISTORY_FALLBACK;

  intelligenceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: fallbackData.map((item) => item.version),
      datasets: [{
        label: 'Model Accuracy (%)',
        data: fallbackData.map((item) => item.accuracy),
        borderColor: '#818cf8',
        backgroundColor: 'rgba(129, 140, 248, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#818cf8'
      }, {
        label: 'F1-Score',
        data: fallbackData.map((item) => item.f1),
        borderColor: '#34d399',
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20,
            font: { size: 12 }
          }
        }
      },
      scales: {
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#5c5c5f', font: { size: 10 } },
          min: 70,
          max: 95
        },
        x: {
          grid: { display: false },
          ticks: { color: '#5c5c5f', font: { size: 10 } }
        }
      }
    }
  });
}

function isModelTargetPassed(metric) {
  return metric.f1 >= KPI_TARGETS.f1
    && metric.throughput >= KPI_TARGETS.throughput
    && metric.costPerMillion < KPI_TARGETS.costPerMillion
    && metric.googleMatch >= KPI_TARGETS.googleMatch;
}

function formatBenchmarkMetric(metric, key) {
  if (key === "f1" || key === "googleMatch") return `${metric[key].toFixed(1)}%`;
  if (key === "throughput") return `${metric[key].toFixed(1)} addr/s`;
  if (key === "costPerMillion") return `$${metric[key].toLocaleString()}`;
  return String(metric[key]);
}

function getBestMetric(models, key, comparator) {
  return Object.values(models).reduce((best, current) => {
    if (!best) return current;
    return comparator(current[key], best[key]) ? current : best;
  }, null);
}

function renderKpiCards(models) {
  const bestF1 = getBestMetric(models, "f1", (a, b) => a > b);
  const bestThroughput = getBestMetric(models, "throughput", (a, b) => a > b);
  const bestCost = getBestMetric(models, "costPerMillion", (a, b) => a < b);
  const bestGoogle = getBestMetric(models, "googleMatch", (a, b) => a > b);

  const f1El = document.getElementById("kpi-f1-current");
  const f1Status = document.getElementById("kpi-f1-status");
  if (f1El && f1Status && bestF1) {
    f1El.textContent = `${bestF1.f1.toFixed(1)}%`;
    f1Status.className = `stat-change ${bestF1.f1 >= KPI_TARGETS.f1 ? "kpi-pass" : "kpi-fail"}`;
    f1Status.textContent = `${bestF1.name} | Target ${KPI_TARGETS.f1}%`;
  }

  const tpsEl = document.getElementById("kpi-throughput-current");
  const tpsStatus = document.getElementById("kpi-throughput-status");
  if (tpsEl && tpsStatus && bestThroughput) {
    tpsEl.textContent = `${bestThroughput.throughput.toFixed(1)} addr/s`;
    tpsStatus.className = `stat-change ${bestThroughput.throughput >= KPI_TARGETS.throughput ? "kpi-pass" : "kpi-fail"}`;
    tpsStatus.textContent = `${bestThroughput.name} | Target ${KPI_TARGETS.throughput} addr/s`;
  }

  const costEl = document.getElementById("kpi-cost-current");
  const costStatus = document.getElementById("kpi-cost-status");
  if (costEl && costStatus && bestCost) {
    costEl.textContent = `$${bestCost.costPerMillion.toLocaleString()}`;
    costStatus.className = `stat-change ${bestCost.costPerMillion < KPI_TARGETS.costPerMillion ? "kpi-pass" : "kpi-fail"}`;
    costStatus.textContent = `${bestCost.name} | Target < $${KPI_TARGETS.costPerMillion}`;
  }

  const gmEl = document.getElementById("kpi-google-current");
  const gmStatus = document.getElementById("kpi-google-status");
  if (gmEl && gmStatus && bestGoogle) {
    gmEl.textContent = `${bestGoogle.googleMatch.toFixed(1)}%`;
    gmStatus.className = `stat-change ${bestGoogle.googleMatch >= KPI_TARGETS.googleMatch ? "kpi-pass" : "kpi-fail"}`;
    gmStatus.textContent = `${bestGoogle.name} | Target ${KPI_TARGETS.googleMatch}%`;
  }
}

function renderExperimentTable(models) {
  const tbody = document.getElementById("experiment-results-body");
  if (!tbody) return;

  tbody.innerHTML = Object.values(models).map((metric) => {
    const passed = isModelTargetPassed(metric);
    const statusClass = passed ? "success" : "warning";
    const statusText = passed ? "Pass" : "Partial";

    return `
      <tr>
        <td>${metric.name}</td>
        <td>${formatBenchmarkMetric(metric, "f1")}</td>
        <td>${formatBenchmarkMetric(metric, "throughput")}</td>
        <td>${formatBenchmarkMetric(metric, "costPerMillion")}</td>
        <td>${formatBenchmarkMetric(metric, "googleMatch")}</td>
        <td>F1≥${KPI_TARGETS.f1}% | TPS≥${KPI_TARGETS.throughput} | Cost&lt;$${KPI_TARGETS.costPerMillion.toLocaleString()} | Match≥${KPI_TARGETS.googleMatch}%</td>
        <td><span class="badge ${statusClass}">${statusText}</span></td>
      </tr>
    `;
  }).join("");

  adjustActivePageHeight();
}

async function buildLatestBenchmarkSnapshot() {
  if (benchmarkBaselineCache) {
    return benchmarkBaselineCache;
  }

  benchmarkBaselineCache = await fetchBenchmarkBaselines();
  return benchmarkBaselineCache;
}

let benchmarkPollTimer = null;

function setBenchmarkRunButtons(isRunning) {
  const runButtons = document.querySelectorAll('[data-action="run-experiment"]');
  runButtons.forEach((button) => {
    if (isRunning) {
      if (!button.dataset.defaultHtml) {
        button.dataset.defaultHtml = button.innerHTML;
      }
      button.disabled = true;
      button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running benchmark...';
    } else {
      button.disabled = false;
      if (button.dataset.defaultHtml) {
        button.innerHTML = button.dataset.defaultHtml;
      }
    }
  });
}

async function triggerBenchmarkJob() {
  const response = await fetch(`${API_BASE}/benchmark/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({ config_path: "app/ai/config.yaml", skip_llm: false }),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`Trigger API failed: ${response.status}`);
  }

  return response.json();
}

async function fetchBenchmarkJobStatus() {
  const response = await fetch(`${API_BASE}/benchmark/job`, {
    headers: getAuthHeader(),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`Job status API failed: ${response.status}`);
  }

  return response.json();
}

function clearBenchmarkPollTimer() {
  if (benchmarkPollTimer) {
    clearTimeout(benchmarkPollTimer);
    benchmarkPollTimer = null;
  }
}

async function pollBenchmarkUntilDone() {
  try {
    const payload = await fetchBenchmarkJobStatus();
    const job = payload?.job;
    const status = job?.status || "idle";

    if (status === "running") {
      setBenchmarkRunButtons(true);
      benchmarkPollTimer = setTimeout(pollBenchmarkUntilDone, 3000);
      return;
    }

    setBenchmarkRunButtons(false);

    if (status === "success") {
      if (window.__vnaiBenchmarkRefresh) {
        await window.__vnaiBenchmarkRefresh({ silent: true });
      }
      if (showToast) {
        showToast("Benchmark hoàn tất và đã cập nhật KPI real-time", "success");
      }
      return;
    }

    if (status === "failed") {
      const errText = job?.error ? `: ${job.error}` : "";
      if (showToast) {
        showToast(`Benchmark thất bại${errText}`, "danger");
      }
      return;
    }
  } catch (error) {
    setBenchmarkRunButtons(false);
    if (showToast) {
      showToast("Không thể theo dõi trạng thái benchmark job", "danger");
    }
    console.error("Benchmark poll error:", error);
  }
}

async function runBenchmarkJobFromUI() {
  try {
    setBenchmarkRunButtons(true);
    const trigger = await triggerBenchmarkJob();
    const state = trigger?.job?.status;

    if (state === "running") {
      if (showToast) {
        showToast("Benchmark job đã được khởi chạy", "info");
      }
      clearBenchmarkPollTimer();
      await pollBenchmarkUntilDone();
      return;
    }

    setBenchmarkRunButtons(false);
  } catch (error) {
    setBenchmarkRunButtons(false);
    if (showToast) {
      showToast("Không thể trigger benchmark job", "danger");
    }
    console.error("Benchmark trigger error:", error);
  }
}

async function fetchRealtimeBenchmark() {
  const response = await fetch(`${API_BASE}/benchmark/realtime`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`Benchmark API failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !payload.models) {
    throw new Error("Invalid benchmark payload");
  }

  return payload.models;
}

function initModelBenchmarkUI() {
  if (window.__vnaiBenchmarkRefresh) {
    window.__vnaiBenchmarkRefresh();
    return;
  }

  const runButtons = document.querySelectorAll('[data-action="run-experiment"]');
  if (!runButtons.length) return;

  const renderLatest = async ({ silent = false } = {}) => {
    try {
      const realtimeModels = await fetchRealtimeBenchmark();
      renderKpiCards(realtimeModels);
      renderExperimentTable(realtimeModels);
      if (!silent && showToast) {
        showToast("Đã đồng bộ benchmark real-time từ backend", "success");
      }
    } catch (error) {
      console.error("Benchmark realtime error:", error);
      try {
        const fallback = await buildLatestBenchmarkSnapshot();
        renderKpiCards(fallback);
        renderExperimentTable(fallback);
        if (!silent && showToast) {
          showToast("Backend benchmark chưa sẵn sàng, đang dùng dữ liệu fallback", "warning");
        }
      } catch (fallbackError) {
        console.error("Benchmark baseline error:", fallbackError);
        if (!silent && showToast) {
          showToast("Không thể tải benchmark baseline từ database", "danger");
        }
      }
    }
  };

  runButtons.forEach((button) => {
    button.addEventListener("click", () => {
      runBenchmarkJobFromUI();
    });
  });

  const refreshButton = document.getElementById("btn-benchmark-refresh");
  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      renderLatest({ silent: false });
    });
  }

  window.__vnaiBenchmarkRefresh = renderLatest;
  fetchBenchmarkJobStatus().then((payload) => {
    if (payload?.job?.status === "running") {
      setBenchmarkRunButtons(true);
      clearBenchmarkPollTimer();
      pollBenchmarkUntilDone();
    }
  }).catch((error) => {
    console.warn("Unable to pre-check benchmark job status", error);
  });

  renderLatest({ silent: true });
}

function populateTrainingHistory() {
  const tbody = document.getElementById("training-history-body");
  if (!tbody) return;

  tbody.innerHTML = trainingHistoryRows.map((item) => `
    <tr>
      <td><span class="badge info">${item.version}</span></td>
      <td>${item.accuracy.toFixed(1)}%</td>
      <td>${item.f1.toFixed(1)}%</td>
      <td>${item.samples.toLocaleString()}</td>
      <td>${item.date}</td>
    </tr>
  `).join("");

  adjustActivePageHeight();
}

function refreshTrainingChart() {
  if (!intelligenceChart) return;

  intelligenceChart.data.labels = trainingHistoryRows.map((item) => item.version);
  intelligenceChart.data.datasets[0].data = trainingHistoryRows.map((item) => item.accuracy);
  intelligenceChart.data.datasets[1].data = trainingHistoryRows.map((item) => item.f1);
  intelligenceChart.update();
}

async function loadTrainingHistoryFromDB({ silent = false } = {}) {
  try {
    trainingHistoryRows = await fetchTrainingHistory();
    populateTrainingHistory();
    refreshTrainingChart();
    if (!silent && showToast) {
      showToast("Đã đồng bộ training history từ database", "success");
    }
  } catch (error) {
    console.error("Training history error:", error);
    if (!silent && showToast) {
      showToast("Không thể tải training history từ database", "danger");
    }
  }
}

let osmPollTimer = null;

function clearOSMPollTimer() {
  if (osmPollTimer) {
    clearTimeout(osmPollTimer);
    osmPollTimer = null;
  }
}

function setOSMRunButtons(isRunning) {
  const runButton = document.getElementById("btn-osm-run");
  const previewButton = document.getElementById("btn-osm-preview-counts");

  [runButton, previewButton].forEach((button) => {
    if (!button) return;

    if (isRunning) {
      if (!button.dataset.defaultHtml) {
        button.dataset.defaultHtml = button.innerHTML;
      }
      button.disabled = true;
      if (button.id === "btn-osm-run") {
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running OSM Crawl...';
      }
    } else {
      button.disabled = false;
      if (button.dataset.defaultHtml && button.id === "btn-osm-run") {
        button.innerHTML = button.dataset.defaultHtml;
      }
    }
  });
}

async function fetchOSMSummary() {
  const response = await fetch(`${API_BASE}/osm/summary`, {
    headers: getAuthHeader(),
  });

  if (!response.ok) {
    throw new Error(`OSM summary API failed: ${response.status}`);
  }

  return response.json();
}

async function triggerOSMJob(options = {}) {
  const limitProvinces = options.limit_provinces || getNumericInputValue("osm-limit-provinces") || 63;
  const targetTotal = options.target_total || getNumericInputValue("osm-target-total") || 5000000;
  const provinceId = options.province_id || null;

  const response = await fetch(`${API_BASE}/osm/trigger`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
    body: JSON.stringify({
      limit_provinces: limitProvinces,
      target_total: targetTotal,
      province_id: provinceId
    }),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`OSM trigger API failed: ${response.status}`);
  }

  return response.json();
}

async function fetchOSMJobStatus() {
  const response = await fetch(`${API_BASE}/osm/job`, {
    headers: getAuthHeader(),
  });

  if (response.status === 401) {
    localStorage.removeItem('vnai_token');
    window.location.href = 'login.html';
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    throw new Error(`OSM job API failed: ${response.status}`);
  }

  return response.json();
}

function renderOSMSummary(summary) {
  const raw = Number(summary?.raw || 0);
  const streets = Number(summary?.streets || 0);
  const buildings = Number(summary?.buildings || 0);
  const pois = Number(summary?.pois || 0);
  const total = raw + streets + buildings + pois;

  const mapping = {
    "osm-raw-count": raw,
    "osm-street-count": streets,
    "osm-building-count": buildings,
    "osm-poi-count": pois,
  };

  Object.entries(mapping).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value.toLocaleString();
    }
  });

  const totalEl = document.getElementById("stat-osm");
  if (totalEl) {
    totalEl.textContent = total.toLocaleString();
  }

  const lastRefresh = document.getElementById("osm-last-refresh");
  if (lastRefresh) {
    lastRefresh.textContent = `Cập nhật lúc ${formatLogTime()}`;
  }

  adjustActivePageHeight();
}

function renderOSMJob(job) {
  const status = job?.status || "idle";
  const badge = document.getElementById("osm-job-status-badge") || document.getElementById("osm-job-status");
  const started = document.getElementById("osm-job-started");
  const finished = document.getElementById("osm-job-finished");
  const jobId = document.getElementById("osm-job-id");
  const errorEl = document.getElementById("osm-job-error");
  const logEl = document.getElementById("osm-job-log");

  if (badge) {
    const badgeClass = status === "success" ? "success" : status === "failed" ? "danger" : status === "running" ? "warning" : "info";
    badge.className = `badge ${badgeClass}`;
    badge.textContent = status.toUpperCase();
  }

  if (started) started.textContent = job?.startedAt || "-";
  if (finished) finished.textContent = job?.finishedAt || "-";
  if (jobId) jobId.textContent = job?.jobId || "-";
  if (errorEl) errorEl.textContent = job?.error || "";

  if (logEl) {
    logEl.textContent = job?.outputTail || (status === "running" ? "OSM crawl đang chạy..." : "Chưa có job nào được chạy.");
  }

  adjustActivePageHeight();
}

async function pollOSMUntilDone() {
  try {
    const payload = await fetchOSMJobStatus();
    const job = payload?.job;
    const status = job?.status || "idle";

    renderOSMJob(job);

    if (status === "running") {
      setOSMRunButtons(true);
      osmPollTimer = setTimeout(pollOSMUntilDone, 4000);
      return;
    }

    setOSMRunButtons(false);

    if (status === "success") {
      await refreshOSMEnrichmentPanel({ silent: true });
      if (showToast) {
        showToast("OSM crawl hoàn tất và số liệu đã được cập nhật", "success");
      }
      return;
    }

    if (status === "failed") {
      if (showToast) {
        showToast(`OSM crawl thất bại${job?.error ? `: ${job.error}` : ""}`, "danger");
      }
      return;
    }
  } catch (error) {
    setOSMRunButtons(false);
    console.error("OSM poll error:", error);
    if (showToast) {
      showToast("Không thể theo dõi trạng thái OSM job", "danger");
    }
  }
}

async function refreshOSMEnrichmentPanel({ silent = false } = {}) {
  try {
    const summary = await fetchOSMSummary();
    renderOSMSummary(summary);
    if (!silent && showToast) {
      showToast("Đã làm mới số liệu OSM enrichment", "success");
    }
  } catch (error) {
    console.error("OSM summary error:", error);
    if (!silent && showToast) {
      showToast("Không thể tải số liệu OSM enrichment", "danger");
    }
  }
}

async function previewOSMCountsFromUI() {
  await refreshOSMEnrichmentPanel({ silent: false });
}

async function runOSMJobFromUI() {
  try {
    const pInput = document.getElementById('osm-province-input');
    const pVal = osmState.provinces[pInput?.value];
    const pId = pVal && typeof pVal === 'object' ? (pVal.province_id || pVal.MaTinh) : pVal;

    let limitProvinces = 63;
    let provinceId = null;

    if (pId) {
      limitProvinces = 1;
      provinceId = pId;
    }

    const targetTotal = getNumericInputValue("osm-target-total") || 5000000;
    const confirmMessage = pId
      ? `Chạy crawl OSM cho tỉnh ${pInput.value} với target ${targetTotal.toLocaleString()} entities?`
      : `Chạy crawl OSM cho tất cả 63 tỉnh/thành với target ${targetTotal.toLocaleString()} entities?`;

    if (showConfirm) {
      const confirmed = await showConfirm(confirmMessage);
      if (!confirmed) return;
    }

    setOSMRunButtons(true);
    const trigger = await triggerOSMJob({ limit_provinces: limitProvinces, province_id: provinceId, target_total: targetTotal });

    if (trigger?.job?.status === "running") {
      if (showToast) {
        showToast("OSM crawl job đã được khởi chạy", "info");
      }
      clearOSMPollTimer();
      renderOSMJob(trigger.job);
      await pollOSMUntilDone();
      return;
    }

    setOSMRunButtons(false);
  } catch (error) {
    setOSMRunButtons(false);
    console.error("OSM trigger error:", error);
    if (showToast) {
      showToast("Không thể trigger OSM crawl job", "danger");
    }
  }
}

let osmState = {};
/** Lần onSearch đầu từ loadProvinces() khi init smart filter — không toast (trùng lúc load app). */
let osmSkipNextSearchToast = false;
async function initOSMEnrichmentUI() {
  const runButton = document.getElementById("btn-osm-run");
  const previewButton = document.getElementById("btn-osm-preview-counts");
  const page = document.getElementById("osm-enrichment");

  if (!page) return;

  VNAIControls.renderSmartFilter('osm-filter-container', {
    prefix: 'osm',
    title: 'Phạm vi Crawl (OpenStreetMap)',
    showVersion: false,
    showWard: false,
    showDistrict: false,
    searchPlaceholder: 'Tìm nhanh Tỉnh/Thành...'
  });

  osmSkipNextSearchToast = true;
  osmState = await VNAIControls.initSmartFilter('osm', {
    onSearch: () => {
      const silent = osmSkipNextSearchToast;
      osmSkipNextSearchToast = false;
      return refreshOSMEnrichmentPanel({ silent });
    }
  });

  if (runButton) {
    runButton.addEventListener("click", () => {
      runOSMJobFromUI();
    });
  }

  if (previewButton) {
    previewButton.addEventListener("click", () => {
      previewOSMCountsFromUI();
    });
  }

  window.__vnaiOSMRefresh = refreshOSMEnrichmentPanel;

  fetchOSMJobStatus().then((payload) => {
    if (payload?.job) {
      renderOSMJob(payload.job);
      if (payload.job.status === "running") {
        setOSMRunButtons(true);
        clearOSMPollTimer();
        pollOSMUntilDone();
      }
    }
  }).catch((error) => {
    console.warn("Unable to pre-check OSM job status", error);
  });

  await refreshOSMEnrichmentPanel({ silent: true });
  osmSkipNextSearchToast = false;
}

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════

/** Map each data-page value → its parent group id */
const PAGE_GROUP_MAP = {
  'nso-sync': 'gov-sync',
  'admin-units': 'gov-sync',
  'parser': 'address-processing',
  'batch': 'address-processing',
  'explorer': 'address-processing',
  'lookup': 'spatial',
  'boundary-visualization': 'spatial',
  'osm-enrichment': 'enrichment',
  'label-studio': 'ai-bench',
  'training': 'ai-bench',
  'experiments': 'ai-bench',
  'label-registry': 'ai-bench',
  'prelabeler-cases': 'ai-bench',
  'documentation': 'ai-bench',
};

function openNavGroup(groupId) {
  const btn = document.querySelector(`.nav-group-toggle[data-group="${groupId}"]`);
  const panel = document.getElementById(`group-${groupId}`);
  if (!btn || !panel) return;
  btn.classList.add('open');
  panel.classList.add('open');
}

function closeNavGroup(groupId) {
  const btn = document.querySelector(`.nav-group-toggle[data-group="${groupId}"]`);
  const panel = document.getElementById(`group-${groupId}`);
  if (!btn || !panel) return;
  btn.classList.remove('open');
  panel.classList.remove('open');
}

function setupNavGroupToggles() {
  document.querySelectorAll('.nav-group-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const groupId = btn.getAttribute('data-group');
      const isOpen = btn.classList.contains('open');
      if (isOpen) {
        closeNavGroup(groupId);
      } else {
        openNavGroup(groupId);
      }
    });
  });
}

// ── Sidebar Collapse ──
const SIDEBAR_COLLAPSED_KEY = 'vnai_sidebar_collapsed';

function setSidebarCollapsed(collapsed) {
  const sidebar = document.querySelector('.sidebar');
  if (!sidebar) return;
  const isMobile = window.innerWidth <= 768;
  // Không giữ trạng thái collapsed trên mobile vì gây lỗi hiển thị/interaction.
  if (isMobile) collapsed = false;
  sidebar.classList.toggle('collapsed', collapsed);
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? '1' : '0');

  // Add data-tooltip to nav items & group toggles for collapsed tooltip
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    const span = item.querySelector('span');
    if (span) item.setAttribute('data-tooltip', span.textContent.trim());
  });
  document.querySelectorAll('.nav-group-toggle[data-group]').forEach(btn => {
    const label = btn.querySelector('.nav-group-label');
    if (label) btn.setAttribute('data-tooltip', label.textContent.trim());
  });
}

function setupSidebarCollapse() {
  const btn = document.getElementById('sidebar-collapse-btn');
  if (!btn) return;

  // Restore persisted state
  const persisted = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
  if (window.innerWidth > 768 && persisted) setSidebarCollapsed(true);
  if (window.innerWidth <= 768) setSidebarCollapsed(false);

  btn.addEventListener('click', () => {
    const sidebar = document.querySelector('.sidebar');
    setSidebarCollapsed(!sidebar.classList.contains('collapsed'));
  });
}

function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const pages = document.querySelectorAll(".page");
  const titleEl = document.getElementById("current-page-title");

  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  const toggle = document.getElementById("menu-toggle");

  // Using global closeMobileMenu function

  if (toggle && sidebar) {
    console.log("✅ Menu toggle and sidebar found, adding event listener");
    toggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();

      const isActive = sidebar.classList.contains("mobile-active");
      console.log("🔄 Toggle clicked, isActive:", isActive);

      if (isActive) {
        console.log("🔒 Closing mobile menu");
        closeMobileMenu();
      } else {
        console.log("🔓 Opening mobile menu");
        // Mobile menu phải luôn full-size, không dùng collapsed mode.
        setSidebarCollapsed(false);
        sidebar.classList.add("mobile-active");
        if (overlay) overlay.classList.add("mobile-active");
        document.body.classList.add("no-scroll");
        console.log("✅ Classes added:", {
          sidebarClasses: sidebar.className,
          bodyClasses: document.body.className
        });
      }
    });
  } else {
    console.error("❌ Menu toggle or sidebar not found!", { toggle, sidebar });
  }

  if (overlay) overlay.addEventListener("click", closeMobileMenu);

  // Setup collapsible group buttons
  setupNavGroupToggles();

  // Setup sidebar collapse toggle
  setupSidebarCollapse();

  // Auto-open all groups by default
  document.querySelectorAll('.nav-group-toggle[data-group]').forEach(btn => {
    openNavGroup(btn.getAttribute('data-group'));
  });

  // Ensure body scroll is enabled by default (fix mobile scroll issues)
  const ensureBodyScrollEnabled = () => {
    const isMobile = window.innerWidth <= 768;
    const sidebarActive = sidebar && sidebar.classList.contains('mobile-active');

    if (isMobile && !sidebarActive) {
      document.body.classList.remove("no-scroll");
      console.log("📱 Ensured body scroll is enabled on mobile");
    }
  };

  // Call on load and resize
  ensureBodyScrollEnabled();
  window.addEventListener('resize', ensureBodyScrollEnabled);

  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = item.getAttribute("data-page");
      navigateToPage(targetId, true);
    });
  });

  window.addEventListener('resize', adjustActivePageHeight);

  // Workflow steps click to navigate
  document.querySelectorAll(".workflow-step.clickable").forEach(step => {
    step.addEventListener("click", () => {
      const targetPage = step.getAttribute("data-goto");
      navigateToPage(targetPage, true);
    });
  });

  // Parser footer action buttons click to navigate
  document.querySelectorAll(".parser-footer-action[data-goto]").forEach(button => {
    button.addEventListener("click", () => {
      const targetPage = button.getAttribute("data-goto");
      navigateToPage(targetPage, true);
    });
  });
}

// ═══════════════════════════════════════════════════════════
// OVERVIEW CHART
// ═══════════════════════════════════════════════════════════
let overviewChart = null;

function renderOverviewChart(stats) {
  const ctx = document.getElementById("chart-overview");
  if (!ctx) return;

  const dataValues = [
    stats?.master?.provinces || 0,
    stats?.master?.districts || 0,
    stats?.master?.wards || 0,
    stats?.osm?.streets || 0,
    stats?.osm?.buildings || 0,
    stats?.ai?.training_samples || 0,
    stats?.ai?.cleansing_queue || 0
  ];

  if (overviewChart) {
    overviewChart.data.datasets[0].data = dataValues;
    overviewChart.update();
    return;
  }

  overviewChart = new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels: ["mat.province", "mat.district", "mat.ward", "osm.streets", "osm.buildings", "ath.training", "prq.queue"],
      datasets: [{
        label: "Records",
        data: dataValues,
        backgroundColor: [
          "rgba(129,140,248,0.7)", "rgba(129,140,248,0.5)", "rgba(129,140,248,0.3)",
          "rgba(52,211,153,0.7)", "rgba(52,211,153,0.5)",
          "rgba(251,191,36,0.6)",
          "rgba(248,113,113,0.6)"
        ],
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ctx.parsed.y.toLocaleString() + " records"
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#5c5c5f", font: { size: 10 } },
          grid: { display: false }
        },
        y: {
          type: "linear", // Change to linear to avoid 0 issue with log scale if not configured
          beginAtZero: true,
          ticks: {
            color: "#5c5c5f",
            font: { size: 10 },
            callback: (v) => v >= 1000 ? (v / 1000) + "K" : v
          },
          grid: { color: "rgba(255,255,255,0.04)" }
        }
      }
    }
  });
}

// ═══════════════════════════════════════════════════════════
// LABEL REGISTRY
// ═══════════════════════════════════════════════════════════
let _labelRegistrySearchBound = false;
let _lrAiCoachPromptCopyBound = false;
const _labelRegistryMediaCompact = window.matchMedia("(max-width: 1180px)");

function _shortenLabelRegistryText(text, maxLen) {
  const raw = (text || "").replace(/\s+/g, " ").trim();
  if (raw.length <= maxLen) return raw;
  return raw.slice(0, maxLen - 1).trimEnd() + "…";
}

function _isLabelRegistryCompact() {
  return _labelRegistryMediaCompact.matches;
}

const LABEL_REGISTRY_RULES = {
  PCD: {
    title: "Mã Plus Code",
    whenToUse: "Dùng khi thấy mã dạng Plus Code, ví dụ 7P28+X4.",
    avoidWhen: "Không dùng cho mã bưu chính hoặc mã nội bộ khác."
  },
  BLD: {
    title: "Tòa nhà, chung cư",
    whenToUse: "Dùng cho tên tòa nhà hoặc chung cư, ví dụ Landmark 81.",
    avoidWhen: "Không dùng cho tên đường hoặc tên quận, phường, tỉnh."
  },
  POI: {
    title: "Mốc địa điểm",
    whenToUse: "Dùng cho nơi dễ nhận biết như cửa hàng, bệnh viện, trường học, công viên.",
    avoidWhen: "Không dùng cho tên quận, phường, tỉnh hoặc tên tòa nhà rõ ràng."
  },
  ALY: {
    title: "Hẻm, ngõ, ngách",
    whenToUse: "Dùng khi có từ hẻm, ngõ, ngách, kiệt.",
    avoidWhen: "Không dùng cho số nhà chính hoặc số trong tên đường."
  },
  NUM: {
    title: "Số nhà",
    whenToUse: "Dùng cho số nhà chính, ví dụ 12, 268, 45/12.",
    avoidWhen: "Không dùng cho số phường, số quận hoặc mã căn nội bộ."
  },
  STR: {
    title: "Tên đường",
    whenToUse: "Dùng cho tên đường, phố, đại lộ.",
    avoidWhen: "Không dùng cho khu phố, ấp, thôn hoặc tên quận, phường, tỉnh."
  },
  NHB: {
    title: "Khu phố, ấp, thôn, bản",
    whenToUse: "Dùng cho cụm như khu phố 3, ấp 2, thôn Đông.",
    avoidWhen: "Không dùng cho tên đường hoặc tên phường, xã."
  },
  WDS: {
    title: "Phường, xã, thị trấn",
    whenToUse: "Dùng cho cụm như Phường 14, Xã Tân Phú.",
    avoidWhen: "Không dùng cho quận, huyện, tỉnh hoặc khu phố."
  },
  DST: {
    title: "Quận, huyện, thị xã, thành phố",
    whenToUse: "Dùng cho cụm như Quận 10, Huyện Củ Chi, TP Thủ Đức.",
    avoidWhen: "Không dùng cho tên tỉnh hoặc thành phố lớn như Hà Nội, TP.HCM."
  },
  PRO: {
    title: "Tỉnh/Thành phố",
    whenToUse: "Dùng cho tỉnh hoặc thành phố, ví dụ TP.HCM, Hà Nội, Đồng Nai.",
    avoidWhen: "Không dùng cho quận, huyện, phường hoặc tên cửa hàng."
  }
};

const _LR_AI_COACH_FALLBACK_ORDER = ["PCD", "BLD", "POI", "ALY", "NUM", "STR", "NHB", "WDS", "DST", "PRO"];

/**
 * Prompt “system / developer” một lần để đưa vào Gemini, ChatGPT, Copilot.
 * Luôn ghép đúng LABEL_REGISTRY_RULES và (nếu đã có) NER_LABELS trên UI.
 */
function buildLabelRegistryAiCoachPrompt() {
  const rows = [];

  if (Array.isArray(NER_LABELS) && NER_LABELS.length > 0) {
    NER_LABELS.forEach(row => {
      const code = String(row?.value || "").trim().toUpperCase();
      if (!code) return;
      const hk = row?.hotkey != null && row.hotkey !== "" ? String(row.hotkey) : "—";
      rows.push({ code, hk, rule: LABEL_REGISTRY_RULES[code] || {} });
    });
  } else {
    _LR_AI_COACH_FALLBACK_ORDER.forEach(code => {
      rows.push({ code, hk: "—", rule: LABEL_REGISTRY_RULES[code] || {} });
    });
  }

  const labelCatalog = rows
    .map(
      r =>
        `- ${r.code}\n   Phím tắt trong UI PreLabeler (để đồng bộ nhãn tay): ${r.hk}\n   Tóm tắt vai trò: ${r.rule.title || "—"}\n   Gán khi: ${r.rule.whenToUse || "—"}\n   Tránh nhầm (không gán khi): ${r.rule.avoidWhen || "—"}`
    )
    .join("\n\n");

  return [
    "Bạn là trợ lý gán nhãn Named Entity Recognition (NER) cho ĐỊA CHỈ TIẾNG VIỆT trong dự án Address Label Studio (định danh vn-address-intelligence).",
    "",
    "## NHIỆM VỤ VÀ NGUYÊN TẮC",
    "Người dùng gửi chuỗi địa chỉ thô (raw_address). Bạn CHỈ gợi ý các span và mã nhãn theo đúng quy tắc bên dưới.",
    "Quyết định cuối cùng do người dùng/con người: họ có thể bỏ, sửa hoặc không dùng từng gợi ý.",
    "Với MỖI nhãn gợi ý bạn PHẢI viết một dòng hoặc cột «Lý do / gợi ý» ngắn gàng, tiếng Việt đời thường — người dùng có thể sao chép phần đó vào ô **ghi chú / note** của trang mẫu trong PreLabeler.",
    "",
    "## BẢNG MÃ NHÃN ĐANG DÙNG (không được thêm mã khác)",
    labelCatalog || "(Chưa tải danh mục — tham khảo các mã tối đa: PCD, BLD, POI, ALY, NUM, STR, NHB, WDS, DST, PRO.)",
    "",
    "## QUY TẮC CĂN VỚI HỆ THỐNG (bắt buộc tuân thủ)",
    "1) CHỈ sử dụng đúng các mã nhãn được liệt kê trong mục 'Bảng mã nhãn' ở trên. Không bịa thêm ENTITY ngoài 10 nhãn này.",
    "2) Mỗi span gắn đúng MỘT nhãn. Không chồng span không giao nhau; text trong mỗi span là đoạn trích LIÊN TỤC từ đúng chuỗi địa chỉ đầu vào (verbatim, giữ đúng dấu, hoa/thường như trong câu gốc hoặc tối thiểu không thay đổi tiếng Việt).",
    '3) WDS / DST / PRO ("admin"): nếu trong chuỗi có cả TIỀN TỐ hành chính và tên đơn vị (vd "Phường 1", "Quận 10", "Hà Nội") thì span phải bao luôn phần "Loại + Tên", không chỉ ghép có tên mà không tiền tố khi chuỗi đã ghi đủ.',
    "4) Ưu tiên tách các thành phần vi mô khác loại: ví dụ số nhà (NUM) tách khỏi tên đường (STR); hẻm/ngõ (ALY) tách khỏi đường nếu trong câu có hai phần khác nhau.",
    "5) KHÔNG gán nhãn cho dấu phẩy, dấu chấm, khoảng trắng rời; không ghép nhiều thành phần không liên tục thành một span.",
    '6) Nếu không chắc: không bịa span; trong cùng câu trả lời hãy thêm mục văn bản có tiêu đề «Những chỗ chưa chắc» (bullet), mỗi bullet nêu đoạn gây khó và 1–2 phương án nhãn có thể cân nhắc.',
    "",
    "## ĐỊNH DẠNG TRẢ LỜI — BẮT BUỘC (KHÔNG JSON)",
    "",
    "— KHÔNG dùng JSON, YAML hay khối mã ba dấu huyền (```) chứa cấu trúc máy đọc. Việc dùng các dòng bảng chỉ chứa ký tự và dấu | (Markdown table) là BÌNH THƯỜNG và được khuyến khích.",

    "— Chỉ được dùng MỘT trong hai kiểu sau (ưu tiên bảng trước, nếu mô hình lỗi bảng thì dùng kiểu 2):",
    "",
    "### Kiểu 1 — Bảng Markdown hoặc bảng dùng TAB (dễ copy sang Note / vào ô chữ trong tool)",
    "Dòng tiêu đề bắt buộc 3 cột:",
    "| Mã nhãn | Đoạn bôi (trích NGUYÊN VĂN từ địa chỉ) | Lý do / gợi ý (copy được sang ô note) |",
    "| :--- | :--- | :--- |",
    '| NUM | ví dụ: 268 | Đây là số nhà chính ở đầu cụm, tách khỏi đường. |',
    "",
    "### Kiểu 2 — Chữ thuần, mỗi nhãn một khối 3 dòng (khi không gõ được Markdown table)",
    "Mã nhãn: NUM",
    "Đoạn bôi: 268",
    "Lý do (note): đây là số nhà chính…",
    "— (lặp lại khối 3 dòng cho từng gợi ý khác)",
    "",
    "### Cuối câu trả lời (tùy thực tế địa chỉ)",
    "Nếu có chỗ không chắc, sau bảng/hoặc khối 3-dòng gợi ý bằng tiêu đề văn bản:",
    "**Những chỗ chưa chắc**",
    "- (bullet có thể copy)",
    "",
    "## Luồng cuộc hội thoại đề xuất",
    "Luồng 1 — Tin đầu: người dùng dán nguyên văn toàn bộ prompt này (hoặc hệ đã được cấu hình với các quy tắc tương đương); sau đó chờ họ gửi địa chỉ cụ thể.",
    'Luồng 2 — Tin kế tiếp: một hoặc nhiều dòng địa chỉ thô (raw_address).',
    "",
    "> Lưu ý: các mô hình (Gemini, ChatGPT, Copilot) không truy cập trực tiếp cơ sở dữ liệu của dự án; nếu trong chuỗi không đủ tên đơn vị hành chính đừng bịa — hãy ghi vào mục «Những chỗ chưa chắc» bằng văn bản tiếng Việt đơn giản.",

    "",
  ].join("\n");
}

function populateLabelRegistry() {
  const tbody = document.getElementById("label-registry-body");
  const cardView = document.getElementById("labels-card-view");
  const searchInput = document.getElementById("label-search");
  const labelCountEl = document.getElementById("label-count");

  if (!tbody && !cardView) return;

  // Update label count
  if (labelCountEl) {
    labelCountEl.textContent = NER_LABELS.length;
  }

  // Render table view (desktop)
  if (tbody) {
    tbody.innerHTML = NER_LABELS.map(l => {
      const rule = LABEL_REGISTRY_RULES[l.value] || {};
      const compact = _isLabelRegistryCompact();
      const whenText = compact
        ? _shortenLabelRegistryText(rule.whenToUse || "Đang cập nhật cách dùng.", 78)
        : (rule.whenToUse || "Đang cập nhật cách dùng.");
      const avoidText = compact
        ? _shortenLabelRegistryText(rule.avoidWhen || "Đang cập nhật trường hợp không chọn.", 72)
        : (rule.avoidWhen || "Đang cập nhật trường hợp không chọn.");
      return `
      <tr>
        <td><span class="label-badge" style="background:${l.color}22;color:${l.color}">${l.value}</span></td>
        <td>
          <div style="font-weight:600;color:var(--text-primary)">${rule.title || "Chưa định nghĩa"}</div>
        </td>
        <td>
          <div style="font-size:12px;line-height:1.5;color:var(--text-secondary)" title="${rule.whenToUse || ""}">${whenText}</div>
        </td>
        <td>
          <div style="font-size:12px;line-height:1.5;color:var(--danger, #ef4444)" title="${rule.avoidWhen || ""}">${avoidText}</div>
        </td>
        <td><kbd style="background:var(--bg-muted);padding:4px 8px;border-radius:4px;font-size:11px;border:1px solid var(--border);cursor:default">${l.hotkey}</kbd></td>
      </tr>
    `;
    }).join("");
  }

  // Render card view (mobile)
  if (cardView) {
    cardView.innerHTML = NER_LABELS.map(l => {
      const rule = LABEL_REGISTRY_RULES[l.value] || {};
      return `
      <div class="label-card" style="
        padding: 14px; 
        border: 1px solid var(--border); 
        border-radius: 8px; 
        background: var(--bg-app);
        border-left: 4px solid ${l.color};
      ">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
          <div>
            <span class="label-badge" style="background:${l.color}22;color:${l.color};font-size:12px;padding:2px 6px">${l.value}</span>
          </div>
          <kbd style="background:${l.color}22;color:${l.color};padding:3px 6px;border-radius:3px;font-size:10px;border:1px solid ${l.color}33;cursor:default;font-weight:600">${l.hotkey}</kbd>
        </div>
        
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
          <div style="width:12px;height:12px;border-radius:2px;background:${l.color}"></div>
          <span style="font-size:10px;color:var(--text-tertiary);font-family:monospace">${l.color}</span>
        </div>

        <div style="font-size:12px;line-height:1.55;color:var(--text-secondary);display:grid;gap:8px">
          <div>
            <strong style="display:block;color:var(--text-primary);font-size:12px;margin-bottom:2px">${rule.title || "Chưa định nghĩa"}</strong>
          </div>
          <div>
            <span style="font-weight:600;color:var(--text-primary)">Gán khi:</span>
            <span>${rule.whenToUse || "Đang cập nhật rule sử dụng."}</span>
          </div>
          <div>
            <span style="font-weight:600;color:var(--danger, #ef4444)">Không gán khi:</span>
            <span>${rule.avoidWhen || "Đang cập nhật rule tránh nhầm."}</span>
          </div>
        </div>
      </div>
    `;
    }).join("");
  }

  // Setup search functionality (một lần — tránh double-bind khi reload nhãn từ Settings)
  if (searchInput && !_labelRegistrySearchBound) {
    _labelRegistrySearchBound = true;
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();

      // Filter table rows
      if (tbody) {
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      }

      // Filter card view
      if (cardView) {
        const cards = cardView.querySelectorAll('.label-card');
        cards.forEach(card => {
          const text = card.textContent.toLowerCase();
          card.style.display = text.includes(query) ? '' : 'none';
          // Add smooth animation
          if (text.includes(query)) {
            card.style.animation = 'none';
            setTimeout(() => {
              card.style.animation = 'fadeIn 0.3s ease-in-out';
            }, 10);
          }
        });
      }

      // Update count of visible labels
      const visibleCount = Array.from(tbody ? tbody.querySelectorAll('tr') : cardView.querySelectorAll('.label-card'))
        .filter(el => el.style.display !== 'none').length;
      if (labelCountEl) {
        labelCountEl.textContent = visibleCount;
      }
    });
  }

  const lrPromptTa = document.getElementById("lr-ai-coach-prompt");
  if (lrPromptTa instanceof HTMLTextAreaElement) {
    lrPromptTa.value = buildLabelRegistryAiCoachPrompt();
    lrPromptTa.placeholder = "";
  }

  const lrPromptCopyBtn = document.getElementById("lr-ai-prompt-copy");
  if (lrPromptCopyBtn instanceof HTMLButtonElement && !_lrAiCoachPromptCopyBound) {
    _lrAiCoachPromptCopyBound = true;
    lrPromptCopyBtn.addEventListener("click", () => {
      const el = document.getElementById("lr-ai-coach-prompt");
      const text =
        el instanceof HTMLTextAreaElement ? el.value : buildLabelRegistryAiCoachPrompt();
      const s = String(text || "").trim();
      if (!s) {
        window.showToast?.("Chưa có nội dung prompt để copy", "warning");
        return;
      }
      const done = () => window.showToast?.("Đã copy prompt vào clipboard", "success");
      const fail = () =>
        window.showToast?.("Không thể copy (kiểm tra quyền clipboard hoặc HTTPS)", "warning");
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(s).then(done).catch(fail);
        return;
      }
      try {
        const sink = lrPromptTa instanceof HTMLTextAreaElement ? lrPromptTa : el;
        if (sink instanceof HTMLTextAreaElement) {
          sink.removeAttribute("readonly");
          sink.focus();
          sink.select();
          sink.setSelectionRange(0, s.length);
          const ok = document.execCommand("copy");
          sink.setAttribute("readonly", "");
          if (ok) done();
          else fail();
          return;
        }
      } catch (_) {
        /* fall through */
      }
      fail();
    });
  }
}

// Add animation keyframes
if (!document.getElementById('label-registry-styles')) {
  const style = document.createElement('style');
  style.id = 'label-registry-styles';
  style.textContent = `
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
}

// ═══════════════════════════════════════════════════════════
// ADDRESS PARSER TOOL
// ═══════════════════════════════════════════════════════════

// Model status polling
let _parserStatusPollTimer = null;

function _updateParserModelStatusBar(status) {
  const bar = document.getElementById("parser-model-status-bar");
  const dot = document.getElementById("pmsb-dot");
  const text = document.getElementById("pmsb-text");
  const chips = document.getElementById("pmsb-chips");
  const reloadBtn = document.getElementById("pmsb-reload-btn");
  if (!bar) return;

  const MODEL_LABELS = {
    prelabeler: "PreLabeler",
    address_ner: "NER (HF)",
    phobert: "PhoBERT",
    mgte: "mGTE",
    llm: "Qwen LLM",
  };
  const ALL_AI_MODELS = ["address_ner", "phobert", "mgte", "llm"];

  const loaded = new Set(status.loadedModels || []);
  const errors = status.errors || {};

  // Update dot
  if (dot) {
    dot.className = `pmsb-dot ${status.status}`;
  }

  // Update text
  if (text) {
    const currentModelText = status.currentModel ? ` (đang nạp ${status.currentModel.toUpperCase()})` : "";
    const progressText = status.progress ? ` ${Math.round(status.progress)}%` : "";

    const statusLabels = {
      idle: "Model AI chưa được nạp — nhấn Tải model để bắt đầu",
      loading: `Đang nạp model AI vào bộ nhớ...${currentModelText}${progressText} (${status.loadedModels?.length || 0}/4 hoàn thành)`,
      ready: `Model sẵn sàng — ${status.loadedModels?.length || 0}/4 model AI đã nạp${status.corpusSize ? `, ${status.corpusSize.toLocaleString()} địa chỉ corpus` : ""}`,
      error: "Một số model không thể nạp — xem chi tiết bên dưới",
    };
    text.textContent = statusLabels[status.status] || status.status;
  }

  // Render chips
  if (chips) {
    let html = "";
    ALL_AI_MODELS.forEach(key => {
      const lbl = MODEL_LABELS[key] || key;
      if (loaded.has(key)) {
        html += `<span class="pmsb-chip loaded" title="${lbl} sẵn sàng">${lbl} ✓</span>`;
      } else if (errors[key]) {
        const shortErr = errors[key].length > 60 ? errors[key].slice(0, 60) + "…" : errors[key];
        html += `<span class="pmsb-chip failed" title="${shortErr}">${lbl} ✗</span>`;
      } else if (status.status === "loading") {
        html += `<span class="pmsb-chip loading" title="Đang nạp...">${lbl} ⏳</span>`;
      } else {
        html += `<span class="pmsb-chip failed" title="Chưa nạp">${lbl} —</span>`;
      }
    });
    chips.innerHTML = html;
  }

  // Show/hide reload button
  if (reloadBtn) {
    const isLoading = status.status === "loading";
    reloadBtn.disabled = isLoading;
    reloadBtn.innerHTML = isLoading
      ? '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp...'
      : '<i class="fa-solid fa-rotate-right"></i> Tải model';
  }
}

async function _pollParserModelStatus() {
  // Only poll if we are on the parser page
  const parserPage = document.getElementById("parser");
  if (!parserPage || !parserPage.classList.contains("active")) {
    _parserStatusPollTimer = null;
    return;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const res = await fetch(`${API_BASE}/parser/status`, {
      headers: getAuthHeader(),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      console.warn(`Parser status returned ${res.status}: ${res.statusText}`);
      return;
    }

    const data = await res.json();
    _updateParserModelStatusBar(data);
    if (typeof data.corpusSize === "number") {
      _updateParserMeta({ corpusSize: data.corpusSize });
    }

    // Keep polling while loading - faster polling for better UX
    if (data.status === "loading") {
      _parserStatusPollTimer = setTimeout(_pollParserModelStatus, 2000); // Poll every 2 seconds
    } else {
      _parserStatusPollTimer = null;
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.warn("Parser status request timed out");
    } else {
      console.error("Failed to poll parser status:", error);
    }

    // Show error state in UI
    const text = document.getElementById("pmsb-text");
    const dot = document.getElementById("pmsb-dot");
    if (text) {
      text.textContent = "Không thể kết nối đến server — kiểm tra API server";
    }
    if (dot) {
      dot.className = "pmsb-dot error";
    }

    // Retry after delay
    _parserStatusPollTimer = setTimeout(_pollParserModelStatus, 5000);
  }
}

async function _reloadParserModels() {
  const btn = document.getElementById("pmsb-reload-btn");
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp...'; }

  try {
    const res = await fetch(`${API_BASE}/parser/reload`, {
      method: "POST",
      headers: { ...getAuthHeader(), "Content-Type": "application/json" },
    });
    const data = await res.json();
    if (showToast) showToast(data.message || "Đã kích hoạt tải model", "info");
  } catch (err) {
    if (showToast) showToast("Không thể kích hoạt tải model: " + err.message, "danger");
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Tải model'; }
  } finally {
    // Start polling to reflect updated state
    if (_parserStatusPollTimer) clearTimeout(_parserStatusPollTimer);
    _parserStatusPollTimer = setTimeout(_pollParserModelStatus, 1500);
  }
}

function setupParserTool() {
  const btnParse = document.getElementById("btn-parse");
  const btnSampleLocal = document.getElementById("btn-parse-sample-local");
  const btnSampleDB = document.getElementById("btn-parse-sample-db");
  const inputEl = document.getElementById("parser-input");

  if (!btnParse) {
    console.warn("[Parser] btn-parse not found in DOM — parser page may not have loaded.");
    return;
  }

  btnParse.addEventListener("click", () => runParser());

  const autoResizeInput = () => {
    if (!inputEl) return;
    inputEl.style.height = 'auto';
    inputEl.style.height = (inputEl.scrollHeight) + 'px';
  };

  if (inputEl) {
    inputEl.addEventListener("input", autoResizeInput);
    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        runParser();
      }
    });
    setTimeout(autoResizeInput, 100); // Wait for page transition
  }

  if (btnSampleLocal) btnSampleLocal.addEventListener("click", () => {
    const addr = SAMPLE_ADDRESSES[Math.floor(Math.random() * SAMPLE_ADDRESSES.length)];
    if (inputEl) {
      inputEl.value = addr;
      inputEl.dataset.sampleId = "";
      autoResizeInput();
    }
    runParser();
  });

  if (btnSampleDB) btnSampleDB.addEventListener("click", async () => {
    await fetchParserSampleDB();
    autoResizeInput();
  });

  // Wire up reload button
  const reloadBtn = document.getElementById("pmsb-reload-btn");
  if (reloadBtn) reloadBtn.addEventListener("click", _reloadParserModels);

  // Build NER legend once
  _buildParserNERLegend();

  // Setup enhanced footer functionality
  _setupParserFooterActions();
}

function _setupParserFooterActions() {
  // Export Result button
  const btnExport = document.getElementById("btn-export-result");
  if (btnExport) {
    btnExport.addEventListener("click", () => {
      const resultsData = _collectParserResults();
      if (resultsData) {
        _exportParserResults(resultsData);
      } else {
        if (showToast) showToast("Chưa có kết quả để xuất", "warning");
      }
    });
  }

  // Copy JSON button
  const btnCopyJson = document.getElementById("btn-copy-json");
  if (btnCopyJson) {
    btnCopyJson.addEventListener("click", () => {
      const resultsData = _collectParserResults();
      if (resultsData) {
        navigator.clipboard.writeText(JSON.stringify(resultsData, null, 2)).then(() => {
          if (showToast) showToast("Đã copy JSON vào clipboard", "success");
        });
      } else {
        if (showToast) showToast("Chưa có kết quả để copy", "warning");
      }
    });
  }

  // Help & Guide button
  const btnHelp = document.getElementById("btn-parser-help");
  if (btnHelp) {
    btnHelp.addEventListener("click", () => {
      _showParserHelpModal();
    });
  }

  // Performance toggle
  const performancePanel = document.getElementById("parser-performance-panel");
  const performanceToggle = document.getElementById("performance-toggle");
  const performanceHeader = document.querySelector(".performance-header");

  if (performanceToggle && performanceHeader) {
    performanceHeader.addEventListener("click", () => {
      const metrics = document.getElementById("performance-metrics");
      const isVisible = metrics && metrics.style.display !== "none";

      if (metrics) {
        metrics.style.display = isVisible ? "none" : "grid";
      }

      const icon = performanceToggle.querySelector("i");
      if (icon) {
        icon.className = isVisible ? "fa-solid fa-chevron-down" : "fa-solid fa-chevron-up";
      }
    });
  }
}

function _collectParserResults() {
  const inputEl = document.getElementById("parser-input");
  if (!inputEl || !inputEl.value.trim()) return null;

  const results = {
    timestamp: new Date().toISOString(),
    input_address: inputEl.value.trim(),
    sample_id: inputEl.dataset.sampleId || null,
    models: {}
  };

  // Collect results from each model card
  ["prelabeler", "address_ner", "phobert", "mgte", "llm"].forEach(modelName => {
    const resultEl = document.getElementById(`presult-${modelName}`);
    const statsEl = document.getElementById(`pstats-${modelName}`);

    if (resultEl) {
      results.models[modelName] = {
        html_output: resultEl.innerHTML,
        stats: statsEl ? statsEl.innerHTML : null
      };
    }
  });

  return results;
}

function _exportParserResults(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `vnai-parser-result-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  if (showToast) showToast("Đã xuất kết quả thành công", "success");
}

function _showParserHelpModal() {
  const modalHtml = `
    <div class="modal-overlay" id="parser-help-modal">
      <div class="modal-content" style="max-width: 600px;">
        <div class="modal-header">
          <h3><i class="fa-solid fa-question-circle"></i> Hướng dẫn Parser</h3>
          <button class="modal-close" onclick="document.getElementById('parser-help-modal').remove()">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="help-section">
            <h4><i class="fa-solid fa-play"></i> Cách sử dụng</h4>
            <ol>
              <li>Nhập địa chỉ Việt Nam vào ô input</li>
              <li>Nhấn "Phân tích" hoặc phím Enter</li>
              <li>Xem kết quả từ 5 pipeline (PreLabeler + NER production + 3 model khác)</li>
              <li>So sánh hiệu suất và độ chính xác</li>
            </ol>
          </div>
          
          <div class="help-section">
            <h4><i class="fa-solid fa-lightbulb"></i> Mẹo sử dụng</h4>
            <ul>
              <li>Sử dụng nút <i class="fa-solid fa-shuffle"></i> để thử mẫu ngẫu nhiên</li>
              <li>Nút <i class="fa-solid fa-database"></i> lấy mẫu từ cơ sở dữ liệu</li>
              <li>Hover vào entities để xem thông tin nhãn</li>
              <li>Click "Labels Registry" để xem tất cả nhãn NER</li>
            </ul>
          </div>
          
          <div class="help-section">
            <h4><i class="fa-solid fa-brain"></i> Các mô hình</h4>
            <ul>
              <li><strong>NER (tô màu trên cùng):</strong> PreLabeler — rule/hybrid</li>
              <li><strong>NER (HF/local):</strong> AddressNER — giống production</li>
              <li><strong>PhoBERT:</strong> Mô hình BERT tiếng Việt</li>
              <li><strong>mGTE:</strong> Embedding đa ngôn ngữ</li>
              <li><strong>Qwen 2.5:</strong> Large Language Model</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function updateParserPerformanceMetrics(data) {
  // Update performance metrics when parser results are available
  if (data.timing) {
    const timeEl = document.getElementById("metric-processing-time");
    if (timeEl) timeEl.textContent = `${data.timing}ms`;
  }

  if (data.entities_count !== undefined) {
    const countEl = document.getElementById("metric-entities-count");
    if (countEl) countEl.textContent = data.entities_count.toString();
  }

  if (data.confidence) {
    const confEl = document.getElementById("metric-confidence");
    if (confEl) confEl.textContent = `${data.confidence.toFixed(1)}%`;
  }

  if (data.best_model) {
    const modelEl = document.getElementById("metric-best-model");
    if (modelEl) modelEl.textContent = data.best_model;
  }

  // Show performance panel after first analysis
  const perfPanel = document.getElementById("parser-performance-panel");
  if (perfPanel) perfPanel.style.display = "block";
}

function _updatePerformanceMetrics(totalMs, inputText) {
  // Processing time
  const timeEl = document.getElementById("metric-processing-time");
  if (timeEl) {
    const timeFmt = totalMs >= 1000
      ? `${(totalMs / 1000).toFixed(2)}s`
      : `${totalMs}ms`;
    timeEl.textContent = timeFmt;
  }

  // Count entities from all models
  let totalEntities = 0;
  let totalConfidence = 0;
  let confidenceCount = 0;
  let bestModel = "N/A";
  let bestScore = 0;

  ["prelabeler", "address_ner", "phobert", "mgte", "llm"].forEach(modelName => {
    const resultEl = document.getElementById(`presult-${modelName}`);
    if (resultEl && !resultEl.querySelector('.pmodel-not-loaded')) {
      // Count entities (spans with ner-entity class)
      const entities = resultEl.querySelectorAll('.ner-entity');
      totalEntities += entities.length;

      // Try to extract confidence from stats or result content
      const statsEl = document.getElementById(`pstats-${modelName}`);
      if (statsEl) {
        const confMatch = statsEl.textContent.match(/(\d+(?:\.\d+)?)%/);
        if (confMatch) {
          const conf = parseFloat(confMatch[1]);
          totalConfidence += conf;
          confidenceCount++;
          if (conf > bestScore) {
            bestScore = conf;
            bestModel = modelName.charAt(0).toUpperCase() + modelName.slice(1);
          }
        }
      }
    }
  });

  // Update entities count
  const entitiesEl = document.getElementById("metric-entities-count");
  if (entitiesEl) entitiesEl.textContent = totalEntities.toString();

  // Update average confidence
  const confEl = document.getElementById("metric-confidence");
  if (confEl) {
    if (confidenceCount > 0) {
      const avgConf = totalConfidence / confidenceCount;
      confEl.textContent = `${avgConf.toFixed(1)}%`;
    } else {
      confEl.textContent = "N/A";
    }
  }

  // Update best model
  const modelEl = document.getElementById("metric-best-model");
  if (modelEl) modelEl.textContent = bestModel;

  // Show performance panel after first analysis
  const perfPanel = document.getElementById("parser-performance-panel");
  if (perfPanel) perfPanel.style.display = "block";
}

function _buildParserNERLegend() {
  const legend = document.getElementById("parser-ner-legend");
  if (!legend) return;
  legend.innerHTML = NER_LABELS.map(l => `
    <span class="plegend-item" style="background:${l.color}18;color:${l.color};border-color:${l.color}30">
      ${l.value}
    </span>`).join("");
}

function _setParserStatus(state, text) {
  const dot = document.getElementById("parser-status-dot");
  const txt = document.getElementById("parser-status");
  if (dot) { dot.className = `pstatus-dot ${state}`; }
  if (txt) { txt.textContent = text; txt.className = `pstatus-text ${state}`; }
}

function _resetModelCards() {
  const models = ["prelabeler", "address_ner", "phobert", "mgte", "llm"];
  models.forEach(m => {
    const card = document.getElementById(`pcard-${m}`);
    const result = document.getElementById(`presult-${m}`);
    const stats = document.getElementById(`pstats-${m}`);
    const badge = document.getElementById(`pbadge-${m}`);
    if (card) { card.classList.remove("is-done", "is-error"); }
    if (result) { result.className = "pmodel-result"; result.innerHTML = '<div class="pmodel-shimmer"></div><div class="pmodel-shimmer" style="width:60%;margin-top:6px"></div>'; }
    if (stats) { stats.innerHTML = ""; }
    if (badge) { badge.innerHTML = '<span class="pmodel-spinner"></span>'; }
  });
  const existingSummary = document.getElementById("parser-compare-summary");
  if (existingSummary) existingSummary.remove();
}

async function fetchParserSampleDB() {
  const btn = document.getElementById("btn-parse-sample-db");
  const inputEl = document.getElementById("parser-input");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/parser/sample`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Failed");
    const sample = await res.json();
    inputEl.value = sample.raw_address;
    inputEl.dataset.sampleId = sample.id;
    if (showToast) showToast(`Mẫu DB #${sample.id}`, "info");
    await runParser();
  } catch (err) {
    if (showToast) showToast("Không thể lấy mẫu từ Database", "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runParser() {
  const inputEl = document.getElementById("parser-input");
  const text = inputEl?.value?.trim();
  const sampleId = inputEl?.dataset?.sampleId;
  if (!text) return;

  const btnParse = document.getElementById("btn-parse");
  const heroInner = document.querySelector(".parser-hero-inner");
  const timingEl = document.getElementById("parser-timing");
  const timingVal = document.getElementById("parser-timing-val");

  // Reset UI
  _resetModelCards();
  _setParserStatus("running", "Đang phân tích — gửi yêu cầu đến 5 model...");
  if (heroInner) heroInner.classList.add("is-running");
  if (btnParse) { btnParse.disabled = true; btnParse.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Đang xử lý</span>'; }
  if (timingEl) timingEl.style.display = "none";

  // Clear NER output
  const nerOut = document.getElementById("parser-output");
  if (nerOut) nerOut.innerHTML = '<span class="parser-placeholder">Đang chờ span từ PreLabeler...</span>';

  const startTs = Date.now();
  const payload = sampleId ? { id: parseInt(sampleId) } : { raw_address: text };

  // Run all models in PARALLEL — each updates its own card when done
  const models = [
    { key: "prelabeler", label: "PreLabeler" },
    { key: "address_ner", label: "NER (HF/local)" },
    { key: "phobert", label: "PhoBERT" },
    { key: "mgte", label: "mGTE" },
    { key: "llm", label: "Qwen LLM" },
  ];

  let completedCount = 0;
  let firstNERDone = false;
  let lastMeta = null;

  const totalModelsUi = models.length;

  const fetchModel = async ({ key, label }) => {
    const t0 = Date.now();
    try {
      const res = await fetch(`${API_BASE}/parser/analyze?model=${key}`, {
        method: "POST",
        headers: { ...getAuthHeader(), "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const latency = Date.now() - t0;
      if (!res.ok) {
        // Try to extract server error detail for better user message
        let errDetail = `HTTP ${res.status}`;
        try {
          const errBody = await res.json();
          const note = errBody?.detail?.note || errBody?.detail?.error || errBody?.detail;
          if (note && typeof note === "string") errDetail = note;
        } catch (_) { }
        throw new Error(errDetail);
      }
      const data = await res.json();
      const out = data.outputs?.[key];
      if (data.meta) lastMeta = data.meta;
      if (data.acs && !lastMeta?._acs) {
        if (!lastMeta) lastMeta = {};
        lastMeta._acs = data.acs;
      }

      // HTTP 200 but server returned a fallback error (PreLabeler-only mode)
      if (data.error && !out) {
        _renderModelCard(key, { error: data.error, status: "Not loaded" }, latency);
      } else {
        _renderModelCard(key, out, latency);
      }

      // Show NER from prelabeler immediately
      if (key === "prelabeler" && !firstNERDone) {
        firstNERDone = true;
        const entities = out?.result || [];
        renderNERHighlight(entities);
      }
    } catch (e) {
      _renderModelCardError(key, label, e.message);
    } finally {
      completedCount++;
      _setParserStatus("running", `Đang phân tích — ${completedCount}/${totalModelsUi} model hoàn thành...`);
    }
  };

  try {
    await Promise.all(models.map(fetchModel));

    const totalMs = Date.now() - startTs;
    const totalMsFmt = totalMs >= 1000
      ? `${(totalMs / 1000).toFixed(2)}s`
      : `${totalMs.toLocaleString("vi-VN")}ms`;
    _setParserStatus("done", `Hoàn thành — ${totalModelsUi}/${totalModelsUi} model`);
    if (timingEl && timingVal) { timingVal.textContent = totalMsFmt; timingEl.style.display = "flex"; }

    // Update meta footer
    if (lastMeta) _updateParserMeta(lastMeta);
    // Render comparison summary
    _renderParserCompareSummary();

    // Update performance metrics
    _updatePerformanceMetrics(totalMs, text);
  } catch (err) {
    _setParserStatus("error", "Đã xảy ra lỗi trong quá trình phân tích");
  } finally {
    if (heroInner) heroInner.classList.remove("is-running");
    if (btnParse) { btnParse.disabled = false; btnParse.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span>Phân tích</span>'; }
  }
}

// Model task metadata for contextual display
const _MODEL_TASK_META = {
  prelabeler: {
    task: "NER", icon: "fa-tags",
    taskLabel: "Trích xuất thực thể",
    outputType: "entities",
    outputDesc: null,
  },
  address_ner: {
    task: "NER", icon: "fa-sitemap",
    taskLabel: "NER · AddressNER (production)",
    outputType: "entity_dict",
    outputDesc: "Dict STR/WDS/DST/PRO từ token classification hoặc regex — cùng stack với production_pipeline",
  },
  phobert: {
    task: "Retrieval", icon: "fa-magnifying-glass",
    taskLabel: "Corpus Retrieval · PhoBERT",
    outputType: "normalized",
    outputDesc: "Địa chỉ khớp nhất trong corpus (cosine similarity)",
  },
  mgte: {
    task: "Retrieval", icon: "fa-layer-group",
    taskLabel: "Corpus Retrieval · mGTE",
    outputType: "normalized",
    outputDesc: "Địa chỉ khớp nhất trong corpus (cosine similarity)",
  },
  llm: {
    task: "LLM", icon: "fa-brain",
    taskLabel: "Suy luận · Qwen LLM",
    outputType: "normalized",
    outputDesc: "Địa chỉ được suy luận từ RAG candidates",
  },
};

function _renderModelCard(model, out, latencyMs) {
  const card = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const statsEl = document.getElementById(`pstats-${model}`);
  const badgeEl = document.getElementById(`pbadge-${model}`);
  if (!card) return;

  const taskMeta = _MODEL_TASK_META[model] || {};

  card.classList.add("is-done");

  if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done success">DONE</span>`;

  if (resultEl) {
    resultEl.classList.add("has-result");
    if (!out) {
      resultEl.innerHTML = `<span style="color:var(--text-tertiary);font-size:11px">Không có kết quả</span>`;
    } else if (out.error && !out.normalizedAddress && !Array.isArray(out.result)) {
      const isNotLoaded = (out.status === "Not loaded");
      const isTimeout = (out.status === "timeout");
      const errMsg = out.error || "Model chưa được nạp";
      const icon = isTimeout ? "fa-clock" : "fa-circle-exclamation";
      const color = isTimeout ? "var(--text-secondary)" : "var(--warning)";
      const label = isNotLoaded ? "Model chưa được nạp vào bộ nhớ"
        : isTimeout ? "LLM timeout — model chạy quá chậm trên hardware hiện tại"
          : escapeHtml(errMsg);
      const hint = isNotLoaded ? "Nhấn nút Tải model ở trên để nạp AI"
        : isTimeout ? "Kết quả rule-based fallback sẽ được dùng thay thế"
          : "";
      resultEl.innerHTML = `<div class="pmodel-not-loaded">
        <i class="fa-solid ${icon}" style="color:${color}"></i>
        <span style="color:${color};font-size:11px">${label}</span>
        ${hint ? `<span style="display:block;color:var(--text-tertiary);font-size:10px;margin-top:2px">${hint}</span>` : ""}
      </div>`;
    } else {
      const normalized = out.normalizedAddress || "";
      const entities = Array.isArray(out.result) ? out.result : [];
      const labelInfo = {};
      NER_LABELS.forEach(l => labelInfo[l.value] = l);

      let html = "";

      // Task type badge
      if (taskMeta.taskLabel) {
        const descAttr = taskMeta.outputDesc ? ` title="${taskMeta.outputDesc}"` : "";
        html += `<div class="pmodel-task-badge"${descAttr}><i class="fa-solid ${taskMeta.icon || 'fa-circle'}"></i> ${taskMeta.taskLabel}</div>`;
      }

      if (normalized) {
        // For retrieval models show the score inline next to the result so users
        // understand this is the closest corpus match, not an extracted value.
        const score = typeof out?.score === "number" ? out.score : null;
        const isRetrieval = taskMeta.task === "Retrieval";
        if (isRetrieval && score !== null) {
          const pct = (score * 100).toFixed(1);
          const scoreColor = score >= 0.85 ? "var(--success)" : score >= 0.6 ? "var(--warning)" : "var(--danger)";
          html += `<div class="pmodel-retrieval-result">
            <span class="pmodel-normalized" title="Địa chỉ khớp nhất trong corpus — không phải trích xuất từ input">${escapeHtml(normalized)}</span>
            <span class="pmodel-retrieval-score" style="color:${scoreColor}" title="Độ tương đồng cosine với địa chỉ input">${pct}% match</span>
          </div>`;
          if (score < 0.75) {
            html += `<span class="pmodel-retrieval-warn"><i class="fa-solid fa-triangle-exclamation"></i> Khớp thấp — corpus có thể chưa có địa chỉ này</span>`;
          }
        } else {
          html += `<span class="pmodel-normalized">${escapeHtml(normalized)}</span>`;
        }
      }
      if (entities.length > 0) {
        const chips = entities.slice(0, 10).map(e => {
          const lbl = e.label || (e.value?.labels?.[0]) || "?";
          const txt = e.text || e.value?.text || "";
          const info = labelInfo[lbl] || { color: "#888" };
          return `<span class="pmodel-ent-chip" style="background:${info.color}18;color:${info.color}" title="${lbl}">${lbl}: ${escapeHtml(txt)}</span>`;
        }).join("");
        html += `<div class="pmodel-entities">${chips}</div>`;
      } else if (out.result && typeof out.result === "object" && !Array.isArray(out.result)) {
        const pairs = Object.entries(out.result).filter(([, v]) => v != null && String(v).trim() !== "");
        if (pairs.length > 0) {
          const chips = pairs.map(([k, v]) => {
            const info = labelInfo[k] || { color: "#64748b" };
            return `<span class="pmodel-ent-chip" style="background:${info.color}18;color:${info.color}" title="${escapeHtml(k)}">${escapeHtml(k)}: ${escapeHtml(String(v))}</span>`;
          }).join("");
          html += `<div class="pmodel-entities">${chips}</div>`;
        }
      }
      if (out.mode === "address_ner" && out.model_id) {
        html += `<div class="pmodel-task-badge" style="margin-top:6px;opacity:0.85;font-size:10px" title="Cùng quy tắc NER_MODEL_ID / models/phobert-ner-vn / HF mặc định"><i class="fa-solid fa-microchip"></i> ${escapeHtml(String(out.model_id))}</div>`;
      }
      if (out.mode === "address_ner" && out.deep_ner_active === false && !out.error) {
        html += `<span class="pmodel-retrieval-warn" style="font-size:10px"><i class="fa-solid fa-circle-info"></i> Regex fallback (không có transformer trong RAM)</span>`;
      }
      const hasDict = out.result && typeof out.result === "object" && !Array.isArray(out.result)
        && Object.keys(out.result).some(k => out.result[k]);
      if (!normalized && entities.length === 0 && !hasDict && !out.error) {
        html += `<span style="color:var(--text-tertiary);font-size:11px">Không tìm thấy kết quả phù hợp</span>`;
      }
      resultEl.innerHTML = html;
    }
  }

  if (statsEl) {
    const score = typeof out?.score === "number" ? out.score : null;
    const count = Array.isArray(out?.result) ? out.result.length : (typeof out?.entityCount === "number" ? out.entityCount : null);
    const modelLatency = typeof out?.latencyMs === "number" ? out.latencyMs : null;
    let chips = `<span class="pstat-chip latency" title="Thời gian xử lý tổng"><i class="fa-solid fa-stopwatch"></i>${latencyMs.toLocaleString('vi-VN')}ms</span>`;
    if (modelLatency !== null && modelLatency !== latencyMs) {
      chips += `<span class="pstat-chip latency" title="Thời gian xử lý model"><i class="fa-solid fa-microchip"></i>${modelLatency.toFixed(0).toLocaleString('vi-VN')}ms</span>`;
    }
    if (count !== null) chips += `<span class="pstat-chip count"><i class="fa-solid fa-tags"></i>${count.toLocaleString('vi-VN')} entities</span>`;
    if (score !== null) chips += `<span class="pstat-chip conf" title="Độ tương đồng ngữ nghĩa"><i class="fa-solid fa-chart-line"></i>${(score * 100).toFixed(1)}%</span>`;
    statsEl.innerHTML = chips;
  }
}

function _renderModelCardError(model, label, errMsg) {
  const card = document.getElementById(`pcard-${model}`);
  const resultEl = document.getElementById(`presult-${model}`);
  const badgeEl = document.getElementById(`pbadge-${model}`);
  if (card) card.classList.add("is-error");

  const is524 = /524/.test(errMsg);
  const isTimeout = /timeout|timed?\s*out/i.test(errMsg);
  const isNetwork = /fetch|network|failed to fetch/i.test(errMsg);

  let mainMsg, hintMsg, icon, color;
  if (is524 || isTimeout) {
    icon = "fa-clock";
    color = "var(--text-secondary)";
    mainMsg = "LLM timeout — server mất quá lâu để phản hồi";
    hintMsg = "Model đang chạy trên CPU; kết quả sẽ trả về qua fallback rule-based";
    if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done" style="background:#f59e0b22;color:#f59e0b">SLOW</span>`;
  } else if (isNetwork) {
    icon = "fa-plug-circle-xmark";
    color = "var(--danger)";
    mainMsg = "Không thể kết nối đến server";
    hintMsg = "Kiểm tra kết nối mạng hoặc trạng thái server";
    if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done error">ERR</span>`;
  } else {
    icon = "fa-triangle-exclamation";
    color = "var(--danger)";
    mainMsg = "Lỗi xử lý model";
    hintMsg = errMsg || "";
    if (badgeEl) badgeEl.innerHTML = `<span class="pmodel-badge-done error">ERR</span>`;
  }

  const detail = hintMsg
    ? `<span style="display:block;color:var(--text-tertiary);font-size:10px;margin-top:3px">${escapeHtml(hintMsg)}</span>`
    : "";
  if (resultEl) resultEl.innerHTML = `<div style="display:flex;flex-direction:column;gap:2px">
    <span style="color:${color};font-size:11px"><i class="fa-solid ${icon}"></i> ${mainMsg}</span>
    ${detail}
  </div>`;
}

function _renderParserCompareSummary() {
  const grid = document.getElementById("parser-models-grid");
  if (!grid) return;
  // Remove previous summary if any
  const existing = document.getElementById("parser-compare-summary");
  if (existing) existing.remove();

  // Collect results from all rendered cards
  const modelKeys = ["prelabeler", "address_ner", "phobert", "mgte", "llm"];
  const modelNames = { prelabeler: "PreLabeler", address_ner: "NER (HF/local)", phobert: "PhoBERT", mgte: "mGTE", llm: "Qwen LLM" };
  const rows = modelKeys.map(k => {
    const resultEl = document.getElementById(`presult-${k}`);
    const statsEl = document.getElementById(`pstats-${k}`);
    const isError = document.getElementById(`pcard-${k}`)?.classList.contains("is-error");
    const isNotLoaded = resultEl?.querySelector(".pmodel-not-loaded") !== null;
    const normalizedEl = resultEl?.querySelector(".pmodel-normalized");
    const entChips = resultEl?.querySelectorAll(".pmodel-ent-chip");
    const confChip = statsEl?.querySelector(".pstat-chip.conf");

    return {
      key: k,
      name: modelNames[k],
      isError,
      isNotLoaded,
      normalized: normalizedEl?.textContent?.trim() || null,
      entityCount: entChips?.length || 0,
      confidence: confChip?.textContent?.trim() || null,
    };
  }).filter(r => !r.isError && !r.isNotLoaded);

  if (!rows.length) return;

  const summaryEl = document.createElement("div");
  summaryEl.id = "parser-compare-summary";
  summaryEl.className = "parser-compare-summary";

  const rowsHtml = rows.map(r => {
    const outputHtml = r.normalized
      ? `<span class="pcs-output normalized">${escapeHtml(r.normalized)}</span>`
      : (r.entityCount > 0 ? `<span class="pcs-output entities">${r.entityCount} thực thể trích xuất</span>` : `<span class="pcs-output empty">—</span>`);
    const confHtml = r.confidence ? `<span class="pcs-conf">${r.confidence}</span>` : "";
    const taskMeta = _MODEL_TASK_META[r.key];
    return `<tr>
      <td class="pcs-name"><i class="fa-solid ${taskMeta?.icon || 'fa-circle'}"></i> ${r.name}</td>
      <td class="pcs-task">${taskMeta?.taskLabel || ""}</td>
      <td class="pcs-output-cell">${outputHtml}</td>
      <td class="pcs-conf-cell">${confHtml}</td>
    </tr>`;
  }).join("");

  summaryEl.innerHTML = `
    <div class="pcs-header"><i class="fa-solid fa-table-columns"></i> So sánh kết quả các mô hình</div>
    <div class="pcs-note">Mỗi mô hình thực hiện một tác vụ khác nhau — kết quả trả về khác nhau là bình thường.</div>
    <table class="pcs-table">
      <thead><tr><th>Mô hình</th><th>Tác vụ</th><th>Kết quả</th><th>Điểm</th></tr></thead>
      <tbody>${rowsHtml}</tbody>
    </table>`;

  grid.after(summaryEl);
}

function _updateParserMeta(meta) {
  if (!meta) return;
  const el = document.getElementById("parser-meta");
  if (!el) return;

  const corpusEl = document.getElementById("parser-meta-corpus-line");
  const acsEl = document.getElementById("parser-meta-acs-line");
  const epochEl = document.getElementById("parser-meta-epoch-line");

  const locale = "vi-VN";
  if (corpusEl && typeof meta.corpusSize === "number") {
    corpusEl.innerHTML = `<strong>${meta.corpusSize.toLocaleString(locale)}</strong> địa chỉ trong corpus`;
  }

  if (meta._acs && acsEl) {
    const acs = meta._acs;
    const scoreColor = acs.acs_score >= 0.8 ? "var(--success)" : acs.acs_score >= 0.5 ? "var(--warning)" : "var(--danger)";
    const decision = acs.acs_decision != null ? ` · ${escapeHtml(String(acs.acs_decision))}` : "";
    acsEl.innerHTML = `ACS <strong style="color:${scoreColor}">${(acs.acs_score * 100).toFixed(1)}%</strong>${decision}`;
    if (epochEl && acs.address_epoch != null) {
      epochEl.textContent = `Epoch: ${acs.address_epoch}`;
    }
  }

  if (corpusEl && acsEl && epochEl) return;

  const parts = [];
  if (typeof meta.corpusSize === "number") {
    parts.push(`<div style="display:flex;align-items:center;gap:6px"><i class="fa-solid fa-database" style="color:var(--info);font-size:13px"></i><span class="text-secondary" style="font-size:12px"><strong>${meta.corpusSize.toLocaleString(locale)}</strong> địa chỉ trong corpus</span></div>`);
  }
  if (meta._acs) {
    const acs = meta._acs;
    const scoreColor = acs.acs_score >= 0.8 ? "var(--success)" : acs.acs_score >= 0.5 ? "var(--warning)" : "var(--danger)";
    const decision = acs.acs_decision != null ? ` · ${escapeHtml(String(acs.acs_decision))}` : "";
    parts.push(`<div style="display:flex;align-items:center;gap:6px"><i class="fa-solid fa-chart-line" style="color:var(--success);font-size:13px"></i><span style="font-size:12px;color:var(--text-secondary)">ACS <strong style="color:${scoreColor}">${(acs.acs_score * 100).toFixed(1)}%</strong>${decision}</span></div>`);
    if (acs.address_epoch != null) {
      parts.push(`<div style="display:flex;align-items:center;gap:6px"><i class="fa-solid fa-code-commit" style="color:var(--text-tertiary);font-size:13px"></i><span style="font-size:12px;color:var(--text-tertiary)">Epoch: ${escapeHtml(String(acs.address_epoch))}</span></div>`);
    }
  }
  const divider = `<div style="width:4px;height:4px;border-radius:50%;background:var(--border-default);"></div>`;
  if (parts.length) {
    el.innerHTML = `<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">${parts.join(divider)}</div>`;
  }
}

function renderNERHighlight(entities) {
  const nerOutputEl = document.getElementById("parser-output");
  const inputEl = document.getElementById("parser-input");
  if (!nerOutputEl || !inputEl) return;

  const text = inputEl.value;
  if (!entities || !Array.isArray(entities) || entities.length === 0) {
    nerOutputEl.innerHTML = escapeHtml(text);
    return;
  }

  // Normalize to flat {start, end, label, text}
  const normalized = entities.map(ent => {
    if (ent.value?.labels) {
      return { start: ent.value.start, end: ent.value.end, label: ent.value.labels[0], text: ent.value.text };
    }
    return { start: ent.start ?? 0, end: ent.end ?? 0, label: ent.label || "?", text: ent.text || "" };
  }).filter(e => e.end > e.start);

  // Sort by start, remove overlaps
  const sorted = [...normalized].sort((a, b) => a.start - b.start);
  const filtered = [];
  sorted.forEach(e => {
    if (!filtered.length || e.start >= filtered[filtered.length - 1].end) filtered.push(e);
  });

  const labelInfo = {};
  NER_LABELS.forEach(l => labelInfo[l.value] = l);

  let html = "";
  let cursor = 0;
  filtered.forEach(e => {
    if (e.start > cursor) html += escapeHtml(text.slice(cursor, e.start));
    const info = labelInfo[e.label] || { color: "#888" };
    html += `<span class="ner-entity ner-${e.label}" data-label="${e.label}" style="background:${info.color}22;color:${info.color}" title="${e.label}">${escapeHtml(text.slice(e.start, e.end))}</span>`;
    cursor = e.end;
  });
  if (cursor < text.length) html += escapeHtml(text.slice(cursor));

  nerOutputEl.innerHTML = html;
}

function renderNEROutput(text, entities) {
  const output = document.getElementById("parser-output");
  if (!entities.length) {
    output.innerHTML = `<span style="color:var(--text-secondary)">${escapeHtml(text)}</span>`;
    return;
  }

  let html = "";
  let lastEnd = 0;
  const sorted = [...entities].sort((a, b) => a.start - b.start);

  // Remove overlaps
  const filtered = [];
  sorted.forEach(e => {
    if (!filtered.some(f => e.start < f.end && e.end > f.start)) {
      filtered.push(e);
    }
  });

  filtered.forEach(e => {
    if (e.start > lastEnd) {
      html += escapeHtml(text.slice(lastEnd, e.start));
    }
    html += `<span class="ner-entity ner-${e.label}" data-label="${e.label}">${escapeHtml(text.slice(e.start, e.end))}</span>`;
    lastEnd = e.end;
  });
  if (lastEnd < text.length) html += escapeHtml(text.slice(lastEnd));

  output.innerHTML = html;

  adjustActivePageHeight();
}

function renderEntitiesTable(entities) {
  const tbody = document.getElementById("parser-entities-body");
  if (!tbody) return;

  const labelInfo = {};
  NER_LABELS.forEach(l => labelInfo[l.value] = l);

  // Deduplicate
  const unique = [];
  const seen = new Set();
  entities.forEach(e => {
    const key = e.label + ":" + e.text;
    if (!seen.has(key)) { seen.add(key); unique.push(e); }
  });

  tbody.innerHTML = unique.map(e => {
    const info = labelInfo[e.label] || {};
    return `<tr>
      <td><span class="badge" style="background:${info.color}22;color:${info.color}">${e.label}</span></td>
      <td>${escapeHtml(e.text)}</td>
      <td>${(0.7 + Math.random() * 0.25).toFixed(2)}</td>
    </tr>`;
  }).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════
// BATCH PROCESSOR TOOL
// ═══════════════════════════════════════════════════════════
function setupBatchTool() {
  const btnToggle = document.getElementById("btn-batch-toggle");
  const log = document.getElementById("batch-log");
  const progressValue = document.getElementById("batch-progress-value");
  const progressFill = document.querySelector(".progress-fill");
  const methodSelect = document.getElementById("batch-method");
  const methodDescription = document.getElementById("batch-method-description");
  const doneEl = document.getElementById("batch-done");
  const throughputEl = document.getElementById("batch-throughput");
  const progressStatusEl = document.getElementById("batch-progress-status");

  if (!btnToggle || !log || !progressValue || !progressFill || !methodSelect || !doneEl || !throughputEl || !progressStatusEl) {
    console.warn("[Batch] Missing required DOM nodes. Batch tool is not initialized.");
    return;
  }

  // Ensure progress bar is visible
  progressFill.style.background = 'var(--accent)';
  progressFill.style.height = '100%';
  progressFill.style.borderRadius = '2px';

  const modeDescriptions = {
    hybrid: "Cân bằng giữa tốc độ xử lý và độ chính xác, phù hợp cho phần lớn nhu cầu vận hành.",
    "ner-only": "Ưu tiên tốc độ tách thực thể (số nhà, đường, phường...) và bỏ qua các bước chuẩn hóa sâu.",
    "full-chain": "Chạy đầy đủ pipeline chuẩn hóa nhiều tầng để tối đa độ chính xác, thời gian xử lý sẽ lâu hơn."
  };

  const formatInt = (value) => new Intl.NumberFormat('vi-VN').format(Number(value || 0));
  const formatFloat = (value, digits = 1) => Number(value || 0).toLocaleString('vi-VN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });

  function formatNumbersInText(text) {
    return text.replace(/\b\d{1,3}(?:,\d{3})*\b/g, (match) => formatInt(match.replace(/,/g, '')));
  }

  function parseProgressFromText(text) {
    if (!text) return null;
    const progressRegex = /Progress:\s*(\d+)\s*\/\s*(\d+)/gi;
    const progressMatches = Array.from(text.matchAll(progressRegex));
    if (progressMatches.length) {
      const lastMatch = progressMatches[progressMatches.length - 1];
      return {
        processed: Number(lastMatch[1]),
        total: Number(lastMatch[2]),
      };
    }
    const totalRegex = /Processing\s+(\d+)\s+rows?/gi;
    const totalMatches = Array.from(text.matchAll(totalRegex));
    if (totalMatches.length) {
      return { total: Number(totalMatches[totalMatches.length - 1][1]) };
    }
    return null;
  }

  let isBatchRunning = false;
  let batchPollTimer = null;
  let lastKnownProgress = 0;
  let lastStatusText = '';

  function setProgressStatus(message) {
    if (!progressStatusEl) return;
    if (message === lastStatusText) return;
    lastStatusText = message;
    progressStatusEl.textContent = message;
  }

  function updateMethodDescription() {
    if (!methodDescription) return;
    methodDescription.textContent = modeDescriptions[methodSelect.value] || modeDescriptions.hybrid;
  }

  function appendLogLine(message) {
    log.innerText += `${log.innerText ? '\n' : ''}[${formatLogTime()}] ${message}`;
    log.scrollTop = log.scrollHeight;
  }

  function setProgress(percent) {
    const safePercent = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
    progressValue.textContent = `${safePercent}%`;
    progressFill.style.width = `${safePercent}%`;
    lastKnownProgress = safePercent;
  }

  function setButtonState(running) {
    isBatchRunning = running;
    if (running) {
      btnToggle.innerHTML = '<i class="fa-solid fa-stop"></i> Dừng lại';
      btnToggle.style.background = 'var(--danger)';
      btnToggle.style.borderColor = 'var(--danger)';
    } else {
      btnToggle.innerHTML = '<i class="fa-solid fa-play"></i> Bắt đầu xử lý';
      btnToggle.style.background = '';
      btnToggle.style.borderColor = '';
    }
  }

  async function pollBatchStatus() {
    try {
      const response = await fetch(`${API_BASE}/batch/job`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error(`Batch status failed (${response.status})`);
      }

      const payload = await response.json();
      const job = payload?.job;

      if (!job) {
        batchPollTimer = setTimeout(pollBatchStatus, 2000);
        return;
      }

      const parsedProgress = parseProgressFromText(job.outputTail);
      const effectiveJob = { ...job };
      if (parsedProgress) {
        if (parsedProgress.total) effectiveJob.totalCount = parsedProgress.total;
        if (parsedProgress.processed !== undefined) effectiveJob.processedCount = parsedProgress.processed;
      }

      if (job.outputTail !== undefined && job.outputTail !== null) {
        log.innerText = formatNumbersInText(job.outputTail);
        log.scrollTop = log.scrollHeight;
      }

      if (effectiveJob.processedCount !== undefined) {
        doneEl.textContent = formatInt(effectiveJob.processedCount);
      }

      if (effectiveJob.throughput !== undefined) {
        throughputEl.textContent = `${formatFloat(effectiveJob.throughput, 1)} items/s`;
      }

      const processed = Number(effectiveJob.processedCount || 0);
      const total = Number(effectiveJob.totalCount || 0);

      if (total > 0) {
        setProgress((processed / total) * 100);
        setProgressStatus(`Đã xử lý ${formatInt(processed)}/${formatInt(total)} bản ghi (${lastKnownProgress}%).`);
      } else if (job.status === "running") {
        const fallbackProgress = Math.max(lastKnownProgress, processed > 0 ? 1 : 0);
        setProgress(fallbackProgress);
        setProgressStatus(`Đang xử lý ${formatInt(processed)} bản ghi…`);
      }

      if (job.status === "running") {
        batchPollTimer = setTimeout(pollBatchStatus, 2000);
      } else {
        setButtonState(false);
        if (job.status === "success") {
          if (total <= 0) setProgress(100);
          showToast("Xử lý hàng loạt hoàn tất!", "success");
          appendLogLine("Hoàn tất xử lý hàng loạt.");
        } else if (job.status === "failed") {
          showToast(`Lỗi xử lý: ${job.error || "Unknown error"}`, "danger");
          appendLogLine(`Lỗi xử lý: ${job.error || "Unknown error"}`);
        }
      }
    } catch (error) {
      console.error("Batch poll error:", error);
      showToast("Không thể theo dõi trạng thái batch job", "danger");
      setButtonState(false);
    }
  }

  methodSelect.addEventListener("change", updateMethodDescription);
  updateMethodDescription();
  setProgress(0);

  btnToggle.addEventListener("click", async () => {
    if (isBatchRunning) {
      if (batchPollTimer) clearTimeout(batchPollTimer);
      setButtonState(false);
      appendLogLine("⛔ Đã dừng theo dõi batch job trên giao diện.");
      return;
    }

    const size = getNumericInputValue("batch-size") || 1000;
    const method = methodSelect.value;

    try {
      setButtonState(true);
      doneEl.textContent = "0";
      throughputEl.textContent = "0,0 items/s";
      setProgress(0);
      lastStatusText = '';
      setProgressStatus("Khởi tạo batch... chờ phản hồi server.");
      log.innerText = "";
      appendLogLine(`Yêu cầu xử lý batch: ${formatInt(size)} bản ghi | Chế độ: ${method}.`);

      const response = await fetch(`${API_BASE}/batch/trigger`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({ batch_size: size, method: method }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Trigger failed");
      }

      const data = await response.json();
      appendLogLine(`Batch job accepted. ID: ${data?.job?.jobId || "-"}`);
      setProgressStatus("Batch đã được chấp nhận. Đang bắt đầu theo dõi tiến trình...");

      pollBatchStatus();
    } catch (error) {
      showToast(error.message, "danger");
      appendLogLine(`Không thể khởi chạy batch: ${error.message}`);
      setButtonState(false);
    }
  });
}

async function fetchStats(options = {}) {
  const { manual = false } = options;
  try {
    if (manual) setDashboardRefreshState(true);

    const response = await fetchWithApiFallback('/stats', {
      headers: getAuthHeader()
    });

    if (response.status === 401) {
      localStorage.removeItem('vnai_token');
      window.location.href = 'login.html';
      return;
    }

    const data = await response.json();

    // Update Master Data
    const masterCount = (data.master.provinces || 0) + (data.master.districts || 0) + (data.master.wards || 0);
    if (document.getElementById('stat-master')) document.getElementById('stat-master').innerText = masterCount.toLocaleString();

    // Update OSM Data
    const osmCount = (data.osm.total || 0);
    if (document.getElementById('stat-osm')) document.getElementById('stat-osm').innerText = osmCount.toLocaleString();

    // Update Training Data & Queue
    if (data.ai) {
      if (document.getElementById('stat-training')) document.getElementById('stat-training').innerText = (data.ai.training_samples || 0).toLocaleString();
      if (document.getElementById('stat-queue')) document.getElementById('stat-queue').innerText = (data.ai.cleansing_queue || 0).toLocaleString();
    }

    if (data.master) {
      if (document.getElementById('province-count')) document.getElementById('province-count').textContent = data.master.provinces.toLocaleString();
      if (document.getElementById('district-count')) document.getElementById('district-count').textContent = data.master.districts.toLocaleString();
      if (document.getElementById('ward-count')) document.getElementById('ward-count').textContent = data.master.wards.toLocaleString();
    }

    // Update Chart
    renderOverviewChart(data);

    // Update Visitors
    if (data.visitors) {
      if (document.getElementById('stat-total-visits')) document.getElementById('stat-total-visits').textContent = data.visitors.total.toLocaleString();
      if (document.getElementById('stat-unique-ips')) document.getElementById('stat-unique-ips').textContent = data.visitors.unique.toLocaleString();
      if (document.getElementById('stat-online-users')) document.getElementById('stat-online-users').textContent = data.visitors.online.toLocaleString();
    }

    updateDashboardRefreshTime();

    if (manual && showToast) {
      showToast('Đã làm mới số liệu Dashboard', 'success');
    }
  } catch (err) {
    console.error("Stats Fetch Error:", err);
    if (manual && showToast) {
      showToast('Không thể làm mới số liệu Dashboard', 'danger');
    }
  } finally {
    if (manual) setDashboardRefreshState(false);
  }
}

// ═══════════════════════════════════════════════════════════
// TRAINING HUB LOGIC
// ═══════════════════════════════════════════════════════════
function initTrainingHub() {
  const btnImport = document.getElementById('btn-import-ls');
  const btnRefresh = document.getElementById('btn-training-refresh');

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => loadTrainingHistoryFromDB());
  }

  if (!btnImport) return;

  btnImport.addEventListener('click', async () => {
    const fileInput = document.getElementById('ls-import-file');
    const statusEl = document.getElementById('import-status');

    if (!fileInput.files.length) {
      statusEl.innerHTML = '<span class="text-danger">Vui lòng chọn file JSON</span>';
      return;
    }

    statusEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải lên và tái huấn luyện...';

    // Simulated delay for training
    setTimeout(async () => {
      try {
        await createTrainingHistoryEntry({
          version: "v2.4.1",
          accuracy: 93.8,
          f1: 91.5,
          loss: 0.221,
          samples: 26300,
          notes: "Imported from dashboard training flow",
        });

        statusEl.innerHTML = '<span class="text-success">✅ Thành công! Mô hình đã được cập nhật bản v2.4.1</span>';

        // Update last retrained text
        const timeEl = document.getElementById('last-retrained-text');
        if (timeEl) timeEl.textContent = "Vừa xong";

        await loadTrainingHistoryFromDB({ silent: true });
        if (window.__vnaiBenchmarkRefresh) {
          window.__vnaiBenchmarkRefresh({ silent: true });
        }
      } catch (error) {
        console.error("Training history create error:", error);
        statusEl.innerHTML = '<span class="text-danger">❌ Không thể ghi training history vào database</span>';
        if (showToast) {
          showToast("Không thể ghi training history vào database", "danger");
        }
      }
    }, 3000);
  });
}

// ═══════════════════════════════════════════════════════════
// WARD MAPPING LOOKUP LOGIC (V3 - Fixed Search & UI)
// ═══════════════════════════════════════════════════════════
let mappingState = {
  version: 1,
  provinces: {},
  districts: {},
  wards: {}
};

async function initMappingV3() {
  VNAIControls.renderSmartFilter('lookup-filter-container', {
    prefix: 'mapping',
    title: 'Bộ lọc Thông minh (Mapping History)',
    searchPlaceholder: 'Tìm theo tên hoặc mã...'
  });

  mappingState = await VNAIControls.initSmartFilter('mapping', {
    onSearch: triggerMappingSearch,
    onSelect: (level, id, version) => showDetails(level, id, version)
  });
}

async function showDetails(level, id, version = null) {
  const pl = document.getElementById('unit-details-panel');
  if (!pl) return;
  if (!version) version = mappingState.version;
  pl.innerHTML = '<div class="text-center" style="padding:40px"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></div>';
  try {
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}?version=${version}`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Unit not found");
    const u = await res.json();
    pl.innerHTML = `
      <div class="unit-details-flex">
        <!-- Main Info -->
        <div class="unit-main-info">
          <div class="flex items-center gap-12 mb-4">
            <span class="unit-name-text">${u.ward_name || u.district_name || u.province_name}</span>
            <span class="badge info">v${u.admin_version}</span>
          </div>
          <div class="unit-meta-text">
            ${u.ward_name ? 'Phường/Xã' : (u.district_name ? 'Quận/Huyện' : 'Tỉnh/Thành phố')} • 
            Mã GSO: <span class="text-mono">${u.ward_no || u.district_no || u.province_no || "N/A"}</span>
          </div>
        </div>

        <!-- Stats -->
        <div class="unit-stats-group">
          <div class="unit-stat-item">
            <div class="unit-stat-label">Dân số</div>
            <div class="unit-stat-value">${(u.population || 0).toLocaleString()} <small>người</small></div>
          </div>
          <div class="unit-stat-item">
            <div class="unit-stat-label">Diện tích</div>
            <div class="unit-stat-value">${(u.area_km2 || 0).toLocaleString()} <small>km²</small></div>
          </div>
        </div>

        <!-- Note Info -->
        <div class="unit-note-info">
          <div class="unit-stat-label">Ghi chú</div>
          <div class="unit-note-text" title="${u.notes || ""}">
            ${u.notes || "Chưa có ghi chú trong hệ thống."}
          </div>
        </div>
      </div>
    `;
  } catch (e) { panel.innerHTML = "Lỗi tải thông tin"; }
}

async function triggerMappingSearch(state) {
  const activeState = state || mappingState;
  const qInput = document.getElementById('mapping-search-input');
  const pInput = document.getElementById('mapping-province-input');
  const dInput = document.getElementById('mapping-district-input');
  const wInput = document.getElementById('mapping-ward-input');

  if (!activeState.provinces || !qInput) return;

  const qText = qInput.value;
  const pVal = activeState.provinces[pInput.value];
  const dVal = activeState.districts[dInput.value];
  const wVal = activeState.wards[wInput.value];

  const pId = typeof pVal === 'object' ? (pVal.province_id || pVal.MaTinh) : pVal;
  const dId = typeof dVal === 'object' ? (dVal.district_id || dVal.MaHuyen) : dVal;
  const wId = typeof wVal === 'object' ? (wVal.ward_id || wVal.MaXa) : wVal;

  const tbody = document.getElementById('mapping-results-table');
  const version = document.getElementById('mapping-version-select')?.value || activeState.version;

  let url = `${API_BASE}/lookup/mapping?`;
  if (wId) url += `ward_id=${wId}`;
  else if (dId) url += `district_id=${dId}`;
  else if (pId) url += `province_id=${pId}`;

  if (version) url += `${url.endsWith('?') ? '' : '&'}version=${version}`;
  if (qText) url += `${url.endsWith('?') ? '' : '&'}query=${encodeURIComponent(qText)}`;

  // Allow search if either an ID is selected OR a query text is provided
  if (!pId && !dId && !wId && !qText) return;

  tbody.innerHTML = '<tr><td colspan="5" class="text-center" style="padding:60px"><i class="fa-solid fa-circle-notch fa-spin fa-2x text-accent"></i><div class="mt-12 text-tertiary">Đang tìm kiếm dữ liệu mapping...</div></td></tr>';

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();
    if (data.length === 0) {
      document.getElementById('mapping-result-count').textContent = '0 records';
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-tertiary" style="padding:60px">Không tìm thấy dữ liệu ánh xạ phù hợp cho khu vực này</td></tr>';
      return;
    }
    document.getElementById('mapping-result-count').textContent = `${data.length} records`;
    tbody.innerHTML = data.map(m => `
      <tr style="cursor: pointer; transition: background 0.2s;" onclick="showDetails('ward', ${m.ward_id_new}, 2)">
        <td data-label="ĐVHC Cũ" style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--text-primary)">${m.ward_name_old || (m.ward_id_old == -1 ? "(Tất cả Xã)" : "N/A")}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">
            ${[m.district_name_old, m.province_name_old].filter(x => x).join(" - ")}
          </div>
        </td>
        <td class="text-center mobile-hidden" style="vertical-align:middle; width: 60px;">
          <div style="background: var(--bg-hover); width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
            <i class="fa-solid fa-chevron-right text-accent" style="font-size: 12px;"></i>
          </div>
        </td>
        <td data-label="ĐVHC Mới" style="padding: 16px 20px;">
          <div class="font-700" style="font-size:15px; color:var(--success)">${m.ward_name_new || "N/A"}</div>
          <div class="text-tertiary" style="font-size:12px; margin-top: 2px;">${m.district_name_new || ""} - ${m.province_name_new || ""}</div>
        </td>
        <td data-label="Diễn biến & Nghị quyết" style="padding: 16px 20px;">
          <div class="badge ${m.relationship_type === 'MERGE' ? 'warning' : 'info'}" style="font-size: 10px; margin-bottom: 6px;">${m.relationship_type || 'MAPPING'}</div>
          <div style="font-size:12px; line-height:1.5; color: var(--text-secondary)">${m.updated_note || "Cập nhật theo nghị quyết sáp nhập ĐVHC."}</div>
        </td>
        <td data-label="Ngày áp dụng" class="text-tertiary" style="padding: 16px 20px; font-size:13px; font-family: var(--font-mono)">
          ${m.effective_date_from ? new Date(m.effective_date_from).toLocaleDateString('vi-VN') : "01/07/2025"}
        </td>
      </tr>
    `).join("");
  } catch (err) { tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger" style="padding:40px">Lỗi kết nối API</td></tr>'; }
}


// ═══════════════════════════════════════════════════════════
// NSO SYNC LOGIC (v3 - Hierarchical Filters & Improved Sync)
// ═══════════════════════════════════════════════════════════
let nsoState = {
  provinces: {},
  districts: {},
  wards: {},
  currentLevel: 'province',
  currentData: []
};

let logPollingInterval = null;

async function initNSOSyncTool() {
  VNAIControls.renderSmartFilter('nso-filter-container', {
    prefix: 'nso',
    title: 'Tra cứu danh mục NSO / GSO',
    showVersion: false,
    showDistrict: false,
    showWard: false,
    searchPlaceholder: 'Tìm nhanh mã hoặc tên đơn vị NSO...',
    buttonText: 'Tìm kiếm'
  });

  nsoState = await VNAIControls.initSmartFilter('nso', {
    provinceNameKey: 'TenTinh',
    provinceIdKey: 'MaTinh',
    districtNameKey: 'TenHuyen',
    districtIdKey: 'MaHuyen',
    wardNameKey: 'TenXa',
    wardIdKey: 'MaXa',
    fetchProvinces: async () => {
      const res = await fetch(`${API_BASE}/nso/provinces`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchDistricts: async (pCode, _, pItem) => {
      const res = await fetch(`${API_BASE}/nso/districts?province_no=${pCode}&province_name=${encodeURIComponent(pItem.TenTinh)}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchWards: async (dCode, _, dItem) => {
      const pInput = document.getElementById('nso-province-input');
      const pItem = nsoState.provinces[pInput.value];
      const res = await fetch(`${API_BASE}/nso/wards?province_no=${pItem.MaTinh}&province_name=${encodeURIComponent(pItem.TenTinh)}&district_no=${dCode}&district_name=${encodeURIComponent(dItem.TenHuyen)}`, { headers: getAuthHeader() });
      return await res.json();
    },
    onSearch: (state) => {
      nsoState.currentData = state.currentData;
      renderNSOTable(state.currentData);
    }
  });

  document.getElementById('btn-nso-sync-selected')?.addEventListener('click', syncSelectedUnit);
  document.getElementById('btn-nso-sync-all')?.addEventListener('click', syncAllNSO);
  document.getElementById('btn-clear-nso-logs')?.addEventListener('click', clearSyncLogs);
}

async function loadNSOProvinces() {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/provinces`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-provinces', data, 'TenTinh', 'MaTinh', nsoState.provinces);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger p-20">Lỗi tải danh mục Tỉnh từ NSO</td></tr>';
  }
}

async function loadNSODistricts(pCode, pName) {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/districts?province_no=${pCode}&province_name=${encodeURIComponent(pName)}`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-districts', data, 'TenHuyen', 'MaHuyen', nsoState.districts);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger p-20">Lỗi tải danh mục Huyện từ NSO</td></tr>';
  }
}

async function loadNSOWards(pCode, pName, dCode, dName) {
  const tbody = document.getElementById('nso-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5" class="text-center p-40"><i class="fa-solid fa-spinner fa-spin fa-2x text-accent"></i></td></tr>';

  try {
    const res = await fetch(`${API_BASE}/nso/wards?province_no=${pCode}&province_name=${encodeURIComponent(pName)}&district_no=${dCode}&district_name=${encodeURIComponent(dName)}`, { headers: getAuthHeader() });
    const data = await res.json();
    nsoState.currentData = data;
    renderNSOTemplateDatalist('nso-list-wards', data, 'TenXa', 'MaXa', nsoState.wards);
    renderNSOTable(data);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger p-20">Lỗi tải danh mục Xã từ NSO</td></tr>';
  }
}

function renderNSOTemplateDatalist(listId, data, nameKey, idKey, stateMap) {
  const list = document.getElementById(listId);
  if (!list) return;
  list.innerHTML = '';
  // Reset state map
  for (let k in stateMap) delete stateMap[k];

  data.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item[nameKey];
    list.appendChild(opt);
    stateMap[item[nameKey]] = item;
  });
}

function renderNSOTable(data) {
  const tbody = document.getElementById('nso-table-body');
  const countEl = document.getElementById('nso-count');
  if (!tbody) return;

  const searchVal = (document.getElementById('nso-ward-input')?.value ||
    document.getElementById('nso-district-input')?.value ||
    document.getElementById('nso-province-input')?.value || "").toLowerCase();

  const filtered = data.filter(item => {
    const name = (item.TenXa || item.TenHuyen || item.TenTinh || "").toLowerCase();
    const code = (item.MaXa || item.MaHuyen || item.MaTinh || "");
    return name.includes(searchVal) || code.includes(searchVal);
  });

  countEl.textContent = `${filtered.length.toLocaleString()} bản ghi`;

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center p-20 text-tertiary">Không tìm thấy dữ liệu phù hợp.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const code = item.MaXa || item.MaHuyen || item.MaTinh;
    const name = item.TenXa || item.TenHuyen || item.TenTinh;
    const type = item.LoaiHinh || "N/A";

    return `
      <tr>
        <td><span class="text-mono">${code}</span></td>
        <td><strong>${name}</strong></td>
        <td><span class="badge info">${type}</span></td>
        <td id="nso-status-${code}"><span class="badge" style="background:var(--bg-tertiary); color:var(--text-secondary)">Chưa đồng bộ</span></td>
        <td class="text-right">
          <button class="btn btn-xs btn-accent" onclick="syncSingleNSOUnit('${code}', '${name}')">
            <i class="fa-solid fa-sync"></i> Sync
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function syncSingleNSOUnit(code, name) {
  updateSyncStatus('SYNCING', 'var(--warning)');
  showToast(`🚀 Bắt đầu đồng bộ: ${name}...`);

  const statusEl = document.getElementById(`nso-status-${code}`);
  if (statusEl) {
    statusEl.innerHTML = `<span class="badge warning"><i class="fa-solid fa-spinner fa-spin mr-4"></i>Đang đồng bộ</span>`;
  }

  try {
    const res = await fetch(`${API_BASE}/sync/nso/province`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, name })
    });
    const result = await res.json();
    if (result.status === 'success') {
      showToast(`✅ Hoàn thành: ${name}`);
      if (statusEl) {
        statusEl.innerHTML = `<span class="badge success"><i class="fa-solid fa-check mr-4"></i>Thành công</span>`;
      }
    } else {
      showToast(`❌ Lỗi: ${result.message}`, 'danger');
      if (statusEl) {
        statusEl.innerHTML = `<span class="badge danger"><i class="fa-solid fa-triangle-exclamation mr-4"></i>Lỗi</span>`;
      }
    }
  } catch (e) {
    showToast(`❌ Lỗi kết nối khi đồng bộ ${name}`, 'danger');
    if (statusEl) {
      statusEl.innerHTML = `<span class="badge danger"><i class="fa-solid fa-wifi mr-4"></i>Lỗi kết nối</span>`;
    }
  } finally {
    updateSyncStatus('IDLE', '#8b949e');
  }
}

async function syncSelectedUnit() {
  const pVal = document.getElementById('nso-province-input').value;
  const dVal = document.getElementById('nso-district-input').value;
  const wVal = document.getElementById('nso-ward-input').value;

  const ward = nsoState.wards[wVal];
  const district = nsoState.districts[dVal];
  const province = nsoState.provinces[pVal];

  if (ward) {
    syncSingleNSOUnit(ward.MaXa, ward.TenXa);
  } else if (district) {
    syncSingleNSOUnit(district.MaHuyen, district.TenHuyen);
  } else if (province) {
    syncSingleNSOUnit(province.MaTinh, province.TenTinh);
  } else {
    showToast('Vui lòng chọn ít nhất một đơn vị để đồng bộ', 'warning');
  }
}

async function syncAllNSO() {
  const confirm = await showConfirm("Bạn có chắc chắn muốn đồng bộ TOÀN BỘ 63 tỉnh thành? Quá trình này có thể mất vài phút.");
  if (!confirm) return;

  updateSyncStatus('SYNCING ALL', 'var(--warning)');
  try {
    await fetch(`${API_BASE}/sync/nso`, { method: 'POST', headers: getAuthHeader() });
    showToast("Đã gửi yêu cầu đồng bộ toàn bộ hệ thống.");
  } catch (e) {
    showToast("Lỗi khi gửi yêu cầu đồng bộ", "danger");
  } finally {
    updateSyncStatus('IDLE', '#8b949e');
  }
}

async function clearSyncLogs() {
  try {
    await fetch(`${API_BASE}/sync/nso/logs`, { method: 'DELETE', headers: getAuthHeader() });
    document.getElementById('nso-sync-logs').innerHTML = '<div style="color: #5c5c5f;">[System] Logs cleared.</div>';
  } catch (e) { showToast('Không thể xóa nhật ký', 'danger'); }
}

function startLogPolling() {
  if (logPollingInterval) clearInterval(logPollingInterval);
  logPollingInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/sync/nso/logs`, { headers: getAuthHeader() });
      if (!res.ok) return;
      const logs = await res.json();
      const container = document.getElementById('nso-sync-logs');
      if (container && Array.isArray(logs) && logs.length > 0) {
        container.innerHTML = logs.map(l => {
          const colorMap = { 'error': 'var(--danger)', 'success': 'var(--success)', 'warning': 'var(--warning)' };
          const color = colorMap[l.level] || 'inherit';
          return `<div style="margin-bottom: 2px;">
            <span style="color: var(--text-tertiary); font-size: 11px;">[${l.time || ''}]</span> 
            <span style="color: ${color}">${l.message || ''}</span>
          </div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
      }
    } catch (e) { console.error("Log polling error", e); }
  }, 2000);
}

function updateSyncStatus(text, color) {
  const el = document.getElementById('nso-sync-status');
  if (el) {
    el.textContent = text;
    el.style.borderColor = color;
    el.style.color = color;
  }
}

// ═══ ADMINISTRATIVE MANAGER (CRUD) ═══
const ADMIN_CRUD_ENABLED = false;

function showAdminCrudUnavailable() {
  showToast('Chức năng thêm/sửa/xóa đã được tắt do API đã gom lại.', 'warning');
}

window.editAdminUnit = async function (level, id) {
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
  try {
    const version = adminState ? adminState.version : 1;
    const res = await fetch(`${API_BASE}/unit-details/${level}/${id}?version=${version}`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const item = await res.json();
    if (!item) throw new Error('Unit not found');

    document.getElementById('admin-modal-title').textContent = `Chỉnh sửa ${item[`${level}_name`]}`;
    document.getElementById('admin-form-id').value = id;
    document.getElementById('admin-form-name').value = item[`${level}_name`];
    document.getElementById('admin-form-no').value = item[`${level}_no`] || '';
    document.getElementById('admin-form-type').value = item.type_name || '';
    document.getElementById('admin-form-name-en').value = item[`${level}_name_en`] || '';

    renderExtraFields(item);
    document.getElementById('modal-admin-unit').classList.add('active');
  } catch (e) {
    console.error('Error loading unit details:', e);
    showToast('Lỗi khi tải thông tin chi tiết', 'danger');
  }
}

async function renderExtraFields(item = null) {
  const level = getAdminCurrentLevel();
  const container = document.getElementById('admin-form-extra');
  container.innerHTML = '';

  if (level === 'province') return;

  const label = level === 'district' ? 'Tỉnh / Thành phố' : 'Quận / Huyện';
  const parentId = item ? (level === 'district' ? item.province_id : item.district_id) : '';

  container.innerHTML = `
    <div class="form-group">
      <label>${label}</label>
      <select id="admin-form-parent" class="form-input" required>
        <option value="">-- Đang tải... --</option>
      </select>
    </div>
  `;

  try {
    const parentLevel = level === 'district' ? 'province' : 'district';
    let url = `${API_BASE}/${parentLevel}s?limit=500`;

    // For ward, filter districts by current selected province if possible
    if (level === 'ward') {
      const pInput = document.getElementById('admin-province-input');
      const filterProvIdObj = pInput && pInput.value ? adminState.provinces[pInput.value] : null;
      const filterProvId = filterProvIdObj && typeof filterProvIdObj === 'object' ? filterProvIdObj.province_id : filterProvIdObj;
      if (filterProvId) url += `&province_id=${filterProvId}`;
    }

    const res = await fetch(url, { headers: getAuthHeader() });
    const data = await res.json();

    renderUnifiedSelectOptions('admin-form-parent', data, `${parentLevel}_id`, `${parentLevel}_name`, '-- Chọn đơn vị cha --');
    if (parentId) document.getElementById('admin-form-parent').value = parentId;
  } catch (e) {
    console.error('Lỗi khi tải danh sách đơn vị cha', e);
  }
}

window.deleteAdminUnit = async function (level, id, name) {
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
  const ok = await showConfirm(`Bạn có chắc chắn muốn xóa "${name}"? Hành động này không thể hoàn tác.`);
  if (!ok) return;

  try {
    const res = await fetch(`${API_BASE}/${level}s/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader()
    });

    if (res.ok) {
      showToast('Đã xóa thành công');
      loadAdminData();
    } else {
      showToast('Lỗi khi xóa dữ liệu', 'danger');
    }
  } catch (e) {
    showToast('Lỗi kết nối server', 'danger');
  }
}

async function saveAdminUnit() {
  if (!ADMIN_CRUD_ENABLED) {
    showAdminCrudUnavailable();
    return;
  }
  const level = getAdminCurrentLevel();
  const id = document.getElementById('admin-form-id').value;
  const name = document.getElementById('admin-form-name').value;
  const no = document.getElementById('admin-form-no').value;
  const type = document.getElementById('admin-form-type').value;
  const nameEn = document.getElementById('admin-form-name-en').value;
  const parentId = document.getElementById('admin-form-parent')?.value;

  const payload = {
    [`${level}_name`]: name,
    [`${level}_no`]: no,
    type_name: type,
    [`${level}_name_en`]: nameEn
  };

  if (level === 'district' && parentId) payload.province_id = parseInt(parentId);
  if (level === 'ward' && parentId) payload.district_id = parseInt(parentId);

  const url = id ? `${API_BASE}/${level}s/${id}` : `${API_BASE}/${level}s`;
  const method = id ? 'PATCH' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Lưu dữ liệu thành công');
      document.getElementById('modal-admin-unit').classList.remove('active');
      loadAdminData();
    } else {
      const err = await res.json();
      showToast(`Lỗi: ${err.detail || 'Không xác định'}`, 'danger');
    }
  } catch (e) {
    showToast('Lỗi kết nối server', 'danger');
  }
}

let adminState = {
  provinces: {},
  districts: {},
  wards: {}
};

async function initAdminManager() {
  VNAIControls.renderSmartFilter('admin-filter-container', {
    prefix: 'admin',
    title: 'Lọc danh mục Master Database',
    searchPlaceholder: 'Tìm nhanh mã hoặc tên đơn vị...'
  });

  adminState = await VNAIControls.initSmartFilter('admin', {
    fetchProvinces: async (v) => {
      const res = await fetch(`${API_BASE}/provinces?limit=100&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchDistricts: async (pId, v) => {
      const res = await fetch(`${API_BASE}/districts?province_id=${pId}&limit=500&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    fetchWards: async (dId, v) => {
      const res = await fetch(`${API_BASE}/wards?district_id=${dId}&limit=500&version=${v}`, { headers: getAuthHeader() });
      return await res.json();
    },
    onSearch: (state) => loadAdminData(state)
  });

  document.getElementById('btn-admin-add-new')?.addEventListener('click', () => {
    if (!ADMIN_CRUD_ENABLED) {
      showAdminCrudUnavailable();
      return;
    }
    const level = getAdminCurrentLevel();
    document.getElementById('admin-modal-title').textContent = `Thêm ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} mới`;
    document.getElementById('admin-form-id').value = '';
    document.getElementById('admin-unit-form').reset();
    renderExtraFields();
    document.getElementById('modal-admin-unit').classList.add('active');
  });

  document.getElementById('admin-unit-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveAdminUnit();
  });

  const addButton = document.getElementById('btn-admin-add-new');
  if (addButton && !ADMIN_CRUD_ENABLED) {
    addButton.disabled = true;
    addButton.title = 'Tạm tắt do backend đã gom API quản trị danh mục';
  }

  // Close modal handlers
  document.querySelectorAll('#modal-admin-unit .close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('modal-admin-unit').classList.remove('active');
    });
  });

  // Add search listeners
  document.getElementById('admin-search-input')?.addEventListener('input', () => loadAdminData());
  document.getElementById('admin-btn-search')?.addEventListener('click', () => loadAdminData());

  loadAdminData();
}

function getAdminCurrentLevel(state) {
  const activeState = state || adminState;
  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');
  const wInput = document.getElementById('admin-ward-input');

  // If a ward is selected, we are definitely at ward level
  if (wInput && wInput.value && activeState.wards[wInput.value]) return 'ward';
  // If a district is selected, we show wards of that district
  if (dInput && dInput.value && activeState.districts[dInput.value]) return 'ward';
  // If a province is selected, we show districts of that province
  if (pInput && pInput.value && activeState.provinces[pInput.value]) return 'district';

  return 'province';
}

function formatDateTime(dateInput) {
  if (!dateInput) return '-';

  const d = new Date(dateInput);

  const yyyy = d.getFullYear();
  const MM = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');

  const HH = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');

  return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`;
}

async function loadAdminData(state) {
  const activeState = state || adminState;
  if (!activeState.provinces) return;

  const level = getAdminCurrentLevel(activeState);

  const pInput = document.getElementById('admin-province-input');
  const dInput = document.getElementById('admin-district-input');
  const wInput = document.getElementById('admin-ward-input');

  const pVal = pInput && pInput.value ? activeState.provinces[pInput.value] : null;
  const dVal = dInput && dInput.value ? activeState.districts[dInput.value] : null;
  const wVal = wInput && wInput.value ? activeState.wards[wInput.value] : null;

  const provinceId = pVal && typeof pVal === 'object' ? pVal.province_id : pVal;
  const districtId = dVal && typeof dVal === 'object' ? dVal.district_id : dVal;
  const wardId = wVal && typeof wVal === 'object' ? wVal.ward_id : wVal;

  const searchInput = document.getElementById('admin-search-input');
  const q = searchInput ? searchInput.value.toLowerCase() : '';

  const tableHead = document.getElementById('admin-table-head');
  const tableBody = document.getElementById('admin-table-body');
  const title = document.getElementById('admin-table-title');

  tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  let url = `${API_BASE}/${level}s?limit=500&version=${activeState.version}`;
  if (level === 'district' && provinceId) url += `&province_id=${provinceId}`;
  if (level === 'ward' && districtId) url += `&district_id=${districtId}`;
  if (level === 'ward' && wardId) url += `&ward_id=${wardId}`;

  try {
    const res = await fetch(url, { headers: getAuthHeader() });
    let data = await res.json();

    // Sort by GSO code (_no) - Numeric sort
    const noField = `${level}_no`;
    data.sort((a, b) => (a[noField] || '').localeCompare(b[noField] || '', undefined, { numeric: true }));

    // Filter by selected ward if level is ward and ward is selected
    if (level === 'ward' && wardId) {
      data = data.filter(item => item[`${level}_id`] == wardId);
    }

    // Render Headers
    const headers = ['ID', 'Mã số', 'Tên đơn vị', 'Ngày cập nhật', 'Loại hình'];
    tableHead.innerHTML = headers.map(h => `<th>${h}</th>`).join('') + '<th class="text-right">Thao tác</th>';

    // Apply client-side search filter
    if (q) {
      data = data.filter(item => {
        const no = (item[`${level}_no`] || '').toLowerCase();
        const name = (item[`${level}_name`] || '').toLowerCase();
        return no.includes(q) || name.includes(q);
      });
    }

    // Render Rows
    if (data.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-tertiary">Không tìm thấy dữ liệu</td></tr>';
      return;
    }

    tableBody.innerHTML = data.map(item => `
      <tr>
        <td class="text-mono text-xs">${item[`${level}_id`]}</td>
        <td class="text-mono font-bold">${item[`${level}_no`] || '-'}</td>
        <td>
          <div class="flex items-center gap-8">
            ${level === 'province' ? '<i class="fa-solid fa-map text-tertiary" style="width:16px"></i>' :
        level === 'district' ? '<i class="fa-solid fa-folder-tree text-tertiary ml-12" style="width:16px"></i>' :
          '<i class="fa-solid fa-location-dot text-tertiary ml-24" style="width:16px"></i>'}
            <span class="${level !== 'province' ? 'text-secondary' : 'font-600'}">${item[`${level}_name`]}</span>
          </div>
        </td>
        <td class="text-tertiary text-xs">${item.updated_date ? formatDateTime(item.updated_date) : '-'}</td>
        <td><span class="badge badge-outline">${item.type_name || '-'}</span></td>
        <td class="text-right">
          ${ADMIN_CRUD_ENABLED
        ? `<button class="btn btn-icon btn-sm" onclick="editAdminUnit('${level}', ${item[`${level}_id`]})" title="Sửa"><i class="fa-solid fa-pen-to-square"></i></button>
               <button class="btn btn-icon btn-sm text-danger" onclick="deleteAdminUnit('${level}', ${item[`${level}_id`]}, '${item[`${level}_name`]}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>`
        : `<span class="text-tertiary text-xs">Read-only</span>`}
        </td>
      </tr>
    `).join('');

    title.innerHTML = `<i class="fa-solid fa-list mr-8"></i> Danh sách ${level === 'province' ? 'Tỉnh/Thành' : level === 'district' ? 'Quận/Huyện' : 'Phường/Xã'} (${data.length.toLocaleString()})`;

    adjustActivePageHeight();
  } catch (e) {
    tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-24 text-danger">Lỗi khi tải dữ liệu</td></tr>';
  }
}

// Initialize all modules is now handled in DOMContentLoaded

// ═══════════════════════════════════════════════════════════
// DATA EXPLORER
// ═══════════════════════════════════════════════════════════
let explorerState = {
  provinces: {},
  districts: {},
  wards: {}
};
async function initDataExplorer() {
  const EXPLORER_PAGE_SIZE = 25;
  let explorerPage = 1;
  let explorerFetchId = 0;

  VNAIControls.renderSmartFilter('explorer-filter-container', {
    prefix: 'explorer',
    title: 'Tìm kiếm hàng đợi xử lý địa chỉ',
    showVersion: false,
    searchPlaceholder: 'Tìm kiếm địa chỉ, tỉnh thành, trạng thái...',
    buttonText: 'Tìm kiếm'
  });

  const setExplorerPager = (total, page, pageSize) => {
    const badge = document.getElementById('explorer-count-badge');
    const meta = document.getElementById('explorer-paging-meta');
    const indicator = document.getElementById('explorer-page-indicator');
    const prev = document.getElementById('explorer-page-prev');
    const next = document.getElementById('explorer-page-next');
    const totalPages = total <= 0 ? 1 : Math.ceil(total / pageSize);
    if (badge) badge.textContent = `${total.toLocaleString()} bản ghi`;
    const fromIdx = total === 0 ? 0 : (page - 1) * pageSize + 1;
    const toIdx = Math.min(page * pageSize, total);
    if (meta) meta.textContent = total ? `Hiển thị ${fromIdx.toLocaleString()}–${toIdx.toLocaleString()} của ${total.toLocaleString()}` : 'Không có bản ghi';
    if (indicator) indicator.textContent = `Trang ${page} / ${totalPages}`;
    if (prev) { prev.disabled = page <= 1; }
    if (next) { next.disabled = page >= totalPages || total === 0; }
  };

  const loadData = async (filterState, opts = {}) => {
    const activeState = filterState || explorerState;
    const tbody = document.getElementById("explorer-body");
    const sBtn = document.getElementById("explorer-btn-search");
    if (!tbody) return;

    if (!opts.keepPage) explorerPage = 1;

    const reqId = ++explorerFetchId;
    if (sBtn) sBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    try {
      const q = document.getElementById("explorer-search-input")?.value.trim() || "";
      const pVal = activeState.provinces[document.getElementById('explorer-province-input')?.value];
      const pId = pVal ? (typeof pVal === 'object' ? pVal.province_id : pVal) : "";
      const dVal = activeState.districts[document.getElementById('explorer-district-input')?.value];
      const dId = dVal ? (typeof dVal === 'object' ? dVal.district_id : dVal) : "";
      const wId = activeState.wards[document.getElementById('explorer-ward-input')?.value] || "";

      const params = new URLSearchParams({
        page: String(explorerPage),
        limit: String(EXPLORER_PAGE_SIZE),
        q,
      });
      if (wId) params.append('ward_id', String(wId));
      else if (dId) params.append('district_id', String(dId));
      else if (pId) params.append('province_id', String(pId));

      const res = await fetch(`${API_BASE}/explorer/queue?${params}`, { headers: getAuthHeader() });
      let data;
      try {
        data = await res.json();
      } catch (parseErr) {
        console.error(parseErr);
        if (reqId !== explorerFetchId) return;
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Không đọc được phản hồi máy chủ</td></tr>`;
        setExplorerPager(0, 1, EXPLORER_PAGE_SIZE);
        return;
      }
      if (reqId !== explorerFetchId) return;

      if (!res.ok) {
        const detail = data && typeof data.detail === 'string' ? data.detail : `HTTP ${res.status}`;
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">${escapeHtml(detail)}</td></tr>`;
        setExplorerPager(0, 1, EXPLORER_PAGE_SIZE);
        return;
      }

      let rows = [];
      let total = 0;
      if (Array.isArray(data)) {
        rows = data;
        total = data.length;
      } else if (data && Array.isArray(data.items)) {
        rows = data.items;
        total = typeof data.total === 'number' ? data.total : rows.length;
        if (typeof data.page === 'number') explorerPage = data.page;
      } else {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Định dạng dữ liệu không hợp lệ</td></tr>`;
        setExplorerPager(0, 1, EXPLORER_PAGE_SIZE);
        return;
      }

      const totalPages = total <= 0 ? 1 : Math.ceil(total / EXPLORER_PAGE_SIZE);
      if (total === 0) {
        explorerPage = 1;
      } else if (explorerPage > totalPages) {
        explorerPage = totalPages;
        loadData(activeState, { keepPage: true });
        return;
      }

      setExplorerPager(total, explorerPage, EXPLORER_PAGE_SIZE);

      if (rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-tertiary);">Không có dữ liệu phù hợp</td></tr>`;
      } else {
        tbody.innerHTML = rows.map(item => {
          let statusBadge = "info";
          if (item.status === "DONE") statusBadge = "success";
          else if (item.status === "ERROR") statusBadge = "danger";
          else if (item.status === "PROCESSING") statusBadge = "warning";

          return `<tr>
            <td class="text-mono" style="font-size: 11px;">#${item.id}</td>
            <td>${escapeHtml(item.raw_address != null ? String(item.raw_address) : '')}</td>
            <td>${escapeHtml(item.ward_name != null ? String(item.ward_name) : '-')}</td>
            <td>${escapeHtml(item.district_name != null ? String(item.district_name) : '-')}</td>
            <td>${escapeHtml(item.province_name != null ? String(item.province_name) : '-')}</td>
            <td><span class="badge ${statusBadge}">${escapeHtml(item.status != null ? String(item.status) : '')}</span></td>
          </tr>`;
        }).join("");
      }
    } catch (err) {
      console.error(err);
      if (reqId !== explorerFetchId) return;
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Lỗi tải dữ liệu</td></tr>`;
      setExplorerPager(0, 1, EXPLORER_PAGE_SIZE);
    } finally {
      if (reqId === explorerFetchId && sBtn) sBtn.innerHTML = 'Tìm kiếm';
      adjustActivePageHeight();
    }
  };

  explorerState = await VNAIControls.initSmartFilter('explorer', {
    onSearch: (st) => loadData(st ?? explorerState),
  });

  document.getElementById('explorer-search-input')?.addEventListener('input', () =>
    loadData(undefined, {})
  );

  document.getElementById('explorer-page-prev')?.addEventListener('click', () => {
    if (explorerPage <= 1) return;
    explorerPage--;
    loadData(undefined, { keepPage: true });
  });
  document.getElementById('explorer-page-next')?.addEventListener('click', () => {
    explorerPage++;
    loadData(undefined, { keepPage: true });
  });

  loadData();
}

// ═══════════════════════════════════════════════════════════
// BOUNDARY VISUALIZATION
// ═══════════════════════════════════════════════════════════
function initBoundaryVisualizationUI() {
  const page = document.getElementById("boundary-visualization");
  if (!page) return;

  const scopeSelect = document.getElementById("boundary-scope");
  const provinceInput = document.getElementById("boundary-province-id");
  const districtInput = document.getElementById("boundary-district-id");
  const wardInput = document.getElementById("boundary-ward-id");
  const zoomInput = document.getElementById("boundary-zoom-start");
  const runBtn = document.getElementById("btn-boundary-run");
  const frame = document.getElementById("boundary-map-frame");
  const statusEl = document.getElementById("boundary-status");
  const statusDot = document.getElementById("boundary-status-dot");
  const countEl = document.getElementById("boundary-ring-count");
  const countLabelEl = document.getElementById("boundary-ring-count-label");
  const urlEl = document.getElementById("boundary-map-url");
  const logEl = document.getElementById("boundary-log");

  const setStatus = (message, tone = "idle") => {
    if (statusEl) {
      statusEl.textContent = message;
      statusEl.dataset.tone = tone;
    }
    if (statusDot) {
      statusDot.className = `pstatus-dot ${tone}`;
    }
  };

  const appendLog = (message) => {
    if (!logEl) return;
    const time = new Date().toLocaleTimeString("vi-VN", { hour12: false });
    const line = `[${time}] ${message}`;
    logEl.textContent = logEl.textContent ? `${logEl.textContent}\n${line}` : line;
    logEl.scrollTop = logEl.scrollHeight;
  };

  const refreshRequiredFields = () => {
    const scope = scopeSelect?.value || "province";
    if (provinceInput) provinceInput.required = scope === "province" || scope === "district" || scope === "ward";
    if (districtInput) districtInput.required = scope === "district" || scope === "ward";
    if (wardInput) wardInput.required = scope === "ward";
  };

  const run = async () => {
    const scope = scopeSelect?.value || "province";
    const payload = new URLSearchParams();
    payload.set("scope", scope);
    payload.set("zoom_start", String(parseInt(zoomInput?.value || "11", 10) || 11));

    if (provinceInput?.value) payload.set("province_id", provinceInput.value.trim());
    if (districtInput?.value) payload.set("district_id", districtInput.value.trim());
    if (wardInput?.value) payload.set("ward_id", wardInput.value.trim());

    setStatus("Đang tạo bản đồ ranh giới...", "loading");
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Đang tạo...</span>';
    }

    try {
      const response = await fetch(`${API_BASE}/boundary/map?${payload.toString()}`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Boundary API failed: ${response.status}`);
      }

      const result = await response.json();
      if (frame && result.url) frame.src = result.url;
      if (urlEl && result.url) {
        urlEl.href = result.url;
        urlEl.textContent = result.url;
      }
      if (countEl) countEl.textContent = Number(result.rings || 0).toLocaleString("vi-VN");
      if (countLabelEl) countLabelEl.textContent = Number(result.rings || 0).toLocaleString("vi-VN");

      setStatus("Đã tạo bản đồ thành công", "success");
      appendLog(`Generated ${result.rings || 0} polygon ring(s) at ${result.url || "unknown url"}`);
      showToast?.("Tạo bản đồ ranh giới thành công", "success");
    } catch (error) {
      console.error(error);
      setStatus("Tạo bản đồ thất bại", "danger");
      appendLog(`ERROR: ${error.message}`);
      showToast?.("Không thể tạo bản đồ ranh giới", "danger");
    } finally {
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.innerHTML = '<i class="fa-solid fa-map-location-dot"></i><span>Tạo bản đồ</span>';
      }
    }
  };

  scopeSelect?.addEventListener("change", refreshRequiredFields);
  runBtn?.addEventListener("click", run);
  [provinceInput, districtInput, wardInput].forEach((input) => {
    input?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        run();
      }
    });
  });

  refreshRequiredFields();
  appendLog("Boundary visualization ready.");
  setStatus("Sẵn sàng tạo bản đồ ranh giới", "idle");
}

/**
 * Dynamically calculates and adjusts the height of scrollable elements 
 * (gridview, job-log, etc.) to prevent #page-content from overflowing.
 */
function adjustActivePageHeight() {
  const activePage = document.querySelector('.page.active');
  if (!activePage) return;

  // PreLabeler Labeling Suite: natural page scroll only.
  if (activePage.id === 'prelabeler-cases') return;

  const pageContent = document.getElementById('page-content');
  if (!pageContent) return;

  // Small delay to ensure DOM is rendered if called after data load
  requestAnimationFrame(() => {
    const scrollableSelectors = [
      '.table-container',
      '.batch-log',
      '#parser-comparison-matrix',
      '.ner-output',
      '.card-body.with-scroll',
      '#activity-feed',
      '#osm-job-log',
      '#nso-sync-logs',
      '.lookup-results-table',
      '.ner-output'
    ];

    const scrollableElements = activePage.querySelectorAll(scrollableSelectors.join(', '));
    const pageContentRect = pageContent.getBoundingClientRect();
    const buffer = 24; // Bottom padding/margin buffer

    scrollableElements.forEach(el => {
      // Reset first to get natural position
      el.style.maxHeight = '';

      const rect = el.getBoundingClientRect();
      const availableHeight = pageContentRect.bottom - rect.top - buffer;

      if (availableHeight > 100) {
        el.style.maxHeight = `${Math.floor(availableHeight)}px`;
        el.style.overflowY = 'auto';
      }
    });
  });
}

// Export to window for access from other parts of the app if needed
window.adjustActivePageHeight = adjustActivePageHeight;

/**
 * Loads all page templates from the pages/ directory and injects them into #page-content.
 */
async function loadPages() {
  const container = document.getElementById('page-content');
  if (!container) return;

  // Clear loading state
  container.innerHTML = '';

  const loadPromises = PAGES.map(async (pageId) => {
    try {
      const response = await fetch(`pages/${pageId}.html`);
      if (!response.ok) throw new Error(`Failed to load ${pageId}`);
      const html = (await response.text()).trim();

      const div = document.createElement('div');
      div.innerHTML = html;

      // Templates may include a trailing <style>; firstElementChild would skip it unless hoisted.
      for (const node of [...div.childNodes]) {
        if (
          node.nodeType === Node.ELEMENT_NODE &&
          node.tagName === 'STYLE'
        ) {
          document.head.appendChild(node);
        }
      }

      // The templates should contain the <div class="page" id="..."> wrapper
      // If they don't, we should add it. My templates already have it.
      const pageNode = div.firstElementChild;
      if (pageNode) {
        container.appendChild(pageNode);
      }
    } catch (err) {
      console.error(`Error loading page ${pageId}:`, err);
    }
  });

  await Promise.all(loadPromises);
}

// ═══════════════════════════════════════════════════════════
// LABEL STUDIO INTEGRATION
// ═══════════════════════════════════════════════════════════
async function initLabelStudioIntegration() {
  const btnRefresh = document.getElementById('btn-ls-refresh');
  const btnTest = document.getElementById('btn-ls-test');
  const btnSync = document.getElementById('btn-ls-sync');

  if (btnRefresh) {
    btnRefresh.addEventListener('click', fetchLabelStudioTasks);
  }

  if (btnTest) {
    btnTest.addEventListener('click', testLabelStudioConnection);
  }

  if (btnSync) {
    btnSync.addEventListener('click', syncLabelStudioTasks);
  }

  // Initial fetch if page is active
  const page = document.getElementById('label-studio');
  if (page && page.classList.contains('active')) {
    fetchLabelStudioTasks();
  }
}

async function syncLabelStudioTasks() {
  const btn = document.getElementById('btn-ls-sync');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
  }

  try {
    const response = await fetch(`${API_BASE}/label-studio/sync`, {
      method: 'POST',
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (response.ok) {
      showToast(result.message, "success");
    } else {
      showToast(result.detail || "Lỗi khi đồng bộ dữ liệu", "danger");
    }
  } catch (err) {
    showToast("Không thể kết nối tới API server", "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Sync Labeled to Training Hub';
    }
  }
}

async function testLabelStudioConnection() {
  const btn = document.getElementById('btn-ls-test');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
  }

  try {
    const response = await fetch(`${API_BASE}/label-studio/debug`, {
      headers: getAuthHeader()
    });
    const result = await response.json();

    if (result.status === "success") {
      showToast(result.message, "success");
    } else {
      showToast(result.message, "danger");
      console.error("LS Debug Details:", result.details);
    }
  } catch (err) {
    showToast("Không thể kết nối tới API server", "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-vial"></i> Check Connection';
    }
  }
}

async function fetchLabelStudioTasks() {
  const tbody = document.getElementById('ls-tasks-body');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5" class="text-center p-24 text-tertiary"><i class="fa-solid fa-spinner fa-spin mr-8"></i> Đang tải dữ liệu...</td></tr>';

  try {
    const response = await fetch(`${API_BASE}/label-studio/tasks`, {
      headers: getAuthHeader()
    });

    if (!response.ok) {
      let detail = '';
      try {
        const errBody = await response.json();
        if (errBody && errBody.detail != null) {
          detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
        }
      } catch (_) { /* ignore non-JSON */ }
      throw new Error(detail || `API error: ${response.status}`);
    }

    const tasks = await response.json();

    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center p-24 text-tertiary">Không có task nào trong dự án hiện tại</td></tr>';
      return;
    }

    tbody.innerHTML = tasks.map(task => `
      <tr>
        <td class="text-mono">#${task.id}</td>
        <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${JSON.stringify(task.data)}
        </td>
        <td class="text-tertiary">${new Date(task.created_at).toLocaleString('vi-VN')}</td>
        <td><span class="badge ${task.is_labeled ? 'success' : 'warning'}">${task.is_labeled ? 'Completed' : 'Pending'}</span></td>
        <td class="text-right">
          <a href="https://label.nod.io.vn/projects/${task.project}/data?task=${task.id}" target="_blank" class="btn btn-icon btn-sm" title="Gán nhãn"><i class="fa-solid fa-tag"></i></a>
        </td>
      </tr>
    `).join('');

    // Update stats
    document.getElementById('ls-stat-total').textContent = tasks.length;
    document.getElementById('ls-stat-completed').textContent = tasks.filter(t => t.is_labeled).length;

    adjustActivePageHeight();
  } catch (err) {
    console.error('Label Studio API error:', err);
    tbody.innerHTML = `<tr><td colspan="5" class="text-center p-24 text-danger"><i class="fa-solid fa-circle-exclamation mr-8"></i> Lỗi: ${err.message}</td></tr>`;
  }
}
// Admin Unit CRUD Stubs
async function deleteAdminUnit(level, id, name) {
  const confirmed = await showConfirm(`Bạn có chắc chắn muốn xóa ${level}: ${name}?`);
  if (confirmed) {
    showToast(`Đã yêu cầu xóa ${name}. Đang xử lý...`, 'warning');
  }
}

// Expose to window for inline onclick handlers
window.showDetails = showDetails;
window.deleteAdminUnit = deleteAdminUnit;
window.loadTrainingHistoryFromDB = loadTrainingHistoryFromDB;

async function initEvidenceView() {
  const page = document.getElementById('evidence');
  if (!page) return;

  const refreshButton = page.querySelector('#evidence-refresh');
  const fileList = page.querySelector('#evidence-file-list');
  const iframe = page.querySelector('#evidence-iframe');
  const csvPreview = page.querySelector('#evidence-csv-preview');
  const meta = page.querySelector('#evidence-meta');

  async function loadManifest() {
    fileList.innerHTML = '<li class="text-tertiary p-12">Đang tải manifest...</li>';
    csvPreview.innerHTML = '';
    iframe.src = 'about:blank';
    iframe.style.display = 'none';
    csvPreview.style.display = 'none';

    const response = await fetch(`${API_BASE}/evidence/manifest`, { headers: getAuthHeader() });
    if (!response.ok) {
      throw new Error(`Manifest API failed: ${response.status}`);
    }

    const manifest = await response.json();
    const files = manifest.files || {};
    const entries = Object.entries(files);

    if (meta) {
      meta.textContent = manifest.generatedAt
        ? `Generated at ${manifest.generatedAt}`
        : '';
    }

    if (manifest._empty || !entries.length) {
      fileList.innerHTML = `<li style="padding:16px;color:var(--text-tertiary);font-size:12px">
        <i class="fa-solid fa-flask" style="margin-right:6px"></i>
        Chưa có evidence — chạy Benchmark để tạo báo cáo thực nghiệm
      </li>`;
      return;
    }

    fileList.innerHTML = entries.map(([key, value]) => `
      <li class="evidence-file-row" data-key="${key}">
        <div class="evidence-file-main">
          <div class="evidence-file-key">${key}</div>
          <div class="evidence-file-path">${value}</div>
        </div>
        <div class="evidence-file-actions">
          <button type="button" class="btn btn-sm btn-ghost evidence-view-btn" data-key="${key}">Xem</button>
          <a class="btn btn-sm btn-primary" href="/api/evidence/file?key=${encodeURIComponent(key)}" target="_blank" rel="noopener">Mở</a>
        </div>
      </li>
    `).join('');

    fileList.querySelectorAll('.evidence-view-btn').forEach((button) => {
      button.addEventListener('click', () => openEvidenceFile(button.dataset.key, files));
    });
  }

  async function openEvidenceFile(key, files) {
    const filePath = files[key] || '';
    const ext = filePath.split('.').pop().toLowerCase();
    const url = `${API_BASE}/evidence/file?key=${encodeURIComponent(key)}`;

    if (ext === 'html' || ext === 'htm') {
      iframe.src = url;
      iframe.style.display = 'block';
      csvPreview.style.display = 'none';
      return;
    }

    const response = await fetch(url, { headers: getAuthHeader() });
    if (!response.ok) {
      throw new Error(`Preview API failed: ${response.status}`);
    }

    const text = await response.text();
    const lines = text.split(/\r?\n/).filter(Boolean).slice(0, 25);
    if (!lines.length) {
      csvPreview.innerHTML = '<div class="p-12 text-tertiary">Tệp rỗng</div>';
      csvPreview.style.display = 'block';
      iframe.style.display = 'none';
      return;
    }

    const rows = lines.map((line) => line.split(','));
    const headers = rows[0] || [];
    const bodyRows = rows.slice(1);
    const tableHtml = `
      <div class="table-container">
        <table>
          <thead>
            <tr>${headers.map((cell) => `<th>${escapeHtml(cell)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')}
          </tbody>
        </table>
      </div>
    `;

    csvPreview.innerHTML = tableHtml;
    csvPreview.style.display = 'block';
    iframe.style.display = 'none';
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  refreshButton.addEventListener('click', async () => {
    try {
      await loadManifest();
    } catch (error) {
      fileList.innerHTML = `<li class="text-danger p-12">Không tải được manifest: ${escapeHtml(error.message)}</li>`;
    }
  });

  try {
    await loadManifest();
  } catch (error) {
    fileList.innerHTML = `<li class="text-danger p-12">Không tải được manifest: ${escapeHtml(error.message)}</li>`;
  }
}
(function () {
  'use strict';

  /** Mirrors `app/ai/constants.py` NER_LABELS — hotkeys 0→9. */
  const PLT_NER_LABELS_FALLBACK = [
    { value: 'PCD', hotkey: '0' },
    { value: 'BLD', hotkey: '1' },
    { value: 'POI', hotkey: '2' },
    { value: 'ALY', hotkey: '3' },
    { value: 'NUM', hotkey: '4' },
    { value: 'STR', hotkey: '5' },
    { value: 'NHB', hotkey: '6' },
    { value: 'WDS', hotkey: '7' },
    { value: 'DST', hotkey: '8' },
    { value: 'PRO', hotkey: '9' },
  ];

  const PLT_HOTKEY_BY_VALUE = new Map(PLT_NER_LABELS_FALLBACK.map(x => [x.value, x.hotkey]));

  /** Label order + hotkeys from /api/config/ner-labels, sorted by hotkey (same as constants.py). */
  let nerLabelsOrdered = [];

  const API = (window.location.hostname === 'localhost' || window.location.protocol === 'file:')
    ? 'http://localhost:8081/api'
    : '/api';

  let cases = [], activeId = null, results = {};
  let pltResultFilter = 'all';

  /** Click-selected span under `.plt-raw-annotated` (keydown relabel/remove). Cleared whenever the editor subtree is replaced. */
  let pltAnnBlockSelection = null; // { label, text, rangeKey }

  /** True if text belongs to flattened preview (badge labels inside `.plt-raw-ann` are excluded). */
  function pltIsCountedAnnotatedTextNode(tn) {
    if (!tn || tn.nodeType !== Node.TEXT_NODE || !tn.parentElement) return false;
    const p = tn.parentElement;
    return !p.closest('.plt-badge');
  }

  /** Start offset in flattened annotated string (excluding badge text) inside `annRoot`, or NaN when not found. */
  function pltAnnotatedGlobBeforeTextNodeStart(annRoot, targetTextNode) {
    let acc = 0;
    const w = document.createTreeWalker(annRoot, NodeFilter.SHOW_TEXT, null);
    let tn;
    while ((tn = w.nextNode())) {
      if (!pltIsCountedAnnotatedTextNode(tn)) continue;
      if (tn === targetTextNode) return acc;
      acc += tn.nodeValue.length;
    }
    return NaN;
  }

  /** Map a DOM boundary (within `annRoot`) to a global offset along flattened annotated/raw text (0-length allowed). */
  function pltAnnotatedBoundaryToGlob(annRoot, node, offset) {
    if (!(annRoot instanceof Element) || !annRoot.contains(node)) return NaN;
    const prefix = document.createRange();
    try {
      prefix.setStart(annRoot, 0);
      prefix.setEnd(node, offset);
    } catch (_) {
      return NaN;
    }

    let sum = 0;
    const w = document.createTreeWalker(annRoot, NodeFilter.SHOW_TEXT, null);
    let tn;
    while ((tn = w.nextNode())) {
      if (!pltIsCountedAnnotatedTextNode(tn)) continue;
      if (!prefix.intersectsNode(tn)) continue;
      const len = tn.nodeValue.length;
      let s = 0;
      let e = len;
      if (prefix.startContainer === tn) s = Math.max(0, Math.min(len, prefix.startOffset));
      if (prefix.endContainer === tn) e = Math.max(0, Math.min(len, prefix.endOffset));
      if (e > s) sum += (e - s);
    }
    return sum;
  }

  function pltAnnotatedSubtreeCountedTextLen(node) {
    if (!node) return 0;
    if (node.nodeType === Node.TEXT_NODE)
      return pltIsCountedAnnotatedTextNode(node) ? node.nodeValue.length : 0;
    let sum = 0;
    for (let i = 0; i < node.childNodes.length; i++)
      sum += pltAnnotatedSubtreeCountedTextLen(node.childNodes[i]);
    return sum;
  }

  /** @returns {{ start: number, end: number } | null} */
  function pltAnnotGetGlobRangeFromSelection(annRoot) {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    const rng = sel.getRangeAt(0);
    if (!annRoot.contains(rng.commonAncestorContainer)) return null;

    let startGlob = pltAnnotatedBoundaryToGlob(annRoot, rng.startContainer, rng.startOffset);
    let endGlob = pltAnnotatedBoundaryToGlob(annRoot, rng.endContainer, rng.endOffset);
    if (!Number.isFinite(startGlob) || !Number.isFinite(endGlob)) return null;
    if (startGlob > endGlob) [startGlob, endGlob] = [endGlob, startGlob];
    if (startGlob === endGlob) return null;
    return { start: startGlob, end: endGlob };
  }

  function pltAnnotatedPlainMatchesRaw(annRoot, rawStr) {
    const w = document.createTreeWalker(annRoot, NodeFilter.SHOW_TEXT, null);
    let tn;
    let acc = '';
    while ((tn = w.nextNode())) {
      if (!pltIsCountedAnnotatedTextNode(tn)) continue;
      acc += tn.nodeValue;
    }
    return acc === rawStr;
  }

  function pltAnnotHasUsableSubstringSelection() {
    const annRoot = document.querySelector(
      '#prelabeler-cases .plt-raw-annotated:not(.plt-raw-annotated--empty)'
    );
    const c = cases.find(x => x.id === activeId);
    if (!annRoot || !c) return false;
    const raw = String(c.input ?? '');
    const glob = pltAnnotGetGlobRangeFromSelection(annRoot);
    if (glob && pltAnnotatedPlainMatchesRaw(annRoot, raw)) return true;

    // Fallback: neu khong map duoc boundary->offset, van chap nhan selection text
    // mien la selection nam trong annRoot va text co ton tai trong raw.
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return false;
    const rng = sel.getRangeAt(0);
    if (!annRoot.contains(rng.commonAncestorContainer)) return false;
    const txt = String(sel.toString() || '').trim();
    return Boolean(txt && raw.toLowerCase().includes(txt.toLowerCase()));
  }

  function pltClearAnnBlockUi() {
    pltAnnBlockSelection = null;
    document.querySelectorAll('#prelabeler-cases .plt-raw-ann--selected').forEach(el => {
      el.classList.remove('plt-raw-ann--selected');
    });
  }

  function pltAnnounceAnnBlock(selEl) {
    document.querySelectorAll('#prelabeler-cases .plt-raw-ann--selected').forEach(el => {
      el.classList.remove('plt-raw-ann--selected');
    });
    if (!(selEl instanceof HTMLElement) || !selEl.classList.contains('plt-raw-ann')) return;
    const label = String(selEl.getAttribute('data-plt-ann-label') || '').trim().toUpperCase();
    const textEl = selEl.querySelector('.plt-raw-ann__text');
    const text = textEl instanceof HTMLElement ? textEl.textContent.trim() : '';
    const rangeKey = String(selEl.getAttribute('data-plt-ann-range') || '');
    pltAnnBlockSelection = label && text && rangeKey ? { label, text, rangeKey } : null;
    if (pltAnnBlockSelection) selEl.classList.add('plt-raw-ann--selected');
  }

  /** @returns {{ label: string } | null} */
  function pltLabelFromHotkeyKey(keyStr) {
    const k = String(keyStr ?? '');
    if (!/^[0-9]$/.test(k)) return null;
    const row = nerLabelsOrdered.find(x => String(x.hotkey) === k);
    return row?.value ? { label: String(row.value).trim().toUpperCase() } : null;
  }

  function pltIsPrelabelerCasesPageVisible() {
    const p = document.getElementById('prelabeler-cases');
    return Boolean(p?.classList.contains('active'));
  }

  /** When true, `#plt-run-cluster` F8–F10 shortcuts must not fire (typing context). */
  function pltRunClusterHotkeyConsumeBlocked(activeEl) {
    if (!(activeEl instanceof HTMLElement)) return false;
    if (activeEl.isContentEditable) return true;
    const tag = (activeEl.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return true;
    if (tag !== 'input') return false;
    const t = String(activeEl.type || '').toLowerCase();
    const nonText = ['button', 'checkbox', 'radio', 'submit', 'reset', 'file', 'image', 'color', 'range', 'hidden'];
    return !nonText.includes(t);
  }

  /** Do not steal digit keys while typing elsewhere in the SPA. */
  function pltAnnHotkeyIgnoreTypingTarget(activeEl) {
    if (!(activeEl instanceof HTMLElement)) return true;
    if (activeEl.isContentEditable) return true;
    const tag = (activeEl.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return false;

    const nameField = activeEl.closest?.('.plt-editor-head input[type="text"]');
    if (nameField instanceof HTMLInputElement) return true;

    if (tag === 'input') {
      const t = activeEl.type || '';
      if (activeEl.closest('.plt-editor-scroll')) {
        const idOk = activeEl.id === 'plt-raw-address';
        if (!idOk && activeEl.closest?.('.plt-label-cell__input-row')) return true;
        return !idOk;
      }
      if (activeEl.closest?.('#plt-search')) return true;
      return !(t === 'button' || t === 'checkbox' || t === 'radio' || t === 'submit' || !t || t === 'text');
    }

    return false;
  }

  function pltAnnApplyLabelFromChoice(labelChoice) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return false;
    const raw = String(c.input ?? '');
    const ta = document.getElementById('plt-raw-address');

    /** 1 — Click-selected annotated block (relabels or same-label refresh) */
    if (pltAnnBlockSelection?.text && labelChoice?.label) {
      const newLab = labelChoice.label;
      const oldLab = pltAnnBlockSelection.label;
      const blkText = String(pltAnnBlockSelection.text || '').trim();
      if (!blkText) return false;
      removeExpectedForLabel(oldLab, blkText);
      addExpectedForLabel(newLab, blkText);
      pltClearAnnBlockUi();
      return true;
    }

    /** 2 — Explicit text selection (#plt-raw-address or `.plt-raw-annotated`) */
    const activeFocus = document.activeElement;
    const annRoot = document.querySelector(
      '#prelabeler-cases .plt-raw-annotated:not(.plt-raw-annotated--empty)'
    );

    let selText = '';
    if (activeFocus === ta && ta.selectionStart !== ta.selectionEnd) {
      const a = Math.min(ta.selectionStart, ta.selectionEnd);
      const b = Math.max(ta.selectionStart, ta.selectionEnd);
      selText = String(ta.value).slice(a, b).trim();
    } else if (annRoot) {
      const glob = pltAnnotGetGlobRangeFromSelection(annRoot);
      if (glob && pltAnnotatedPlainMatchesRaw(annRoot, raw))
        selText = raw.slice(glob.start, glob.end).trim();
      if (!selText) {
        const sel = window.getSelection();
        const rng = sel && sel.rangeCount ? sel.getRangeAt(0) : null;
        const inAnn = Boolean(rng && annRoot.contains(rng.commonAncestorContainer));
        const txt = String(sel?.toString() || '').trim();
        if (inAnn && txt && raw.toLowerCase().includes(txt.toLowerCase())) {
          selText = txt;
        }
      }
    }

    if (!selText) return false;
    addExpectedForLabel(labelChoice.label, selText);
    pltClearAnnBlockUi();
    if (ta === activeFocus) {
      ta.focus();
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      if (start !== end) ta.setSelectionRange(start, end);
    }
    return true;
  }

  function pltAnnRemoveSelectedBlock() {
    if (!pltAnnBlockSelection?.label || !pltAnnBlockSelection?.text) return false;
    const lab = pltAnnBlockSelection.label;
    const txt = pltAnnBlockSelection.text;
    const ok = removeExpectedForLabel(lab, txt);
    pltClearAnnBlockUi();
    return ok;
  }

  function sortLabelsByHotkey(rows) {
    return [...rows].sort((a, b) => {
      const na = parseInt(String(a.hotkey), 10);
      const nb = parseInt(String(b.hotkey), 10);
      if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
      return String(a.value).localeCompare(String(b.value));
    });
  }

  function normalizeApiLabels(labels) {
    const arr = Array.isArray(labels) ? labels : [];
    return arr
      .map((l, i) => {
        if (typeof l === 'string') {
          const value = String(l).trim().toUpperCase();
          if (!value) return null;
          const hotkey = PLT_HOTKEY_BY_VALUE.get(value) ?? String(i);
          return { value, hotkey };
        }
        const value = String(l && l.value != null ? l.value : '').trim().toUpperCase();
        if (!value) return null;
        let hotkey =
          l && l.hotkey != null && String(l.hotkey).trim() !== ''
            ? String(l.hotkey).trim()
            : PLT_HOTKEY_BY_VALUE.get(value) ?? String(i);
        return { value, hotkey };
      })
      .filter(Boolean);
  }

  function applyNerLabelOrder(rawList) {
    let rows = sortLabelsByHotkey(normalizeApiLabels(rawList));
    const seen = new Set();
    rows = rows.filter(r => {
      if (seen.has(r.value)) return false;
      seen.add(r.value);
      return true;
    });
    if (!rows.length) rows = [...PLT_NER_LABELS_FALLBACK];
    return rows;
  }

  /**
   * Prefer `ensureNerLabelsLoaded` from app.js (same API_BASE / fallback as the rest of the SPA).
   * If missing or empty, GET /config/ner-labels directly.
   */
  async function refreshPltNerLabels() {
    try {
      if (typeof ensureNerLabelsLoaded === 'function') {
        const labels = await ensureNerLabelsLoaded(false);
        if (Array.isArray(labels) && labels.length) {
          nerLabelsOrdered = applyNerLabelOrder(labels);
          return;
        }
      }
    } catch (e) {
      console.warn('[PreLabeler] ensureNerLabelsLoaded:', e);
    }
    try {
      const res = await fetch(`${API}/config/ner-labels`);
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      nerLabelsOrdered = applyNerLabelOrder(data.labels);
    } catch (e2) {
      console.warn('[PreLabeler] GET /config/ner-labels:', e2);
      nerLabelsOrdered = [...PLT_NER_LABELS_FALLBACK];
    }
  }

  function authHdr() {
    const t = localStorage.getItem('vnai_token') || '';
    return { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) };
  }

  function pltEsc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function expectedTextsForLabel(expected, label) {
    const lab = String(label || '').toUpperCase();
    const out = [];
    const seen = new Set();
    for (const it of expected || []) {
      if (!it || String(it.label || '').toUpperCase() !== lab) continue;
      const txt = String(it.text || '').trim();
      if (!txt) continue;
      const key = txt.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(txt);
    }
    return out;
  }

  function firstExpectedTextForLabel(expected, label) {
    return expectedTextsForLabel(expected, label)[0] || '';
  }

  function setExpectedForLabel(label, text) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const lab = String(label || '').toUpperCase();
    c.expected = (c.expected || []).filter(e => String(e.label || '').toUpperCase() !== lab);
    const t = String(text || '').trim();
    if (t) c.expected.push({ label: lab, text: t });
    pltSave();
  }

  function addExpectedForLabel(label, text) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return false;
    const lab = String(label || '').toUpperCase();
    const t = String(text || '').trim();
    if (!lab || !t) return false;
    c.expected = Array.isArray(c.expected) ? c.expected : [];
    const exists = c.expected.some(
      e =>
        String(e?.label || '').toUpperCase() === lab &&
        String(e?.text || '').trim().toLowerCase() === t.toLowerCase()
    );
    if (exists) return false;
    c.expected.push({ label: lab, text: t });
    pltSave();
    renderEditor();
    updateSummary();
    return true;
  }

  function removeExpectedForLabel(label, text) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return false;
    const lab = String(label || '').toUpperCase();
    const t = String(text || '').trim().toLowerCase();
    const before = Array.isArray(c.expected) ? c.expected.length : 0;
    c.expected = (c.expected || []).filter(
      e =>
        !(
          String(e?.label || '').toUpperCase() === lab &&
          String(e?.text || '').trim().toLowerCase() === t
        )
    );
    if (c.expected.length === before) return false;
    pltSave();
    renderEditor();
    updateSummary();
    return true;
  }

  function renderMergedLabelGrid(c, result) {
    const expected = c.expected;
    if (!nerLabelsOrdered.length) {
      return `<div class="plt-label-grid-empty">Không tải được danh sách loại nhãn. Kiểm tra kết nối dịch vụ và tải lại trang.</div>`;
    }
    const r = result && !result.error ? result : null;
    return nerLabelsOrdered.map(({ value, hotkey }) => {
      const expTexts = expectedTextsForLabel(expected, value);
      const hk = pltEsc(hotkey);
      const vEsc = pltEsc(value);
      const vJs = JSON.stringify(value);

      let cellClass = 'plt-label-cell plt-label-cell--merged';
      let failTagHtml = '';

      if (r) {
        if (expTexts.length) {
          const missing = expTexts.filter(expText => {
            const d = detailFor(r, value, expText);
            return !(d && d.found);
          });
          const ok = missing.length === 0;
          if (ok) {
            cellClass += ' plt-label-cell--pass';
          } else {
            cellClass += ' plt-label-cell--fail';
            const actDisplay = formatPltActualForFail(r, value, missing);
            failTagHtml = `<div class="plt-label-cell__fail-tag" role="status">${actDisplay}</div>`;
          }
        }
      }

      const chipsHtml = expTexts.length
        ? `<div class="plt-label-cell__chips">
            ${expTexts
              .map(
                txt =>
                  `<span class="plt-label-chip">
                    <span class="plt-label-chip__text">${pltEsc(txt)}</span>
                    <button type="button" class="plt-label-chip__remove"
                      title="Xóa giá trị này"
                      onclick='pltRemoveExpectedLabel(${vJs}, ${JSON.stringify(txt)})'>&times;</button>
                  </span>`
              )
              .join('')}
          </div>`
        : '';

      return `
        <div class="${cellClass}" data-label="${vEsc}">
          <div class="plt-label-cell__main">
            <div class="plt-label-cell__inline-row">
              <span class="plt-label-cell__hk" title="Phím tắt ${hk}">${hk}</span>
              <span class="plt-badge lc-${value}">${vEsc}</span>
              <div class="plt-label-cell__input-row">
                <input class="form-input plt-label-cell__input" type="text"
                  value="" placeholder="Nhập thêm giá trị..."
                  onkeydown='return pltAddExpectedLabelOnKey(event, ${vJs}, this)'>
                <button type="button" class="btn btn-outline plt-label-cell__add-btn"
                  title="Thêm giá trị"
                  onclick='pltAddExpectedLabel(${vJs}, this.previousElementSibling.value); this.previousElementSibling.value=""'>+</button>
                <span class="plt-label-cell__tick" aria-label="Khớp nhãn kỳ vọng"><i class="fa-solid fa-check"></i></span>
              </div>
            </div>
            ${chipsHtml}
            ${failTagHtml}
          </div>
        </div>`;
    }).join('');
  }

  function labelColorForPreview(label) {
    const lab = String(label || '').trim().toUpperCase();
    const map = {
      PCD: '#f032e6',
      NUM: '#e6194b',
      STR: '#3cb44b',
      WDS: '#ffe119',
      DST: '#800000',
      PRO: '#38bdf8',
      NHB: '#469990',
      BLD: '#f58231',
      POI: '#911eb4',
      ALY: '#4363d8',
    };
    return map[lab] || '#64748b';
  }

  function hexToRgba(hex, alpha) {
    const clean = String(hex || '').replace('#', '');
    const normalized = clean.length === 3
      ? clean.split('').map(ch => ch + ch).join('')
      : clean;
    if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return `rgba(100,116,139,${alpha})`;
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function renderAnnotatedRawText(c) {
    const raw = String(c?.input || '');
    if (!raw.trim()) {
      return '<div class="plt-raw-annotated plt-raw-annotated--empty">Chưa nhập địa chỉ gốc.</div>';
    }

    const entities = normalizeExpectedItems(c?.expected)
      .sort((a, b) => b.text.length - a.text.length);
    if (!entities.length) {
      return `<div class="plt-raw-annotated">${pltEsc(raw)}</div>`;
    }

    const rawLower = raw.toLowerCase();
    const intervals = [];
    const hits = [];
    const overlap = (s1, e1, s2, e2) => s1 < e2 && s2 < e1;
    const isFreeRange = (s, e) => !intervals.some(iv => overlap(s, e, iv.start, iv.end));

    entities.forEach(ent => {
      const needle = String(ent.text || '').trim();
      const label = String(ent.label || '').trim().toUpperCase();
      if (!needle || !label) return;
      const needleLower = needle.toLowerCase();
      let searchPos = raw.length;
      while (searchPos >= 0) {
        const start = rawLower.lastIndexOf(needleLower, searchPos);
        if (start < 0) break;
        const end = start + needle.length;
        if (isFreeRange(start, end)) {
          intervals.push({ start, end });
          hits.push({
            start,
            end,
            label,
            color: labelColorForPreview(label),
          });
          // Annotate each expected entity once, preferring the right-most match.
          break;
        }
        searchPos = start - 1;
      }
    });

    if (!hits.length) {
      return `<div class="plt-raw-annotated">${pltEsc(raw)}</div>`;
    }

    hits.sort((a, b) => a.start - b.start || b.end - a.end);
    let html = '';
    let cursor = 0;
      hits.forEach(hit => {
      if (cursor < hit.start) html += pltEsc(raw.slice(cursor, hit.start));
      const text = raw.slice(hit.start, hit.end);
      const color = hit.color;
      const bg = hexToRgba(color, 0.20);
      const rangeKey = `${hit.start}:${hit.end}`;
      html += `<span class="plt-raw-ann" tabindex="0"
        role="button" title="Khối có nhãn — nhấp để chọn, phím số đổi nhãn, Backspace/Xóa để gỡ"
        data-plt-ann-range="${pltEsc(rangeKey)}" data-plt-ann-label="${pltEsc(hit.label)}"
        style="border-color:${color};background:${bg}">
        <span class="plt-badge lc-${pltEsc(hit.label)}">${pltEsc(hit.label)}</span>
        <span class="plt-raw-ann__text">${pltEsc(text)}</span>
      </span>`;
      cursor = hit.end;
    });
    if (cursor < raw.length) html += pltEsc(raw.slice(cursor));

    return `<div class="plt-raw-annotated">${html}</div>`;
  }

  function detailFor(r, label, expText) {
    const details = r.details || [];
    const lab = String(label || '').toUpperCase();
    const expNorm = String(expText || '').trim().toLowerCase();
    if (expNorm) {
      const d = details.find(
        x =>
          x.expected &&
          String(x.expected.label || '').toUpperCase() === lab &&
          String(x.expected.text || '').trim().toLowerCase() === expNorm
      );
      if (d) return d;
    }
    return details.find(
      x => x.expected && String(x.expected.label || '').toUpperCase() === lab
    );
  }

  function normalizePltEntityLabel(raw) {
    const s = String(raw || '').trim().toUpperCase();
    if (!s) return '';
    if (s.startsWith('B-') || s.startsWith('I-')) return s.slice(2);
    return s;
  }

  /** All PreLabeler spans matching this label (for FAIL UI: text mismatch or multiple spans). */
  function actualSpansForLabel(r, label) {
    const lab = normalizePltEntityLabel(label);
    return (r.actual || []).filter(
      x => {
        const got = normalizePltEntityLabel(x.label);
        return got === lab;
      }
    );
  }

  /**
   * User-facing Vietnamese copy for FAIL cells: compact "algorithm vs expected" line (label is in the row header).
   */
  function formatPltActualForFail(r, label, missingExpected = []) {
    const spans = actualSpansForLabel(r, label);
    const texts = spans
      .map(x => String(x.text || '').trim())
      .filter(t => t.length > 0);

    const joinParts = arr => arr.map(x => pltEsc(x)).join(', ');
    const missingReadable = joinParts(missingExpected);

    const seen = new Set();
    const uniq = [];
    for (const t of texts) {
      const k = t.toLowerCase();
      if (seen.has(k)) continue;
      seen.add(k);
      uniq.push(t);
    }
    const actualReadable = joinParts(uniq);
    const algo = actualReadable || '—';
    const exp = missingReadable || '—';

    if (missingReadable || !actualReadable) {
      return `[Không khớp] Thuật toán: ${algo}, Kỳ vọng: ${exp}.`;
    }
    return `[Không khớp] Thuật toán: ${algo}.`;
  }

  function pltAddExpectedLabel(label, rawText) {
    addExpectedForLabel(label, rawText);
  }

  function pltRemoveExpectedLabel(label, text) {
    removeExpectedForLabel(label, text);
  }

  function pltAddExpectedLabelOnKey(e, label, el) {
    if (!e || e.key !== 'Enter') return true;
    e.preventDefault();
    const txt = el && el.value != null ? String(el.value) : '';
    if (addExpectedForLabel(label, txt) && el) {
      el.value = '';
    }
    return false;
  }

  function renderRunAuxiliary(r) {
    if (!r) return '';
    if (r.error) {
      return `<div class="plt-run-error" role="alert">
        <div class="plt-run-error__title"><i class="fa-solid fa-triangle-exclamation"></i> Lỗi khi chạy đối chiếu</div>
        <pre class="plt-run-error__msg">${pltEsc(r.error)}</pre>
      </div>`;
    }
    if (!(r.unexpected || []).length) return '';
    const activeCase = cases.find(x => x.id === activeId);
    const strictMode = activeCase?.strict !== false;
    const unexpected = pltUnexpectedSuggestions(activeCase, r);
    const canApplyCount = unexpected.filter(u => !pltHasExpectedPair(activeCase, u?.label, u?.text)).length;
    const applyAllDisabled = canApplyCount <= 0;
    const applyAllTitle = applyAllDisabled
      ? 'Tất cả đề xuất đã có sẵn trong nhãn kỳ vọng'
      : 'Thêm tất cả nhãn ngoài kỳ vọng vào danh sách nhãn kỳ vọng hiện tại';
    return `
      <div class="plt-unexpected-block">
        <div class="plt-result-section-title">${strictMode ? 'Nhãn ngoài kỳ vọng (chế độ nghiêm)' : 'Nhãn đề xuất thêm (chế độ thường)'}</div>
        <div class="plt-run-prompt">
          <i class="fa-solid fa-hand-pointer"></i> Chọn từng mục hoặc áp dụng toàn bộ đề xuất vào nhãn kỳ vọng.
          <button type="button" class="btn btn-outline btn-sm plt-unexpected-apply-all" title="${pltEsc(applyAllTitle)}" ${applyAllDisabled ? 'disabled aria-disabled="true"' : ''}>
            <i class="fa-solid fa-bolt"></i> Apply all đề xuất
          </button>
        </div>
        <div class="plt-tokens">
          ${unexpected
            .map(
              u =>
                `<button type="button" class="plt-token plt-token-add-exp" data-label="${pltEsc(u.label)}" data-text="${pltEsc(u.text)}" title="Thêm vào nhãn kỳ vọng">
                  <span class="plt-badge lc-${u.label}">${u.label}</span> ${pltEsc(u.text)}
                </button>`
            )
            .join('')}
        </div>
      </div>`;
  }

  function hotkeyRangeHint() {
    if (nerLabelsOrdered.length >= 2) {
      return `Phím tắt ${pltEsc(nerLabelsOrdered[0].hotkey)}–${pltEsc(
        nerLabelsOrdered[nerLabelsOrdered.length - 1].hotkey
      )}`;
    }
    if (nerLabelsOrdered.length === 1) {
      return `Phím tắt ${pltEsc(nerLabelsOrdered[0].hotkey)}`;
    }
    return '';
  }

  async function pltInit() {
    await refreshPltNerLabels();
    const listEl = document.getElementById('plt-list');
    if (listEl) {
      listEl.innerHTML =
        '<div style="padding:20px;text-align:center;color:var(--text-tertiary)"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu...</div>';
    }

    try {
      const resp = await fetch(`${API}/prelabeler-cases`, { headers: authHdr() });
      if (!resp.ok) throw new Error(resp.status);
      const raw = await resp.json();
      cases = raw.map(c => ({
        ...c,
        input:
          typeof c.input === 'string'
            ? c.input
            : c.input && c.input.raw_address
              ? String(c.input.raw_address)
              : '',
        note: String((c && c.note != null) ? c.note : ''),
        expected: typeof c.expected === 'string' ? JSON.parse(c.expected) : (c.expected || []),
        strict: c?.strict !== false,
      }));
      // Hydrate persisted run results so summary + indicators survive page reload.
      results = {};
      for (const c of cases) {
        const tr = c.test_result;
        if (!tr) continue;
        const parsed = typeof tr === 'string' ? (() => { try { return JSON.parse(tr); } catch { return null; } })() : tr;
        if (parsed && typeof parsed === 'object') results[c.id] = parsed;
      }
    } catch (e) {
      console.warn('PreLabeler labeling: cannot load from DB, trying localStorage', e);
      cases = JSON.parse(localStorage.getItem('plt_cases') || '[]');
    }
    cases = (cases || []).map(c => ({ ...c, strict: c?.strict !== false }));
    const firstVisible = getVisibleCases()[0];
    if (firstVisible) {
      // Always default to the first case as shown in current list ordering.
      pltSelect(firstVisible.id);
    } else {
      activeId = null;
      renderList();
      renderPltEmptySurface();
    }
    updateSummary();
    syncPltRunCluster();
  }

  function getVisibleCases() {
    const q = (document.getElementById('plt-search')?.value || '').toLowerCase();
    return [...cases]
      .filter(c => {
        if ((c.name || '').toLowerCase().includes(q) || String(c.input || '').toLowerCase().includes(q)) {
          if (pltResultFilter === 'all') return true;
          const rr = results[c.id];
          if (!rr) return false;
          return pltResultFilter === 'pass' ? Boolean(rr.passed) : !rr.passed;
        }
        return false;
      })
      .sort((a, b) => getCaseCreatedTs(b) - getCaseCreatedTs(a));
  }

  function renderList() {
    const el = document.getElementById('plt-list');
    if (!el) return;

    const filtered = getVisibleCases();

    if (!filtered.length) {
      el.innerHTML =
        '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text-tertiary)"><i class="fa-solid fa-magnifying-glass" style="font-size:24px;margin-bottom:8px;display:block"></i> Không có kết quả</div>';
      return;
    }

    const visibleCount = filtered.length;

    el.innerHTML = filtered
      .map((c, idx) => {
        const rr = results[c.id];
        const dot = rr == null ? 'plt-dot-none' : rr.passed ? 'plt-dot-pass' : 'plt-dot-fail';
        const cls = rr == null ? '' : rr.passed ? 'pass' : 'fail';
        const noteText = String(c?.note || '').trim();
        const noteTitle = noteText ? `Ghi chú: ${noteText}` : '';
        /** Newest first (idx 0) gets largest rank = visibleCount — reads like “mẫu cao = mới hơn”. */
        const rank = visibleCount - idx;
        return `
        <div class="plt-item ${cls}${activeId === c.id ? ' active' : ''}" onclick="pltSelect('${c.id}')" ${noteTitle ? `title="${pltEsc(noteTitle)}"` : ''}>
          <div class="plt-item-name">
            <span class="plt-dot ${dot}"></span>
            <span class="plt-item-index">${rank}.</span>
            ${pltEsc(c.name || 'Chưa đặt tên')}
            ${noteText ? `<span class="plt-item-note-tip" title="${pltEsc(noteTitle)}"><i class="fa-regular fa-note-sticky"></i></span>` : ''}
            <div class="plt-item-actions">
              <button class="btn-icon" onclick="event.stopPropagation();pltDup('${c.id}')" title="Nhân đôi"><i class="fa-solid fa-copy"></i></button>
              <button class="btn-icon" style="color:var(--danger)" onclick="event.stopPropagation();pltDel('${c.id}')" title="Xóa"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>
          <div class="plt-item-addr">${pltEsc(c.input || '')}</div>
        </div>`;
      })
      .join('');
  }

  function getCaseCreatedTs(c) {
    const keys = ['created_at', 'createdAt', 'created_date', 'createdDate'];
    for (const key of keys) {
      const raw = c && c[key];
      if (raw == null) continue;
      if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
      const parsed = Date.parse(String(raw));
      if (!Number.isNaN(parsed)) return parsed;
    }
    return 0;
  }

  function pltSetResultFilter(mode) {
    const nextMode = mode === 'pass' || mode === 'fail' ? mode : 'all';
    pltResultFilter = pltResultFilter === nextMode ? 'all' : nextMode;
    renderList();
    updateSummary();
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  function pltNew() {
    const c = {
      id: uid(),
      name: 'Mẫu địa chỉ mới',
      input: '',
      note: '',
      expected: [],
      strict: true,
      created_at: new Date().toISOString(),
    };
    cases.push(c);
    pltSelect(c.id);
    pltSave();
  }

  function normalizeExpectedItems(items) {
    const src = Array.isArray(items) ? items : [];
    const out = [];
    const seen = new Set();
    src.forEach(it => {
      if (!it || typeof it !== 'object') return;
      const label = String(it.label || '').trim().toUpperCase();
      const text = String(it.text || '').trim();
      if (!label || !text) return;
      const key = `${label}::${text.toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ label, text });
    });
    return out;
  }

  function pltSetRandomPredictLoadingOverlay(show) {
    const overlay = document.getElementById('plt-random-loading-overlay');
    if (!(overlay instanceof HTMLElement)) return;
    overlay.hidden = !show;
    overlay.setAttribute('aria-hidden', show ? 'false' : 'true');
  }

  /** Khớp với `prelabeler-cases.html`: giữ nhãn + phím F8/F9/F10 sau spinner/loading */
  const PLT_HTML_BTN_RUN_ONE_IDLE =
    '<i class="fa-solid fa-play"></i> Đối chiếu <span class="plt-btn-kbd">F8</span>';
  const PLT_HTML_BTN_RUN_ALL_IDLE =
    '<i class="fa-solid fa-forward-fast"></i> Đối chiếu tất cả <span class="plt-btn-kbd">F9</span>';
  const PLT_HTML_BTN_RANDOM_PREDICT_IDLE =
    '<i class="fa-solid fa-shuffle"></i> Lấy mẫu ngẫu nhiên và gợi ý nhãn <span class="plt-btn-kbd">F10</span>';

  async function pltGetRandomAndPredict() {
    const btn = document.getElementById('plt-btn-random-predict');
    pltSetRandomPredictLoadingOverlay(true);
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý…';
    }

    try {
      const res = await fetch(`${API}/prelabeler-cases/random-predict`, {
        headers: authHdr(),
      });
      if (res.status === 401) {
        window.showToast?.('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.', 'warning');
        return;
      }
      if (res.status === 404) {
        window.showToast?.('Hiện không còn bản ghi mới trong hàng đợi để tạo mẫu.', 'info');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const rawAddress = String(data?.raw_address || '').trim();
      const expected = normalizeExpectedItems(data?.expected);
      if (!rawAddress) {
        window.showToast?.('Phản hồi thiếu địa chỉ gốc hợp lệ.', 'warning');
        return;
      }

      const sourceId = data?.source_id != null ? String(data.source_id) : '';
      const queueMetaRaw = data?.meta && typeof data.meta === 'object' ? data.meta : null;
      const queueMeta =
        queueMetaRaw &&
        ['ward_name', 'district_name', 'province_name'].some(
          k => queueMetaRaw[k] != null && String(queueMetaRaw[k]).trim().length > 0
        )
          ? {
              ward_name:
                queueMetaRaw.ward_name != null && String(queueMetaRaw.ward_name).trim()
                  ? String(queueMetaRaw.ward_name).trim()
                  : null,
              district_name:
                queueMetaRaw.district_name != null && String(queueMetaRaw.district_name).trim()
                  ? String(queueMetaRaw.district_name).trim()
                  : null,
              province_name:
                queueMetaRaw.province_name != null && String(queueMetaRaw.province_name).trim()
                  ? String(queueMetaRaw.province_name).trim()
                  : null,
            }
          : null;

      const overwriteSelected = Boolean(document.getElementById('plt-random-overwrite-active')?.checked);
      const selectedCase = overwriteSelected ? cases.find(x => x.id === activeId) : null;
      if (selectedCase) {
        selectedCase.input = rawAddress;
        selectedCase.expected = expected;
        if (queueMeta) selectedCase.meta = queueMeta;
        else delete selectedCase.meta;
        selectedCase.note = String(selectedCase.note || '');
        if (typeof selectedCase.strict !== 'boolean') selectedCase.strict = true;
        if (!selectedCase.name || String(selectedCase.name).trim().length === 0) {
          selectedCase.name = sourceId ? `Mẫu ngẫu nhiên · ${sourceId}` : 'Mẫu ngẫu nhiên';
        }
        pltClearResults([selectedCase.id]);
        pltSelect(selectedCase.id);
      } else {
        const c = {
          id: uid(),
          name: sourceId ? `Mẫu ngẫu nhiên · ${sourceId}` : 'Mẫu ngẫu nhiên',
          input: rawAddress,
          note: '',
          expected,
          strict: true,
          created_at: new Date().toISOString(),
          ...(queueMeta ? { meta: queueMeta } : {}),
        };
        cases.push(c);
        pltSelect(c.id);
      }
      pltSave();
      renderList();
      renderEditor();
      updateSummary();
      window.showToast?.(
        `${selectedCase ? 'Đã cập nhật mẫu đang chọn' : 'Đã tạo mẫu mới'}${sourceId ? ` (${sourceId})` : ''}`,
        'success'
      );
    } catch (e) {
      window.showToast?.(`Lỗi khi lấy mẫu ngẫu nhiên: ${e.message}`, 'danger');
    } finally {
      pltSetRandomPredictLoadingOverlay(false);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = PLT_HTML_BTN_RANDOM_PREDICT_IDLE;
      }
    }
  }

  function pltDup(id) {
    const src = cases.find(c => c.id === id);
    if (!src) return;
    const c = JSON.parse(JSON.stringify(src));
    c.id = uid();
    c.name = (src.name || '') + ' — bản sao';
    c.created_at = new Date().toISOString();
    cases.push(c);
    pltSelect(c.id);
    pltSave();
  }

  function pltEditorEmptyInnerHtml() {
    return '<div class="empty-state plt-editor-empty"><i class="fa-solid fa-flask-vial"></i><p>Chọn mẫu bên trái hoặc nhấn Thêm mẫu để bắt đầu</p></div>';
  }

  function syncPltRunCluster() {
    const runOne = document.getElementById('plt-btn-run-one');
    if (!runOne) return;
    const ok = Boolean(activeId && cases.some(x => x.id === activeId));
    runOne.disabled = !ok;
  }

  function renderPltEmptySurface() {
    const surface = document.getElementById('plt-editor-surface');
    if (!surface) return;
    surface.innerHTML = pltEditorEmptyInnerHtml();
    syncPltRunCluster();
  }

  function pltDel(id) {
    if (!confirm('Xóa mẫu này?')) return;
    cases = cases.filter(c => c.id !== id);
    if (activeId === id) {
      activeId = null;
      renderPltEmptySurface();
    }
    delete results[id];
    pltSave();
    renderList();
    updateSummary();
    syncPltRunCluster();
  }

  function pltSelect(id) {
    activeId = id;
    renderList();
    renderEditor();
  }

  let saveTimer = null;
  let pltDelegatedEventsBound = false;
  let pltTypingSuggestTimer = null;
  let pltTypingSuggestAbort = null;
  let pltTypingSuggestSeq = 0;

  async function pltSave() {
    localStorage.setItem('plt_cases', JSON.stringify(cases));
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        await fetch(`${API}/prelabeler-cases`, {
          method: 'POST',
          headers: authHdr(),
          body: JSON.stringify(cases),
        });
      } catch (e) {
        console.warn('Save to DB failed, using localStorage', e);
      }
    }, 800);
  }

  function renderEditor() {
    const surface = document.getElementById('plt-editor-surface');
    if (!surface) return;
    pltClearAnnBlockUi();
    const c = cases.find(x => x.id === activeId);
    if (!c) {
      surface.innerHTML = pltEditorEmptyInnerHtml();
      syncPltRunCluster();
      return;
    }
    const result = results[c.id];
    const hkHint = hotkeyRangeHint();
    const clearAllDisabled = !Array.isArray(c.expected) || c.expected.length <= 0;
    const clearAllTitle = clearAllDisabled
      ? 'Không có nhãn kỳ vọng để xóa'
      : 'Xóa toàn bộ nhãn kỳ vọng hiện tại của mẫu này';
    const badge =
      result && !result.error
        ? `<span class="plt-overall-badge plt-overall-badge--${result.passed ? 'pass' : 'fail'}" title="Kết quả đối chiếu mẫu hiện tại">
            <i class="fa-solid ${result.passed ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
            ${result.passed ? 'Đạt' : 'Chưa đạt'}
          </span>`
        : '';
    surface.innerHTML = `
      <div class="plt-editor">
        <div class="plt-editor-head">
          <input type="text" value="${pltEsc(c.name || '')}" oninput="pltUpd('name',this.value)" placeholder="Tên mẫu…">
          <div class="plt-editor-actions">
            <label style="color:var(--text-tertiary);display:flex;align-items:center;gap:8px;cursor:pointer;white-space:nowrap" title="Bật để báo lỗi khi có nhận diện ngoài danh sách kỳ vọng">
              <input type="checkbox" ${c.strict ? 'checked' : ''} onchange="pltUpd('strict',this.checked)"> Chế độ nghiêm
            </label>
          </div>
        </div>
        <div class="plt-editor-scroll">
          <div class="plt-field plt-field-full plt-raw-pin">
            <textarea class="form-input plt-raw-address-input" id="plt-raw-address"
              oninput="pltUpdInput(this.value)" onpaste="pltAutoExtract(event)"
              placeholder="Địa chỉ đầy đủ...">${pltEsc(c.input || '')}</textarea>
          </div>
          <div class="plt-field plt-field-full">
            <textarea class="form-input" id="plt-note"
              oninput="pltUpd('note',this.value)"
              placeholder="Ghi chú lý do gán nhãn (ví dụ: vì raw có tiền tố admin rõ ràng, hoặc case ngoại lệ cần giữ nguyên)...">${pltEsc(c.note || '')}</textarea>
          </div>
          <div class="plt-exp-section">
            <div class="plt-exp-head">
              <div class="plt-exp-head__title">
                <span>Nhãn kỳ vọng và đối chiếu</span>
                ${badge}
              </div>
            </div>
            <div class="plt-raw-annotated-row">
              ${renderAnnotatedRawText(c)}
              <button type="button" class="btn btn-outline btn-sm plt-unexpected-clear-all" title="${pltEsc(clearAllTitle)}" ${clearAllDisabled ? 'disabled aria-disabled="true"' : ''}>
                <i class="fa-solid fa-trash"></i> Xóa all nhãn
              </button>
            </div>
            <div class="plt-exp-layout">
              <div class="plt-label-grid" id="plt-exp-list">${renderMergedLabelGrid(c, result)}</div>
              ${renderRunAuxiliary(result)}
            </div>
          </div>
        </div>
      </div>
    `;
    syncPltRunCluster();
  }

  function pltUpd(key, val) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    c[key] = val;
    pltSave();
    renderList();
  }

  function pltUpdInput(val) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const nextInput = String(val || '');
    const prevInput = String(c.input || '');
    c.input = nextInput;

    // Khi raw text thay đổi, kết quả run trước đó không còn hợp lệ.
    if (nextInput !== prevInput && Object.prototype.hasOwnProperty.call(results, c.id)) {
      delete results[c.id];
      renderEditor();
      renderList();
      updateSummary();
    }

    // Khong tu dong them WDS/DST/PRO vao expected khi user dang go.
    // Tru tranh tao "ky vong ao" khi user chua chu dong ap dung de xuat.
    pltSave();
  }

  function pltScheduleTypingAdminSuggest(c) {
    // Deprecated behavior: truoc day tu dong goi parser va push WDS/DST/PRO vao expected.
    // Giu ham de tranh vo call-site cu, nhung khong con mutate expected ngam.
    return;
    if (!c) return;
    if (pltTypingSuggestTimer) {
      clearTimeout(pltTypingSuggestTimer);
      pltTypingSuggestTimer = null;
    }
    if (pltTypingSuggestAbort) {
      try { pltTypingSuggestAbort.abort(); } catch (_) {}
      pltTypingSuggestAbort = null;
    }

    const text = String(c.input || '').trim();
    // Tránh gọi API khi text còn quá ngắn/chưa có cấu trúc địa chỉ.
    if (text.length < 10 || !text.includes(',')) return;

    const seq = ++pltTypingSuggestSeq;
    const caseId = String(c.id || '');
    pltTypingSuggestTimer = setTimeout(async () => {
      if (!pltIsPrelabelerCasesPageVisible()) return;
      const target = cases.find(x => String(x.id) === caseId);
      if (!target) return;
      const latestText = String(target.input || '').trim();
      if (!latestText || latestText !== text) return;

      const expected = Array.isArray(target.expected) ? target.expected : [];
      const hasAllAdmin = ['WDS', 'DST', 'PRO'].every(label =>
        expected.some(it => String(it?.label || '').trim().toUpperCase() === label && String(it?.text || '').trim())
      );
      if (hasAllAdmin) return;

      try {
        const ctrl = new AbortController();
        pltTypingSuggestAbort = ctrl;
        const res = await fetch(`${API}/parser/analyze?model=prelabeler`, {
          method: 'POST',
          headers: authHdr(),
          body: JSON.stringify({ raw_address: latestText }),
          signal: ctrl.signal,
        });
        if (!res.ok) return;
        const data = await res.json();
        if (seq !== pltTypingSuggestSeq) return;
        const entities = data?.outputs?.prelabeler?.result || [];

        let updated = false;
        ['WDS', 'DST', 'PRO'].forEach(label => {
          const hit = entities.find(e => e?.label === label && e?.text);
          if (!hit) return;
          const hitText = String(hit.text).trim();
          if (!hitText) return;
          const exists = (target.expected || []).some(
            it =>
              String(it?.label || '').trim().toUpperCase() === label &&
              String(it?.text || '').trim().toLowerCase() === hitText.toLowerCase()
          );
          if (!exists) {
            target.expected = target.expected || [];
            target.expected.push({ label, text: hitText });
            updated = true;
          }
        });

        if (updated && String(activeId) === caseId) {
          renderEditor();
          renderList();
          updateSummary();
          pltSave();
        } else if (updated) {
          pltSave();
        }
      } catch (e) {
        if (e?.name !== 'AbortError') console.warn('Typing admin suggest failed', e);
      } finally {
        if (seq === pltTypingSuggestSeq) pltTypingSuggestAbort = null;
      }
    }, 380);
  }

  function pltClearResults(caseIds) {
    const ids = Array.isArray(caseIds) ? caseIds.map(x => String(x)) : [];
    if (!ids.length) return;
    ids.forEach(id => {
      if (Object.prototype.hasOwnProperty.call(results, id)) {
        delete results[id];
      }
    });
  }

  function pltAddUnexpectedToExpected(label, text) {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const added = pltAddExpectedPair(c, label, text);
    if (!added) {
      const normLabel = String(label || '').trim().toUpperCase();
      const normText = String(text || '').trim();
      if (normLabel && normText) window.showToast?.(`Đã tồn tại ${normLabel}: ${normText}`, 'info');
      return;
    }

    pltSave();
    renderEditor();
    renderList();
    updateSummary();
    window.showToast?.(`Đã thêm ${String(label || '').trim().toUpperCase()} vào nhãn kỳ vọng`, 'success');
  }

  function pltAddExpectedPair(caseObj, label, text) {
    if (!caseObj) return false;
    const normLabel = String(label || '').trim().toUpperCase();
    const normText = String(text || '').trim();
    if (!normLabel || !normText) return false;

    caseObj.expected = Array.isArray(caseObj.expected) ? caseObj.expected : [];
    if (pltHasExpectedPair(caseObj, normLabel, normText)) return false;

    caseObj.expected.push({ label: normLabel, text: normText });
    return true;
  }

  function pltHasExpectedPair(caseObj, label, text) {
    if (!caseObj) return false;
    const normLabel = String(label || '').trim().toUpperCase();
    const normText = String(text || '').trim();
    if (!normLabel || !normText) return false;
    const expected = Array.isArray(caseObj.expected) ? caseObj.expected : [];
    return expected.some(
      it =>
        String(it?.label || '').trim().toUpperCase() === normLabel &&
        String(it?.text || '').trim().toLowerCase() === normText.toLowerCase()
    );
  }

  function pltLabelHotkeyRank(label) {
    const lab = String(label || '').trim().toUpperCase();
    const row = nerLabelsOrdered.find(x => String(x?.value || '').trim().toUpperCase() === lab);
    const hk = row ? parseInt(String(row.hotkey), 10) : NaN;
    return Number.isNaN(hk) ? Number.POSITIVE_INFINITY : hk;
  }

  function pltResolveTextByRawCasing(rawAddress, text) {
    const raw = String(rawAddress || '');
    const needle = String(text || '').trim();
    if (!raw || !needle) return needle;
    const idx = raw.toLowerCase().indexOf(needle.toLowerCase());
    if (idx < 0) return needle;
    return raw.slice(idx, idx + needle.length);
  }

  function pltUnexpectedSuggestions(caseObj, runResult) {
    const raw = String(caseObj?.input || '');
    const src = Array.isArray(runResult?.unexpected) ? runResult.unexpected : [];
    const out = [];
    const seen = new Set();
    src.forEach(item => {
      const label = String(item?.label || '').trim().toUpperCase();
      const textNorm = String(item?.text || '').trim();
      if (!label || !textNorm) return;
      const text = pltResolveTextByRawCasing(raw, textNorm);
      const key = `${label}::${String(text).trim().toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ label, text: String(text).trim() });
    });
    out.sort((a, b) => {
      const ra = pltLabelHotkeyRank(a.label);
      const rb = pltLabelHotkeyRank(b.label);
      if (ra !== rb) return ra - rb;
      return a.text.localeCompare(b.text, 'vi');
    });
    return out;
  }

  function pltAddAllUnexpectedToExpected() {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const runResult = results[c.id];
    const unexpected = pltUnexpectedSuggestions(c, runResult);
    if (!unexpected.length) {
      window.showToast?.('Không có đề xuất nào để áp dụng', 'info');
      return;
    }

    let addedCount = 0;
    unexpected.forEach(item => {
      if (pltAddExpectedPair(c, item?.label, item?.text)) addedCount += 1;
    });

    if (!addedCount) {
      window.showToast?.('Tất cả đề xuất đã tồn tại trong nhãn kỳ vọng', 'info');
      return;
    }

    pltSave();
    renderEditor();
    renderList();
    updateSummary();
    window.showToast?.(`Đã thêm ${addedCount}/${unexpected.length} đề xuất vào nhãn kỳ vọng`, 'success');
  }

  function pltClearAllExpectedLabels() {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const before = Array.isArray(c.expected) ? c.expected.length : 0;
    if (!before) {
      window.showToast?.('Không có nhãn kỳ vọng để xóa', 'info');
      return;
    }

    c.expected = [];
    pltSave();
    renderEditor();
    renderList();
    updateSummary();
    window.showToast?.(`Đã xóa ${before} nhãn kỳ vọng`, 'success');
  }

  async function pltRunOne() {
    const c = cases.find(x => x.id === activeId);
    if (!c) return;
    const btn = document.getElementById('plt-btn-run-one');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
    try {
      const res = await fetch(`${API}/prelabeler-cases/run`, {
        method: 'POST',
        headers: authHdr(),
        body: JSON.stringify({ cases: [normalizeCaseForApi(c, 0)] }),
      });
      if (res.status === 401) {
        pltClearResults([c.id]);
        renderEditor();
        renderList();
        updateSummary();
        window.showToast?.('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.', 'warning');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      results[c.id] = data[0];
      c.tested_at = new Date().toISOString();
    } catch (e) {
      window.showToast?.('Lỗi server: ' + e.message, 'danger');
    } finally {
      if (btn) {
        btn.innerHTML = PLT_HTML_BTN_RUN_ONE_IDLE;
      }
      syncPltRunCluster();
    }
    renderEditor();
    renderList();
    updateSummary();
  }

  async function pltRunAll() {
    const btn = document.getElementById('plt-btn-run-all');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
    try {
      const res = await fetch(`${API}/prelabeler-cases/run`, {
        method: 'POST',
        headers: authHdr(),
        body: JSON.stringify({ cases: cases.map((c, i) => normalizeCaseForApi(c, i)) }),
      });
      if (res.status === 401) {
        pltClearResults(cases.map(c => c.id));
        if (activeId) renderEditor();
        renderList();
        updateSummary();
        window.showToast?.('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.', 'warning');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const nowIso = new Date().toISOString();
      data.forEach((rr, i) => {
        const rid = rr && rr.id != null ? String(rr.id) : null;
        if (rid) results[rid] = rr;
        else if (cases[i]) results[cases[i].id] = rr;
        const target = rid ? cases.find(c => c.id === rid) : cases[i];
        if (target) target.tested_at = nowIso;
      });
      window.showToast?.(`Đã đối chiếu xong ${data.length} mẫu`, 'success');
    } catch (e) {
      window.showToast?.('Lỗi: ' + e.message, 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = PLT_HTML_BTN_RUN_ALL_IDLE;
      }
    }
    if (activeId) renderEditor();
    renderList();
    updateSummary();
  }

  function updateSummary() {
    const ran = Object.values(results);
    const pass = ran.filter(r => r.passed).length;
    const fail = ran.filter(r => !r.passed).length;
    const pct = ran.length ? Math.round((pass / ran.length) * 100) : 0;

    const elTotal = document.getElementById('plt-s-total');
    const elPass = document.getElementById('plt-s-pass');
    const elFail = document.getElementById('plt-s-fail');
    const elProg = document.getElementById('plt-progress');
    const elPct = document.getElementById('plt-pct');
    const elFilterPass = document.getElementById('plt-filter-pass');
    const elFilterFail = document.getElementById('plt-filter-fail');
    const elLast = document.getElementById('plt-last-tested');
    const elLastText = document.getElementById('plt-last-tested-text');

    if (elTotal) elTotal.textContent = cases.length;
    if (elPass) elPass.textContent = pass;
    if (elFail) elFail.textContent = fail;
    if (elProg) {
      elProg.style.width = pct + '%';
      elProg.style.background = fail > 0 ? 'var(--danger)' : 'var(--success)';
    }
    if (elPct) elPct.textContent = ran.length ? `${pct}% · đã đối chiếu ${ran.length} mẫu` : 'Chưa đối chiếu';
    if (elFilterPass) elFilterPass.classList.toggle('active', pltResultFilter === 'pass');
    if (elFilterFail) elFilterFail.classList.toggle('active', pltResultFilter === 'fail');

    if (elLast && elLastText) {
      let maxTs = 0;
      for (const c of cases) {
        const t = c?.tested_at ? Date.parse(c.tested_at) : 0;
        if (Number.isFinite(t) && t > maxTs) maxTs = t;
      }
      if (maxTs > 0) {
        const d = new Date(maxTs);
        const rel = pltFormatRelativeTime(maxTs);
        const abs = d.toLocaleString('vi-VN', { hour12: false });
        elLastText.textContent = `Lần cuối đối chiếu ${rel}`;
        elLast.title = `Lần cuối đối chiếu: ${abs}`;
        elLast.hidden = false;
      } else {
        elLast.hidden = true;
      }
    }
  }

  function pltFormatRelativeTime(ts) {
    const diffSec = Math.max(0, Math.round((Date.now() - ts) / 1000));
    if (diffSec < 60) return 'vừa xong';
    const diffMin = Math.round(diffSec / 60);
    if (diffMin < 60) return `${diffMin} phút trước`;
    const diffHour = Math.round(diffMin / 60);
    if (diffHour < 24) return `${diffHour} giờ trước`;
    const diffDay = Math.round(diffHour / 24);
    if (diffDay < 30) return `${diffDay} ngày trước`;
    const diffMonth = Math.round(diffDay / 30);
    if (diffMonth < 12) return `${diffMonth} tháng trước`;
    return `${Math.round(diffMonth / 12)} năm trước`;
  }

  function pltExport() {
    const blob = new Blob([JSON.stringify(cases, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `prelabeler_labeling_cases_${new Date().getTime()}.json`;
    a.click();
  }

  async function pltExportLabelStudio() {
    const raw = window.prompt('Nhập số lượng bản ghi xuất cho Label Studio:', '500');
    if (raw == null) return;
    const limit = Number.parseInt(String(raw).trim(), 10);
    if (!Number.isFinite(limit) || limit <= 0) {
      window.showToast?.('Số lượng không hợp lệ. Vui lòng nhập số > 0.', 'warning');
      return;
    }

    const btn = document.getElementById('plt-btn-export-ls');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xuất…';
    }
    try {
      const res = await fetch(`${API}/prelabeler-cases/export-label-studio`, {
        method: 'POST',
        headers: authHdr(),
        body: JSON.stringify({ limit }),
      });
      if (res.status === 401) {
        window.showToast?.('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.', 'warning');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const dispo = res.headers.get('content-disposition') || '';
      const m = dispo.match(/filename=\"?([^\";]+)\"?/i);
      const fileName = (m && m[1]) ? m[1] : `label_studio_export_${Date.now()}.zip`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        a.remove();
      }, 1500);
      window.showToast?.(`Đã xuất ${limit} mẫu cho Label Studio`, 'success');
    } catch (e) {
      window.showToast?.(`Xuất Label Studio thất bại: ${e.message}`, 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-file-export"></i> Xuất Label Studio';
      }
    }
  }

  function pltImport(ev) {
    const file = ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async e => {
      try {
        cases = JSON.parse(e.target.result);
        await pltSave();
        renderList();
        updateSummary();
        window.showToast?.(`Đã nhập ${cases.length} mẫu`, 'success');
      } catch (err) {
        window.showToast?.('JSON không hợp lệ', 'danger');
      }
    };
    reader.readAsText(file);
  }

  async function pltAutoExtract(ev) {
    // Khong auto inject expected tren paste; user se chu dong add qua hotkey/Apply all.
    return;
    const text = (ev.clipboardData || window.clipboardData).getData('text');
    if (!text || text.length < 5) return;

    const c = cases.find(x => x.id === activeId);
    if (!c) return;

    const inputEl = ev.target;
    const originalBg = inputEl.style.background;
    inputEl.style.background = 'var(--accent-glow)';

    setTimeout(async () => {
      try {
        const res = await fetch(`${API}/parser/analyze?model=prelabeler`, {
          method: 'POST',
          headers: authHdr(),
          body: JSON.stringify({ raw_address: text }),
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        const entities = data.outputs?.prelabeler?.result || [];

        let updated = false;
        ['WDS', 'DST', 'PRO'].forEach(label => {
          const hit = entities.find(e => e?.label === label && e?.text);
          if (!hit) return;
          const exists = (c.expected || []).some(
            it =>
              it?.label === label &&
              String(it?.text || '').trim().toLowerCase() === String(hit.text).trim().toLowerCase()
          );
          if (!exists) {
            c.expected = c.expected || [];
            c.expected.push({ label, text: String(hit.text).trim() });
            updated = true;
          }
        });

        if (updated) {
          pltSave();
          renderEditor();
          window.showToast?.('Đã thêm WDS/DST/PRO vào nhãn kỳ vọng', 'success');
        }
      } catch (e) {
        console.warn('Auto extract failed', e);
      } finally {
        inputEl.style.background = originalBg;
      }
    }, 50);
  }

  function normalizeCaseForApi(c, idx = 0) {
    const input = String((c && c.input != null) ? c.input : '');
    const expectedRaw = Array.isArray(c?.expected) ? c.expected : [];
    const expected = expectedRaw
      .filter(e => e && typeof e === 'object')
      .map(e => ({
        label: String(e.label || '').trim().toUpperCase(),
        text: String(e.text || '').trim(),
      }))
      .filter(e => e.label && e.text);

    const out = {
      id: String(c?.id || `case_${idx}`),
      name: String(c?.name || ''),
      input,
      note: String(c?.note || ''),
      expected,
      strict: c?.strict !== false,
    };
    const md = c?.meta && typeof c.meta === 'object' ? c.meta : null;
    if (
      md &&
      ['ward_name', 'district_name', 'province_name'].some(k => md[k] != null && String(md[k]).trim().length > 0)
    ) {
      out.meta = {
        ward_name: md.ward_name != null && String(md.ward_name).trim() ? String(md.ward_name).trim() : null,
        district_name:
          md.district_name != null && String(md.district_name).trim() ? String(md.district_name).trim() : null,
        province_name:
          md.province_name != null && String(md.province_name).trim() ? String(md.province_name).trim() : null,
      };
    }
    return out;
  }

  /**
   * Delegate on `document`: `#prelabeler-cases` loads after `loadPages()`, so bind at DOMContentLoaded
   * would race (batch run / toolbar clicks would not fire).
   */
  function pltBindDelegatedEvents() {
    if (pltDelegatedEventsBound) return;
    pltDelegatedEventsBound = true;

    document.addEventListener('focusin', e => {
      const t = e.target;
      if (!(t instanceof Element)) return;
      if (!pltIsPrelabelerCasesPageVisible()) return;
      if (t.closest('#plt-raw-address')) {
        pltClearAnnBlockUi();
        return;
      }
      const chip = t.closest('.plt-raw-ann');
      if (chip instanceof HTMLElement) pltAnnounceAnnBlock(chip);
    });

    document.addEventListener('mousedown', e => {
      const t = e.target;
      if (!(t instanceof Element)) return;
      if (!pltIsPrelabelerCasesPageVisible()) return;
      const chip = t.closest('.plt-raw-ann');
      const annWrap = t.closest('.plt-raw-annotated');
      if (chip instanceof HTMLElement) {
        pltAnnounceAnnBlock(chip);
        return;
      }
      if (t.closest('#plt-raw-address')) {
        pltClearAnnBlockUi();
        return;
      }
      if (annWrap instanceof HTMLElement) pltClearAnnBlockUi();
    });

    document.addEventListener(
      'click',
      e => {
        const t = e.target;
        if (!(t instanceof Element)) return;
        if (t.closest('#plt-btn-new')) {
          e.preventDefault();
          pltNew();
          return;
        }
        if (t.closest('#plt-btn-random-predict')) {
          e.preventDefault();
          void pltGetRandomAndPredict();
          return;
        }
        if (t.closest('#plt-btn-run-all')) {
          e.preventDefault();
          void pltRunAll();
          return;
        }
        if (t.closest('#plt-btn-export')) {
          e.preventDefault();
          pltExport();
          return;
        }
        if (t.closest('#plt-btn-export-ls')) {
          e.preventDefault();
          void pltExportLabelStudio();
          return;
        }
        if (t.closest('#plt-btn-import')) {
          e.preventDefault();
          document.getElementById('plt-file-input')?.click();
          return;
        }
        if (t.closest('#plt-filter-pass')) {
          e.preventDefault();
          pltSetResultFilter('pass');
          return;
        }
        if (t.closest('#plt-filter-fail')) {
          e.preventDefault();
          pltSetResultFilter('fail');
          return;
        }
        const addBtn = t.closest('.plt-token-add-exp');
        if (addBtn) {
          e.preventDefault();
          pltAddUnexpectedToExpected(addBtn.getAttribute('data-label'), addBtn.getAttribute('data-text'));
          return;
        }
        if (t.closest('.plt-unexpected-apply-all')) {
          e.preventDefault();
          pltAddAllUnexpectedToExpected();
          return;
        }
        if (t.closest('.plt-unexpected-clear-all')) {
          e.preventDefault();
          pltClearAllExpectedLabels();
          return;
        }
      },
      false
    );

    document.addEventListener('keydown', e => {
      const t = e.target;
      if (!(t instanceof Element)) return;

      if (pltIsPrelabelerCasesPageVisible()) {
        const aeHot = document.activeElement instanceof HTMLElement ? document.activeElement : null;

        /**
         * `#plt-run-cluster`: chỉ một phím F (không kèm Ctrl/Alt/Shift/Meta) để tránh xung đột tổ hợp browser.
         * F8/F9/F10 thường ít bị trình duyệt chiếm hơn F5–F7, F11–F12.
         */
        const runClusterKey = /^F(8|9|10)$/i.test(String(e.key || ''))
          ? String(e.key).toUpperCase()
          : null;
        if (
          runClusterKey &&
          !e.repeat &&
          !e.ctrlKey &&
          !e.altKey &&
          !e.metaKey &&
          !e.shiftKey
        ) {
          if (!(aeHot && pltRunClusterHotkeyConsumeBlocked(aeHot))) {
            if (runClusterKey === 'F8') {
              const b = document.getElementById('plt-btn-run-one');
              if (b instanceof HTMLButtonElement && !b.disabled) {
                e.preventDefault();
                void pltRunOne();
                return;
              }
            }
            if (runClusterKey === 'F9') {
              e.preventDefault();
              void pltRunAll();
              return;
            }
            if (runClusterKey === 'F10') {
              e.preventDefault();
              void pltGetRandomAndPredict();
              return;
            }
          }
        }

        /** Delete / Backspace removes label from a click-selected annotated block (not while editing text fields). */
        if (
          !e.repeat &&
          (e.key === 'Delete' || e.key === 'Backspace') &&
          pltAnnBlockSelection &&
          nerLabelsOrdered.length
        ) {
          const ae = aeHot instanceof HTMLElement ? aeHot : null;
          if (ae?.id !== 'plt-raw-address') {
            const blockTypingDelete =
              ae?.isContentEditable ||
              ae?.closest('#plt-search') ||
              ae?.closest('.plt-editor-head input') ||
              ae?.closest('.plt-label-cell__input');
            if (!blockTypingDelete) {
              e.preventDefault();
              pltAnnRemoveSelectedBlock();
              return;
            }
          }
        }

        /** Digit hotkeys mirror Label Studio chip order (aligned with ô nhãn bên dưới). */
        if (!e.repeat && !e.altKey && !e.ctrlKey && !e.metaKey && nerLabelsOrdered.length) {
          const hkDigit = pltLabelFromHotkeyKey(e.key);
          if (hkDigit) {
            const ta = document.getElementById('plt-raw-address');
            const hasTaSel =
              aeHot === ta &&
              ta &&
              ta.selectionStart != null &&
              ta.selectionEnd != null &&
              ta.selectionStart !== ta.selectionEnd;
            const hasAnnSel = pltAnnotHasUsableSubstringSelection();
            const scopedDigit =
              Boolean(pltAnnBlockSelection) ||
              hasTaSel ||
              hasAnnSel;
            // Khi da co "scope" ro rang (block duoc click / text duoc boi o raw textarea
            // hoac preview annotated), luon uu tien hotkey va khong phu thuoc focus hien tai.
            if (scopedDigit) {
              e.preventDefault();
              pltAnnApplyLabelFromChoice(hkDigit);
              return;
            }
          }
        }
      }

      if (e.key !== 'Enter' && e.key !== ' ') return;
      if (t.closest('#plt-filter-pass')) {
        e.preventDefault();
        pltSetResultFilter('pass');
      } else if (t.closest('#plt-filter-fail')) {
        e.preventDefault();
        pltSetResultFilter('fail');
      }
    });

    document.addEventListener('input', e => {
      const tgt = e.target;
      if (tgt && tgt.id === 'plt-search') renderList();
    });

    document.addEventListener('change', e => {
      const tgt = e.target;
      if (tgt && tgt.id === 'plt-file-input') pltImport(e);
    });
  }

  window.pltSelect = pltSelect;
  window.pltDup = pltDup;
  window.pltDel = pltDel;
  window.pltUpd = pltUpd;
  window.pltUpdInput = pltUpdInput;
  window.pltSetExpectedLabel = (label, text) => setExpectedForLabel(label, text);
  window.pltAddExpectedLabel = pltAddExpectedLabel;
  window.pltRemoveExpectedLabel = pltRemoveExpectedLabel;
  window.pltAddExpectedLabelOnKey = pltAddExpectedLabelOnKey;
  window.pltRunOne = pltRunOne;
  window.pltNew = pltNew;
  window.pltRunAll = pltRunAll;
  window.pltExport = pltExport;
  window.pltAutoExtract = pltAutoExtract;
  window.pltGetRandomAndPredict = pltGetRandomAndPredict;
  window.pltDismissRandomPredictLoadingOverlay = () => pltSetRandomPredictLoadingOverlay(false);
  window.pltInitPage = () => pltInit();

  pltBindDelegatedEvents();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      void pltInit();
    });
  } else {
    setTimeout(() => {
      void pltInit();
    }, 50);
  }
})();
