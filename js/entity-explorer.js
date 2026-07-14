(function () {
  "use strict";

  var DATA_URL = "files/entities.json";
  var SOURCE_URLS = {
    html: "files/index.html",
    tei: "files/tei.xml"
  };

  var entities = [];
  var activeFilter = "all";
  var selectedId = "";
  var pendingId = "";
  var sourceCache = {};

  var entityList = document.getElementById("entity-list");
  var detail = document.getElementById("entity-detail");
  var status = document.getElementById("entity-status");
  var frame = document.getElementById("article-frame");
  var rawLink = document.getElementById("viewer-raw-link");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function appendLink(parent, label, href) {
    if (!href) return;
    var link = el("a", "entity-authority-link", label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener";
    parent.appendChild(link);
  }

  function clearArticleHighlight() {
    if (!frame || !frame.contentDocument) return;
    frame.contentDocument.querySelectorAll(".entity[data-entity]").forEach(function (node) {
      node.classList.remove("entity-muted", "entity-selected");
    });
  }

  function highlightArticle(entityId, shouldScroll) {
    if (!frame || !frame.contentDocument) {
      pendingId = entityId;
      return;
    }

    var mentions = Array.prototype.slice.call(
      frame.contentDocument.querySelectorAll(".entity[data-entity]")
    );
    if (!mentions.length) {
      pendingId = entityId;
      return;
    }

    var selected = [];
    mentions.forEach(function (node) {
      var matches = node.dataset.entity === entityId;
      node.classList.toggle("entity-selected", matches);
      node.classList.toggle("entity-muted", !matches);
      if (matches) selected.push(node);
    });

    pendingId = "";
    if (shouldScroll && selected.length) {
      selected[0].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function renderEmptyDetail() {
    if (!detail) return;
    detail.innerHTML = "";
    var empty = el("div", "entity-detail-empty");
    empty.appendChild(el("span", "entity-detail-rune", "ᚱ"));
    empty.appendChild(el("h3", "", "Choose an entity"));
    empty.appendChild(el(
      "p",
      "",
      "Its authority records, reconciliation strategy, RDF statements, and occurrences in the TEI article will appear here."
    ));
    detail.appendChild(empty);
  }

  function renderDetail(entity) {
    if (!detail) return;
    detail.innerHTML = "";

    var header = el("div", "entity-detail-header");
    var label = el("span", "entity-layer entity-layer-" + entity.layer, entity.layerLabel);
    var heading = el("h3", "", entity.name);
    var uri = el("code", "entity-uri", entity.uri);
    header.appendChild(label);
    header.appendChild(heading);
    header.appendChild(uri);
    detail.appendChild(header);

    var facts = el("dl", "entity-facts");
    [
      ["Type", entity.type],
      ["TEI occurrences", String(entity.mentionCount)],
      ["Reconciliation", entity.reconciliation.property]
    ].forEach(function (fact) {
      facts.appendChild(el("dt", "", fact[0]));
      facts.appendChild(el("dd", "", fact[1]));
    });
    detail.appendChild(facts);

    var note = el("p", "entity-reconciliation-note", entity.reconciliation.note);
    detail.appendChild(note);

    var authorities = el("div", "entity-authorities");
    appendLink(authorities, entity.wikidata ? "Wikidata " + entity.wikidata + " ↗" : "", entity.wikidataUrl);
    appendLink(authorities, entity.viaf ? "VIAF ↗" : "", entity.viafUrl);
    if (authorities.children.length) detail.appendChild(authorities);

    if (entity.images && entity.images.length) {
      var imageGrid = el("div", "entity-image-pair");
      entity.images.forEach(function (image) {
        var figure = el("figure", "entity-image-card");
        var link = el("a", "");
        link.href = image.src;
        link.target = "_blank";
        link.rel = "noopener";
        var img = el("img", "");
        img.src = image.src;
        img.alt = entity.name + " — " + image.label;
        link.appendChild(img);
        figure.appendChild(link);
        figure.appendChild(el("figcaption", "", image.label));
        imageGrid.appendChild(figure);
      });
      detail.appendChild(imageGrid);
    }

    detail.appendChild(el("h4", "entity-triples-title", "RDF statements involving this entity"));
    var tripleList = el("ul", "entity-triple-list");
    entity.triples.forEach(function (triple) {
      var item = el("li", "");
      item.appendChild(el("code", "", triple.subject));
      item.appendChild(document.createTextNode(" "));
      item.appendChild(el("code", "", triple.predicate));
      item.appendChild(document.createTextNode(" "));
      item.appendChild(el("code", "", triple.object));
      tripleList.appendChild(item);
    });
    detail.appendChild(tripleList);
  }

  function setSelectedButton() {
    if (!entityList) return;
    entityList.querySelectorAll(".entity-choice").forEach(function (button) {
      var active = button.dataset.entity === selectedId;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function selectEntity(entityId, shouldScroll) {
    var entity = entities.find(function (item) { return item.id === entityId; });
    if (!entity) return;
    selectedId = entityId;
    setSelectedButton();
    renderDetail(entity);
    setViewerView("rendered");
    highlightArticle(entityId, shouldScroll !== false);
    if (status) {
      status.textContent = entity.name + " selected: " + entity.mentionCount +
        " occurrences in the TEI article and " + entity.triples.length + " outgoing RDF statements.";
    }
  }

  function clearSelection() {
    selectedId = "";
    pendingId = "";
    setSelectedButton();
    clearArticleHighlight();
    renderEmptyDetail();
    if (status) status.textContent = "Entity selection cleared.";
  }

  function renderEntityButtons() {
    if (!entityList) return;
    entityList.innerHTML = "";

    entities.filter(function (entity) {
      return activeFilter === "all" || entity.layer === activeFilter;
    }).forEach(function (entity) {
      var button = el("button", "entity-choice");
      button.type = "button";
      button.dataset.entity = entity.id;
      button.setAttribute("aria-pressed", String(entity.id === selectedId));
      button.appendChild(el("span", "", entity.name));
      button.appendChild(el("small", "", String(entity.mentionCount)));
      button.addEventListener("click", function () { selectEntity(entity.id, true); });
      entityList.appendChild(button);
    });
    setSelectedButton();
  }

  function initFilters() {
    document.querySelectorAll(".entity-filter").forEach(function (button) {
      button.addEventListener("click", function () {
        activeFilter = button.dataset.filter;
        document.querySelectorAll(".entity-filter").forEach(function (candidate) {
          var active = candidate === button;
          candidate.classList.toggle("active", active);
          candidate.setAttribute("aria-pressed", String(active));
        });
        renderEntityButtons();
      });
    });

    var clearButton = document.getElementById("entity-clear");
    if (clearButton) clearButton.addEventListener("click", clearSelection);
  }

  function loadSource(view) {
    var code = document.getElementById(view + "-source-code");
    if (!code || !SOURCE_URLS[view]) return;
    if (sourceCache[view]) {
      code.textContent = sourceCache[view];
      return;
    }
    code.textContent = "Loading " + SOURCE_URLS[view] + "…";
    fetch(SOURCE_URLS[view], { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.text();
      })
      .then(function (text) {
        sourceCache[view] = text;
        code.textContent = text;
      })
      .catch(function (error) {
        code.textContent = "Could not load " + SOURCE_URLS[view] + ": " + error.message;
      });
  }

  function setViewerView(view) {
    document.querySelectorAll(".viewer-tab").forEach(function (button) {
      var active = button.dataset.view === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll(".viewer-panel").forEach(function (panel) {
      panel.hidden = panel.dataset.view !== view;
    });

    if (view === "rendered") {
      if (rawLink) {
        rawLink.href = SOURCE_URLS.html;
        rawLink.textContent = "Open rendered article ↗";
      }
    } else {
      loadSource(view);
      if (rawLink) {
        rawLink.href = SOURCE_URLS[view];
        rawLink.textContent = "Open " + view.toUpperCase() + " file ↗";
      }
    }
  }

  function initViewerTabs() {
    document.querySelectorAll(".viewer-tab").forEach(function (button) {
      button.addEventListener("click", function () { setViewerView(button.dataset.view); });
    });
  }

  function initExplorer() {
    renderEmptyDetail();
    initFilters();
    initViewerTabs();

    if (frame) {
      frame.addEventListener("load", function () {
        if (pendingId || selectedId) highlightArticle(pendingId || selectedId, false);
      });
    }

    fetch(DATA_URL, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        entities = data;
        renderEntityButtons();
        if (status) status.textContent = entities.length + " entities loaded from the TEI and RDF graph.";
      })
      .catch(function (error) {
        if (entityList) entityList.textContent = "Could not load entity data.";
        if (status) status.textContent = "Entity explorer unavailable: " + error.message;
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initExplorer);
  } else {
    initExplorer();
  }
})();
