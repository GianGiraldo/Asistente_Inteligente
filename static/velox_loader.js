(function () {
  "use strict";
  if (window.__veloxLoaderInit) return;
  window.__veloxLoaderInit = true;

  var dismissed = false;
  var debounceTimer = null;

  var bootHideSelectors = [
    "header[data-testid='stHeader']",
    "[data-testid='stToolbar']",
    "[data-testid='stDecoration']",
    "[data-testid='stStatusWidget']",
    ".stStatusWidget",
    "#MainMenu",
    "[data-testid='stMainMenu']",
    "footer",
  ];

  var alwaysHideSelectors = [
    "[data-testid='stDecoration']",
    "[data-testid='stStatusWidget']",
    ".stStatusWidget",
    "#MainMenu",
    "[data-testid='stMainMenu']",
    "footer",
  ];

  var sidebarToggleSelectors = [
    "[data-testid='stExpandSidebarButton']",
    "[data-testid='collapsedControl']",
    "div:has(> [data-testid='collapsedControl'])",
    "[data-testid='stHeader'] [data-testid='stExpandSidebarButton']",
    "[data-testid='stHeader'] div:has(> [data-testid='collapsedControl'])",
  ];

  var css = [
    ".stApp:has(.velox-id-bar) header[data-testid='stHeader'],",
    ".stApp:has(.velox-auth-brand) header[data-testid='stHeader'],",
    ".stApp:has(.velox-id-bar) [data-testid='stToolbar'],",
    ".stApp:has(.velox-auth-brand) [data-testid='stToolbar'],",
    ".stApp:has(.velox-id-bar) [data-testid='stDecoration'],",
    ".stApp:has(.velox-auth-brand) [data-testid='stDecoration'],",
    ".stApp:has(.velox-id-bar) [data-testid='stStatusWidget'],",
    ".stApp:has(.velox-auth-brand) [data-testid='stStatusWidget'],",
    ".stApp:has(.velox-id-bar) .stStatusWidget,",
    ".stApp:has(.velox-auth-brand) .stStatusWidget,",
    ".stApp:has(.velox-id-bar) #MainMenu,",
    ".stApp:has(.velox-auth-brand) #MainMenu,",
    ".stApp:has(.velox-id-bar) [data-testid='stMainMenu'],",
    ".stApp:has(.velox-auth-brand) [data-testid='stMainMenu'],",
    ".stApp:has(.velox-id-bar) footer,",
    ".stApp:has(.velox-auth-brand) footer {",
    "  display: none !important;",
    "  visibility: hidden !important;",
    "  opacity: 0 !important;",
    "  height: 0 !important;",
    "  min-height: 0 !important;",
    "  max-height: 0 !important;",
    "  overflow: hidden !important;",
    "  pointer-events: none !important;",
    "}",
    "@keyframes velox-spin { to { transform: rotate(360deg); } }",
    "#velox-boot-loader {",
    "  position: fixed;",
    "  inset: 0;",
    "  z-index: 2147483646;",
    "  display: grid;",
    "  place-items: center;",
    "  background: #0A0E14;",
    "  transition: opacity 0.28s ease, visibility 0.28s ease;",
    "}",
    "#velox-boot-loader.velox-boot-loader--hide {",
    "  opacity: 0;",
    "  visibility: hidden;",
    "  pointer-events: none;",
    "}",
    "#velox-boot-loader .velox-boot-spinner {",
    "  width: 52px;",
    "  height: 52px;",
    "  border: 4px solid rgba(74, 111, 165, 0.25);",
    "  border-top-color: #4a6fa5;",
    "  border-right-color: #00E5FF;",
    "  border-radius: 50%;",
    "  animation: velox-spin 0.85s linear infinite;",
    "  box-shadow: 0 0 24px rgba(0, 229, 255, 0.22);",
    "}",
    "[data-testid='stAppSkeleton'],",
    "[data-testid='stAppSkeleton'] * {",
    "  visibility: hidden !important;",
    "  opacity: 0 !important;",
    "}",
  ].join("\n");

  var style = document.getElementById("velox-critical-loader");
  if (!style) {
    style = document.createElement("style");
    style.id = "velox-critical-loader";
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  }

  function ensureOverlay() {
    if (document.getElementById("velox-boot-loader")) return;
    var overlay = document.createElement("div");
    overlay.id = "velox-boot-loader";
    overlay.setAttribute("aria-live", "polite");
    overlay.setAttribute("aria-label", "Cargando veloX");
    overlay.innerHTML = '<div class="velox-boot-spinner"></div>';
    (document.body || document.documentElement).appendChild(overlay);
  }

  function hideOverlay() {
    var overlay = document.getElementById("velox-boot-loader");
    if (!overlay) return;
    overlay.classList.add("velox-boot-loader--hide");
    window.setTimeout(function () {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 320);
  }

  function isAuthScreen() {
    return !!document.querySelector(".velox-id-bar, .velox-auth-brand");
  }

  function isPostLogin() {
    return !!document.querySelector('[data-testid="stSidebar"]') && !isAuthScreen();
  }

  function hideElements(selectors) {
    selectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.style.setProperty("display", "none", "important");
        el.style.setProperty("visibility", "hidden", "important");
        el.style.setProperty("opacity", "0", "important");
        el.style.setProperty("height", "0", "important");
        el.style.setProperty("overflow", "hidden", "important");
        el.style.setProperty("pointer-events", "none", "important");
      });
    });
  }

  function clearInlineStyles(selectors) {
    var props = [
      "display",
      "visibility",
      "opacity",
      "height",
      "min-height",
      "max-height",
      "overflow",
      "pointer-events",
    ];
    selectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        props.forEach(function (prop) {
          el.style.removeProperty(prop);
        });
      });
    });
  }

  function ensureSidebarToggleVisible() {
    sidebarToggleSelectors.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.style.removeProperty("display");
        el.style.removeProperty("visibility");
        el.style.removeProperty("opacity");
        el.style.removeProperty("height");
        el.style.removeProperty("overflow");
        el.style.setProperty("pointer-events", "auto", "important");
      });
    });
  }

  function hideNativeChrome() {
    hideElements(alwaysHideSelectors);

    if (dismissed && isPostLogin()) {
      clearInlineStyles(["header[data-testid='stHeader']", "[data-testid='stToolbar']"]);
      ensureSidebarToggleVisible();
      return;
    }

    if (isAuthScreen() || !dismissed) {
      hideElements(bootHideSelectors);
      return;
    }

    clearInlineStyles(["header[data-testid='stHeader']", "[data-testid='stToolbar']"]);
    ensureSidebarToggleVisible();
  }

  function appReady() {
    return !!document.querySelector(
      [
        ".velox-auth-brand",
        ".velox-id-bar",
        ".velox-login-form",
        ".velox-portal-form",
        ".st-key-btn_iniciar_sesion_velox",
        ".st-key-login_recordarme_row",
        "[data-testid='stSidebar']",
        "[data-testid='stTextInput'] input",
        "[data-testid='stMain'] button",
      ].join(",")
    );
  }

  function streamlitRunning() {
    var status = document.querySelector("[data-testid='stStatusWidget']");
    if (!status) return false;
    var rect = status.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    var computed = window.getComputedStyle(status);
    return computed.display !== "none" && computed.visibility !== "hidden" && computed.opacity !== "0";
  }

  function dismissLoader() {
    if (dismissed) return;
    dismissed = true;
    hideOverlay();
    hideNativeChrome();
  }

  function syncLoader() {
    hideNativeChrome();
    if (dismissed) return;

    if (appReady() && !streamlitRunning()) {
      dismissLoader();
      return;
    }

    ensureOverlay();
  }

  function scheduleSync() {
    if (debounceTimer) window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(syncLoader, 120);
  }

  ensureOverlay();
  syncLoader();

  new MutationObserver(scheduleSync).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });

  document.addEventListener("DOMContentLoaded", syncLoader);
  window.addEventListener("load", syncLoader);

  window.setInterval(function () {
    if (!dismissed && appReady() && !streamlitRunning()) {
      dismissLoader();
    } else if (dismissed && isPostLogin()) {
      hideNativeChrome();
    }
  }, 500);

  window.setTimeout(function () {
    if (appReady()) dismissLoader();
  }, 8000);

  window.setTimeout(dismissLoader, 20000);
})();
