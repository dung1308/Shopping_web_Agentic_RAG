(function () {
  const NAV_ITEMS = [
    { href: 'shopper_chat.html', label: 'Chat', icon: '💬' },
    { href: 'store_directory.html', label: 'Mall Map', icon: '🏬' },
    { href: 'admin_governance.html', label: 'Governance', icon: '📊' },
    { href: 'rag_debugger.html', label: 'Debugger', icon: '🔮' },
    { href: 'scraper_manager.html', label: 'Scraper', icon: '🕷️' },
    { href: 'document_studio.html', label: 'Ingest', icon: '📄' },
    { href: 'connection_status.html', label: 'Setup', icon: '⚡' },
    { href: 'auth.html', label: 'Auth', icon: '🔑', isAuth: true }
  ];

  const PAGE_META = {
    'index.html': { icon: '🛒', title: 'Shopping Mall Agentic RAG', subtitle: 'Dual-View AI Platform • Shopper Discovery & Admin Governance' },
    'shopper_chat.html': { icon: '💬', title: 'Shopper AI Assistant', subtitle: 'Conversational RAG Discovery' },
    'store_directory.html': { icon: '🏬', title: 'VinMall Spatial Directory', subtitle: 'Tenant store locations, deal vouchers & floor maps' },
    'admin_governance.html': { icon: '🛡️', title: 'Data Governance & Audit Center', subtitle: 'Pydantic AI compliance & audit flags' },
    'rag_debugger.html': { icon: '🐞', title: 'RAG Pipeline Debugger', subtitle: 'Vector search scores & prompt payload debugging' },
    'scraper_manager.html': { icon: '🕷️', title: 'Playwright Scraper Engine', subtitle: 'Crawler pipeline & active scrape jobs' },
    'document_studio.html': { icon: '📄', title: 'Document & Ingest Studio', subtitle: 'Docling, Playwright & ChromaDB ingestion' },
    'connection_status.html': { icon: '⚡', title: 'Connection Diagnostics', subtitle: 'Neon DB, Redis & LLM Probing' },
    'auth.html': { icon: '🔑', title: 'Identity & RBAC Auth', subtitle: 'Admin, Store Manager & Shopper Roles' }
  };

  function renderNav() {
    const navMount = document.getElementById('app-nav');
    if (!navMount) return;

    // Detect active page from URL path
    const rawPath = window.location.pathname.split('/').pop() || 'index.html';
    const activePage = (rawPath === '' || rawPath === '/') ? 'index.html' : rawPath;
    const meta = PAGE_META[activePage] || PAGE_META['index.html'];

    // Check if running inside iframe preview
    const isInsideIframe = window.self !== window.top;
    const targetAttr = isInsideIframe ? 'target="_top"' : '';

    const navLinksHtml = NAV_ITEMS.map(item => {
      const isActive = activePage === item.href;
      let styleClass = 'nav-pill-link';
      
      if (item.isAuth) {
        styleClass += isActive ? ' nav-pill-auth-active' : ' nav-pill-auth';
      } else {
        styleClass += isActive ? ' nav-pill-active' : '';
      }

      return `<a href="${item.href}" ${targetAttr} class="${styleClass}">
        <span>${item.icon}</span>
        <span>${item.label}</span>
      </a>`;
    }).join('');

    navMount.innerHTML = `
      <nav class="app-universal-navbar">
        <div class="app-nav-left">
          <a href="index.html" ${targetAttr} class="app-nav-home-btn">
            🏠 Main Dashboard
          </a>
          <span class="app-nav-divider">|</span>
          <div class="app-nav-brand">
            <span class="app-nav-icon">${meta.icon}</span>
            <div>
              <div class="app-nav-title">${meta.title}</div>
              <div class="app-nav-subtitle">${meta.subtitle}</div>
            </div>
          </div>
        </div>

        <div class="app-nav-links">
          ${navLinksHtml}
        </div>
      </nav>
    `;
  }

  function injectNavStyles() {
    if (document.getElementById('app-nav-styles')) return;
    const style = document.createElement('style');
    style.id = 'app-nav-styles';
    style.textContent = `
      .app-universal-navbar {
        background: rgba(15, 23, 42, 0.95);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 10px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: sticky;
        top: 0;
        z-index: 1000;
        backdrop-filter: blur(12px);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
      }

      .app-nav-left {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .app-nav-home-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(30, 41, 59, 0.9);
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 0.8rem;
        font-weight: 700;
        text-decoration: none;
        transition: all 0.2s ease;
      }
      .app-nav-home-btn:hover {
        background: rgba(51, 65, 85, 0.9);
        border-color: rgba(255, 255, 255, 0.25);
        color: #ffffff;
      }

      .app-nav-divider {
        color: #475569;
        font-size: 0.9rem;
      }

      .app-nav-brand {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .app-nav-icon {
        font-size: 1.2rem;
      }

      .app-nav-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.2;
      }

      .app-nav-subtitle {
        font-size: 0.68rem;
        color: #7acfd6;
        line-height: 1.2;
      }

      .app-nav-links {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        font-size: 0.78rem;
      }

      .nav-pill-link {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        color: #cbd5e1;
        text-decoration: none;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: 1px solid transparent;
      }

      .nav-pill-link:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.1);
        color: #ffffff;
      }

      .nav-pill-active {
        background: #f04b4c !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(240, 75, 76, 0.35);
        border-color: rgba(240, 75, 76, 0.5) !important;
      }

      .nav-pill-auth {
        background: rgba(240, 75, 76, 0.12);
        color: #f04b4c;
        border: 1px solid rgba(240, 75, 76, 0.3);
        font-weight: 600;
      }
      .nav-pill-auth:hover {
        background: rgba(240, 75, 76, 0.22);
        color: #ffffff;
      }

      .nav-pill-auth-active {
        background: #f04b4c !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(240, 75, 76, 0.35);
        border-color: rgba(240, 75, 76, 0.5) !important;
      }
    `;
    document.head.appendChild(style);
  }

  function initNav() {
    injectNavStyles();
    renderNav();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNav);
  } else {
    initNav();
  }
})();
