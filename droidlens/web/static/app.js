/* ── DroidLens Graph Browser — Frontend ───────────────────────────── */
"use strict";

// ── Colour map ────────────────────────────────────────────────────────────────
const NODE_COLORS = {
  Class:         "#6c63ff",
  AbstractClass: "#a78bfa",
  Interface:     "#00d4aa",
  Enum:          "#fb923c",
  Object:        "#38bdf8",
  Method:        "#f472b6",
  Function:      "#e879f9",
  Field:         "#4ade80",
  Property:      "#34d399",
  Package:       "#facc15",
};
const EDGE_COLORS = {
  CONTAINS:      "#334155",
  EXTENDS:       "#00d4aa",
  IMPLEMENTS:    "#6c63ff",
  CALLS:         "#f472b6",
  USES:          "#94a3b8",
  OVERRIDES:     "#fb923c",
  INSTANTIATES:  "#38bdf8",
};
function nodeColor(type) { return NODE_COLORS[type] || "#94a3b8"; }
function edgeColor(type) { return EDGE_COLORS[type] || "#334155"; }

// ── State ─────────────────────────────────────────────────────────────────────
let cy = null;
let allData = { nodes: [], edges: [] };
let currentLayout = "cose";
let activeTypes = new Set(Object.keys(NODE_COLORS));
let statsData = {};

// ── Cytoscape init ────────────────────────────────────────────────────────────
function initCy(elements) {
  if (cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    style: buildStyle(),
    wheelSensitivity: 0.3,
    minZoom: 0.05,
    maxZoom: 4,
  });

  cy.on("tap", "node", onNodeTap);
  cy.on("mouseover", "node", onNodeHover);
  cy.on("mouseout",  "node", onNodeOut);
  cy.on("tap", (e) => { if (e.target === cy) closeDetail(); });

  runLayout();
}

function buildStyle() {
  return [
    {
      selector: "node",
      style: {
        "background-color": (n) => nodeColor(n.data("type")),
        "background-opacity": 0.9,
        "border-width": 2,
        "border-color": (n) => nodeColor(n.data("type")),
        "border-opacity": 0.5,
        "label": "data(name)",
        "color": "#e2e8f0",
        "font-size": 10,
        "font-family": "Inter, sans-serif",
        "font-weight": 500,
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-outline-color": "#080b12",
        "text-outline-width": 1,
        "width": (n) => nodeSize(n.data("type")),
        "height": (n) => nodeSize(n.data("type")),
        "shape": (n) => nodeShape(n.data("type")),
        "transition-property": "background-color, border-color, width, height",
        "transition-duration": "0.15s",
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 3,
        "border-opacity": 1,
        "border-color": "#fff",
        "shadow-blur": 16,
        "shadow-color": (n) => nodeColor(n.data("type")),
        "shadow-opacity": 0.8,
        "shadow-offset-x": 0,
        "shadow-offset-y": 0,
      },
    },
    {
      selector: "node.highlighted",
      style: {
        "border-width": 3,
        "border-opacity": 1,
        "opacity": 1,
      },
    },
    {
      selector: "node.dimmed",
      style: { "opacity": 0.15 },
    },
    {
      selector: "edge",
      style: {
        "width": 1.5,
        "line-color": (e) => edgeColor(e.data("type")),
        "line-opacity": 0.6,
        "target-arrow-color": (e) => edgeColor(e.data("type")),
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.7,
        "curve-style": "bezier",
        "label": "",
      },
    },
    {
      selector: "edge.highlighted",
      style: { "line-opacity": 1, "width": 2.5 },
    },
    {
      selector: "edge.dimmed",
      style: { "line-opacity": 0.04 },
    },
  ];
}

function nodeSize(type) {
  const sizes = { Package: 40, Class: 28, AbstractClass: 28, Interface: 24, Enum: 22, Object: 24, Method: 16, Function: 16, Field: 12, Property: 12 };
  return sizes[type] || 18;
}
function nodeShape(type) {
  const shapes = { Interface: "diamond", Enum: "pentagon", Object: "hexagon", Method: "ellipse", Function: "ellipse", Field: "rectangle", Property: "rectangle" };
  return shapes[type] || "ellipse";
}

// ── Layout ────────────────────────────────────────────────────────────────────
function runLayout() {
  if (!cy) return;
  const layouts = {
    cose:      { name: "cose",  animate: true, animationDuration: 600, nodeRepulsion: 8000, idealEdgeLength: 80 },
  };
  cy.layout(layouts[currentLayout] || layouts.cose).run();
}

// ── Load graph data ───────────────────────────────────────────────────────────
async function loadGraph() {
  showLoading(true);
  try {
    const types = [...activeTypes].join(",");
    const resp = await fetch(`/api/graph?node_types=${encodeURIComponent(types)}&max_nodes=600`);
    allData = await resp.json();
    renderGraph(allData);

    const statsResp = await fetch("/api/stats");
    statsData = await statsResp.json();
    updateStatsBar(statsData);
    updateProjectName(statsData);
    buildFilterList(statsData);
    buildEdgeLegend();
  } catch (e) {
    showToast("Failed to load graph: " + e.message, 4000);
  } finally {
    showLoading(false);
  }
}

function renderGraph(data) {
  const elements = [
    ...data.nodes.map((n) => ({
      group: "nodes",
      data: { id: n.id, label: n.name, ...n },
    })),
    ...data.edges.map((e) => ({
      group: "edges",
      data: { id: e.id, source: e.source_id, target: e.target_id, ...e },
    })),
  ];
  initCy(elements);
  document.getElementById("stat-nodes").textContent = data.nodes.length;
  document.getElementById("stat-edges").textContent = data.edges.length;
}

// ── Filters ───────────────────────────────────────────────────────────────────
function buildFilterList(stats) {
  const container = document.getElementById("filter-list");
  const byType = stats.nodes_by_type || {};
  container.innerHTML = "";
  Object.entries(NODE_COLORS).forEach(([type, color]) => {
    const count = byType[type] || 0;
    const checked = activeTypes.has(type);
    const div = document.createElement("div");
    div.className = "filter-item";
    div.innerHTML = `
      <input type="checkbox" id="f-${type}" ${checked ? "checked" : ""} />
      <span class="filter-dot" style="background:${color}"></span>
      <label class="filter-label" for="f-${type}">${type}</label>
      <span class="filter-count">${count}</span>
    `;
    div.querySelector("input").addEventListener("change", (e) => {
      e.target.checked ? activeTypes.add(type) : activeTypes.delete(type);
      loadGraph();
    });
    container.appendChild(div);
  });
}

function buildEdgeLegend() {
  const container = document.getElementById("edge-legend-list");
  if (!container) return;
  container.innerHTML = "";
  Object.entries(EDGE_COLORS).forEach(([type, color]) => {
    const div = document.createElement("div");
    div.className = "edge-legend-item";
    div.innerHTML = `
      <div class="edge-legend-line" style="background:${color}"></div>
      <div class="edge-legend-label">${type}</div>
    `;
    container.appendChild(div);
  });
}

// ── Search ────────────────────────────────────────────────────────────────────
let searchTimer = null;
document.getElementById("search-input").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  if (!q) { clearSearchResults(); return; }
  searchTimer = setTimeout(() => doSearch(q), 250);
});

async function doSearch(q) {
  const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
  const results = await resp.json();
  renderSearchResults(results);
}

function renderSearchResults(results) {
  const container = document.getElementById("search-results");
  container.innerHTML = "";
  if (!results.length) {
    container.innerHTML = `<div style="padding:12px;color:var(--text-muted);font-size:12px;">No results</div>`;
    return;
  }
  results.slice(0, 30).forEach((n) => {
    const div = document.createElement("div");
    div.className = "search-result-item";
    div.innerHTML = `
      <span class="sri-dot" style="background:${nodeColor(n.type)}"></span>
      <div style="min-width:0">
        <div class="sri-name">${n.name}</div>
        <div class="sri-pkg">${n.package_name || n.qualified_name || ""}</div>
      </div>
    `;
    div.addEventListener("click", () => focusNode(n.id));
    container.appendChild(div);
  });
}

function clearSearchResults() {
  document.getElementById("search-results").innerHTML = "";
}

function focusNode(nodeId) {
  if (!cy) return;
  const node = cy.getElementById(nodeId);
  if (!node || !node.length) { showToast("Node not visible — adjust filters."); return; }
  cy.animate({ fit: { eles: node.closedNeighborhood(), padding: 80 }, duration: 400 });
  node.select();
  showDetail(node.data());
}

// ── Node interactions ─────────────────────────────────────────────────────────
function onNodeTap(e) {
  const node = e.target;
  dimAll();
  highlightNeighborhood(node);
  showDetail(node.data());
  showCodeViewer(node.data("file_path"), node.data("line_number"), node.data("language"));
}

function onNodeHover(e) {
  const node = e.target;
  const pos = e.renderedPosition || { x: 0, y: 0 };
  const wrap = document.getElementById("graph-wrap");
  const rect = wrap.getBoundingClientRect();
  const tt = document.getElementById("hover-tooltip");
  tt.innerHTML = `<strong>${node.data("name")}</strong><br/><span style="color:var(--text-dim)">${node.data("type")} · ${node.data("language") || ""}</span>`;
  tt.style.display = "block";
  tt.style.left = (pos.x + rect.left + 12) + "px";
  tt.style.top  = (pos.y + rect.top  - 10) + "px";
}
function onNodeOut() {
  document.getElementById("hover-tooltip").style.display = "none";
}

function dimAll() {
  cy.elements().removeClass("highlighted dimmed");
  cy.elements().addClass("dimmed");
}
function highlightNeighborhood(node) {
  const hood = node.closedNeighborhood();
  hood.removeClass("dimmed").addClass("highlighted");
}

// ── Detail panel ──────────────────────────────────────────────────────────────
async function showDetail(nodeData) {
  const panel = document.getElementById("detail-panel");
  const body  = document.getElementById("detail-body");
  panel.classList.add("open");

  body.innerHTML = `<div style="color:var(--text-dim);font-size:13px;padding:20px 0;text-align:center;">Loading…</div>`;

  try {
    const resp = await fetch(`/api/node/${nodeData.id}`);
    const data = await resp.json();
    renderDetailPanel(data);
  } catch {
    body.innerHTML = `<div style="color:var(--text-dim);font-size:13px;">Failed to load node detail.</div>`;
  }
}

function renderDetailPanel(data) {
  const n = data.node;
  const color = nodeColor(n.type);
  const body  = document.getElementById("detail-body");

  const relSection = (title, items, isOutgoing) => {
    if (!items.length) return "";
    const rows = items.map((e) => {
      const other = e.other_node;
      if (!other) return "";
      return `<div class="related-item" data-id="${other.id}">
        <span class="related-dot" style="background:${nodeColor(other.type)}"></span>
        <span class="related-name">${other.name}</span>
        <span class="related-badge">${e.type}</span>
      </div>`;
    }).join("");
    return `<div class="detail-section">
      <div class="detail-section-title">${title}</div>
      ${rows}
    </div>`;
  };

  body.innerHTML = `
    <div class="detail-type-badge" style="background:${color}22;color:${color}">
      ${typeIcon(n.type)} ${n.type}
    </div>
    <div class="detail-name">${n.name}</div>
    <div class="detail-qname">${n.qualified_name || n.name}</div>

    <div class="detail-section">
      <div class="detail-section-title">Info</div>
      <div class="detail-kv"><span class="k">Language</span><span class="v">${n.language || "—"}</span></div>
      <div class="detail-kv"><span class="k">Package</span><span class="v">${n.package_name || "—"}</span></div>
      <div class="detail-kv"><span class="k">Visibility</span><span class="v">${n.visibility || "—"}</span></div>
      <div class="detail-kv"><span class="k">Abstract</span><span class="v">${n.is_abstract ? "yes" : "no"}</span></div>
      <div class="detail-kv">
        <span class="k">File</span>
        <span class="v" style="font-size:10px; display:flex; align-items:center; gap:8px;">
          ${shortPath(n.file_path)}
        </span>
      </div>
      <div class="detail-kv"><span class="k">Line</span><span class="v">${n.line_number || "—"}</span></div>
    </div>

    ${relSection("Outgoing Relations", data.outgoing || [], true)}
    ${relSection("Incoming Relations", data.incoming || [], false)}
  `;

  // Click related nodes to navigate
  body.querySelectorAll(".related-item[data-id]").forEach((el) => {
    el.addEventListener("click", () => focusNode(el.dataset.id));
  });
}

function typeIcon(type) {
  const icons = { Class:"⬡", AbstractClass:"⬡", Interface:"◇", Enum:"⬠", Object:"⬡", Method:"ƒ", Function:"ƒ", Field:"▪", Property:"▪", Package:"📦" };
  return icons[type] || "●";
}
function shortPath(fp) {
  if (!fp) return "—";
  const parts = fp.replace(/\\/g, "/").split("/");
  return parts.slice(-3).join("/");
}

function closeDetail() {
  document.getElementById("detail-panel").classList.remove("open");
  document.getElementById("code-panel").classList.remove("open");
  cy && cy.elements().removeClass("highlighted dimmed");
}

// ── Stats & project info ───────────────────────────────────────────────────────
function updateStatsBar(stats) {
  document.getElementById("stat-nodes").textContent = stats.node_count ?? "—";
  document.getElementById("stat-edges").textContent = stats.edge_count ?? "—";
}
function updateProjectName(stats) {
  const el = document.getElementById("project-name");
  el.textContent = stats.project ? `📁 ${stats.project}` : "No project loaded";
}

// ── Controls ──────────────────────────────────────────────────────────────────
document.getElementById("btn-zoom-in").addEventListener("click",  () => cy && cy.zoom({ level: cy.zoom() * 1.25, renderedPosition: { x: cy.width()/2, y: cy.height()/2 } }));
document.getElementById("btn-zoom-out").addEventListener("click", () => cy && cy.zoom({ level: cy.zoom() * 0.8,  renderedPosition: { x: cy.width()/2, y: cy.height()/2 } }));
document.getElementById("btn-fit").addEventListener("click",      () => cy && cy.fit(undefined, 40));
document.getElementById("btn-reload").addEventListener("click",   () => loadGraph());
document.getElementById("detail-close").addEventListener("click", closeDetail);

// ── Code Viewer ───────────────────────────────────────────────────────────────
async function showCodeViewer(filePath, lineNumber, language) {
  const panel = document.getElementById("code-panel");
  if (!filePath) {
    panel.classList.remove("open");
    return;
  }
  
  const title = document.getElementById("code-panel-title");
  const codeContent = document.getElementById("code-content");
  
  title.textContent = filePath.split(/[\\/]/).pop();
  title.title = filePath;
  codeContent.textContent = "Loading...";
  codeContent.className = "hljs"; // Reset hljs classes
  panel.classList.add("open");
  
  try {
    const resp = await fetch(`/api/source?file_path=${encodeURIComponent(filePath)}`);
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Failed to load file");
    }
    const data = await resp.json();
    
    // Highlight the raw string first, then split by newline and wrap.
    let highlighted;
    if (language === "kotlin" || language === "java") {
      highlighted = hljs.highlight(data.content, { language: language }).value;
    } else {
      highlighted = hljs.highlightAuto(data.content).value;
    }
    
    const hlLines = highlighted.split('\n');
    let finalHtml = "";
    hlLines.forEach((line, idx) => {
      const currentLine = idx + 1;
      if (lineNumber && currentLine === lineNumber) {
        finalHtml += `<span class="hl-line" id="hl-target">${line || ' '}</span>\n`;
      } else {
        finalHtml += `${line}\n`;
      }
    });
    
    codeContent.innerHTML = finalHtml;
    
    // Auto-scroll to the highlighted line
    setTimeout(() => {
      const target = document.getElementById("hl-target");
      if (target) {
        // scroll inside the panel body
        target.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
    
  } catch (e) {
    codeContent.textContent = "Error: " + e.message;
  }
}

document.getElementById("code-panel-close").addEventListener("click", () => {
  document.getElementById("code-panel").classList.remove("open");
});

// Theme toggle
const themeBtn = document.getElementById("btn-theme");
const iconSun = document.getElementById("icon-sun");
const iconMoon = document.getElementById("icon-moon");
const hljsTheme = document.getElementById("hljs-theme");

function setTheme(theme) {
  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
    iconSun.style.display = "none";
    iconMoon.style.display = "block";
    hljsTheme.href = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css";
    localStorage.setItem("droidlens-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
    iconSun.style.display = "block";
    iconMoon.style.display = "none";
    hljsTheme.href = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css";
    localStorage.setItem("droidlens-theme", "dark");
  }
}

// ── Resizers ──────────────────────────────────────────────────────────────────
function initResizer(resizerId, panelId, isRight, minW, maxW) {
  const resizer = document.getElementById(resizerId);
  const panel = document.getElementById(panelId);
  if (!resizer || !panel) return;

  let isDragging = false;
  let startX, startWidth;

  resizer.addEventListener("mousedown", (e) => {
    isDragging = true;
    startX = e.clientX;
    startWidth = panel.offsetWidth;
    panel.classList.add("no-transition");
    resizer.classList.add("dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    let dx = e.clientX - startX;
    let newWidth = isRight ? startWidth + dx : startWidth - dx;
    if (newWidth < minW) newWidth = minW;
    if (newWidth > maxW) newWidth = maxW;
    
    if (panelId === "sidebar") {
      document.documentElement.style.setProperty("--sidebar-w", newWidth + "px");
    } else if (panelId === "detail-panel") {
      document.documentElement.style.setProperty("--detail-w", newWidth + "px");
    } else if (panelId === "code-panel") {
      document.documentElement.style.setProperty("--code-w", newWidth + "px");
    }
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      panel.classList.remove("no-transition");
      resizer.classList.remove("dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      if (cy) setTimeout(() => cy.resize(), 50);
    }
  });
}

initResizer("resizer-sidebar", "sidebar", true, 200, 600);
initResizer("resizer-code", "code-panel", true, 300, 800);
initResizer("resizer-detail", "detail-panel", false, 250, 600);


themeBtn.addEventListener("click", () => {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  setTheme(isLight ? "dark" : "light");
});

// Init theme
const savedTheme = localStorage.getItem("droidlens-theme");
if (savedTheme) {
  setTheme(savedTheme);
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, duration = 2500) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), duration);
}

// ── Loading ───────────────────────────────────────────────────────────────────
function showLoading(show) {
  document.getElementById("loading").classList.toggle("show", show);
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadGraph();
