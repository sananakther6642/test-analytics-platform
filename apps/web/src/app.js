// Plain JS, no framework, no build step — deliberate per the plan (D1.2):
// this exists to give Playwright something real to click, and to let a
// separate nginx container demonstrate a genuine two-service K8s topology
// later. Relative URLs throughout so this works unmodified behind any
// reverse proxy — never hardcode a hostname.

const API_BASE = "/api/v1";

let chart = null;

async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API_BASE}/reports`, { method: "POST", body: form });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(body.detail || `Upload failed (${resp.status})`);
  }
  return resp.json();
}

async function fetchSummary() {
  const resp = await fetch(`${API_BASE}/analytics/summary`);
  if (!resp.ok) throw new Error(`Summary fetch failed (${resp.status})`);
  return resp.json();
}

async function fetchFlaky() {
  const resp = await fetch(`${API_BASE}/analytics/flaky`);
  if (!resp.ok) throw new Error(`Flaky fetch failed (${resp.status})`);
  return resp.json();
}

function renderSummary(summary) {
  const el = document.getElementById("summary-cards");
  el.innerHTML = `
    <div class="card"><span class="label">Runs</span><span class="value">${summary.total_runs}</span></div>
    <div class="card"><span class="label">Tests</span><span class="value">${summary.total_tests}</span></div>
    <div class="card"><span class="label">Pass rate</span><span class="value">${(summary.pass_rate * 100).toFixed(1)}%</span></div>
  `;
}

function renderChart(summary) {
  const ctx = document.getElementById("pass-fail-chart");
  const data = {
    labels: ["Passed", "Failed", "Skipped", "Error"],
    datasets: [{
      label: "Test results",
      data: [summary.passed, summary.failed, summary.skipped, summary.error],
      backgroundColor: ["#2e7d32", "#c62828", "#9e9e9e", "#ef6c00"],
    }],
  };
  if (chart) {
    chart.data = data;
    chart.update();
  } else {
    chart = new Chart(ctx, { type: "bar", data, options: { scales: { y: { beginAtZero: true } } } });
  }
}

function renderFlaky(results) {
  const tbody = document.querySelector("#flaky-table tbody");
  const empty = document.getElementById("flaky-empty");
  tbody.innerHTML = "";

  if (results.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  for (const r of results) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.test_id}</td>
      <td>${r.score.toFixed(3)}</td>
      <td>${r.same_commit_disagreements}</td>
      <td>${(r.flip_rate * 100).toFixed(1)}%</td>
      <td>${r.total_runs}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function refreshDashboard() {
  const [summary, flaky] = await Promise.all([fetchSummary(), fetchFlaky()]);
  renderSummary(summary);
  renderChart(summary);
  renderFlaky(flaky);
}

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById("file-input");
  const status = document.getElementById("upload-status");
  const file = fileInput.files[0];
  if (!file) return;

  status.textContent = "Uploading...";
  try {
    const result = await uploadFile(file);
    status.textContent = `Uploaded ${result.run_id} (${result.test_count} tests).`;
    fileInput.value = "";
    await refreshDashboard();
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
});

refreshDashboard().catch((err) => {
  document.getElementById("upload-status").textContent = `Error loading dashboard: ${err.message}`;
});
