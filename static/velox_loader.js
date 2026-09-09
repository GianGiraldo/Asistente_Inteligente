(function () {
  "use strict";
  if (window.__veloxLoaderInit) return;
  window.__veloxLoaderInit = true;

  var css = [
    "header[data-testid='stHeader'],",
    "[data-testid='stToolbar'],",
    "[data-testid='stDecoration'],",
    "[data-testid='stStatusWidget'],",
    ".stStatusWidget,",
    "#MainMenu,",
    "[data-testid='stMainMenu'],",
    "footer {",
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
    "  transition: opacity 0.35s ease, visibility 0.35s ease;",
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

  function hideNativeChrome() {
    var selectors = [
      "header[data-testid='stHeader']",
      "[data-testid='stToolbar']",
      "[data-testid='stDecoration']",
      "[data-testid='stStatusWidget']",
      ".stStatusWidget",
      "#MainMenu",
      "[data-testid='stMainMenu']",
      "footer",
    ];
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

  function appReady() {
    return !!document.querySelector(
      ".velox-auth-brand, .velox-id-bar, [data-testid='stSidebar'], .velox-login-form"
    );
  }

  function scriptRunning() {
    if (!appReady()) return true;
    var status = document.querySelector("[data-testid='stStatusWidget']");
    if (!status) return false;
    var rect = status.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function syncLoader() {
    hideNativeChrome();
    if (!appReady() || scriptRunning()) {
      ensureOverlay();
      var overlay = document.getElementById("velox-boot-loader");
      if (overlay) overlay.classList.remove("velox-boot-loader--hide");
      return;
    }
    var overlay = document.getElementById("velox-boot-loader");
    if (!overlay) return;
    overlay.classList.add("velox-boot-loader--hide");
    window.setTimeout(function () {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 400);
  }

  ensureOverlay();
  syncLoader();
  new MutationObserver(syncLoader).observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: true,
  });
  document.addEventListener("DOMContentLoaded", syncLoader);
  window.addEventListener("load", syncLoader);
})();
