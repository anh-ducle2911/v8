/* HPL i18n — zero-dependency runtime for the Flask/standalone build. */
(function (global) {
  "use strict";

  var STORAGE_KEY = "hpl.lang";
  var dicts = {};
  var lang = "vi";
  var observer = null;
  var applying = false;
  var textSources = new WeakMap();
  var attrSources = new WeakMap();
  var compiledPairs = null;

  function get(obj, path) {
    return path.split(".").reduce(function (value, key) {
      return value && value[key] !== undefined ? value[key] : undefined;
    }, obj);
  }

  function interpolate(value, vars) {
    if (!vars) return value;
    return String(value).replace(/\{\{\s*([\w.-]+)\s*\}\}/g, function (_, key) {
      return vars[key] === undefined ? "" : String(vars[key]);
    });
  }

  function t(key, vars) {
    var value = get(dicts[lang], key);
    if (value === undefined) value = get(dicts.vi, key);
    return interpolate(value === undefined ? key : value, vars);
  }

  function flatten(obj, prefix, out) {
    Object.keys(obj || {}).forEach(function (key) {
      var value = obj[key];
      var path = prefix ? prefix + "." + key : key;
      if (value && typeof value === "object") flatten(value, path, out);
      else if (typeof value === "string") out[path] = value;
    });
    return out;
  }

  function literalPairs() {
    if (compiledPairs) return compiledPairs;
    var vi = flatten(dicts.vi || {}, "", {});
    var en = flatten(dicts.en || {}, "", {});
    compiledPairs = Object.keys(vi).filter(function (key) {
      return en[key] !== undefined && vi[key] && vi[key] !== en[key];
    }).map(function (key) {
      return { key: key, source: vi[key], target: en[key] };
    }).sort(function (a, b) { return b.source.length - a.source.length; });
    return compiledPairs;
  }

  function replaceAll(value, search, replacement) {
    return value.split(search).join(replacement);
  }

  function translateLiteral(value) {
    var output = String(value == null ? "" : value);
    if (lang === "vi") return output;
    var exact = literalPairs().find(function (pair) { return pair.source === output; });
    if (exact) return exact.target;
    literalPairs().forEach(function (pair) {
      /* Short labels are exact-match only. This prevents "Xe" from changing
         "Xem" and "Không" from changing "Không đủ" in generated messages. */
      if ((pair.source.length >= 10 || pair.key.indexOf("ui.fragments.") === 0) && output.indexOf(pair.source) !== -1) {
        output = replaceAll(output, pair.source, pair.target);
      }
    });
    return output;
  }

  function nodesWithSelf(root, selector) {
    var nodes = [];
    if (root && root.nodeType === 1 && root.matches(selector)) nodes.push(root);
    if (root && root.querySelectorAll) nodes = nodes.concat(Array.from(root.querySelectorAll(selector)));
    return nodes;
  }

  function applyDeclared(root) {
    nodesWithSelf(root, "[data-i18n]").forEach(function (el) {
      var next = t(el.getAttribute("data-i18n"));
      if (el.textContent !== next) el.textContent = next;
    });
    ["placeholder", "title", "aria-label"].forEach(function (attr) {
      var marker = "data-i18n-" + attr;
      nodesWithSelf(root, "[" + marker + "]").forEach(function (el) {
        var next = t(el.getAttribute(marker));
        if (el.getAttribute(attr) !== next) el.setAttribute(attr, next);
      });
    });
    nodesWithSelf(root, "[data-i18n-document-title]").forEach(function (el) {
      var next = t(el.getAttribute("data-i18n-document-title"));
      if (document.title !== next) document.title = next;
    });
  }

  function sourceForAttribute(el, attr) {
    var stored = attrSources.get(el) || {};
    if (stored[attr] === undefined) {
      stored[attr] = el.getAttribute(attr);
      attrSources.set(el, stored);
    }
    return stored[attr];
  }

  function applyRuntimeText(root) {
    if (!root) return;
    var walkerRoot = root.nodeType === 9 ? root.documentElement : (root.nodeType === 3 ? root.parentElement : root);
    if (!walkerRoot) return;
    var walker = document.createTreeWalker(walkerRoot, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      var parent = node.parentElement;
      if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/.test(parent.tagName)) continue;
      if (parent.closest("[data-i18n]")) continue;
      var source = textSources.get(node);
      if (source === undefined) {
        source = node.nodeValue;
        textSources.set(node, source);
      }
      var next = lang === "vi" ? source : translateLiteral(source);
      if (node.nodeValue !== next) node.nodeValue = next;
    }

    ["placeholder", "title", "aria-label"].forEach(function (attr) {
      nodesWithSelf(walkerRoot, "[" + attr + "]").forEach(function (el) {
        if (el.hasAttribute("data-i18n-" + attr)) return;
        if (el.hasAttribute("data-i18n-runtime")) return;
        var source = sourceForAttribute(el, attr);
        var next = lang === "vi" ? source : translateLiteral(source);
        if (el.getAttribute(attr) !== next) el.setAttribute(attr, next);
      });
    });
  }

  function apply(root, notify) {
    if (applying) return;
    applying = true;
    try {
      var target = root || document;
      applyDeclared(target);
      applyRuntimeText(target);
      document.documentElement.lang = lang;
      if (notify !== false) {
        document.dispatchEvent(new CustomEvent("hpl:languagechange", { detail: { lang: lang } }));
      }
    } finally {
      applying = false;
    }
  }

  function detect() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "vi" || saved === "en") return saved;
    } catch (_) {}
    return (navigator.language || "vi").toLowerCase().indexOf("en") === 0 ? "en" : "vi";
  }

  function setLang(next) {
    lang = next === "en" ? "en" : "vi";
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
    apply(document, true);
  }

  function mountSwitcher(target) {
    var host = typeof target === "string" ? document.querySelector(target) : target;
    if (!host) return null;
    var existing = host.querySelector(".hpl-lang");
    if (existing) return existing;
    var wrap = document.createElement("div");
    wrap.className = "hpl-lang";
    wrap.setAttribute("role", "group");
    wrap.innerHTML =
      '<span class="hpl-lang__globe" aria-hidden="true">' +
      '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" ' +
      'stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>' +
      '<path d="M3 12h18M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18"/></svg></span>' +
      '<button type="button" class="hpl-lang__btn" data-lang="vi" lang="vi">VI</button>' +
      '<button type="button" class="hpl-lang__btn" data-lang="en" lang="en">EN</button>';
    wrap.addEventListener("click", function (event) {
      var button = event.target.closest("[data-lang]");
      if (!button) return;
      setLang(button.getAttribute("data-lang"));
    });
    host.appendChild(wrap);

    function sync() {
      wrap.querySelectorAll("[data-lang]").forEach(function (button) {
        var code = button.getAttribute("data-lang");
        button.setAttribute("aria-pressed", String(code === lang));
        button.setAttribute("title", t("language." + code));
      });
      wrap.setAttribute("aria-label", t("language.switchAria"));
      wrap.setAttribute("data-active", lang);
    }

    sync();
    document.addEventListener("hpl:languagechange", sync);
    return wrap;
  }

  function observe() {
    if (observer) observer.disconnect();
    observer = new MutationObserver(function (mutations) {
      if (applying) return;
      mutations.forEach(function (mutation) {
        if (mutation.type === "childList") {
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType === 1 || node.nodeType === 3) apply(node, false);
          });
        } else if (mutation.type === "attributes") apply(mutation.target, false);
      });
    });
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label"]
    });
  }

  function init(resources) {
    dicts = resources || {};
    compiledPairs = null;
    lang = detect();
    apply(document, false);
    observe();
    document.dispatchEvent(new CustomEvent("hpl:i18nready", { detail: { lang: lang } }));
  }

  global.HPLI18N = {
    init: init,
    t: t,
    apply: function (root) { apply(root || document, false); },
    setLang: setLang,
    translateLiteral: translateLiteral,
    mountSwitcher: mountSwitcher,
    get lang() { return lang; }
  };
})(window);
