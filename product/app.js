const DATA_URL = "../app/data/dashboard.json";
const ROUTES = {
  overview: "治理总览",
  passports: "可信护照",
  risk: "风险监测",
  queue: "治理队列",
  audit: "审计追溯",
  benchmark: "基准验证",
};

let state = { data: null, route: "overview", passportIndex: 0, query: "", tier: "ALL" };
const content = document.querySelector("#content");
const loading = document.querySelector("#loading");
const errorBox = document.querySelector("#error");

const fmt = (value, digits = 0) => Number(value).toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
const pct = (value, digits = 1) => `${fmt(Number(value) * 100, digits)}%`;
const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const tierLetter = (tier) => String(tier || "C").charAt(0);
const scoreOf = (p) => Number(p.dts ?? p.data_trust_score ?? 0);
const coverageOf = (p) => Number(p.coverage ?? p.evidence_coverage ?? 0);
const uncertaintyOf = (p) => Number(p.uncertainty ?? 0);

function metric(label, value, note) {
  return `<article class="metric"><small>${label}</small><strong>${value}</strong><em>${note}</em></article>`;
}

function lineChart(rows, keys) {
  const width = 620, height = 250, left = 46, right = 18, top = 18, bottom = 38;
  const innerW = width - left - right, innerH = height - top - bottom;
  const xs = rows.map((_, i) => left + i * innerW / Math.max(rows.length - 1, 1));
  const y = v => top + (1 - Math.max(0, Math.min(1, Number(v)))) * innerH;
  const colors = ["#0e6b57", "#d88624", "#376c88"];
  const grid = [0, .25, .5, .75, 1].map(v => `<line class="grid" x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}"/><text x="5" y="${y(v)+4}">${fmt(v,2)}</text>`).join("");
  const paths = keys.map((k, j) => {
    const d = rows.map((r, i) => `${i ? "L" : "M"}${xs[i].toFixed(1)},${y(r[k.key]).toFixed(1)}`).join(" ");
    const points = rows.map((r, i) => `<circle cx="${xs[i]}" cy="${y(r[k.key])}" r="4" fill="${colors[j]}"/>`).join("");
    return `<path d="${d}" fill="none" stroke="${colors[j]}" stroke-width="2.5"/>${points}`;
  }).join("");
  const labels = rows.map((r, i) => `<text x="${xs[i]}" y="${height-9}" text-anchor="middle">${fmt(r.contamination_level * 100)}%</text>`).join("");
  return `<div class="chart"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="污染率与检测指标折线图">${grid}<line class="axis" x1="${left}" x2="${width-right}" y1="${height-bottom}" y2="${height-bottom}"/>${paths}${labels}</svg><div class="legend">${keys.map((k,i)=>`<span><i style="background:${colors[i]}"></i>${k.label}</span>`).join("")}</div></div>`;
}

function overview(d) {
  const h = d.headline;
  const levels = d.benchmark.contamination_levels;
  const rows = levels.map(level => {
    const entry = d.benchmark.metrics?.find?.(x => x.contamination_level === level) || {};
    return entry;
  }).filter(x => Object.keys(x).length);
  const tierTotal = Object.values(d.tier_distribution).reduce((a,b)=>a+b,0);
  const tierColors = ["#169b79", "#4d8ca5", "#d8a13d", "#c96852", "#8b3a35"];
  const tiers = Object.entries(d.tier_distribution).map(([name,value],i)=>`<div class="tier-row"><span><span class="pill ${name[0]}">${name[0]}</span> ${name.slice(2).replaceAll("_"," ")}</span><div class="tier-track"><span style="width:${value/tierTotal*100}%;background:${tierColors[i]}"></span></div><b>${fmt(value)}</b></div>`).join("");
  return `<div class="hero-grid">
    <article class="panel"><p class="eyebrow">UGC DATA USE-RISK ASSESSMENT</p><h2>UGC 数据使用风险的可解释评估与分级</h2><p class="lead">系统联合来源、行为、内容、跨源一致性与时间结构信号，按业务场景生成 DTS、证据覆盖度、不确定性、治理等级和操作建议。当前任务聚焦数据使用风险；事实核查与生成来源判别由独立流程承担。</p><div class="evidence-strip"><b>E2</b><span>当前效能证据来自观测分布播种的受控合成基准；线上效度将在平台试点中验证。</span></div></article>
    <article class="panel ring-wrap"><div class="ring"><div class="ring-copy"><strong>${pct(h.risk_detection_auprc_at_30pct)}</strong><small>30% 污染 AUPRC</small></div></div></article>
  </div>
  <div class="metric-grid">
    ${metric("观测数据记录", fmt(d.observed_data.entities_total + d.observed_data.reviews_total), "实体 + 已发表评论")}
    ${metric("跨源对齐实体", fmt(d.observed_data.cross_source_entities), "AOTY × RYM")}
    ${metric("30% 污染检测 F1", pct(h.risk_detection_f1_at_30pct), "固定验证阈值")}
    ${metric("30% 清洁误伤率", pct(h.false_positive_rate_at_30pct,2), "FPR · 越低越好")}
  </div>
  <div class="two-col">
    <article class="panel"><h3>污染强度下的检测表现</h3>${rows.length ? lineChart(rows,[{key:"f1",label:"F1"},{key:"auprc",label:"AUPRC"},{key:"recall",label:"Recall"}]) : '<p class="notice">详细曲线见“基准验证”页。</p>'}</article>
    <article class="panel"><h3>治理等级分布</h3>${tiers}<p class="callout">${fmt(d.review_queue_count)} 条记录进入人工复核队列。等级用于表达治理优先级和建议动作。</p></article>
  </div>`;
}

function passportTable(d) {
  const rows = d.passports.filter(p => {
    const hit = !state.query || JSON.stringify(p).toLowerCase().includes(state.query.toLowerCase());
    const tierHit = state.tier === "ALL" || tierLetter(p.tier) === state.tier;
    return hit && tierHit;
  });
    return `<article class="panel"><div class="toolbar"><input id="passport-search" value="${esc(state.query)}" placeholder="搜索记录、实体或贡献者…" aria-label="搜索可信护照"><select id="tier-filter" aria-label="按等级筛选"><option value="ALL">全部等级</option>${["A","B","C","D","E"].map(t=>`<option ${state.tier===t?"selected":""}>${t}</option>`).join("")}</select></div><div class="table-wrap"><table><thead><tr><th>记录</th><th>DTS</th><th>覆盖度</th><th>等级</th><th>建议动作</th></tr></thead><tbody>${rows.map((p,i)=>`<tr data-passport="${d.passports.indexOf(p)}" tabindex="0"><td><b>${esc(p.record_id || p.id)}</b><br><small>${esc(p.entity_id || "—")}</small></td><td><div class="bar"><span style="width:${scoreOf(p)}%"></span></div><small>${fmt(scoreOf(p),2)}</small></td><td>${pct(coverageOf(p))}</td><td><span class="pill ${tierLetter(p.tier)}">${esc(p.tier)}</span></td><td>${esc(p.action || p.recommended_action || "—")}</td></tr>`).join("")}</tbody></table>${rows.length?"":'<div class="empty">当前筛选结果为空</div>'}</div></article>`;
}

function passports(d) {
  const p = d.passports[state.passportIndex] || d.passports[0];
  const vector = p.trust_vector || p.vector || {P:p.P,B:p.B,C:p.C,X:p.X,T:p.T};
  return `<div class="two-col"><section>${passportTable(d)}</section><aside class="panel"><div class="passport-head"><div><p class="eyebrow">TRUST PASSPORT</p><h2>${esc(p.entity_id || "记录可信护照")}</h2><p class="passport-id">${esc(p.record_id || p.id)}</p></div><span class="pill ${tierLetter(p.tier)}">${esc(p.tier)}</span></div><div class="vector-grid">${["P","B","C","X","T"].map(k=>`<div class="vector-card"><b>${fmt(vector?.[k] ?? 0,1)}</b><small>${k}</small></div>`).join("")}</div><div class="metric-grid" style="grid-template-columns:1fr 1fr">${metric("DTS",fmt(scoreOf(p),2),"0–100 场景化可信分")}${metric("不确定性",fmt(uncertaintyOf(p),2),"0–100 · 越低越稳定")}</div><h3>治理建议</h3><p class="callout">${esc(p.action || p.recommended_action || "进入人工复核")}</p><p class="notice">P 来源 · B 行为 · C 内容 · X 跨源一致性 · T 时间结构。缺失维度通过覆盖度与不确定性显式披露。</p></aside></div>`;
}

function risk(d) {
  const h = d.headline;
  return `<div class="metric-grid">${metric("模型验证阈值",fmt(h.validation_threshold,2),"在验证集锁定")}${metric("30% F1",pct(h.risk_detection_f1_at_30pct),"风险检测")}${metric("30% AUPRC",pct(h.risk_detection_auprc_at_30pct),"类不平衡指标")}${metric("30% FPR",pct(h.false_positive_rate_at_30pct,2),"清洁记录误伤")}</div><div class="two-col"><article class="panel"><h2>风险构成</h2><p class="lead">模型汇总可审计的结构性信号：元数据缺失、行为集中、重复模板、跨源偏差与时间突发。高风险表示记录直接进入排序、训练或经营分析时可能带来较高代价。</p><div class="vector-grid">${[['P','来源完整性'],['B','行为结构'],['C','内容结构'],['X','跨源一致性'],['T','时间结构']].map(x=>`<div class="vector-card"><b>${x[0]}</b><small>${x[1]}</small></div>`).join("")}</div></article><article class="panel"><h2>公平性护栏</h2><div class="table-wrap"><table><thead><tr><th>账号年龄组</th><th>清洁样本</th><th>误伤率</th></tr></thead><tbody>${d.fairness.map(r=>`<tr><td>${esc(r.group ?? r.account_age_group)}</td><td>${fmt(r.clean_count ?? r.clean_n ?? r.n_clean)}</td><td>${pct(r.false_positive_rate ?? r.fpr,2)}</td></tr>`).join("")}</tbody></table></div><p class="callout">账号年龄仅占较低特征权重，风险判断需结合其余证据。</p></article></div>`;
}

function queue(d) {
  const items = d.passports.filter(p => ["D","E"].includes(tierLetter(p.tier)));
  return `<div class="metric-grid">${metric("待复核总量",fmt(d.review_queue_count),"完整基准")}${metric("页面样例",fmt(items.length),"脱敏展示")}${metric("处置模式", "人工复核", "原型提供建议动作")}${metric("复核 SLA", "试点定义", "依据平台容量校准")}</div><article class="panel"><h2>人工治理队列</h2><p class="lead">优先级由风险、覆盖度与业务场景共同确定。原型输出建议动作，平台治理人员负责最终决策。</p><div class="table-wrap"><table><thead><tr><th>等级</th><th>记录</th><th>DTS</th><th>不确定性</th><th>动作</th></tr></thead><tbody>${items.map(p=>`<tr><td><span class="pill ${tierLetter(p.tier)}">${esc(p.tier)}</span></td><td>${esc(p.record_id || p.id)}</td><td>${fmt(scoreOf(p),2)}</td><td>${fmt(uncertaintyOf(p),2)}</td><td>${esc(p.action || p.recommended_action)}</td></tr>`).join("")}</tbody></table></div></article>`;
}

function audit() {
  const events = [
    ["阶段 05","实验完成","受控污染 1/5/10/20/30% 全部运行；输出分类、排序、消融、公平性与五次分组敏感性结果。"],
    ["阶段 04","阈值锁定","验证集按误伤约束选择 0.90；测试集用于独立评估。"],
    ["阶段 03","特征生成","P/B/C/X/T 五维信号按版本化配置计算，保留覆盖度与缺失指示。"],
    ["阶段 02","基准构造","从观测分布采样实体与已发表评论文本，注入五类可控风险。"],
    ["阶段 01","数据快照","26 个源文件完成逐文件哈希、行列数、缺失与重复检查。"],
  ];
  return `<div class="two-col"><article class="panel"><h2>本次运行审计链</h2><ol class="audit-list">${events.map(e=>`<li><time>${e[0]}</time><div><strong>${e[1]}</strong><p>${e[2]}</p></div></li>`).join("")}</ol></article><article class="panel"><h2>证据适用范围</h2><ul class="limitations"><li>实验数值可回溯到运行清单、配置、随机种子与文件哈希。</li><li>观测数据用于分布与实体参考；风险标签来自受控合成注入。</li><li>当前证据属于团队内部受控评测；平台上线与商业验证进入后续试点。</li><li>数据许可逐源管理；RYM 数据保留在内部研究环境。</li></ul></article></div>`;
}

function benchmark(d) {
  const h = d.headline;
  const s30 = d.split_sensitivity?.find?.(x => Number(x.contamination) === 0.3) || {};
  const r30 = d.benchmark.metrics?.find?.(x => Number(x.contamination_level) === 0.3) || {};
  const rankReduction = r30.raw_mean_rank_error > 0 ? 1 - r30.weighted_mean_rank_error / r30.raw_mean_rank_error : 0;
  const attackCount = Object.keys(d.benchmark.attack_types || {}).length;
  return `<div class="hero-grid"><article class="panel"><p class="eyebrow">CONTROLLED CONTAMINATION BENCHMARK</p><h2>性能随污染强度和数据划分变化</h2><p class="lead">5%–30% 污染下检测性能保持稳定区间。1% 污染下精确率和 F1 明显下降。排序加权在 20%–30% 降低平均排名误差；1% 场景采用监测与人工复核策略。</p></article><article class="panel"><h3>基准规模</h3><div class="metric-grid" style="grid-template-columns:1fr 1fr">${metric("清洁记录",fmt(d.benchmark.clean_records),"合成行为/观测内容")}${metric("最大注入",fmt(d.benchmark.maximum_injected_records),"30% 污染")}${metric("攻击类型",fmt(attackCount),"受控机制")}${metric("分组复算",fmt(s30.split_runs || 0),"贡献者隔离划分")}</div></article></div><div class="metric-grid">${metric("30% F1",pct(h.risk_detection_f1_at_30pct),"主运行")}${metric("分组 F1 中位数",pct(s30.f1_median),`${pct(s30.f1_min)}–${pct(s30.f1_max)}`)}${metric("30% 排名误差降幅",pct(rankReduction),"可信加权相对原始排序")}${metric("证据等级","E2","受控合成验证")}</div><article class="panel"><h2>适用范围</h2><ul class="limitations">${d.limitations.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></article>`;
}

function bindInteractions() {
  document.querySelector("#passport-search")?.addEventListener("input", e => { state.query = e.target.value; render(); });
  document.querySelector("#tier-filter")?.addEventListener("change", e => { state.tier = e.target.value; render(); });
  document.querySelectorAll("[data-passport]").forEach(row => {
    const open = () => { state.passportIndex = Number(row.dataset.passport); render(); };
    row.addEventListener("click", open);
    row.addEventListener("keydown", e => { if (["Enter"," "].includes(e.key)) open(); });
  });
}

function render() {
  if (!state.data) return;
  state.route = (location.hash || "#overview").slice(1);
  if (!ROUTES[state.route]) state.route = "overview";
  document.querySelector("#page-title").textContent = ROUTES[state.route];
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("active", a.dataset.route === state.route));
  const views = { overview, passports, risk, queue, audit, benchmark };
  content.innerHTML = views[state.route](state.data);
  bindInteractions();
}

window.addEventListener("hashchange", render);
document.querySelector("#export-button").addEventListener("click", () => {
  const payload = { exported_at: new Date().toISOString(), route: state.route, evidence_class: state.data.evidence_class, headline: state.data.headline, limitations: state.data.limitations };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type:"application/json"});
  const link = Object.assign(document.createElement("a"), {href:URL.createObjectURL(blob), download:`trustdata-${state.route}.json`});
  link.click(); URL.revokeObjectURL(link.href);
});

fetch(DATA_URL).then(r => { if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }).then(data => {
  state.data = data; loading.hidden = true; render();
}).catch(error => {
  loading.hidden = true; errorBox.hidden = false;
  errorBox.textContent = `实验数据读取失败：${error.message}。请通过项目根目录启动的本地服务访问本页面。`;
});
