const DATA_URL = "./data/tree.json";

const state = {
  data: null,
  byId: new Map(),          // id -> node, built at load time (needed to resolve category-pointer nodes)
  allTitledNodes: [],       // flat [{id, title}] over every titled node, built once at load time (see collectTitledNodes)
  translitCache: new Map(), // scheme -> Map(id -> transliterated title), filled in lazily per scheme on first use (see ensureSchemeCached)
  searchIndex: new Map(),   // scheme -> Map(id -> lowercased transliterated title), same laziness as translitCache (see indexedTitle)
  siblingIds: new Map(),    // id -> [other occurrence ids of the same shared category] (both directions)
  parentPath: new Map(),    // id -> array of ancestor titles (root excluded), for "see also X > Y" hints
  multiCatTitles: new Set(),// page/index-item titles that appear under >1 category (see build_category_membership_maps
                             // in pipeline/process.py -- each such category independently shows the full real item, so
                             // this is purely a UI hint, not a dedup mechanism) -- powers the "also filed under..." button
  multiCatLocations: new Map(), // page/index-item title -> [{path, stats}] over every occurrence, for the hover tooltip/highlight
  selectedCatId: null,
  axis: localStorage.getItem("axis") || "loc", // which of root.children is being browsed: loc | lst.
                             // Both branches cover the same 8547 documents by different routes, so
                             // showing them as siblings under one root meant identical stat lines and
                             // a redundant "by folder" wrapper in the main pane. One is active at a
                             // time instead, and activeBranch() stands in for the root everywhere below.
  statsByDocId: new Map(),   // doc id -> its own byte stats, so a filtered node can be retotalled from
                             // the documents that survived, by whichever route it reaches them.
  categoryIndex: new Map(),  // canonical category tag -> Set(doc id) over the whole corpus, built once at
                             // load time from each page's meta.categories (see buildCategoryIndex).
                             // Tags arrive already normalized by pipeline/parse_snapshot -- the frontend
                             // never folds, aliases, or de-duplicates them.
  activeFilters: [],         // category tags ANDed together; a document must carry every one to show.
                             // Categories were a third browse axis until 2026-08-13. As a branch they
                             // rolled up per-placement stats and reported 26718 "texts" for the same
                             // 8547 documents; a filter has no rollup, so that class of bug can't recur.
  rootExpanded: false,      // when true, "All" renders the full nested tree (renderCategoryBlock)
                             // instead of the lightweight one-row-per-top-level-category summary
                             // (renderRootOverview) -- see the "Expand All" button there.
  includeOrphans: localStorage.getItem("includeOrphans") !== "0", // when true (default), the "All"
                             // headline stats use data.all_stats (root + असम्बद्धवर्गीकृतम्, the orphan
                             // bucket) instead of root.stats (the central, well-categorized tree only) --
                             // user-toggleable via the "include asambaddhavargīkṛta" pill, persisted like theme.
  scheme: "iast",           // devanagari | iast | hk | itrans | slp1
  expanded: new Set(),      // node ids expanded in sidebar
  searchQuery: "",
  searchExact: false,       // when true, search matches a node's whole (transliterated, lowercased) title
                             // exactly instead of substring-matching searchQuery -- user-toggleable via the
                             // "exact" checkbox, and set automatically by the multi-category magnifying-glass
                             // button, since a short/common title (e.g. "योगवासिष्ठः") can otherwise
                             // substring-match thousands of unrelated titles, defeating the button's purpose
                             // of finding its own handful of sibling occurrences.
  expandedPageLists: new Set(), // category ids whose page/index-item list has been expanded past the cap
  expandedSubpages: new Set(),  // page ids whose nested subpages sub-list is expanded (collapsed by default)
  collapsedSubpages: new Set(), // subpage expand-keys the user explicitly collapsed while a search was active --
                                 // overrides search's force-expand default so a disclosure arrow always does
                                 // what it says, even if that hides a subpage-only search hit (see renderPageLi)
};

// Rendering every descendant page as a DOM node is what's actually slow (there are
// ~20k pages total, and some single categories like पुराणानि have thousands). Any
// page/index-item list past this length renders capped with a "show all" button.
const PAGE_LIST_CAP = 300;

// Searching is a full tree walk (~38k titled nodes) plus a full re-render of every
// match, uncapped -- a 1-2 character query is both too broad to be useful (matches
// a huge fraction of the corpus) and the most expensive case to render. Below this
// length, search is simply inactive (same as an empty query).
const MIN_SEARCH_QUERY_LENGTH = 3;

function isSearchActive() {
  if (state.searchExact) return state.searchQuery.length > 0;
  return state.searchQuery.length >= MIN_SEARCH_QUERY_LENGTH;
}

// Navigates to a category by id, exiting search mode first. While search is
// active, renderMain shows the full filtered tree from root regardless of
// state.selectedCatId (see its isSearchActive() branch), so setting
// selectedCatId alone would otherwise produce no visible change -- every
// sidebar/breadcrumb/"see also" navigation click needs to clear search too
// for the click to do anything the user can see.
function selectCategory(catId) {
  state.selectedCatId = catId;
  state.rootExpanded = false;
  state.searchQuery = "";
  state.searchExact = false;
  state.collapsedSubpages.clear();  // leaving search discards its per-result collapse state
  const input = document.getElementById("searchInput");
  if (input) input.value = "";
  const exactToggle = document.getElementById("searchExactToggle");
  if (exactToggle) exactToggle.checked = false;
}

// --- utils

function isExpandAllGesture(ev) {
  // macOS: Option=altKey. Windows/Linux: Alt=altKey.
  // Fallbacks: Shift (browser-safe), Ctrl / Cmd.
  return !!(ev.altKey || ev.shiftKey || ev.ctrlKey || ev.metaKey);
}

// Flat [{id, title, deva}] over every titled node (categories/pointers, pages,
// subpages, index items) -- built once at load time, no transliteration involved.
// This is the source list that ensureSchemeCached()/indexedTitle() lazily
// transliterate against per scheme.
//
// `deva` is the node's Devanagari title where the site gives one (8477 of 8547
// documents). It is what the transliterator must read: `title` is the site's
// free-text English label ("Akshara Ramayanam"), which is not in any scheme and
// carries no diacritics, so feeding it to Sanscript as Devanagari was a silent
// no-op -- the string came back unchanged and every scheme rendered identically.
// Category nodes have no Devanagari form (their titles are slugs like "aShTaka"),
// so they fall back to `title` and keep their existing behaviour.
function collectTitledNodes(root) {
  const nodes = [];
  const add = (n) => {
    if (!n.id) return;
    nodes.push({ id: n.id, title: n.title, deva: n.meta?.title_deva || "" });
  };

  const walkPage = (p) => {
    add(p);
    for (const sp of (p.subpages || [])) walkPage(sp);
  };

  const walkCategory = (node) => {
    add(node);
    for (const p of (node.pages || [])) walkPage(p);
    for (const it of (node.index_items || [])) add(it);
    for (const ch of (node.children || [])) walkCategory(ch);
  };

  walkCategory(root);
  return nodes;
}

// Transliterates every title into `scheme` exactly once, the first time that scheme
// is actually needed (initial load only warms the frontend's default scheme -- see
// loadData), and caches the result forever in state.translitCache. Devanagari needs
// no transliteration call at all, since it's the data's native storage script.
function ensureSchemeCached(scheme) {
  if (state.translitCache.has(scheme)) return state.translitCache.get(scheme);
  const map = new Map();
  for (const { id, title, deva } of state.allTitledNodes) {
    // Only the Devanagari title can be transliterated. Without one -- category
    // nodes, and the ~70 documents whose Devanagari the site omits -- the
    // English label is all there is, and it is shown as-is in every scheme
    // rather than being run through a converter that cannot read it.
    if (!deva) {
      map.set(id, title);
      continue;
    }
    if (scheme === "devanagari") {
      map.set(id, deva);
      continue;
    }
    try {
      map.set(id, window.Sanscript.t(deva, "devanagari", scheme));
    } catch {
      map.set(id, title);
    }
  }
  state.translitCache.set(scheme, map);
  return map;
}

// Per-node display title in the current scheme, drawn from the lazy per-scheme
// cache -- never calls Sanscript.t directly outside of ensureSchemeCached.
function displayTitle(raw, id) {
  if (!id) {
    // Rare fallback: a caller has a raw title string but no node id (e.g. an
    // ancestor title captured before this function existed) -- transliterate
    // directly rather than skipping display, but don't cache under a fake key.
    return translitTextUncached(raw);
  }
  return ensureSchemeCached(state.scheme).get(id) ?? raw;
}

function translitTextUncached(s) {
  if (!s) return s;
  if (state.scheme === "devanagari") return s;
  try {
    return window.Sanscript.t(s, "devanagari", state.scheme);
  } catch {
    return s;
  }
}

// Lowercased version of the per-scheme cache, built lazily alongside it (once per
// scheme, first time that scheme is searched in) -- this is what filterTree/
// filterPage/filterIndexItem match against instead of re-transliterating live.
function indexedTitleById(id) {
  const scheme = state.scheme;
  if (!state.searchIndex.has(scheme)) state.searchIndex.set(scheme, new Map());
  const cache = state.searchIndex.get(scheme);
  if (cache.has(id)) return cache.get(id);
  const translit = ensureSchemeCached(scheme).get(id) || "";
  const lowered = translit.toLowerCase();
  cache.set(id, lowered);
  return lowered;
}

function indexedTitle(node) {
  return indexedTitleById(node.id);
}

// The author, for search only. Kept out of the title index because that one
// also backs exact match, and a title and an author sharing one string could be
// matched exactly by neither. No transliteration: sanskritdocuments writes its
// authors in Latin ("Shri Nagesh Karambelkar", "gopAladAsa"), so there is
// nothing for Sanscript to read, and only 3677 of the 9756 documents carry one.
function indexedAuthor(node) {
  const author = node.meta?.author;
  return author ? author.toLowerCase() : "";
}

const CAT_TYPES = new Set(["category", "category-pointer"]);

function walkCategories(node, fn) {
  if (node.id) fn(node);
  for (const ch of (node.children || [])) walkCategories(ch, fn);
}

// Find category node by id (matches category-pointer occurrences too -- each is
// independently selectable, distinct from the occurrence that holds real content).
function findCatById(node, id) {
  if (!node) return null;
  if (CAT_TYPES.has(node.type) && node.id === id) return node;
  for (const ch of (node.children || [])) {
    const hit = findCatById(ch, id);
    if (hit) return hit;
  }
  return null;
}

// Resolve a category-pointer occurrence to the occurrence holding its real content
// (children/pages/index_items/stats). Non-pointer nodes resolve to themselves.
function resolveContent(node) {
  if (!node) return node;
  if (node.type === "category-pointer") return state.byId.get(node.points_to) || node;
  return node;
}

// Path of ancestor category nodes from (but not including) root down to (but not including) id.
function findAncestorPath(node, id, path = []) {
  if (!node) return null;
  if (CAT_TYPES.has(node.type) && node.id === id) return path;
  for (const ch of (node.children || [])) {
    const hit = findAncestorPath(ch, id, [...path, node]);
    if (hit) return hit;
  }
  return null;
}

function setExpandedDeep(catNode, expand) {
  walkCategories(catNode, (c) => {
    if (expand) state.expanded.add(c.id);
    else state.expanded.delete(c.id);
  });
}

// --- rendering

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on") && k.length > 2 && typeof v === "function") n.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(n.dataset, v);
    else n.setAttribute(k, v);
  }
  for (const kid of kids) {
    if (kid == null) continue;
    if (typeof kid === "string") n.appendChild(document.createTextNode(kid));
    else n.appendChild(kid);
  }
  return n;
}

function formatBytes(bytes) {
  if (bytes == null) return "";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

// transliterated_bytes (IAST) is the primary size figure displayed: raw_bytes is
// Devanagari wikitext including markup/template overhead, not meaningful on its
// own; content_bytes is Devanagari post-strip, still not directly comparable/
// intuitive since Devanagari UTF-8 runs ~1.975x IAST bytes for the same text.
// Falls back to content_bytes (e.g. when transliteration was skipped for a faster
// pipeline run) and then raw_bytes.
function contentSizeBytes(stats) {
  if (!stats) return null;
  if (stats.transliterated_bytes) return stats.transliterated_bytes;
  if (stats.content_bytes != null) return stats.content_bytes;
  return stats.raw_bytes;
}

// "2024-06" -> "Jun 2024", matching how the parent's federated search prints
// the same field. A bare YYYY-MM reads as data; the month name reads as a
// date, and it is the same width.
//
// The value comes from meta.updated, which the pipeline has already parsed
// from the site's free-text `Latest update` ("May 12, 2019", "Julu 11, 2018",
// "11-Feb-2015") -- see build_tree. Nothing here re-parses that text: one
// parser for the corpus, in Python, where the upstream typos are catalogued.
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function formatDate(iso) {
  if (!iso) return "";
  const m = /^(\d{4})(?:-(\d{2}))?/.exec(iso);
  if (!m) return "";
  if (!m[2]) return m[1];
  const name = MONTH_NAMES[Number(m[2]) - 1];
  return name ? `${name} ${m[1]}` : m[1];
}

function formatStats(stats, { includeDate, includeCount } = {}) {
  if (!stats) return "";
  const size = formatBytes(contentSizeBytes(stats));
  if (!size) return "";
  const parts = [size];
  if (stats.text_count != null) parts.push(`${stats.text_count} ${stats.text_count === 1 ? "text" : "texts"}`);
  if (includeCount && stats.count != null) parts.push(`${stats.count} ${stats.count === 1 ? "page" : "pages"}`);
  if (includeDate) {
    const date = formatDate(stats.last_changed);
    if (date) parts.push(date);
  }
  return `(${parts.join(", ")})`;
}

// The branch the axis switch has selected. Everything that used to treat
// data.root as the tree root now goes through here, so only one axis is ever
// on screen. Falls back to the first child (and then the root itself) if a
// persisted axis names a branch this tree.json does not have.
function activeBranch() {
  const root = state.data.root;
  const children = root.children || [];
  return children.find((ch) => ch.id === state.axis) || children[0] || root;
}

function setAxis(axis) {
  if (state.axis === axis) return;
  state.axis = axis;
  localStorage.setItem("axis", axis);
  invalidateVisibleBranch();
  // Node ids are branch-scoped, so a selection or expansion from the old axis
  // means nothing in the new one. Reset rather than leave a dangling id.
  state.selectedCatId = null;
  state.expanded.clear();
  state.rootExpanded = false;
  renderAxisSwitch();
  renderSidebarTree();
  renderMain();
}

function renderAxisSwitch() {
  for (const ch of (state.data.root.children || [])) {
    const btn = document.getElementById(`axis-${ch.id}`);
    if (!btn) continue;
    btn.classList.toggle("active", ch.id === activeBranch().id);
    if (!btn.dataset.bound) {
      btn.dataset.bound = "1";
      btn.onclick = () => setAxis(ch.id);
    }
  }
}

function renderSidebarTree() {
  const root = visibleBranch();
  const host = document.getElementById("sidebarTree");
  host.innerHTML = "";

  for (const ch of (root.children || [])) {
    host.appendChild(renderSidebarNode(ch, 0));
  }

  // "All" is the active branch's own total. Each branch reaches every document
  // exactly once (build_tree.distinct_stats), so all three agree -- but reading
  // it off the branch keeps the number honest if that ever stops being true.
  const allStats = root.stats;

  const allStatsEl = document.getElementById("allStats");
  if (allStatsEl) {
    allStatsEl.textContent = formatStats(allStats);
  }

  const allRowEl = document.getElementById("allRow");
  if (allRowEl) {
    const tooltipStatsText = formatStats(allStats, { includeCount: true });
    allRowEl.title = tooltipStatsText ? `All ${tooltipStatsText}` : "";
    allRowEl.classList.toggle("selected", state.selectedCatId == null || state.selectedCatId === root.id);
    allRowEl.onclick = (ev) => {
      if (isExpandAllGesture(ev)) {
        setExpandedDeep(root, true);
      }
      selectCategory(null);
      renderSidebarTree();
      renderMain();
      closeSidebarIfMobile();
    };
    // allRowEl is a static element (re-fetched, not re-created) on every render --
    // bind the long-press gesture once rather than accumulating listeners.
    if (!allRowEl.dataset.longPressExpandBound) {
      allRowEl.dataset.longPressExpandBound = "1";
      bindLongPressExpand(allRowEl, () => {
        setExpandedDeep(root, true);
        renderSidebarTree();
        renderMain();
      });
    }
  }
}

function renderSidebarNode(catNode, depth) {
  const isPointer = catNode.type === "category-pointer";
  // A pointer occurrence has no children/pages/index_items of its own -- expanding
  // it browses into the occurrence that actually holds the content.
  const content = resolveContent(catNode);

  const isExpanded = state.expanded.has(catNode.id);
  const hasKids = (content.children || []).length > 0;

  const toggleNode = (expandAll) => {
    const currentlyExpanded = state.expanded.has(catNode.id);
    if (currentlyExpanded) {
      // Collapsing: always collapse deep so that re-opening shows only immediate children
      setExpandedDeep(catNode, false);
    } else {
      // Expanding
      if (expandAll) {
        setExpandedDeep(catNode, true);
      } else {
        state.expanded.add(catNode.id);
      }
    }
    renderSidebarTree();
    renderMain();
  };

  // Both branches are flat -- `by folder` since sublocation stopped shaping
  // the tree, `by topic` always -- so a row has no children to disclose and
  // the arrow column is omitted rather than rendered as a bullet placeholder.
  // The machinery above is kept, not inlined away: it costs nothing, and a
  // future branch with real depth needs only the arrow back.
  const toggleArrow = hasKids
    ? el("span", {
        class: "toggleArrow",
        onclick: (ev) => {
          ev.stopPropagation();
          toggleNode(isExpandAllGesture(ev));
        }
      }, isExpanded ? "▾" : "▸")
    : null;
  // Touch devices have no Option/Shift-click -- long-pressing the disclosure
  // arrow does the same "expand all descendants" gesture instead.
  if (toggleArrow) bindLongPressExpand(toggleArrow, () => toggleNode(true));

  // Every occurrence of a shared category is equally real and shows its own real
  // stats -- no occurrence is privileged over another for display purposes.
  const statsText = formatStats(catNode.stats);

  // Shared-category bookkeeping: siblings are the other occurrence(s) of this same
  // category elsewhere in the tree. Non-shared categories have none.
  const siblings = state.siblingIds.get(catNode.id) || [];
  const isShared = siblings.length > 0;
  // Group key for hover highlighting -- same value for every occurrence in the group.
  const groupKey = isPointer ? catNode.points_to : (isShared ? catNode.id : null);
  const siblingLocations = siblings
    .map((sid) => (state.parentPath.get(sid) || []).map((t) => translitTextUncached(t)).join(" > "))
    .filter(Boolean);
  const tooltipStatsText = formatStats(catNode.stats, { includeCount: true });
  const nameAndStats = tooltipStatsText ? `${displayTitle(catNode.title, catNode.id)} ${tooltipStatsText}` : displayTitle(catNode.title, catNode.id);
  const rowTitle = siblingLocations.length
    ? `Also filed under: ${siblingLocations.join("; ")}\n${nameAndStats}`
    : nameAndStats;

  const row = el("div", {
    class: "row" + (state.selectedCatId === catNode.id ? " selected" : ""),
    dataset: groupKey ? { sharedGroup: groupKey } : {},
    title: rowTitle,
    onclick: () => {
      selectCategory(catNode.id);
      renderSidebarTree();
      renderMain();
      closeSidebarIfMobile();
    },
    onmouseenter: () => setSharedGroupHighlight(groupKey, true),
    onmouseleave: () => setSharedGroupHighlight(groupKey, false),
  },
    toggleArrow,
    el("span", { class: depth === 0 ? "title topLevel" : "title" }, displayTitle(catNode.title, catNode.id)),
    statsText ? el("span", { class: depth === 0 ? "small topLevel" : "small", style: "margin-left:auto; padding-left:10px; opacity:0.7;" }, statsText) : null
  );

  const wrap = el("div", { class: depth ? "indent" : "" }, row);

  if (hasKids && isExpanded) {
    for (const ch of content.children) {
      wrap.appendChild(renderSidebarNode(ch, depth + 1));
    }
  }
  return wrap;
}

function renderMain() {
  const host = document.getElementById("content");
  host.innerHTML = "";

  const root = visibleBranch();

  if (isSearchActive()) {
    const filtered = filterTree(root, currentSearchMatcher());
    if (filtered) {
      host.appendChild(renderCategoryBlock(filtered, { includeLeaves: true, depth: 0, isRoot: true, isSearch: true }));
    } else {
      host.innerHTML = "<div class='block'>No results found.</div>";
    }
  } else {
    // Below MIN_SEARCH_QUERY_LENGTH, treated identically to an empty query -- the
    // normal focused view stays put rather than showing a half-active search state.
    // focused: render the selected node's own subtree in full, but wrapped in sticky
    // "breadcrumb" headers for its ancestors, so super-category context stays visible
    // while scrolling, instead of being discarded just because a deeper category was
    // picked in the sidebar.
    const selected = findCatById(root, state.selectedCatId) || root;
    const ancestors = findAncestorPath(root, state.selectedCatId) || [];
    // ancestors[0] is the true root (no header of its own); skip it, keep the rest.
    const breadcrumb = ancestors.slice(1);

    // The actual root has ~20k descendant pages across the whole tree -- fully
    // recursing here (as any other category selection does) would build DOM for
    // all of them on every initial load. Show one level of category summaries
    // instead; drilling into a specific category still renders its subtree in
    // full, and root's own "Expand All" button opts into the same full render.
    const isActualRoot = selected.id === root.id;
    const selectedBlock = isActualRoot && !state.rootExpanded
      ? renderRootOverview(selected)
      : renderCategoryBlock(selected, { includeLeaves: true, depth: isActualRoot ? 0 : breadcrumb.length + 1, isRoot: isActualRoot });

    let inner = selectedBlock;
    for (let i = breadcrumb.length - 1; i >= 0; i--) {
      const anc = breadcrumb[i];
      const ancDepth = i + 1;
      const header = el("div", {
        class: "panelTitle sticky-header",
        dataset: { stickyDepth: String(ancDepth) },
        style: `z-index:${1000 - ancDepth};`
      },
        el("span", {
          class: "panelTitleLink",
          onclick: () => {
            selectCategory(anc.id);
            renderSidebarTree();
            renderMain();
          },
        }, displayTitle(anc.title, anc.id)),
        (() => {
          const s = formatStats(anc.stats, { includeDate: true });
          return s ? el("span", { class: "small", style: "font-weight:normal; margin-left:8px;" }, s) : null;
        })(),
        anc.url
          ? el("a", { class: "catLinkArrow", href: anc.url, target: "_blank", rel: "noreferrer", title: "Open this page on sanskritdocuments.org" })
          : null,
        renderSeeAlso(anc)
      );
      inner = el("div", { class: "block" }, header, el("div", { style: "margin-top:10px" }, inner));
    }

    host.appendChild(inner);
  }

  positionStickyHeaders(host);
}

// Each sticky header's `top` must equal the total height of all its ancestor
// sticky headers, so nested headers stack below one another instead of overlapping.
// Computed from actual measured heights (rather than a fixed constant) since
// header height varies with title length/wrapping and stats text.
function positionStickyHeaders(host) {
  const headers = host.querySelectorAll(".sticky-header");
  for (const header of headers) {
    let offset = 0;
    let node = header.parentElement;
    while (node && node !== host) {
      const ancestorHeader = node.querySelector(":scope > .sticky-header");
      if (ancestorHeader && ancestorHeader !== header) {
        offset += ancestorHeader.getBoundingClientRect().height;
      }
      node = node.parentElement;
    }
    header.style.top = `${offset}px`;
  }
}

// Lightweight initial/root view: one row per top-level category with its stats,
// clickable to drill in via the same selection path as clicking the sidebar.
// See the comment at its call site in renderMain() for why this exists.
function renderRootOverview(root) {
  const block = el("div", {});
  // "All" is the one sidenav selection with no actual text links of its own --
  // just top-level category summaries -- so offer a way to blow it open into
  // the full nested listing, same as drilling into any other category.
  block.appendChild(
    el("button", {
      type: "button",
      class: "expandAllButton",
      style: "margin-bottom:10px;",
      onclick: () => {
        state.rootExpanded = true;
        renderMain();
      },
    }, "Expand All"),
  );
  for (const ch of (root.children || [])) {
    const statsText = formatStats(ch.stats, { includeDate: true });
    const row = el("div", {
      class: "block panelTitle",
      style: "cursor:pointer;",
      onclick: () => {
        selectCategory(ch.id);
        renderSidebarTree();
        renderMain();
      },
    },
      displayTitle(ch.title, ch.id),
      statsText ? el("span", { class: "small", style: "font-weight:normal; margin-left:8px;" }, statsText) : null,
      // Same out-link the drilled-in header carries, so the overview rows are
      // not the one place a heading names an upstream page without reaching it.
      // stopPropagation, or the row's own onclick would drill in underneath.
      ch.url
        ? el("a", {
            class: "catLinkArrow",
            href: ch.url,
            target: "_blank",
            rel: "noreferrer",
            title: "Open this page on sanskritdocuments.org",
            onclick: (ev) => ev.stopPropagation(),
          })
        : null,
    );
    block.appendChild(row);
  }
  return block;
}

// Renders a single Main-namespace page's <li> (link + size/date meta), plus, if
// it has its own MediaWiki subpages (build_tree.MainPageNode nesting), a
// collapsible toggle that reveals a nested indented sub-list. Deliberately NOT
// the same visual treatment as category nesting (renderCategoryBlock): no sticky
// header, no per-node stats block, just a plain indented <ul> -- reads as "parts
// of this page" (structural, from the page-title graph itself) rather than "a
// subcategory" (an editorial grouping).
// Is this server offering the local corpus text? Only `serve_docs.py
// --fulltext` answers /text/ with this header. On GitHub Pages the probe gets
// no header and every `txt` link stays unrendered. A runtime question, not a
// build-time one: the same docs/ is deployed either way.
let FULLTEXT_MODE = false;

async function detectFulltextMode() {
  try {
    const res = await fetch("/text/", { method: "HEAD" });
    FULLTEXT_MODE = res.headers.get("X-Fulltext-Mode") === "on";
  } catch {
    FULLTEXT_MODE = false;   // offline, file://, or no server at all
  }
}

function renderPageLi(p, ownPath) {
  const hasSubpages = (p.subpages || []).length > 0;
  // p.id alone is NOT unique per rendered occurrence -- pipeline/process.py's
  // build_page_node derives it purely from title, so the same top-level page
  // independently filed under two categories (see "Silent subpage category
  // divergence") gets the same id both places. Key expand state by id PLUS
  // the enclosing category path so expanding one occurrence's subpage list
  // doesn't also expand every other occurrence of the same page elsewhere.
  const expandKey = (ownPath || []).join("␟") + "␟" + p.id;
  // In search mode, subpages default to force-expanded so a match nested in a
  // subpage stays visible even if the user never manually expanded its parent.
  // But the disclosure arrow must never be inert: a manual collapse (recorded in
  // collapsedSubpages) always wins over that default, even when it hides a
  // subpage-only hit -- once results are on screen, the user drives the UI.
  const searchDefaultExpanded = isSearchActive() && hasSubpages && !state.collapsedSubpages.has(expandKey);
  const isExpanded = state.expandedSubpages.has(expandKey) || searchDefaultExpanded;

  const a = el("a", { href: p.url, target: "_blank", rel: "noreferrer" }, displayTitle(p.title, p.id));

  // The locally extracted text, served by `serve_docs.py --fulltext`. Two
  // conditions, both required: the build saw the text on disk (`has_text`),
  // and this server is offering it (FULLTEXT_MODE). Never renders on the
  // published site -- the text is not ours to republish. The id is
  // `doc:<path>`; the server resolves it through an index, never a join.
  const localTxt = (FULLTEXT_MODE && p.has_text)
    ? el("a", {
        href: `/text/${p.id.replace(/^doc:/, "").split("/").map(encodeURIComponent).join("/")}`,
        target: "_blank",
        rel: "noreferrer",
        class: "localTxtLink",
        title: "Open the locally extracted plain text (this machine only)",
      }, "txt")
    : null;

  // p.stats is a full rollup (this page's own size/date plus every descendant
  // subpage's, see process.py's build_page_node/recompute_page_dedup) -- shown
  // while collapsed, since then it's the only summary of what's nested inside.
  // Once expanded, the subpages are individually visible below with their own
  // sizes, so showing the rollup here too would double-count on screen; show
  // p.own_stats (this page's content alone, un-rolled-up) instead.
  const statsToShow = hasSubpages && isExpanded ? p.own_stats : p.stats;
  const metaParts = [];
  const pageSize = contentSizeBytes(statsToShow);
  if (pageSize != null) metaParts.push(formatBytes(pageSize));
  // The site's own `Latest update`, normalized to YYYY-MM by the pipeline.
  // It sits on meta, not stats: it is a fact about the document, not a
  // measurement of it, and a rolled-up parent has no single such date.
  const date = formatDate(p.meta?.updated);
  if (date) metaParts.push(date);
  const meta = metaParts.length ? ` (${metaParts.join(", ")})` : "";

  const toggleSubpages = (ev) => {
    ev.preventDefault();
    if (isExpanded) {
      state.expandedSubpages.delete(expandKey);
      // During search the row is expanded-by-default, so removing the manual
      // expand isn't enough to collapse it -- record an explicit collapse that
      // overrides the search default (see searchDefaultExpanded above).
      if (isSearchActive()) state.collapsedSubpages.add(expandKey);
    } else {
      state.expandedSubpages.add(expandKey);
      state.collapsedSubpages.delete(expandKey);
    }
    renderMain();
  };

  // The "(+ N pp)" count and the triangle are one combined disclosure control --
  // grouped together (tight gap, shared click target) rather than the count
  // living inside pageRowMain and the triangle sitting separately at the row's
  // end, so clicking the count itself also expands/collapses the subpage list.
  const toggle = hasSubpages
    ? el("span", { class: "subpageToggleGroup", onclick: toggleSubpages },
        el("span", { class: "small", style: "opacity:0.6;" }, `(+ ${p.subpages.length} pp)`),
        el("span", { class: "toggleArrow subpageToggle" },
          el("span", { class: "triangleIcon" + (isExpanded ? " expanded" : "") })),
      )
    : null;

  const row = el("div", { class: "pageRow", ...multiCatRowProps(p.title, ownPath) },
    el("span", { class: "pageRowMain" },
      a,
      meta ? el("span", { class: "small" }, meta) : null,
      localTxt,
      renderSourceIndexLinks(p.source_indexes),
      renderScanLinks(p.meta?.scans),
    ),
    toggle,
    renderMultiCatButton(p.title, p.id),
  );

  const li = el("li", {}, row);

  if (hasSubpages && isExpanded) {
    const subUl = el("ul", { class: "subpageList" });
    for (const sp of p.subpages) {
      subUl.appendChild(renderPageLi(sp, ownPath));
    }
    li.appendChild(subUl);
  }

  return li;
}

// Renders a small scan-icon link per Index item this page transcludes leaves
// from (build_tree_json's source_indexes -- see pipeline/process.py's
// build_page_node), for a reader who wants to jump to the original scan even
// though the Atlas otherwise drops a transcluded Index item from display
// entirely in favor of this page (see docs/about.html, "Transclusion").
// Absent/empty for the overwhelming majority of pages (no ProofreadPage
// involvement at all), so this returns null rather than an empty wrapper.
function renderSourceIndexLinks(sourceIndexes) {
  if (!sourceIndexes || !sourceIndexes.length) return null;
  return el("span", { class: "sourceIndexLinks" },
    ...sourceIndexes.map((src) =>
      el("a", {
        href: src.url, target: "_blank", rel: "noreferrer",
        class: "sourceIndexLink",
        title: `Scanned source: ${displayTitle(src.title)}`,
      },
        el("span", { class: "small" }, "pdf"),
        el("span", { class: "scanIcon" }),
      ),
    ),
  );
}

// Renders a scan link per scanned source the SITE links beside this document
// (build_tree's compact_scans, from pipeline/parse_scans.py).
//
// Deliberately NOT reusing renderSourceIndexLinks above, whose "Scanned
// source:" wording carries the Wikisource meaning -- the scan a text was
// transcribed FROM. sanskritdocuments.org never claims that: the same volume
// is linked from every text excerpted out of it, so one Shiva-purana scan sits
// on dozens of stotras. The wording here says "printed witness", which is all
// the site's own markup supports.
const SCAN_KIND_NOTE = {
  archive: "on archive.org",
  scannedbooks: "hosted by sanskritdocuments.org",
  "third-party": "on a third-party site",
};

function renderScanLinks(scans) {
  if (!scans || !scans.length) return null;
  return el("span", { class: "sourceIndexLinks" },
    ...scans.map((s) =>
      el("a", {
        href: s.u, target: "_blank", rel: "noreferrer",
        class: "sourceIndexLink",
        title: `Printed witness ${SCAN_KIND_NOTE[s.k] ?? ""} \u2014 a scan of an edition containing this text, not necessarily the one it was encoded from`,
      },
        el("span", { class: "small" }, "scan"),
        el("span", { class: "scanIcon" }),
      ),
    ),
  );
}

// Renders a single Index-namespace item (untranscluded scan/OCR-source page --
// see transclusion.is_transcluded and publish.py's build_index_item_node).
// Never expandable into individual पृष्ठम्:Title/N (scanned-leaf) rows --
// Index is the organizing principle pre-transclusion, so leaves are only
// ever summed into one rolled-up stat on the Index item, never listed (see
// notes/sawikisource-scraper-spec.md, "Untranscluded Index items"). This is
// a scanned book with OCR proofing underway on Wikisource but NOT YET
// assembled into a readable mainspace article -- there is nothing to click
// through to but the raw scan. Badge text and tooltip spell that out
// explicitly (a bare "Index" badge reads as a content-type label, not a
// "not real content yet" warning; "Proofing" names the Wikisource
// workflow stage it's actually in, see docs/about.html's "OCR 'Proofreading'
// Pipeline Types"). stats here already include the
// पृष्ठम्:Title/N rollup (see build_index_item_node/compute_page_ns_rollup),
// so the byte size shown is the real scanned/proofread content size, not
// just the Index page's own near-empty proofreading-status scaffolding.
function renderIndexItemLi(item, ownPath) {
  const a = el("a", { href: item.url, target: "_blank", rel: "noreferrer" }, displayTitle(item.title, item.id));

  const metaParts = [];
  const size = contentSizeBytes(item.stats);
  if (size != null) metaParts.push(formatBytes(size));
  const date = formatDate(item.stats?.last_changed);
  if (date) metaParts.push(date);
  const meta = metaParts.length ? ` (${metaParts.join(", ")})` : "";

  return el("li", {},
    el("span", { class: "pageRow", ...multiCatRowProps(item.title, ownPath) },
      el("span", { class: "indexBadge", title: "Scanned/OCR source, still in the Proofreading workflow -- not yet transcluded into a finished mainspace text" }, "Proofing"),
      a,
      meta ? el("span", { class: "small" }, meta) : null,
      renderMultiCatButton(item.title, item.id),
    )
  );
}

// Extra props to spread onto a page/index-item row (alongside its existing
// class) when its title is filed under more than one category directly (see
// state.multiCatTitles) -- hover-highlights every occurrence of this same
// title elsewhere in the currently-rendered view, mirroring how a shared
// category's occurrences highlight each other (see renderSidebarNode's
// groupKey/setSharedGroupHighlight). Titles, not ids, are the group key here
// since duplicate pages/index-items don't share an id the way category-
// pointers point back to one canonical id -- see collectMultiCatLocations.
function multiCatRowProps(title, ownPath) {
  if (!state.multiCatTitles.has(title)) return {};
  const ownKey = (ownPath || []).join("␟");
  const others = (state.multiCatLocations.get(title) || [])
    .filter((o) => o.path.join("␟") !== ownKey);
  const otherLocations = others
    .map((o) => o.path.map((t) => translitTextUncached(t)).join(" > "))
    .filter(Boolean);
  const rowTitle = otherLocations.length
    ? `Also filed under: ${otherLocations.join("; ")}\nClick the search icon to find them`
    : "Filed under more than one category -- click the search icon to find them";
  return {
    // Spread AFTER `class: "pageRow"` at both call sites, so this must carry
    // that class forward itself. `selectable-title` opts the row out of the
    // blanket `user-select:none` that [title] elements get (see styles.css):
    // that rule exists to stop iOS's long-press callout fighting our own
    // popup, but on a row whose text is the document title it also made the
    // link text impossible to highlight -- and an unselectable element aborts
    // a drag-selection across the whole row, not just its own text.
    class: "pageRow selectable-title",
    dataset: { sharedGroup: `title:${title}` },
    title: rowTitle,
    onmouseenter: () => setSharedGroupHighlight(`title:${title}`, true),
    onmouseleave: () => setSharedGroupHighlight(`title:${title}`, false),
  };
}

// Small icon button shown only on a page/index-item row whose title is filed
// under more than one category directly. Clicking it populates the search box
// with the item's title and turns on exact mode (state.searchExact, also
// user-toggleable via the "exact" checkbox) -- reusing search (rather than a
// bespoke "see also" cross-reference UI) is a deliberately lightweight way to
// show every category location at once, since each now renders the item in
// full with its own real stats (see pipeline/process.py's build_category).
// Exact mode matters because a short/common title can otherwise substring-
// match thousands of unrelated titles. No tooltip of its own -- the
// enclosing row's title (see multiCatRowProps) already explains it, and a
// second tooltip on the button would just fight the first one for the
// mouse's attention.
function renderMultiCatButton(title, id) {
  if (!state.multiCatTitles.has(title)) return null;
  return el("button", {
    class: "multiCatBtn",
    type: "button",
    onclick: (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      // The node's id, not just its title: displayTitle keys the per-scheme
      // cache by id, and called without one it falls through to
      // translitTextUncached, which cannot read the site's roman label and
      // returns it unchanged. That put "Shri MahalakShmi AkSharamalika
      // Namavali" into a search box matching against transliterated
      // Devanagari -- and since this button also forces exact mode, the
      // result was always "No results found".
      const displayed = displayTitle(title, id);
      const input = document.getElementById("searchInput");
      input.value = displayed;
      state.searchQuery = displayed.toLowerCase();
      state.searchExact = true;
      const exactToggle = document.getElementById("searchExactToggle");
      if (exactToggle) exactToggle.checked = true;
      renderSidebarTree();
      renderMain();
    },
  }, el("span", { class: "searchIcon" }));
}

// "See also" hint: this category is filed under more than one parent -- name the
// other occurrence(s) and link to jump there instead of duplicating full content.
// Shared by renderCategoryBlock (for the selected node and its descendants) and
// the breadcrumb ancestor headers in renderMain (ancestors are shared categories
// just as often as the selected node itself, and previously lost this hint).
function renderSeeAlso(catNode) {
  const siblings = state.siblingIds.get(catNode.id) || [];
  if (!siblings.length) return null;
  return el("span", { class: "small", style: "font-weight:normal; margin-left:8px; opacity:0.75;" },
    "see also: ",
    ...siblings.flatMap((sid, i) => {
      const loc = (state.parentPath.get(sid) || []).map((t) => translitTextUncached(t)).join(" > ") || displayTitle(catNode.title, catNode.id);
      const link = el("a", {
        href: "#",
        onclick: (ev) => {
          ev.preventDefault();
          selectCategory(sid);
          renderSidebarTree();
          renderMain();
        },
      }, loc);
      return i === 0 ? [link] : [", ", link];
    })
  );
}

function renderCategoryBlock(catNode, { includeLeaves, depth, isRoot, isSearch }) {
  const isActualRoot = catNode.id === activeBranch().id;

  // Resolve to the occurrence that actually holds children/pages/index_items (a
  // category-pointer occurrence carries none of its own). Every occurrence
  // renders its full content here; nothing is collapsed.
  const content = resolveContent(catNode);

  // In search mode: only show stats if this node itself is a direct title match
  // (parent containers pulled in only because a descendant matched stay quiet).
  let showStats = true;
  if (isSearch && !content.__isMatch) {
    showStats = false;
  }

  const statsText = showStats ? formatStats(catNode.stats, { includeDate: true }) : "";

  // Link to the live Wikisource category page itself -- a plain external-link arrow
  // (no visible text) placed right after the stats parenthesis. catNode.url is set by
  // pipeline/process.py's build_category() for both "category" and "category-pointer"
  // nodes; the synthetic spliced root has none (not a real wiki category).
  const catLink = showStats && catNode.url
    ? el("a", { class: "catLinkArrow", href: catNode.url, target: "_blank", rel: "noreferrer", title: "Open this page on sanskritdocuments.org" })
    : null;

  const seeAlso = renderSeeAlso(catNode);

  // depth (1-indexed among non-root headers) determines stacking order/offset of sticky headers.
  // Shallower headers must paint OVER deeper ones (so descendants scroll underneath their
  // ancestors' sticky headers, not on top of them) -- hence z-index decreases with depth.
  const header = isActualRoot ? null : el("div", {
    class: "panelTitle sticky-header",
    dataset: { stickyDepth: String(depth) },
    style: `z-index:${1000 - depth};`
  },
    el("span", {
      class: "panelTitleLink",
      onclick: () => {
        selectCategory(catNode.id);
        renderSidebarTree();
        renderMain();
      },
    }, displayTitle(catNode.title, catNode.id)),
    statsText ? el("span", { class: "small", style: "font-weight:normal; margin-left:8px;" }, statsText) : null,
    catLink,
    seeAlso
  );

  const block = el("div", { class: isActualRoot ? "" : "block" }, header);

  // child categories
  for (const ch of (content.children || [])) {
    block.appendChild(el("div", { style: "margin-top:10px" },
      renderCategoryBlock(ch, { includeLeaves, depth: depth + 1, isRoot: false, isSearch })
    ));
  }

  // Main-namespace pages and Index-namespace items are rendered as two separate
  // lists (rather than merged) since they're structurally different: pages nest
  // via subpages, index items never expand into page-namespace detail.
  if (includeLeaves) {
    const leafPages = content.pages || [];
    const indexItems = content.index_items || [];

    const ownPath = [...(state.parentPath.get(catNode.id) || []), catNode.title];

    if (leafPages.length) {
      const isExpanded = state.expandedPageLists.has(catNode.id + ":pages");
      const capped = !isExpanded && leafPages.length > PAGE_LIST_CAP;
      const shown = capped ? leafPages.slice(0, PAGE_LIST_CAP) : leafPages;

      const ul = el("ul", {});
      for (const p of shown) ul.appendChild(renderPageLi(p, ownPath));

      const showAllBtn = capped
        ? el("button", {
            class: "theme-toggle",
            type: "button",
            style: "margin-top:8px;",
            onclick: () => {
              state.expandedPageLists.add(catNode.id + ":pages");
              renderMain();
            },
          }, `Show all ${leafPages.length} pages`)
        : null;

      block.appendChild(el("div", { style: "margin-top:10px" }, ul, showAllBtn));
    }

    if (indexItems.length) {
      const isExpanded = state.expandedPageLists.has(catNode.id + ":index");
      const capped = !isExpanded && indexItems.length > PAGE_LIST_CAP;
      const shown = capped ? indexItems.slice(0, PAGE_LIST_CAP) : indexItems;

      const ul = el("ul", {});
      for (const item of shown) ul.appendChild(renderIndexItemLi(item, ownPath));

      const showAllBtn = capped
        ? el("button", {
            class: "theme-toggle",
            type: "button",
            style: "margin-top:8px;",
            onclick: () => {
              state.expandedPageLists.add(catNode.id + ":index");
              renderMain();
            },
          }, `Show all ${indexItems.length} index items`)
        : null;

      block.appendChild(el("div", { style: "margin-top:10px" }, ul, showAllBtn));
    }
  }

  return block;
}

// --- wiring

// Walks every page/index-item title in the tree (including nested subpages) and
// records every occurrence's stats plus the category path it's filed under --
// i.e. filed under >1 category directly, per pipeline/process.py's
// build_category_membership_maps. Powers renderMultiCatButton's hover highlight
// and tooltip, mirroring renderSeeAlso's treatment of shared categories -- the
// pipeline no longer emits pointer nodes for pages/index-items (each category
// shows the full real item -- see pipeline/process.py's recompute_stats_dedup
// for how ancestor rollups still avoid double-counting without needing
// pointers at this level), so titles (not ids) are the only thing tying
// occurrences of the same item together on the frontend.
function collectMultiCatLocations(node, locations, ancestorPath) {
  const isActualRoot = ancestorPath.length === 0 && node === state.data.root;
  const ownPath = isActualRoot ? ancestorPath : [...ancestorPath, node.title];
  for (const p of (node.pages || [])) {
    if (!locations.has(p.title)) locations.set(p.title, []);
    locations.get(p.title).push({ path: ownPath, stats: p.stats });
    collectSubpageLocations(p, locations, ownPath);
  }
  for (const it of (node.index_items || [])) {
    if (!locations.has(it.title)) locations.set(it.title, []);
    locations.get(it.title).push({ path: ownPath, stats: it.stats });
  }
  for (const ch of (node.children || [])) {
    collectMultiCatLocations(ch, locations, ownPath);
  }
}

function collectSubpageLocations(p, locations, catPath) {
  for (const sp of (p.subpages || [])) {
    if (!locations.has(sp.title)) locations.set(sp.title, []);
    locations.get(sp.title).push({ path: catPath, stats: sp.stats });
    collectSubpageLocations(sp, locations, catPath);
  }
}

function indexById(node, byId, parentPath, ancestorTitles = []) {
  if (node.id) {
    byId.set(node.id, node);
    parentPath.set(node.id, ancestorTitles);
  }
  const isActualRoot = ancestorTitles.length === 0 && node === state.data.root;
  const childAncestors = isActualRoot ? ancestorTitles : [...ancestorTitles, node.title];
  for (const ch of (node.children || [])) indexById(ch, byId, parentPath, childAncestors);
}

const SITE_BASE = "https://sanskritdocuments.org";

// The per-format suffixes the site appends to a document's path. Kept here
// rather than in tree.json, where spelling out every href cost 3.3 MB.
const DOWNLOAD_SUFFIXES = {
  "ITX": ".itx",
  "Devanagari PDF": ".pdf",
  "Tamil PDF": "-ta.pdf",
  "Telugu PDF": "-te.pdf",
  "Kananda PDF": "-kn.pdf",
  "Kannada PDF": "-kn.pdf",
  "Gujarati PDF": "-gu.pdf",
  "Bengali PDF": "-bn.pdf",
  "Oriya PDF": "-or.pdf",
  "Malayalam PDF": "-ml.pdf",
  "Punjabi PDF": "-pa.pdf",
  "Assamese PDF": "-as.pdf",
  "Sanskrit PDF": "-sa.pdf",
};

// tree.json omits what it can derive, to stay loadable: a document's url is
// always <base>/<doc_id>.html, its download hrefs are that path plus a
// per-format suffix, and a category entry is a bare {ref} pointing at the
// document's real node in the location branch. Put all three back before the
// rest of the UI, which expects whole page objects, ever sees them.
function rehydrate(root) {
  const byDocId = new Map();

  const visit = (node, fn) => {
    for (const p of (node.pages || [])) fn(p);
    for (const ch of (node.children || [])) visit(ch, fn);
  };

  visit(root, (p) => {
    if (!p.meta?.doc_id) return;
    p.url = `${SITE_BASE}/${p.meta.doc_id}.html`;
    p.meta.download_urls = (p.meta.downloads || []).map((label) => ({
      label,
      href: `${SITE_BASE}/${p.meta.doc_id}${DOWNLOAD_SUFFIXES[label] ?? ""}`,
    }));
    byDocId.set(`doc:${p.meta.doc_id}`, p);
  });

  // Second pass: category entries borrow the referenced document's metadata
  // and stats. They stay distinct objects -- the same text under two tags is
  // two rows on screen -- but share the one copy of the underlying facts.
  visit(root, (p) => {
    if (!p.ref) return;
    const src = byDocId.get(p.ref);
    if (!src) return;
    p.url = src.url;
    p.meta = src.meta;
    p.stats = src.stats;
    p.own_stats = src.own_stats;
    p.subpages = p.subpages || [];
  });

  // Browse nodes get their upstream page the same way documents do: derived
  // from the id, never stored (see the size note in build_tree). Both axes are
  // a real browsable page on the site --
  //   loc:doc_devii        -> /doc_devii/
  //   lst:subrahmanya      -> /sanskrit/subrahmanya/
  // -- so every heading can link out, which is what the axis means.
  for (const branch of (root.children || [])) {
    for (const node of (branch.children || [])) {
      const [kind, key] = [node.id.slice(0, 3), node.id.slice(4)];
      if (kind === "loc") node.url = `${SITE_BASE}/${key}/`;
      else if (kind === "lst") node.url = `${SITE_BASE}/sanskrit/${key}/`;
    }
  }
}

async function loadData() {
  const r = await fetch(DATA_URL);
  if (!r.ok) throw new Error(`Failed to load ${DATA_URL}: ${r.status}`);
  state.data = await r.json();
  rehydrate(state.data.root);

  state.byId = new Map();
  state.parentPath = new Map();
  indexById(state.data.root, state.byId, state.parentPath);
  state.allTitledNodes = collectTitledNodes(state.data.root);
  state.translitCache = new Map();
  state.searchIndex = new Map();
  // Warm only the frontend's default/initial scheme up front. Every other scheme
  // (including devanagari, the data's native script) is transliterated lazily, the
  // first time the user actually switches to it -- see ensureSchemeCached.
  ensureSchemeCached(state.scheme);

  // Group every occurrence of a shared category (content-holder + all its
  // category-pointers) so each can look up its sibling(s), in either direction.
  const groups = new Map(); // content-holder id -> [all occurrence ids in that group]
  for (const node of state.byId.values()) {
    if (node.type === "category-pointer") {
      if (!groups.has(node.points_to)) groups.set(node.points_to, [node.points_to]);
      groups.get(node.points_to).push(node.id);
    }
  }
  state.siblingIds = new Map();
  for (const ids of groups.values()) {
    for (const id of ids) {
      state.siblingIds.set(id, ids.filter((x) => x !== id));
    }
  }

  const locations = new Map(); // page/index-item title -> [{path, stats}] over every occurrence
  collectMultiCatLocations(state.data.root, locations, []);
  state.multiCatLocations = locations;
  state.multiCatTitles = new Set([...locations].filter(([, occ]) => occ.length > 1).map(([t]) => t));

  state.categoryIndex = buildCategoryIndex(state.data.root);
  state.statsByDocId = buildStatsByDocId(state.data.root);

  state.selectedCatId = activeBranch().id;
  state.expanded.add(activeBranch().id);
}

// Hover highlight for occurrences of a shared category: toggles a CSS class on
// every sidebar row (content-holder + all pointer occurrences) sharing groupKey.
function setSharedGroupHighlight(groupKey, on) {
  if (!groupKey) return;
  const rows = document.querySelectorAll(`[data-shared-group="${groupKey}"]`);
  for (const row of rows) row.classList.toggle("shared-highlight", on);
}

const SUN_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 3v2"/><path d="M12 19v2"/><path d="M5 5l1.4 1.4"/><path d="M17.6 17.6L19 19"/><path d="M3 12h2"/><path d="M19 12h2"/><path d="M5 19l1.4-1.4"/><path d="M17.6 6.4L19 5"/></svg>`;
const MOON_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/></svg>`;

function updateThemeToggleLabel() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  const theme = document.documentElement.getAttribute("data-theme") || "dark";
  const icon = theme === "dark" ? SUN_ICON : MOON_ICON;
  const label = theme === "dark" ? "Light" : "Dark";
  btn.innerHTML = `${icon}<span class="toggle-label">${label}</span>`;
}

const MOBILE_BREAKPOINT = 800;

function isMobileLayout() {
  return window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;
}

function openSidebar() {
  document.getElementById("sidenav").classList.add("open");
  document.getElementById("sidebarBackdrop").classList.add("open");
  document.getElementById("sidebarToggle").setAttribute("aria-expanded", "true");
  // Body itself scrolls at the mobile breakpoint (see .layout in styles.css), so
  // the mainpane's own overflow isn't enough to stop background scroll -- lock body.
  document.body.classList.add("sidebar-open-lock");
}

function closeSidebar() {
  document.getElementById("sidenav").classList.remove("open");
  document.getElementById("sidebarBackdrop").classList.remove("open");
  document.getElementById("sidebarToggle").setAttribute("aria-expanded", "false");
  document.body.classList.remove("sidebar-open-lock");
  hideTooltipPopup();
}

function closeSidebarIfMobile() {
  if (isMobileLayout()) closeSidebar();
}

const SIDEBAR_WIDTH_MIN = 240;
const SIDEBAR_WIDTH_MAX = 800;

function applySidebarWidth(px) {
  document.documentElement.style.setProperty("--sidebar-width", `${px}px`);
}

function initSidebarResizer() {
  const resizer = document.getElementById("sidebarResizer");
  if (!resizer) return;

  const saved = parseFloat(localStorage.getItem("sidebarWidth"));
  if (!Number.isNaN(saved)) applySidebarWidth(saved);

  resizer.addEventListener("pointerdown", (ev) => {
    if (isMobileLayout()) return;
    ev.preventDefault();
    resizer.setPointerCapture(ev.pointerId);
    resizer.classList.add("dragging");
    const startX = ev.clientX;
    const startWidth = document.getElementById("sidenav").getBoundingClientRect().width;

    const onMove = (moveEv) => {
      const raw = startWidth + (moveEv.clientX - startX);
      const clamped = Math.min(SIDEBAR_WIDTH_MAX, Math.max(SIDEBAR_WIDTH_MIN, raw));
      applySidebarWidth(clamped);
    };
    const onUp = () => {
      resizer.classList.remove("dragging");
      resizer.releasePointerCapture(ev.pointerId);
      resizer.removeEventListener("pointermove", onMove);
      resizer.removeEventListener("pointerup", onUp);
      const width = document.getElementById("sidenav").getBoundingClientRect().width;
      localStorage.setItem("sidebarWidth", String(Math.round(width)));
    };
    resizer.addEventListener("pointermove", onMove);
    resizer.addEventListener("pointerup", onUp);
  });

  resizer.addEventListener("dblclick", () => {
    document.documentElement.style.removeProperty("--sidebar-width");
    localStorage.removeItem("sidebarWidth");
  });
}

// Native `title` tooltips never fire on touch devices (no hover concept), so
// on mobile a long-press on any element carrying a `title` attribute (sidebar
// rows, badges, etc.) shows the same text in a small floating popup instead.
// Delegated at the document level rather than wired per-row, so it works for
// every current and future `title`-bearing element without extra plumbing.
const LONG_PRESS_MS = 500;
let longPressTimer = null;
let longPressTarget = null;
// Set true the moment a long-press popup is actually shown (timer fired, not
// just started), so the click that mobile browsers synthesize right after
// the matching touchend can be told apart from a normal tap-to-select and
// suppressed -- otherwise every long-press-to-view-tooltip also navigated/
// selected the row underneath it.
let longPressFired = false;

function showTooltipPopup(text, x, y) {
  hideTooltipPopup();
  const popup = el("div", { class: "touch-tooltip", style: `left:${x}px; top:${y}px;` }, text);
  document.body.appendChild(popup);
  longPressTarget = popup;
}

function hideTooltipPopup() {
  if (longPressTarget) {
    longPressTarget.remove();
    longPressTarget = null;
  }
}

// Touch-device equivalent of isExpandAllGesture's Option/Shift/Ctrl/Cmd-click:
// binds a long-press on `element` to `onExpandAll`, and swallows the
// synthesized click that follows touchend so a long-press doesn't also
// trigger the element's normal (single-level) onclick handler.
function bindLongPressExpand(element, onExpandAll) {
  let timer = null;
  let fired = false;

  element.addEventListener("touchstart", (ev) => {
    fired = false;
    timer = setTimeout(() => {
      fired = true;
      if (navigator.vibrate) navigator.vibrate(15);
      onExpandAll();
    }, LONG_PRESS_MS);
  }, { passive: true });

  const cancel = () => clearTimeout(timer);
  element.addEventListener("touchmove", cancel, { passive: true });
  element.addEventListener("touchend", cancel);
  element.addEventListener("touchcancel", cancel);

  element.addEventListener("click", (ev) => {
    if (fired) {
      fired = false;
      ev.preventDefault();
      ev.stopPropagation();
    }
  }, { capture: true });
}

function initLongPressTooltips() {
  document.addEventListener("touchstart", (ev) => {
    hideTooltipPopup();
    const target = ev.target.closest("[title]");
    if (!target) return;
    const touch = ev.touches[0];
    const x = touch.clientX;
    const y = touch.clientY;
    longPressTimer = setTimeout(() => {
      longPressFired = true;
      showTooltipPopup(target.getAttribute("title"), x, y);
    }, LONG_PRESS_MS);
  }, { passive: true });

  const cancel = () => clearTimeout(longPressTimer);
  document.addEventListener("touchmove", cancel, { passive: true });
  document.addEventListener("touchend", cancel);
  document.addEventListener("touchcancel", cancel);

  // Swallow the click a mobile browser synthesizes right after the touch
  // that triggered our popup, so releasing a long-press doesn't also
  // select/navigate the row underneath. Capture phase so it runs before the
  // row's own onclick handler.
  document.addEventListener("click", (ev) => {
    if (longPressFired) {
      longPressFired = false;
      ev.preventDefault();
      ev.stopPropagation();
    }
  }, { capture: true });

  // iOS/Safari's native long-press (text selection callout, "copy" /
  // "search with Google" context menu) fires independently of our JS timer
  // above -- block it specifically on title-bearing elements so it doesn't
  // show up alongside our popup.
  document.addEventListener("contextmenu", (ev) => {
    if (ev.target.closest("[title]")) ev.preventDefault();
  });
}

function initUI() {
  initSidebarResizer();
  initLongPressTooltips();

  document.getElementById("sidebarToggle").addEventListener("click", () => {
    const sidenav = document.getElementById("sidenav");
    if (sidenav.classList.contains("open")) closeSidebar();
    else openSidebar();
  });
  document.getElementById("sidebarBackdrop").addEventListener("click", closeSidebar);

  // The brand is a "start over" control, so it reloads rather than resetting in
  // place. A soft reset left the category filters, search box, expansion and
  // scroll position exactly where they were, which is the opposite of what
  // clicking the title reads as. Reloading re-reads tree.json too, so it also
  // picks up a rebuilt data file without a manual refresh. The axis and theme
  // survive on purpose -- those are persisted preferences, not where you are.
  document.getElementById("brandTitle").addEventListener("click", () => {
    window.location.href = window.location.pathname;
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeSidebar();
  });

  document.getElementById("schemeSelect").addEventListener("change", (ev) => {
    state.scheme = ev.target.value;
    renderSidebarTree();
    renderMain();
  });

  document.getElementById("searchInput").addEventListener("input", (ev) => {
    state.searchQuery = ev.target.value.toLowerCase().trim();
    // A changed query is a fresh result set -- drop any manual in-search
    // collapses so the new results start from the force-expanded default.
    state.collapsedSubpages.clear();
    renderMain();
  });

  document.getElementById("searchExactToggle").addEventListener("change", (ev) => {
    state.searchExact = ev.target.checked;
    renderMain();
  });

  // The orphan toggle is wikisource-specific (असम्बद्धवर्गीकृतम्, pages outside
  // the category tree) and has no ebharati equivalent, so index.html omits it.
  const includeOrphansCheckbox = document.getElementById("includeOrphansCheckbox");
  if (includeOrphansCheckbox) {
    includeOrphansCheckbox.checked = state.includeOrphans;
    includeOrphansCheckbox.addEventListener("change", (ev) => {
      state.includeOrphans = ev.target.checked;
      localStorage.setItem("includeOrphans", state.includeOrphans ? "1" : "0");
      renderSidebarTree();
    });
    // Stop the click from also bubbling to allRowEl's onclick (which selects
    // the root category) -- this label sits inside #allRow but toggling it
    // shouldn't also change the current selection.
    document.getElementById("includeOrphansToggle").addEventListener("click", (ev) => {
      ev.stopPropagation();
    });
  }

  const filterAdd = document.getElementById("filterAdd");
  if (filterAdd) filterAdd.addEventListener("click", () => openFilterEditor());

  updateThemeToggleLabel();
  document.getElementById("themeToggle").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeToggleLabel();
  });
}

// Builds the match predicate for the current search mode: either substring
// matching against the transliterated/lowercased query (normal typed search),
// or, when the "exact" checkbox (state.searchExact) is on, matching the
// node's whole transliterated/lowercased title exactly instead. A common/
// short title (e.g. "योगवासिष्ठः") can otherwise substring-match thousands
// of unrelated titles -- exact mode is what makes the multi-category
// magnifying-glass button's "find my sibling occurrences" click useful, but
// it's also independently toggleable so the user can reach for it whenever.
// ---- Category filter ----------------------------------------------------

const STAT_KEYS = ["raw_bytes", "content_bytes", "transliterated_bytes"];
//
// Modelled on muktalib-v2-app's filter builder (templates/index.html:
// filterIndex / countFiltered / formatCount). The shape is the same: an index
// of value -> members built once, counts recomputed against the *other* active
// filters so each option shows what it would actually yield, and rows ANDed.
//
// The difference is where the counting happens. muktalib counts DOM rows, since
// it renders every item up front; this tree renders lazily and caps long lists,
// so counts come from the id index instead and stay correct for documents that
// were never rendered.

// tag -> Set(doc id). Built from the location branch alone: every document
// appears there exactly once, so a Set per tag is the document set, not a
// placement count. (Walking every branch would add the same ids again.)
function buildCategoryIndex(root) {
  const index = new Map();
  const locBranch = (root.children || []).find((ch) => ch.id === "loc") || root;
  const visit = (node) => {
    for (const p of (node.pages || [])) {
      const docId = p.meta?.doc_id;
      if (!docId) continue;
      for (const tag of (p.meta.categories || [])) {
        let members = index.get(tag);
        if (!members) index.set(tag, (members = new Set()));
        members.add(docId);
      }
    }
    for (const ch of (node.children || [])) visit(ch);
  };
  visit(locBranch);
  return index;
}

function filtersActive() {
  return state.activeFilters.length > 0;
}

// The documents surviving every filter in `tags` -- the intersection of their
// member sets. Empty `tags` means "no constraint", signalled by null rather
// than a set of the whole corpus, so callers can skip the membership test.
function matchingDocIds(tags) {
  if (!tags.length) return null;
  let survivors = null;
  // Intersect smallest-first: the result can only shrink, so starting from the
  // rarest tag keeps every subsequent pass short.
  const sets = tags
    .map((t) => state.categoryIndex.get(t) || new Set())
    .sort((a, b) => a.size - b.size);
  for (const members of sets) {
    if (survivors === null) {
      survivors = new Set(members);
      continue;
    }
    for (const id of survivors) {
      if (!members.has(id)) survivors.delete(id);
    }
    if (!survivors.size) break;
  }
  return survivors;
}

// How many documents a candidate tag would leave, given the filters already
// active. This is what makes the (N → M) display meaningful: it counts against
// the current selection, not the whole corpus.
function countWithFilter(tag) {
  const survivors = matchingDocIds([...state.activeFilters, tag]);
  return survivors ? survivors.size : 0;
}

// Stats over a document-id set, in the shape formatStats expects, so filter
// rows read "(9.2 MB, 1431 texts)" like every other figure in the UI rather
// than a bare count.
function statsForDocIds(docIds) {
  const stats = { raw_bytes: 0, content_bytes: 0, transliterated_bytes: 0, count: 0, text_count: 0 };
  if (!docIds) return stats;
  for (const docId of docIds) {
    const own = state.statsByDocId.get(docId);
    if (!own) continue;
    for (const k of STAT_KEYS) stats[k] += own[k] || 0;
    stats.count += 1;
    stats.text_count += (own.content_bytes || 0) > 0 ? 1 : 0;
  }
  return stats;
}

function addFilter(tag) {
  if (state.activeFilters.includes(tag)) return;
  state.activeFilters.push(tag);
  onFiltersChanged();
}

function removeFilter(tag) {
  state.activeFilters = state.activeFilters.filter((t) => t !== tag);
  onFiltersChanged();
}

function clearFilters() {
  if (!state.activeFilters.length) return;
  state.activeFilters = [];
  onFiltersChanged();
}

function onFiltersChanged() {
  // Expansion state is keyed on node ids that survive filtering, so it stays
  // valid; the selected category may now hold nothing, which renders as an
  // empty block rather than an error.
  invalidateVisibleBranch();
  renderFilterPanel();
  renderSidebarTree();
  renderMain();
}

// Every distinct document id at or below a node, as a Set. Deduping has to
// happen per node rather than once across the branch: on the listing axis a
// document sits on 2.24 pages on average, so a single branch-wide "already
// counted" set would credit each document to whichever node happened to be
// visited first and leave every other node reporting zero. Each node counts
// its own members in full; the branch total is the union, not the sum.
function collectDocIds(node, into) {
  for (const p of (node.pages || [])) {
    const docId = p.meta?.doc_id || (p.ref || "").replace(/^doc:/, "");
    if (docId) into.add(docId);
  }
  for (const ch of (node.children || [])) collectDocIds(ch, into);
  return into;
}

// Recompute every node's stats over the documents that actually survived, the
// same way pipeline/build_tree.distinct_stats does: distinct doc ids, counted
// once each. Without this a filtered node keeps the stats the pipeline wrote
// for its unfiltered membership, and the sidebar reports the whole corpus
// beside a handful of visible rows -- a smaller cousin of the placement
// double-count that retiring the category branch was meant to end.
function restatFiltered(node, statsByDocId) {
  const stats = { raw_bytes: 0, content_bytes: 0, transliterated_bytes: 0, count: 0, text_count: 0 };
  for (const docId of collectDocIds(node, new Set())) {
    const own = statsByDocId.get(docId);
    if (!own) continue;
    for (const k of STAT_KEYS) stats[k] += own[k] || 0;
    stats.count += 1;
    stats.text_count += (own.content_bytes || 0) > 0 ? 1 : 0;
  }
  node.stats = stats;
  for (const ch of (node.children || [])) restatFiltered(ch, statsByDocId);
  return stats;
}

// doc id -> its own byte stats, so restatFiltered can total a document it
// reaches by any route. Built from the location branch, where each document
// appears exactly once carrying real (non-ref) stats.
function buildStatsByDocId(root) {
  const map = new Map();
  const locBranch = (root.children || []).find((ch) => ch.id === "loc") || root;
  const visit = (node) => {
    for (const p of (node.pages || [])) {
      const docId = p.meta?.doc_id;
      if (docId && !map.has(docId)) map.set(docId, p.own_stats || p.stats);
    }
    for (const ch of (node.children || [])) visit(ch);
  };
  visit(locBranch);
  return map;
}

// A filtered view of the active branch, or the branch itself when no filter is
// set. Both the sidebar and the main pane read through this, so their stats and
// their contents can never disagree about what is being shown.
//
// Filtering walks the whole branch and restats it, so the result is cached and
// reused until something invalidates it (a filter change, an axis switch).
// renderSidebarTree and renderMain each call this on every render.
let visibleBranchCache = null;

function invalidateVisibleBranch() {
  visibleBranchCache = null;
}

function visibleBranch() {
  if (visibleBranchCache) return visibleBranchCache;
  const branch = activeBranch();
  if (!filtersActive()) return (visibleBranchCache = branch);
  const survivors = matchingDocIds(state.activeFilters);
  const filtered = filterTree(branch, (node) => {
    // Categories are a property of documents, so only pages are tested. A
    // category node survives on account of its surviving members, which
    // filterTree already handles by keeping any node with matching children.
    if (node.type !== "page") return false;
    const docId = node.meta?.doc_id || (node.ref || "").replace(/^doc:/, "");
    return docId ? survivors.has(docId) : false;
  }) || { ...branch, children: [], pages: [], index_items: [] };
  // filterTree copies nodes ({...node}), so this restats the copies and never
  // touches the loaded tree.
  restatFiltered(filtered, state.statsByDocId);
  return (visibleBranchCache = filtered);
}

// ---- Filter panel UI ----------------------------------------------------

// Size then count, matching formatStats everywhere else in the UI -- the
// sidebar's "(107.5 MB, 8547 texts)" and a filter option should read the same
// way. Once other filters narrow the set, the count becomes "N → M" in place
// and the size is the *filtered* size, since the pre-filter bytes describe a
// set the reader can no longer get to.
function formatFilterStats(absStats, filteredStats) {
  const base = formatStats(filteredStats);
  if (!base) return "(0)";
  if (absStats.text_count === filteredStats.text_count) return base;
  return base.replace(
    /(\d[\d,]*)(\s+texts?\))/,
    (_, n, tail) => `${absStats.text_count} → ${n}${tail}`,
  );
}

// Options for the autocomplete: every tag not already active, matching the
// typed query, annotated with what it would yield. Sorted by that filtered
// count descending so the most productive choice is first; zero-count options
// are dropped, since picking one could only empty the view.
function filterOptions(query) {
  const q = query.trim().toLowerCase();
  const active = new Set(state.activeFilters);
  const options = [];
  for (const [tag, members] of state.categoryIndex) {
    if (active.has(tag)) continue;
    if (q && !tag.toLowerCase().includes(q)) continue;
    const survivors = filtersActive()
      ? matchingDocIds([...state.activeFilters, tag])
      : members;
    const filtered = survivors ? survivors.size : 0;
    if (!filtered) continue;
    options.push({
      tag,
      count: filtered,
      absStats: statsForDocIds(members),
      filteredStats: statsForDocIds(survivors),
    });
  }
  options.sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
  return options;
}

function renderFilterPanel() {
  const rows = document.getElementById("filterRows");
  const clearBtn = document.getElementById("filterClear");
  if (!rows) return;
  rows.innerHTML = "";

  // Every active row shows the same surviving set -- they are ANDed, so the
  // figure describes the filtered corpus, not that row's own tag.
  const activeStats = statsForDocIds(matchingDocIds(state.activeFilters));
  for (const tag of state.activeFilters) {
    rows.appendChild(el("div", { class: "filterRow" },
      el("span", { class: "filterRowValue", title: tag }, tag),
      el("span", { class: "filterRowCount" }, formatStats(activeStats) || "(0)"),
      el("button", {
        class: "filterRemove",
        type: "button",
        title: `Remove filter ${tag}`,
        onclick: () => removeFilter(tag),
      }, "×"),
    ));
  }

  if (clearBtn) {
    clearBtn.hidden = state.activeFilters.length < 2;
    if (!clearBtn.dataset.bound) {
      clearBtn.dataset.bound = "1";
      clearBtn.onclick = () => clearFilters();
    }
  }
}

// The "+ add filter" affordance expands into a text input with a dropdown, and
// collapses again on pick/blur -- so the resting sidebar shows only the filters
// actually in force.
function openFilterEditor() {
  const rows = document.getElementById("filterRows");
  const addBtn = document.getElementById("filterAdd");
  if (!rows || rows.querySelector(".filterEditor")) return;

  const input = el("input", {
    type: "text",
    class: "filterInput",
    placeholder: "category…",
    autocomplete: "off",
    spellcheck: false,
  });
  const menu = el("div", { class: "filterMenu" });
  const editor = el("div", { class: "filterEditor" }, input, menu);
  rows.appendChild(editor);
  if (addBtn) addBtn.hidden = true;

  const close = () => {
    editor.remove();
    if (addBtn) addBtn.hidden = false;
  };

  const renderMenu = () => {
    menu.innerHTML = "";
    const options = filterOptions(input.value).slice(0, 50);
    if (!options.length) {
      menu.appendChild(el("div", { class: "filterMenuEmpty" }, "no matches"));
      return;
    }
    for (const { tag, absStats, filteredStats } of options) {
      menu.appendChild(el("div", {
        class: "filterMenuItem",
        // mousedown, not click: blur fires first on click and would tear the
        // menu down before the selection registered.
        onmousedown: (ev) => {
          ev.preventDefault();
          close();
          addFilter(tag);
        },
      },
        el("span", { class: "filterMenuVal" }, tag),
        el("span", { class: "filterMenuCount" }, formatFilterStats(absStats, filteredStats)),
      ));
    }
  };

  input.addEventListener("input", renderMenu);
  input.addEventListener("blur", () => setTimeout(close, 150));
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") { ev.preventDefault(); close(); return; }
    if (ev.key === "Enter") {
      const first = filterOptions(input.value)[0];
      if (first) { ev.preventDefault(); close(); addFilter(first[0]); }
    }
  });

  renderMenu();
  input.focus();
}

function currentSearchMatcher() {
  const query = state.searchQuery;
  // Author as well as title -- looking for a text by who wrote it is as
  // ordinary as looking for it by name, and this atlas has no author axis to
  // fall back on. Each field is compared whole in exact mode, so an author's
  // name matches their documents without also matching every title containing
  // the string.
  if (state.searchExact) {
    return (node) => indexedTitle(node) === query || indexedAuthor(node) === query;
  }
  return (node) => indexedTitle(node).includes(query) || indexedAuthor(node).includes(query);
}

// Checks a Main-namespace page (or subpage) against the query, recursively
// including its nested subpages -- a subpage whose own title matches (even if
// its parent's doesn't) still needs to surface in search.
function filterPage(p, matches) {
  const matchingSubpages = (p.subpages || [])
    .map(sp => filterPage(sp, matches))
    .filter(Boolean);
  const selfMatch = matches(p);
  if (selfMatch || matchingSubpages.length > 0) {
    return { ...p, subpages: matchingSubpages };
  }
  return null;
}

function filterIndexItem(item, matches) {
  return matches(item) ? item : null;
}

function filterTree(node, matches) {
  const matchingPages = (node.pages || []).map(p => filterPage(p, matches)).filter(Boolean);
  const matchingIndexItems = (node.index_items || []).map(i => filterIndexItem(i, matches)).filter(Boolean);

  const matchingChildren = [];
  for (const ch of (node.children || [])) {
    const filteredCh = filterTree(ch, matches);
    if (filteredCh) matchingChildren.push(filteredCh);
  }

  const selfMatch = matches(node);

  if (selfMatch || matchingPages.length > 0 || matchingIndexItems.length > 0 || matchingChildren.length > 0) {
    return {
      ...node,
      children: matchingChildren,
      pages: matchingPages,
      index_items: matchingIndexItems,
      __isMatch: selfMatch,
    };
  }

  return null;
}

// Primary datestamp shown to users (topbar #dataUpdated) is __content_version__:
// the date of the Wikimedia dump snapshot itself (not a rollup over
// page-edit timestamps -- the main panel already surfaces per-item edit
// dates on its own). __data_version__ (when we last ran the pipeline
// against that snapshot) is secondary and only surfaces as a tooltip here;
// see about.html for both shown in full.
async function loadVersion() {
  try {
    const r = await fetch("./VERSION");
    if (!r.ok) return;
    const text = await r.text();
    const lines = text.split("\n");
    let pipelineRunDate = "";
    let contentDate = "";
    for (const line of lines) {
      if (!line.includes("=")) continue;
      const eqIdx = line.indexOf("=");
      const key = line.slice(0, eqIdx).trim();
      const value = line.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, "");
      if (key === "__code_version__") {
        const el = document.getElementById("appVersion");
        if (el) el.textContent = "v" + value;
      } else if (key === "__data_version__") {
        pipelineRunDate = value;
      } else if (key === "__content_version__") {
        contentDate = value;
      }
    }
    const el = document.getElementById("dataUpdated");
    if (el && contentDate) {
      el.textContent = contentDate;
      el.title = pipelineRunDate
        ? `data last sourced from Wikimedia; pipeline last run ${pipelineRunDate}`
        : "date of the Wikimedia dump snapshot this data was built from";
    }
  } catch (e) {
    console.log("Could not load version:", e);
  }
}


// A `?q=` in the URL preloads the search box, so another page can deep-link a
// specific title into this Atlas -- the parent's federated search sends every
// result row here, which is the only way a hit over there reaches the item's
// own collection. `?exact=1` additionally turns on exact mode, matching the
// whole transliterated title rather than any substring; the parent uses it
// because it knows the exact title it linked.
//
// Read once at startup and NOT written back as the user types: the query is a
// handoff, not a synced piece of state, and rewriting the URL on every
// keystroke would bury the page in history entries.
function applyQueryFromURL() {
  const params = new URLSearchParams(location.search);
  const q = (params.get("q") || "").trim();
  if (!q) return;
  const input = document.getElementById("searchInput");
  if (input) input.value = q;
  state.searchQuery = q.toLowerCase();
  if (params.get("exact") === "1") {
    state.searchExact = true;
    const exactToggle = document.getElementById("searchExactToggle");
    if (exactToggle) exactToggle.checked = true;
  }
}

(async function main() {
  initUI();
  loadVersion();
  await detectFulltextMode();
  await loadData();
  applyQueryFromURL();
  renderAxisSwitch();
  renderFilterPanel();
  renderSidebarTree();
  renderMain();
})();
