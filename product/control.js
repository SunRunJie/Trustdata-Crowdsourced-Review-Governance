const state = { config: null, upload: null, jobs: [], selected: null, poller: null };
const $ = (selector) => document.querySelector(selector);
const api = async (url, options = {}) => {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `请求失败：${response.status}`);
  return body;
};
const showNotice = (text, bad = false) => { const el = $("#notice"); el.textContent = text; el.hidden = false; el.style.borderColor = bad ? "var(--red)" : "var(--amber)"; setTimeout(() => { el.hidden = true; }, 6000); };

function setPage(id) {
  document.querySelectorAll(".console-page").forEach(el => el.classList.toggle("active", el.id === id));
  document.querySelectorAll("#nav a").forEach(el => el.classList.toggle("active", el.getAttribute("href") === `#${id}`));
}
document.querySelectorAll("#nav a").forEach(link => link.addEventListener("click", (event) => { event.preventDefault(); setPage(link.getAttribute("href").slice(1)); }));

function formValue(form, name) { return new FormData(form).get(name) || ""; }
function setInput(form, name, value) { const input = form.elements[name]; if (input) input.value = value ?? ""; }

async function refreshStatus() {
  const value = await api("/api/status");
  $("#server-status").textContent = "本机控制台已就绪";
  $("#env-badge").textContent = `${value.python} · ${value.env_configured ? ".env 已找到" : "未配置 .env"}`;
  $("#status-list").innerHTML = `<dt>Python</dt><dd>${value.python}</dd><dt>.env</dt><dd>${value.env_configured ? "已配置" : "尚未创建"}</dd><dt>前置研究</dt><dd>${value.prior_requirements ? "可检查依赖" : "缺少 requirements"}</dd>`;
}

async function loadConfig() {
  const data = await api("/api/config/llm"); state.config = data.config;
  const c = data.config, form = $("#llm-form");
  ["api_type", "model", "api_key_env", "base_url", "max_tokens", "temperature"].forEach(key => setInput(form, key, c.llm?.[key]));
  ["request_delay", "max_pages_total", "max_pages_per_entity", "request_timeout", "user_agent"].forEach(key => setInput(form, key, c.crawl?.[key]));
  setInput(form, "platform_domains", JSON.stringify(c.crawl?.platform_domains || {}, null, 2));
  setInput(form, "min_citation_score", c.verification?.min_citation_score);
  $("#key-state").textContent = data.api_key_configured ? `当前密钥：${data.api_key_masked}` : "当前尚未配置 API Key。";
}

$("#llm-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const f = event.currentTarget;
  const number = (name) => Number(formValue(f, name));
  let platformDomains; try { platformDomains = JSON.parse(formValue(f, "platform_domains")); } catch (_) { return showNotice("平台域名白名单必须是有效 JSON。", true); }
  const payload = { config: { llm: { api_type: formValue(f,"api_type"), model: formValue(f,"model"), api_key_env: formValue(f,"api_key_env"), base_url: formValue(f,"base_url"), max_tokens: number("max_tokens"), temperature: number("temperature") }, crawl: { request_delay: number("request_delay"), max_pages_total: number("max_pages_total"), max_pages_per_entity: number("max_pages_per_entity"), request_timeout: number("request_timeout"), user_agent: formValue(f,"user_agent"), platform_domains: platformDomains }, verification: {min_citation_score: number("min_citation_score")} } };
  const key = formValue(f, "api_key"); if (key) payload.api_key = key;
  try { await api("/api/config/llm", { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) }); f.elements.api_key.value = ""; await loadConfig(); showNotice("本机配置已保存，API Key 未回显。"); } catch (e) { showNotice(e.message, true); }
});

async function startJob(kind, params = {}) {
  try { const job = await api("/api/jobs", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({kind, params}) }); state.jobs.unshift(job); selectJob(job.id); renderJobs(); setPage("results"); showNotice(`已加入任务：${kind}`); return job; } catch (e) { showNotice(e.message, true); return null; }
}

async function loadJobs() {
  try { state.jobs = await api("/api/jobs"); renderJobs(); } catch (e) { showNotice(e.message, true); }
}

$("#mining-form").addEventListener("submit", async (event) => { event.preventDefault(); const f = event.currentTarget; const taskFile = f.elements.task_file.files[0]; let taskUploadId = ""; if (taskFile) { const body = new FormData(); body.append("file", taskFile); try { taskUploadId = (await api("/api/uploads", {method:"POST", body})).upload_id; } catch (e) { showNotice(e.message, true); return; } } await startJob("mine", {task: formValue(f, "task"), task_upload_id: taskUploadId}); });
$("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const file = event.currentTarget.elements.file.files[0]; if (!file) return;
  const body = new FormData(); body.append("file", file);
  try { const result = await api("/api/uploads", {method:"POST", body}); state.upload = result; $("#assess-button").disabled = Boolean(result.preview_error || result.preview?.canonical_missing?.length); $("#upload-preview").textContent = result.preview_error ? `预检失败：${result.preview_error}` : JSON.stringify(result.preview, null, 2); showNotice("文件已上传至控制台暂存区。"); } catch (e) { showNotice(e.message, true); }
});
$("#assessment-form").addEventListener("submit", async (event) => { event.preventDefault(); if (!state.upload) return showNotice("请先上传数据文件。", true); await startJob("assess", {upload_id: state.upload.upload_id, scenario: formValue(event.currentTarget,"scenario")}); });
$("#main-tasks").addEventListener("click", event => { const button = event.target.closest("button[data-job]"); if (button) startJob(button.dataset.job); });
$("#verify-form").addEventListener("submit", event => { event.preventDefault(); startJob("verify_manifest", {run_id: formValue(event.currentTarget, "run_id")}); });
$("#publish-form").addEventListener("submit", event => { event.preventDefault(); const f = event.currentTarget; if (!f.elements.confirmed.checked) return showNotice("发布前必须明确确认覆盖正式产物。", true); startJob("publish_dashboard", {run_id: formValue(f, "run_id"), confirmed: true}); });
document.querySelectorAll("[data-job='research_install']").forEach(button => button.addEventListener("click", () => startJob("research_install")));
$("#research-form").addEventListener("submit", event => { event.preventDefault(); const f = event.currentTarget; if (f.elements.collect.checked && !f.elements.collection_confirmed.checked) return showNotice("实时采集前必须勾选合规确认。", true); startJob("prior_research", {mode: formValue(f,"mode"), collect: f.elements.collect.checked, collection_confirmed: f.elements.collection_confirmed.checked}); });

function renderJobs() {
  $("#recent-run-count").textContent = state.jobs.length;
  $("#job-list").innerHTML = state.jobs.length ? state.jobs.map(job => `<button class="job-item ${job.state === "failed" ? "failed" : ""}" data-id="${job.id}"><b>${job.kind}</b><span class="state">${job.state}</span><small>${job.id}</small></button>`).join("") : '<p class="notice">尚未启动任务。</p>';
  document.querySelectorAll(".job-item").forEach(el => el.addEventListener("click", () => selectJob(el.dataset.id)));
}
function selectJob(id) { state.selected = id; renderJobs(); if (!state.poller) state.poller = setInterval(refreshSelected, 1200); refreshSelected(); }
async function refreshSelected() {
  if (!state.selected) return;
  try { const job = await api(`/api/jobs/${state.selected}`); const index = state.jobs.findIndex(item => item.id === job.id); if (index >= 0) state.jobs[index] = job; else state.jobs.unshift(job); $("#job-title").textContent = `${job.kind} · ${job.state}`; $("#job-log").textContent = job.events.map(event => `[${event.at}] ${event.message}`).join("\n") || "任务已创建，等待日志…"; $("#job-log").scrollTop = $("#job-log").scrollHeight; $("#artifact-list").innerHTML = job.artifacts.map(a => `<a target="_blank" rel="noopener" href="/api/jobs/${job.id}/artifacts/${a.path}">${a.path} (${Math.ceil(a.bytes / 1024)} KB)</a>`).join(""); renderJobs(); if (["succeeded","failed"].includes(job.state)) { clearInterval(state.poller); state.poller = null; } } catch (e) { showNotice(e.message, true); }
}

(async () => { try { await Promise.all([refreshStatus(), loadConfig(), loadJobs()]); } catch (e) { $("#server-status").textContent = "服务检查失败"; showNotice(e.message, true); } })();
