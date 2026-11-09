/* script.js - dashboard logic. Talks to the Flask REST API using fetch(). */
"use strict";

const COLORS = { "git-flow": "#f05133", "github-flow": "#58a6ff", "trunk-based": "#3fb950" };
const FALLBACK_COLORS = ["#d29922", "#bc8cff", "#39c5cf"];
const METRIC_KEYS = [
  "merge_conflicts", "integration_time_hours", "commit_frequency",
  "collaboration_efficiency", "deployment_failure_rate",
];
const METRIC_ICONS = {
  merge_conflicts: "bi-exclude", integration_time_hours: "bi-stopwatch",
  commit_frequency: "bi-clock-history", collaboration_efficiency: "bi-people",
  deployment_failure_rate: "bi-exclamation-octagon",
};
const DEFAULT_SLIDER = {
  merge_conflicts: 20, integration_time_hours: 25, commit_frequency: 15,
  collaboration_efficiency: 20, deployment_failure_rate: 20,
};

const state = { comparison: null, metrics: [], workflows: [], barChart: null, radarChart: null };
let metricModal = null;

/* ---------- helpers ---------- */
function esc(value) {
  const div = document.createElement("div");
  div.textContent = value === null || value === undefined ? "" : String(value);
  return div.innerHTML;
}
const $ = (id) => document.getElementById(id);

function colorFor(slug, index) {
  return COLORS[slug] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

function showAlert(message, type = "success") {
  const box = $("alertBox");
  const el = document.createElement("div");
  el.className = `alert alert-${type} alert-dismissible fade show shadow`;
  el.innerHTML = `${esc(message)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  box.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

async function api(path, options = {}) {
  const init = { headers: { "Content-Type": "application/json" }, ...options };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const response = await fetch(path, init);
  let data = {};
  try { data = await response.json(); } catch (_) { /* empty body */ }
  if (!response.ok) {
    const details = data.details ? " " + Object.entries(data.details).map(([k, v]) => `${k}: ${v}`).join("; ") : "";
    throw new Error((data.error || `Request failed (${response.status})`) + details);
  }
  return data;
}

/* ---------- loading ---------- */
async function loadAll() {
  // 1) CRUD data always loads, so the user can fix missing records.
  try {
    const [metrics, workflows] = await Promise.all([api("/api/metrics"), api("/api/workflows")]);
    state.metrics = metrics.metrics;
    state.workflows = workflows.workflows;
    renderMetricsTable();
  } catch (err) {
    showAlert(err.message, "danger");
    return;
  }
  // 2) Comparison needs at least two workflows with metrics.
  try {
    const [comparison, rec, history] = await Promise.all([
      api("/api/comparison"), api("/api/recommendation"), api("/api/history"),
    ]);
    state.comparison = comparison;
    renderMetricCards(comparison);
    renderWorkflowCards(comparison, rec.recommendation);
    renderCharts(comparison);
    renderRawTable(comparison);
    renderRecommendation(rec);
    renderHistory(history.history);
  } catch (err) {
    const msg = `<div class="alert alert-warning mb-0">Comparison unavailable: ${esc(err.message)}. Add metrics in the "Manage Data" section.</div>`;
    $("metricCards").innerHTML = `<div class="col-12">${msg}</div>`;
    $("workflowCards").innerHTML = "";
    $("recommendationBox").innerHTML = msg;
    $("scoreBars").innerHTML = "";
    $("rawTable").innerHTML = "";
    [state.barChart, state.radarChart].forEach((c) => c && c.destroy());
    state.barChart = state.radarChart = null;
  }
}

/* ---------- overview cards ---------- */
function renderMetricCards(cmp) {
  $("metricCards").innerHTML = METRIC_KEYS.map((key) => {
    const def = cmp.metric_definitions[key];
    const best = cmp.best_per_metric[key];
    const arrow = def.direction === "lower" ? "lower is better" : "higher is better";
    return `<div class="col-6 col-md-4 col-xl">
      <div class="metric-card">
        <div class="icon"><i class="bi ${METRIC_ICONS[key]}"></i></div>
        <div class="label mt-2">${esc(def.label)}</div>
        <div class="value">${esc(best.value)}</div>
        <div class="small text-secondary">${esc(def.unit)}</div>
        <div class="small mt-2"><i class="bi bi-award text-warning"></i> ${esc(best.workflow)}</div>
        <div class="small text-secondary">${arrow}</div>
      </div></div>`;
  }).join("");
}

/* ---------- workflow cards ---------- */
function renderWorkflowCards(cmp, rec) {
  const winnerId = rec.winner.workflow_id;
  $("workflowCards").innerHTML = cmp.workflows.map((wf) => {
    const isWinner = wf.id === winnerId;
    return `<div class="col-md-6 col-xl-4">
      <div class="wf-card ${esc(wf.slug)}">
        ${isWinner ? '<span class="badge bg-success winner-ribbon"><i class="bi bi-trophy-fill"></i> Recommended</span>' : ""}
        <h4 class="mb-1">${esc(wf.name)}</h4>
        <div class="model mb-2">${esc(wf.branching_model)}</div>
        <p class="text-secondary small">${esc(wf.description)}</p>
        <div class="d-flex align-items-baseline gap-2 mb-2">
          <span class="score" style="color:${colorFor(wf.slug, 0)}">${wf.overall_score.toFixed(1)}</span>
          <span class="text-secondary">/ 100 overall</span>
        </div>
        <ul>
          <li>Conflicts: <strong>${esc(wf.metrics.merge_conflicts)}</strong> / month</li>
          <li>Integration: <strong>${esc(wf.metrics.integration_time_hours)}</strong> h</li>
          <li>Commits: <strong>${esc(wf.metrics.commit_frequency)}</strong> / dev / day</li>
          <li>Collaboration: <strong>${esc(wf.metrics.collaboration_efficiency)}</strong> / 100</li>
          <li>Deploy failures: <strong>${esc(wf.metrics.deployment_failure_rate)}</strong> %</li>
        </ul>
        <hr>
        <div class="small"><strong>Best for:</strong> ${esc(wf.best_for)}</div>
      </div></div>`;
  }).join("");
}

/* ---------- charts ---------- */
function renderCharts(cmp) {
  const labels = METRIC_KEYS.map((k) => cmp.metric_definitions[k].label);
  const datasets = cmp.workflows.map((wf, i) => ({
    label: wf.name,
    data: METRIC_KEYS.map((k) => wf.normalized[k]),
    backgroundColor: colorFor(wf.slug, i) + "cc",
    borderColor: colorFor(wf.slug, i),
    borderWidth: 1,
  }));
  Chart.defaults.color = "#c9d1d9";
  Chart.defaults.borderColor = "#30363d";

  if (state.barChart) state.barChart.destroy();
  state.barChart = new Chart($("barChart"), {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: "Normalised score (100 = best)" } },
        x: { title: { display: true, text: "Parameter" } },
      },
      plugins: { legend: { position: "bottom" }, title: { display: false } },
    },
  });

  if (state.radarChart) state.radarChart.destroy();
  state.radarChart = new Chart($("radarChart"), {
    type: "radar",
    data: {
      labels,
      datasets: datasets.map((d) => ({ ...d, fill: true, backgroundColor: d.borderColor + "33", pointBackgroundColor: d.borderColor })),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, backdropColor: "transparent" }, grid: { color: "#30363d" }, angleLines: { color: "#30363d" } } },
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function renderRawTable(cmp) {
  const head = `<thead><tr><th>Parameter</th><th>Better when</th>${cmp.workflows.map((w) => `<th>${esc(w.name)}</th>`).join("")}</tr></thead>`;
  const rows = METRIC_KEYS.map((key) => {
    const def = cmp.metric_definitions[key];
    const best = cmp.best_per_metric[key].workflow;
    const cells = cmp.workflows.map((w) =>
      `<td class="${w.name === best ? "text-success fw-bold" : ""}">${esc(w.metrics[key])}</td>`).join("");
    return `<tr><td>${esc(def.label)} <small class="text-secondary">(${esc(def.unit)})</small></td><td>${esc(def.direction)}</td>${cells}</tr>`;
  }).join("");
  $("rawTable").innerHTML = head + `<tbody>${rows}</tbody>`;
}

/* ---------- recommendation ---------- */
function renderRecommendation(data) {
  const r = data.recommendation;
  const list = (items, icon, cls) => items.map((t) => `<li><i class="bi ${icon} ${cls} me-1"></i>${esc(t)}</li>`).join("");
  $("recommendationBox").innerHTML = `
    <div class="winner-box">
      <div class="text-secondary small text-uppercase">Recommended workflow</div>
      <h3 class="mb-1">${esc(r.winner.name)} <span class="badge bg-success">${r.winner.overall_score.toFixed(1)} / 100</span></h3>
      <p class="mb-2">${esc(r.summary)}</p>
      <p class="small mb-3">Confidence: <strong>${esc(r.confidence)}</strong> (margin ${esc(r.margin)} points)</p>
    </div>
    <h6 class="mt-3">Why this workflow?</h6>
    <ul class="list-unstyled small mb-2">${list(r.strengths, "bi-check-circle-fill", "text-success")}</ul>
    ${r.weaknesses.length ? `<h6>Trade-offs to be aware of</h6>
    <ul class="list-unstyled small mb-0">${list(r.weaknesses, "bi-exclamation-circle-fill", "text-warning")}</ul>` : ""}`;

  $("scoreBars").innerHTML = data.scores.map((s, i) => {
    const color = colorFor(s.slug, i);
    return `<div class="score-row">
      <div class="d-flex justify-content-between">
        <span><span class="dot" style="background:${color}"></span>#${s.rank} ${esc(s.name)}</span>
        <strong>${s.overall_score.toFixed(2)} / 100</strong>
      </div>
      <div class="progress"><div class="progress-bar" style="width:${s.overall_score}%;background:${color}"></div></div>
    </div>`;
  }).join("") + `<small class="text-secondary">Weights used: ${METRIC_KEYS.map((k) =>
    `${esc(state.comparison.metric_definitions[k].label)} ${(data.weights[k] * 100).toFixed(0)}%`).join(" &middot; ")}</small>`;
}

function renderHistory(history) {
  if (!history.length) {
    $("historyBody").innerHTML = `<tr><td colspan="5" class="text-secondary">No saved recommendations yet. Click "Recalculate &amp; save".</td></tr>`;
    return;
  }
  $("historyBody").innerHTML = history.map((h) => `<tr>
    <td>${h.id}</td><td>${esc(h.created_at.replace("T", " ").replace("+00:00", ""))}</td>
    <td>${esc(h.winner_name)}</td><td>${h.winner_score.toFixed(2)}</td>
    <td class="small">${h.results.map((r) => `${r.rank}. ${esc(r.name)} (${r.overall_score.toFixed(1)})`).join(" &nbsp; ")}</td></tr>`).join("");
}

/* ---------- weight sliders ---------- */
function buildSliders() {
  const defs = {
    merge_conflicts: "Merge Conflicts", integration_time_hours: "Integration Time",
    commit_frequency: "Commit Frequency", collaboration_efficiency: "Collaboration",
    deployment_failure_rate: "Deployment Failures",
  };
  $("weightSliders").innerHTML = METRIC_KEYS.map((key) => `
    <div class="mb-2">
      <div class="d-flex justify-content-between small"><label for="w_${key}">${defs[key]}</label><span id="wv_${key}">${DEFAULT_SLIDER[key]}</span></div>
      <input type="range" class="form-range" min="0" max="50" step="5" value="${DEFAULT_SLIDER[key]}" id="w_${key}">
    </div>`).join("");
  METRIC_KEYS.forEach((key) => {
    $(`w_${key}`).addEventListener("input", (e) => { $(`wv_${key}`).textContent = e.target.value; });
  });
}

function readWeights() {
  const weights = {};
  METRIC_KEYS.forEach((k) => { weights[k] = Number($(`w_${k}`).value); });
  return weights;
}

async function recalculate() {
  try {
    const data = await api("/api/recommendation", { method: "POST", body: { weights: readWeights() } });
    renderRecommendation(data);
    const history = await api("/api/history");
    renderHistory(history.history);
    showAlert(`Recommendation saved: ${data.recommendation.winner.name}`);
  } catch (err) {
    showAlert(err.message, "danger");
  }
}

function resetWeights() {
  METRIC_KEYS.forEach((k) => { $(`w_${k}`).value = DEFAULT_SLIDER[k]; $(`wv_${k}`).textContent = DEFAULT_SLIDER[k]; });
}

/* ---------- CRUD table ---------- */
function renderMetricsTable() {
  $("metricsBody").innerHTML = state.metrics.length ? state.metrics.map((m) => `<tr>
    <td><strong>${esc(m.name)}</strong></td>
    <td>${esc(m.merge_conflicts)}</td><td>${esc(m.integration_time_hours)}</td><td>${esc(m.commit_frequency)}</td>
    <td>${esc(m.collaboration_efficiency)}</td><td>${esc(m.deployment_failure_rate)}</td>
    <td><span class="badge ${m.data_source === "simulated" ? "bg-secondary" : "bg-info text-dark"}">${esc(m.data_source)}</span></td>
    <td class="text-end">
      <button class="btn btn-sm btn-outline-primary" data-edit="${m.id}"><i class="bi bi-pencil"></i></button>
      <button class="btn btn-sm btn-outline-danger" data-delete="${m.id}"><i class="bi bi-trash"></i></button>
    </td></tr>`).join("")
    : `<tr><td colspan="8" class="text-secondary">No metric records. Click "Add metrics".</td></tr>`;
}

function openModal(metric) {
  $("formError").textContent = "";
  $("metricForm").classList.remove("was-validated");
  const select = $("fWorkflow");
  if (metric) {
    $("metricModalTitle").textContent = `Edit metrics - ${metric.name}`;
    $("metricId").value = metric.id;
    select.innerHTML = `<option value="${metric.workflow_id}">${esc(metric.name)}</option>`;
    select.disabled = true;
    $("fConflicts").value = metric.merge_conflicts;
    $("fIntegration").value = metric.integration_time_hours;
    $("fCommits").value = metric.commit_frequency;
    $("fCollab").value = metric.collaboration_efficiency;
    $("fFailure").value = metric.deployment_failure_rate;
  } else {
    const used = new Set(state.metrics.map((m) => m.workflow_id));
    const free = state.workflows.filter((w) => !used.has(w.id));
    if (!free.length) { showAlert("Every workflow already has metrics. Edit an existing record instead.", "info"); return; }
    $("metricModalTitle").textContent = "Add metrics";
    $("metricId").value = "";
    select.innerHTML = free.map((w) => `<option value="${w.id}">${esc(w.name)}</option>`).join("");
    select.disabled = false;
    ["fConflicts", "fIntegration", "fCommits", "fCollab", "fFailure"].forEach((id) => { $(id).value = ""; });
  }
  metricModal.show();
}

async function saveMetric(event) {
  event.preventDefault();
  const form = $("metricForm");
  if (!form.checkValidity()) { form.classList.add("was-validated"); return; }
  const body = {
    merge_conflicts: Number($("fConflicts").value),
    integration_time_hours: Number($("fIntegration").value),
    commit_frequency: Number($("fCommits").value),
    collaboration_efficiency: Number($("fCollab").value),
    deployment_failure_rate: Number($("fFailure").value),
  };
  const id = $("metricId").value;
  try {
    if (id) {
      await api(`/api/metrics/${id}`, { method: "PUT", body });
    } else {
      body.workflow_id = Number($("fWorkflow").value);
      await api("/api/metrics", { method: "POST", body });
    }
    metricModal.hide();
    showAlert(id ? "Metrics updated" : "Metrics created");
    await loadAll();
  } catch (err) {
    $("formError").textContent = err.message;
  }
}

async function deleteMetric(id) {
  if (!confirm("Delete this metric record? The workflow will be excluded from comparison until you add it again.")) return;
  try {
    await api(`/api/metrics/${id}`, { method: "DELETE" });
    showAlert("Metric record deleted", "warning");
    await loadAll();
  } catch (err) {
    showAlert(err.message, "danger");
  }
}

/* ---------- init ---------- */
document.addEventListener("DOMContentLoaded", () => {
  metricModal = new bootstrap.Modal($("metricModal"));
  buildSliders();
  $("btnRecalc").addEventListener("click", recalculate);
  $("btnResetWeights").addEventListener("click", resetWeights);
  $("btnAdd").addEventListener("click", () => openModal(null));
  $("metricForm").addEventListener("submit", saveMetric);
  $("metricsBody").addEventListener("click", (e) => {
    const edit = e.target.closest("[data-edit]");
    const del = e.target.closest("[data-delete]");
    if (edit) openModal(state.metrics.find((m) => m.id === Number(edit.dataset.edit)));
    if (del) deleteMetric(Number(del.dataset.delete));
  });
  loadAll();
});
