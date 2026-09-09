// about.html's only scripted behavior: the theme toggle.
//
// The scheme <select> needs nothing here -- initStaticTranslit() binds its own
// "change" listener, and this page's Devanagari is all hand-written .sa prose,
// with no tree.json titles to re-render.
//
// The theme icons and handler are duplicated from app.js rather than shared,
// because about.html deliberately doesn't load app.js (which expects a sidebar,
// a tree, and tree.json). The inline <script> in the page <head> already applies
// the saved theme before first paint, so this only handles the click and keeps
// the button's label in sync. Both pages read/write the same localStorage
// "theme" key, so a switch here carries over to the tree and back.

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

const themeToggle = document.getElementById("themeToggle");
if (themeToggle) {
  updateThemeToggleLabel();
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeToggleLabel();
  });
}

// ---------------------------------------------------------------------------
// Changelog
// ---------------------------------------------------------------------------
// docs/data/changelog.json is one record per MONTH, built by
// pipeline/build_changelog.py from each document's own `Latest update` field.
// A bucket is "documents whose most recent update falls in it" -- the site
// keeps only the latest touch per document, so this tracks growth, not
// revision history. See the module docstring for what that does and doesn't
// support.
//
// Months are the granularity the three atlases publish, so sagara-sangama can
// plot all three on one time axis; the grouping up to quarters and years
// happens below, at render time, where the reader picks it. Year is the
// default view -- 329 monthly bars is a texture, not a reading.
//
// The wikisource sibling renders a much richer version of this file; ours is
// deliberately a bar chart plus a table, because our data carries no
// per-revision detail to drill into.

const CHANGELOG_URL = "./data/changelog.json";

function fmtBytes(n) {
  if (!n) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${units[i]}`;
}

// Two independent axes of view:
//   metric: "count" (documents) or "size" (IAST bytes, so a purana outweighs
//           a hundred short stotras)
//   mode:   "year" (that period's own additions) or "cumulative" (running total)
// `granularity` is months per group: 1 monthly, 3 quarterly, 12 yearly.
const clState = { metric: "count", mode: "year", granularity: 12 };

// Group the oldest-first monthly records into calendar chunks: quarters at
// Jan/Apr/Jul/Oct, years at January. Anchored to the calendar rather than
// counted back from the newest month, so a bar labelled "2026" covers 2026 --
// the newest and oldest groups can therefore be partial, which is honest
// where the period is genuinely still in progress.
function groupRows(rows, size) {
  if (size <= 1 || rows.length < 2) return rows;
  const groups = [];
  let chunk = [];
  for (const r of rows) {
    // `period` is "YYYY-MM" once the build is monthly; a yearly file (or the
    // older shape) has no "-" and is left alone.
    if (r.period.length < 7) return rows;
    const month = Number(r.period.slice(5, 7)) - 1;
    const key = `${r.period.slice(0, 4)}:${Math.floor(month / size)}`;
    if (chunk.length && chunk.key !== key) {
      groups.push(reduceRows(chunk, size));
      chunk = [];
    }
    chunk.key = key;
    chunk.push(r);
  }
  if (chunk.length) groups.push(reduceRows(chunk, size));
  return groups;
}

// One record standing for several. `new` is a running total, so the group's
// is the last record's; `items_added_count` and the size deltas are disjoint
// per-period figures, so they sum. Getting those two rules the wrong way
// round is the one way this goes quietly wrong.
function reduceRows(chunk, size) {
  const first = chunk[0], last = chunk[chunk.length - 1];
  // A one-month group still gets the calendar label: a year holding a single
  // document is that year, and returning the record untouched would put
  // "1992-06" on a bar the axis reads as years.
  if (chunk.length === 1) return { ...first, period: groupLabel(first, size) };
  const sum = (get) => chunk.reduce((s, r) => s + (get(r) || 0), 0);

  const sizes = {};
  for (const k of Object.keys(last.sizes || {})) {
    sizes[k] = {
      old: first.sizes[k].old,
      new: last.sizes[k].new,
      delta: sum((r) => r.sizes[k].delta),
      delta_pct: first.sizes[k].old
        ? (100 * sum((r) => r.sizes[k].delta)) / first.sizes[k].old : null,
    };
  }

  return {
    ...last,
    period: groupLabel(first, size),
    old: first.old,
    new: last.new,
    old_date: first.old_date,
    sizes,
    delta: {
      count: last.new.count - first.old.count,
      text_count: last.new.text_count - first.old.text_count,
    },
    items_added_count: sum((r) => r.items_added_count),
    items_removed_count: sum((r) => r.items_removed_count),
    items_changed_count: sum((r) => r.items_changed_count),
    // A group is only fully measured if every record in it is.
    sizes_partial: chunk.some((r) => r.sizes_partial),
  };
}

// "2026" at year grouping, "2026-Q3" at quarter -- named for the calendar
// period the group covers, not for the months that happen to carry data. A
// year holding one document is still that year, and labelling it "1992-06"
// would read as a month.
function groupLabel(first, size) {
  const year = first.period.slice(0, 4);
  if (size >= 12) return year;
  const a = Number(first.period.slice(5, 7));
  return `${year}-Q${Math.floor((a - 1) / 3) + 1}`;
}

// One accessor per (metric, mode) corner, reading the fields build_changelog
// already emits: per-period deltas and running totals for both series.
function clValue(r) {
  if (clState.metric === "size") {
    return clState.mode === "cumulative"
      ? r.sizes.transliterated_bytes.new
      : r.sizes.transliterated_bytes.delta;
  }
  return clState.mode === "cumulative" ? r.new.count : r.items_added_count;
}

function clFormat(v) {
  return clState.metric === "size" ? fmtBytes(v) : v.toLocaleString();
}

// Round `max` up to a clean top-of-scale and hand back the tick values below
// it. Ticks carry every value the bars aren't labelled with, so they have to
// read as round numbers -- 10,000 rather than 9,756. The step is the largest
// of 1/2/2.5/5 x 10^n that leaves at most `want` intervals.
//
// `unit` is what one displayed unit is worth in the value's own terms, and it
// is the whole reason this isn't a plain decimal rounding: under "size" the
// axis is bytes but the label is megabytes, so a round step has to be round
// in the unit the reader sees. Choosing 50,000,000 bytes because it is a
// round decimal number prints "48 MB", which is not a tick anyone can read.
function axisTicks(max, want = 4, unit = 1) {
  if (!(max > 0)) return { top: 1, ticks: [] };
  const raw = max / want / unit;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = ([1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag) * unit;
  const top = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = step; v <= top + step / 1000; v += step) ticks.push(v);
  return { top, ticks };
}

// The 1024-power fmtBytes will render `max` in, as a byte count -- so the tick
// step can be chosen in that unit. Capped at GB because that is the largest
// unit fmtBytes knows.
function byteUnit(max) {
  const i = Math.min(3, Math.floor(Math.log(Math.max(max, 1)) / Math.log(1024)));
  return Math.pow(1024, i);
}

// Axis ticks are the same quantity as the bars, so they take the metric's own
// formatting -- byte units under "size", thousands separators under
// "documents".
//
// fmtBytes gives one decimal below 10, which is right for a tooltip reporting
// one document's size and wrong for a tick standing beside "10 MB" and
// "15 MB". A tick that lands on a whole number of its unit prints as one, so
// the column reads 5 / 10 / 15 rather than 5.0 / 10 / 15.
function fmtTick(v) {
  if (clState.metric !== "size") return Math.round(v).toLocaleString();
  const unit = byteUnit(v);
  const n = v / unit;
  if (unit > 1 && Math.abs(n - Math.round(n)) < 0.001) {
    const label = ["B", "KB", "MB", "GB"][Math.round(Math.log(unit) / Math.log(1024))];
    return `${Math.round(n)} ${label}`;
  }
  return fmtBytes(v);
}

function drawChart(rows, chartEl) {
  const values = rows.map(clValue);
  // Bars are measured against the axis top, not the raw maximum: a bar drawn
  // to 100% of its own max would sit above the topmost gridline and make the
  // scale a lie.
  const peak = Math.max(...values, 1);
  const { top, ticks } = axisTicks(peak, 4, clState.metric === "size" ? byteUnit(peak) : 1);

  chartEl.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "cl-wrap";

  // The gutter and the plot share the grid's top row and so are exactly the
  // same height: a tick at 50% and a bar at 50% land on one line, with neither
  // needing to know the other's size.
  const axis = document.createElement("div");
  axis.className = "cl-yaxis";
  // The topmost tick is flagged rather than positioned like the rest. Every
  // other label is centred on its gridline by a 50% translate, but at
  // `bottom:100%` that leaves half the text above the plot -- which is what
  // pushed "1,500" out through the panel's top border. `cl-tick-top` sits it
  // fully inside, the same exception `cl-tick-zero` already makes at the
  // baseline.
  axis.innerHTML = ticks
    .map((v) => {
      const cls = "cl-tick" + (v === top ? " cl-tick-top" : "");
      return `<div class="${cls}" style="bottom:${(v / top) * 100}%">`
        + `${fmtTick(v)}</div>`;
    })
    .join("") + `<div class="cl-tick cl-tick-zero">0</div>`;
  wrap.appendChild(axis);

  const plot = document.createElement("div");
  plot.className = "cl-plot";

  // Gridlines sit behind the bars in the plot's own coordinate space -- one
  // per tick, hairline and recessive, so they locate a bar without competing
  // with it. The zero line is the baseline the bars stand on.
  const grid = document.createElement("div");
  grid.className = "cl-grid";
  grid.innerHTML = ticks
    .map((v) => `<div class="cl-gridline" style="bottom:${(v / top) * 100}%"></div>`)
    .join("");
  plot.appendChild(grid);

  const chart = document.createElement("div");
  // Dense once the columns are thinner than a comfortable bar: tightens the
  // gap and squares the caps, so monthly reads as a profile rather than as a
  // dashed line of rounded stubs.
  const dense = rows.length > 60;
  chart.className = "cl-chart" + (dense ? " cl-dense" : "");
  // Ticks are chosen by the period's own calendar value, NOT by row index.
  // A bucket with no documents is absent from the file rather than present as
  // a zero -- the corpus has nothing dated 1993 -- so the Nth row is not the
  // Nth period, and `i % labelEvery` drifts a little further past every hole.
  // That is what printed 92, 96, 99, 02 on a supposedly 3-year cadence.
  //
  // The stride is a whole number of YEARS at every granularity, so the labels
  // read as a calendar rather than as an arbitrary sampling of the rows: at
  // month density a stride of 27 months would print 95, 98, 00, 02, which is
  // no cadence at all. Aim for about a dozen labels, then round to a year
  // count that divides the span evenly.
  const yearOf = (r) => Number(r.period.slice(0, 4));
  const span = rows.length ? yearOf(rows[rows.length - 1]) - yearOf(rows[0]) + 1 : 1;
  const yearsEvery = Math.max(1, Math.round(span / 12));
  // Only the first period of a labelled year gets the tick -- otherwise every
  // month or quarter inside it would print the same year over and over.
  const seenYear = new Set();

  // The x labels are their own row under the plot rather than a box inside
  // each column: the bars' baseline is now the axis's zero line rather than
  // the top of a text row, which is what lets a gridline meet a bar. The row
  // repeats the bars' column geometry so the two stay in step.
  const xaxis = document.createElement("div");
  xaxis.className = "cl-xaxis" + (dense ? " cl-dense" : "");

  rows.forEach((r, i) => {
    const v = values[i];
    const col = document.createElement("div");
    // A size bar for the unmeasured final bucket would be a flat zero, which
    // reads as "nothing was added" rather than "we haven't weighed it yet".
    // Hatch it in both metrics and say so in the tooltip.
    col.className = "cl-col" + (r.sizes_partial ? " cl-col-partial" : "");
    const h = Math.max(v > 0 ? 2 : 0, Math.round((v / top) * 100));
    const year = yearOf(r);
    const onCadence = year % yearsEvery === 0 && !seenYear.has(year);
    if (onCadence) seenYear.add(year);
    // The last column is labelled too, but only when the cadence has not
    // already put one within a year of it -- otherwise the two overprint at
    // the right edge.
    const showTick = onCadence
      || (i === rows.length - 1 && !seenYear.has(year)
          && year - Math.max(...seenYear, -Infinity) > yearsEvery / 2);
    if (showTick) seenYear.add(year);
    // "26" from "2026" or "2026-Q3": the century is the same on every bar and
    // costs width the axis does not have, and the quarter/month is dropped
    // because the tick marks the START of a labelled year -- printing
    // "26-Q1" would imply the label describes that quarter alone. The
    // tooltip carries the full period either way.
    const tick = !showTick ? "" : String(year).slice(2);
    col.innerHTML = `<div class="cl-bar" style="height:${h}%"></div>`;

    const label = clState.mode === "cumulative" ? "total" : "added";
    // In cumulative-size view an unmeasured bucket inherits the previous
    // total, so its bar is full height while contributing nothing. Say that
    // outright rather than letting the hatching carry the whole message.
    const unmeasuredSize = r.sizes_partial && clState.metric === "size";
    col.title =
      `${r.period} — ${label}: ${clFormat(v)}` +
      (unmeasuredSize
        ? clState.mode === "cumulative"
          ? " (unchanged — these documents are not yet measured)"
          : " (not yet measured)"
        : "") +
      `\ndocuments: +${r.items_added_count.toLocaleString()} ` +
      `(cumulative ${r.new.count.toLocaleString()})` +
      (r.sizes_partial
        ? "\nadded since the snapshot — counted, not yet measured"
        : "");
    chart.appendChild(col);

    const xl = document.createElement("div");
    xl.className = "cl-year";
    xl.textContent = tick;
    xaxis.appendChild(xl);
  });

  plot.appendChild(chart);
  wrap.appendChild(plot);
  // The wrap is a 2x2 grid: gutter and plot on the top row, an empty cell and
  // the x labels beneath. The empty cell is what indents the labels past the
  // gutter, so the first one sits over the first bar without either row
  // hard-coding the gutter's width.
  wrap.appendChild(document.createElement("div"));
  wrap.appendChild(xaxis);
  chartEl.appendChild(wrap);
}

function renderChangelog(rows, chartEl) {
  drawChart(groupRows(rows, clState.granularity), chartEl);
  for (const btn of document.querySelectorAll("#changelogControls button")) {
    // String(...) on both sides: granularity is a number in state and a
    // string in the DOM, and === across the two would never match.
    const on = String(clState[btn.dataset.axis]) === btn.dataset.value;
    btn.classList.toggle("cl-on", on);
    btn.setAttribute("aria-pressed", String(on));
  }
}

async function loadChangelog() {
  const chartEl = document.getElementById("changelogChart");
  if (!chartEl) return;
  try {
    const r = await fetch(CHANGELOG_URL);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const rows = await r.json();
    if (!rows.length) throw new Error("empty");

    const controls = document.getElementById("changelogControls");
    if (controls) {
      controls.addEventListener("click", (ev) => {
        const btn = ev.target.closest("button[data-axis]");
        if (!btn) return;
        const { axis, value } = btn.dataset;
        clState[axis] = axis === "granularity" ? Number(value) : value;
        renderChangelog(rows, chartEl);
      });
    }
    renderChangelog(rows, chartEl);
  } catch (e) {
    chartEl.textContent = "Changelog unavailable.";
    console.log("Could not load changelog:", e);
  }
}

loadChangelog();

// ---------------------------------------------------------------------------
// The About page's one outbound link to the parent project
// ---------------------------------------------------------------------------
// This is the mirror image of the parent's docs/local-links.js: that file ships
// the published Atlas URLs and rewrites them down to ports 8001-8003 when it is
// itself served locally. Here there is a single link going the other way, up to
// the parent, so a whole rewrite pass would be overkill -- the markup carries
// the production URL (the file that ships is the file that is deployed) and we
// swap in the local parent only when this Atlas is being served from localhost.
// Port 8000 matches the parent's serve_docs.py and Makefile, where 8003 is us.
const PARENT_LOCAL_PORT = 8000;

/* Host test copied from the parent's local-links.js, deliberately identical --
   including the private-IPv4 range, which the e-bharatisampat sibling's copy
   drops. "Local" means reachable on this machine or this LAN, not just
   loopback: browsing from a phone at 192.168.1.165:8003 is a normal way to work
   here (see the Makefile's get-server-ip-address target), and a loopback-only
   test sends those sessions to the public parent site instead. `127.` is inside
   PRIVATE_IPV4, so it needs no separate clause. */
const PRIVATE_IPV4 = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

function isLocal(hostname) {
  return hostname === "localhost"
      || hostname === "[::1]"
      || hostname === "::1"
      || hostname.endsWith(".localhost")
      || hostname.endsWith(".local")   // mDNS, e.g. my-mac.local
      || PRIVATE_IPV4.test(hostname);
}

if (isLocal(location.hostname)) {
  const parentLink = document.getElementById("parentLink");
  if (parentLink) {
    parentLink.href = `http://${location.hostname}:${PARENT_LOCAL_PORT}/`;
    parentLink.dataset.localized = "true";  // visible in devtools, as in the parent
  }
}
