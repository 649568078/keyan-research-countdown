const state = { items: [], cursor: new Date(), view: "calendar", drawerDate: null, collapsedNodeGroups: new Set(), collapsedDrawerItems: new Set() };
const $ = (selector) => document.querySelector(selector);
const pad = (n) => String(n).padStart(2, "0");
const localISO = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const parseDate = (value) => { const [y, m, d] = value.split("-").map(Number); return new Date(y, m - 1, d); };
const addDaysISO = (value, days) => { const date = parseDate(value); date.setDate(date.getDate() + days); return localISO(date); };
const statusColor = { urgent: "#ef476f", soon: "#f59e0b", normal: "#00a896", overdue: "#8a94a6", completed: "#8a94a6" };

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || "操作失败，请稍后再试"); }
  return response.status === 204 ? null : response.json();
}

async function loadItems() {
  state.items = await api("/api/countdowns");
  renderAll();
}

function renderAll() { renderStats(); renderCalendar(); renderDashboard(); renderNodeParentOptions(); renderNodes(); }

function renderStats() {
  const active = state.items.filter((i) => !i.completed);
  const values = [
    ["进行中", active.length, "◎"],
    ["14 天内截止", active.filter((i) => i.days_left >= 0 && i.days_left <= 14).length, "◷"],
    ["已逾期", active.filter((i) => i.days_left < 0).length, "!"],
    ["已完成", state.items.filter((i) => i.completed).length, "✓"],
  ];
  $("#stats").innerHTML = values.map(([label, value, icon]) => `<div class="stat-card"><div><small>${label}</small><strong>${value}</strong></div><span class="stat-icon">${icon}</span></div>`).join("");
}

function renderCalendar() {
  const year = state.cursor.getFullYear(), month = state.cursor.getMonth();
  $("#monthTitle").textContent = `${year} 年 ${month + 1} 月`;
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - ((first.getDay() + 6) % 7));
  const today = localISO(new Date());
  let html = "";
  for (let n = 0; n < 42; n++) {
    const day = new Date(start); day.setDate(start.getDate() + n);
    const iso = localISO(day);
    const content = calendarContentForDate(iso);
    const deadlineCountHtml = content.deadlineProjectCount ? `<span class="deadline-count">● ${content.deadlineProjectCount} 个项目截止</span>` : "";
    const deadlineHtml = content.deadlines.slice(0, 2).map((entry) => `<button class="calendar-event deadline" style="--event-color:${entry.item.color}" data-day-details="${iso}" title="查看当天事项：${escapeHtml(entry.label)}">${escapeHtml(entry.label)}</button>`).join("");
    const hiddenDeadlineHtml = content.deadlines.length > 2 ? `<button class="more-count deadline-summary" data-day-details="${iso}">另有 ${content.deadlines.length - 2} 项截止</button>` : "";
    const ongoingHtml = content.ongoingCount ? `<button class="more-count ongoing-summary" data-day-details="${iso}">进行中 ${content.ongoingCount} 项 · 查看</button>` : "";
    html += `<div class="day ${day.getMonth() !== month ? "outside" : ""} ${iso === today ? "today" : ""}" data-date="${iso}"><span class="day-number">${day.getDate()}</span><div class="day-events">${deadlineCountHtml}${deadlineHtml}${hiddenDeadlineHtml}${ongoingHtml}</div></div>`;
  }
  $("#calendarGrid").innerHTML = html;
}

function calendarContentForDate(iso) {
  const deadlines = [];
  let ongoingCount = 0;
  state.items.filter((item) => !item.completed && iso >= item.start_date && iso <= item.deadline).forEach((item) => {
    const deadlineNodes = item.milestones.filter((node) => !node.completed && iso === node.deadline);
    if (deadlineNodes.length) {
      deadlineNodes.forEach((node) => deadlines.push({ item, node, label: `${item.title} · ${node.title}` }));
    } else if (iso === item.deadline) {
      deadlines.push({ item, node: null, label: `${item.title} · 最终截止` });
    } else {
      ongoingCount += 1;
    }
  });
  const deadlineProjectCount = new Set(deadlines.map((entry) => entry.item.id)).size;
  return { deadlines, ongoingCount, deadlineProjectCount };
}

function renderDashboard() {
  const filter = $("#statusFilter").value;
  const sort = $("#timelineSort").value;
  let points = state.items.flatMap((item) => [
    ...item.milestones.map((node) => ({
      id: node.id, kind: "milestone", title: node.title, parent: item,
      deadline: node.deadline, days_left: node.days_left,
      status: node.status, status_label: node.status_label, completed: node.completed,
    })),
    {
      id: item.id, kind: "final", title: item.title, parent: item,
      deadline: item.deadline, days_left: item.days_left,
      status: item.status, status_label: item.status_label, completed: item.completed,
    },
  ]);
  points = points.filter((point) => filter === "all" || (filter === "active" ? point.status !== "completed" : point.status === filter));
  points.sort((a, b) => {
    if (sort === "reverse") return b.deadline.localeCompare(a.deadline);
    const aPast = a.days_left < 0, bPast = b.days_left < 0;
    if (aPast !== bPast) return aPast ? 1 : -1;
    return aPast ? b.days_left - a.days_left : a.days_left - b.days_left;
  });

  const pending = state.items.flatMap((item) => [
    ...item.milestones.map((node) => ({ ...node, title: node.title, parent: item, kind: "milestone" })),
    { ...item, title: item.title, parent: item, kind: "final" },
  ]).filter((point) => point.status !== "completed" && point.days_left >= 0).sort((a, b) => a.days_left - b.days_left)[0];
  $("#nextDeadlineHero").innerHTML = pending ? `<div><p>下一个关键截止点</p><h3>${escapeHtml(pending.parent.title)} · ${pending.kind === "final" ? "最终截止" : escapeHtml(pending.title)}</h3><span>${formatDate(pending.deadline)} · ${escapeHtml(pending.status_label)}</span></div><strong>${pending.days_left === 0 ? "今天" : pending.days_left}<small>${pending.days_left === 0 ? "截止" : "天后截止"}</small></strong>` : `<div><p>下一个关键截止点</p><h3>暂无待处理的截止节点</h3><span>新建事项或恢复已完成节点后将在这里显示</span></div><strong>—</strong>`;

  if (!points.length) {
    $("#countdownList").innerHTML = `<div class="empty-state"><b>当前筛选下没有截止点</b>可切换状态筛选，或在事项管理中添加子任务。</div>`;
    return;
  }
  $("#countdownList").innerHTML = `<div class="timeline-cap start">时间线起点</div>${points.map((point) => {
    const remaining = point.status === "completed" ? "已完成" : point.days_left < 0 ? `逾期 ${Math.abs(point.days_left)} 天` : point.days_left === 0 ? "今天截止" : `${point.days_left} 天后`;
    const action = point.kind === "milestone" ? `data-node-edit="${point.id}"` : `data-item-details="${point.parent.id}" data-date="${point.deadline}"`;
    return `<article class="timeline-point ${point.kind}" style="--point-color:${statusColor[point.status]};--item-color:${point.parent.color}"><i class="timeline-dot"></i><time>${formatDate(point.deadline)}</time><div class="timeline-card ${point.completed ? "completed" : ""}"><label class="timeline-check" title="${point.completed ? "标记为未完成" : "标记为已完成"}"><input type="checkbox" data-timeline-toggle="${point.id}" data-timeline-kind="${point.kind}" ${point.completed ? "checked" : ""}><span></span></label><button class="timeline-card-main" ${action}><div><span class="timeline-kind">${point.kind === "final" ? "◆ 最终截止" : "◇ 阶段截止"}</span><h3>${escapeHtml(point.kind === "final" ? point.parent.title : point.title)}</h3><p>${escapeHtml(point.parent.title)} · ${escapeHtml(point.parent.category)}</p></div><div class="timeline-remaining"><strong>${remaining}</strong><small>${escapeHtml(point.status_label)}</small></div></button></div></article>`;
  }).join("")}<div class="timeline-cap end">时间线终点 · 共 ${points.length} 个截止点</div>`;
}

function allNodes() {
  return state.items.flatMap((item) => item.milestones.map((node) => ({ ...node, parent: item })));
}

function renderNodeParentOptions() {
  const filter = $("#nodeParentFilter");
  const oldFilter = filter.value;
  filter.innerHTML = `<option value="all">全部事项</option>${state.items.map((item) => `<option value="${item.id}">${escapeHtml(item.title)}</option>`).join("")}`;
  filter.value = [...filter.options].some((option) => option.value === oldFilter) ? oldFilter : "all";
  const parent = $("#nodeParent");
  const oldParent = parent.value;
  parent.innerHTML = state.items.map((item) => `<option value="${item.id}">${escapeHtml(item.title)}</option>`).join("");
  if ([...parent.options].some((option) => option.value === oldParent)) parent.value = oldParent;
}

function renderNodes() {
  const filter = $("#nodeParentFilter").value;
  const items = state.items.filter((item) => filter === "all" || item.id === Number(filter));
  if (!items.length) {
    $("#nodeList").innerHTML = `<div class="empty-state"><b>还没有倒计时事项</b>请先点击左侧“新建倒计时”，创建一个主事项。</div>`;
    return;
  }
  $("#nodeList").innerHTML = items.map((item) => {
    const collapsed = state.collapsedNodeGroups.has(item.id);
    const nodes = [...item.milestones].sort((a, b) => a.deadline.localeCompare(b.deadline));
    const children = nodes.length ? nodes.map((node) => {
      const remaining = node.completed ? "已完成" : node.days_left < 0 ? `逾期 ${Math.abs(node.days_left)} 天` : node.days_left === 0 ? "今天截止" : `剩余 ${node.days_left} 天`;
      return `<article class="node-card ${node.completed ? "completed" : ""}" style="--status-color:${statusColor[node.status]}"><i class="status-bar"></i><div><h3>${escapeHtml(node.title)}</h3><span class="node-parent">阶段子任务</span></div><div class="date-range">${formatDate(node.start_date)} → ${formatDate(node.deadline)}</div><div class="node-status"><b>${remaining}</b><small>${escapeHtml(node.status_label)}</small></div><div class="card-actions"><button data-node-toggle="${node.id}" title="${node.completed ? "恢复节点" : "完成节点"}">${node.completed ? "↶" : "✓"}</button><button data-node-edit="${node.id}" title="编辑节点">✎</button><button data-node-delete="${node.id}" title="删除节点">⌫</button></div></article>`;
    }).join("") : `<div class="node-child-empty">这个倒计时还没有子任务 <button data-node-add="${item.id}">＋ 添加第一个子任务</button></div>`;
    return `<section class="node-group ${collapsed ? "collapsed" : ""}"><button class="node-group-header" data-node-group-toggle="${item.id}"><span class="group-chevron">⌄</span><i class="status-bar" style="--status-color:${statusColor[item.status]}"></i><div class="node-group-title"><h3>${escapeHtml(item.title)}</h3><span>${escapeHtml(item.category)} · ${escapeHtml(item.status_label)}</span></div><div class="date-range">${formatDate(item.start_date)} → ${formatDate(item.deadline)}</div><div class="group-count"><strong>${nodes.length}</strong><small>个子任务</small></div></button><div class="node-group-body"><div class="node-group-actions"><span>阶段子任务按截止时间排列</span><div><button data-edit="${item.id}">编辑倒计时</button><button data-node-add="${item.id}">＋ 添加子任务</button></div></div><div class="node-children">${children}</div></div></section>`;
  }).join("");
}

function openDialog(item = null, chosenDate = null) {
  $("#eventForm").reset(); $("#eventId").value = item?.id || "";
  $("#dialogTitle").textContent = item ? "编辑倒计时" : "新建倒计时";
  const date = chosenDate || localISO(new Date());
  $("#title").value = item?.title || ""; $("#startDate").value = item?.start_date || date; $("#deadline").value = item?.deadline || date;
  $("#category").value = item?.category || "论文"; $("#description").value = item?.description || "";
  const color = item?.color || "#536dfe"; document.querySelector(`input[name=color][value="${color}"]`).checked = true;
  renderMilestoneRows(item?.milestones || []);
  $("#deleteEventButton").hidden = !item;
  $("#formError").textContent = ""; $("#eventDialog").showModal(); $("#title").focus();
}

function renderMilestoneRows(nodes) {
  $("#milestoneRows").innerHTML = "";
  nodes.forEach((node) => addMilestoneRow(node));
}

function addMilestoneRow(node = {}) {
  const existingRows = [...document.querySelectorAll(".milestone-row")];
  const previousDeadline = existingRows.at(-1)?.querySelector(".node-deadline")?.value;
  const taskStart = $("#startDate").value || localISO(new Date());
  const taskDeadline = $("#deadline").value || taskStart;
  const proposedStart = previousDeadline ? addDaysISO(previousDeadline, 1) : taskStart;
  const fallbackStart = proposedStart > taskDeadline ? taskDeadline : proposedStart;
  const fallbackEnd = fallbackStart;
  const row = document.createElement("div");
  row.className = "milestone-row";
  row.innerHTML = `<label>节点名称<input class="node-title" maxlength="80" required placeholder="如：单位审核" value="${escapeHtml(node.title || "")}"></label><label>开始日期<input class="node-start" type="date" required value="${node.start_date || fallbackStart}"></label><label>截止日期<input class="node-deadline" type="date" required value="${node.deadline || fallbackEnd}"></label><button type="button" class="remove-milestone" title="删除节点">×</button>`;
  $("#milestoneRows").appendChild(row);
  row.querySelector(".remove-milestone").addEventListener("click", () => row.remove());
}

async function saveEvent(event) {
  event.preventDefault();
  const id = $("#eventId").value;
  const milestones = [...document.querySelectorAll(".milestone-row")].map((row) => ({ title: row.querySelector(".node-title").value, start_date: row.querySelector(".node-start").value, deadline: row.querySelector(".node-deadline").value }));
  const payload = { title: $("#title").value, start_date: $("#startDate").value, deadline: $("#deadline").value, category: $("#category").value, description: $("#description").value, color: $("input[name=color]:checked").value, milestones };
  try {
    await api(id ? `/api/countdowns/${id}` : "/api/countdowns", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    $("#eventDialog").close(); toast(id ? "事项已更新" : "倒计时已创建"); await loadItems();
  } catch (error) { $("#formError").textContent = error.message; }
}

function openDayDrawer(iso, itemId = null) {
  state.drawerDate = iso;
  const date = parseDate(iso);
  $("#drawerDate").textContent = `${date.getFullYear()} 年 ${date.getMonth() + 1} 月 ${date.getDate()} 日`;
  const relevant = state.items.filter((item) => !item.completed && iso >= item.start_date && iso <= item.deadline && (!itemId || item.id === Number(itemId)));
  $("#drawerItems").innerHTML = relevant.length ? relevant.map((item) => {
    const collapsed = state.collapsedDrawerItems.has(item.id);
    const nodes = [...item.milestones].sort((a, b) => a.deadline.localeCompare(b.deadline));
    const nodeHtml = nodes.length ? nodes.map((node, index) => {
      const active = iso >= node.start_date && iso <= node.deadline;
      const marker = iso === node.deadline ? "当天截止" : active ? "当前阶段" : node.completed ? "已完成" : "未到此阶段";
      return `<article class="drawer-node ${active ? "active" : ""} ${iso === node.deadline ? "deadline" : ""} ${node.completed ? "completed" : ""}"><span class="drawer-node-order">${index + 1}</span><button class="drawer-node-main" data-node-edit="${node.id}"><b>${escapeHtml(node.title)}</b><span class="drawer-node-range">${formatDate(node.start_date)} → ${formatDate(node.deadline)}</span><span class="drawer-node-status">${escapeHtml(node.status_label)} · ${marker}</span></button><div class="drawer-actions drawer-node-actions"><button data-node-edit="${node.id}">编辑</button><button data-node-toggle="${node.id}">${node.completed ? "恢复" : "完成"}</button><button data-node-delete="${node.id}">删除</button></div></article>`;
    }).join("") : `<div class="drawer-node-empty"><b>暂无子任务</b><span>可在“事项管理”中添加阶段子任务</span></div>`;
    return `<article class="drawer-card ${collapsed ? "collapsed" : ""}" style="--item-color:${item.color}"><div class="drawer-card-head"><button class="drawer-card-toggle" data-drawer-toggle="${item.id}" aria-expanded="${!collapsed}"><span class="group-chevron">⌄</span><div><h3>${escapeHtml(item.title)}</h3><span class="meta">${escapeHtml(item.category)} · ${escapeHtml(item.status_label)} · ${nodes.length} 个子任务</span></div></button><div class="drawer-actions drawer-project-actions"><button data-edit="${item.id}">编辑主事项</button><button data-toggle="${item.id}">${item.completed ? "恢复" : "完成"}</button><button data-delete="${item.id}">删除</button></div></div><div class="drawer-card-body">${nodeHtml}</div></article>`;
  }).join("") : `<div class="drawer-empty">当天没有进行中的事项</div>`;
  $("#dayDrawer").classList.add("open"); $("#drawerBackdrop").classList.add("open"); $("#dayDrawer").setAttribute("aria-hidden", "false");
}

function closeDayDrawer() {
  $("#dayDrawer").classList.remove("open"); $("#drawerBackdrop").classList.remove("open"); $("#dayDrawer").setAttribute("aria-hidden", "true");
}

function updateNodeRangeHint(setDefaults = false) {
  const parent = state.items.find((item) => item.id === Number($("#nodeParent").value));
  if (!parent) { $("#nodeRangeHint").textContent = "请先创建一个主事项。"; return; }
  $("#nodeRangeHint").textContent = `可用时间范围：${formatDate(parent.start_date)} 至 ${formatDate(parent.deadline)}`;
  if (setDefaults) {
    const today = localISO(new Date());
    const existingNodes = [...parent.milestones].sort((a, b) => a.deadline.localeCompare(b.deadline));
    const nextAfterLast = existingNodes.length ? addDaysISO(existingNodes.at(-1).deadline, 1) : parent.start_date;
    const preferred = existingNodes.length ? nextAfterLast : today;
    const defaultDate = preferred < parent.start_date ? parent.start_date : preferred > parent.deadline ? parent.deadline : preferred;
    $("#nodeStart").value = defaultDate; $("#nodeDeadline").value = defaultDate;
  }
}

function openNodeDialog(node = null, parentId = null) {
  if (!state.items.length) { toast("请先新建一个主事项"); return; }
  $("#nodeForm").reset(); $("#nodeId").value = node?.id || "";
  $("#nodeDialogTitle").textContent = node ? "编辑时间节点" : "新建时间节点";
  $("#deleteNodeButton").hidden = !node;
  $("#editParentFromNode").hidden = !node;
  $("#nodeParent").disabled = Boolean(node);
  if (node) {
    $("#nodeParent").value = node.parent.id; $("#nodeTitle").value = node.title;
    $("#nodeStart").value = node.start_date; $("#nodeDeadline").value = node.deadline;
    updateNodeRangeHint(false);
  } else {
    if (parentId && state.items.some((item) => item.id === Number(parentId))) $("#nodeParent").value = String(parentId);
    updateNodeRangeHint(true);
  }
  $("#nodeFormError").textContent = ""; $("#nodeDialog").showModal(); $("#nodeTitle").focus();
}

async function saveNode(event) {
  event.preventDefault();
  const id = $("#nodeId").value;
  const payload = { countdown_id: Number($("#nodeParent").value), title: $("#nodeTitle").value, start_date: $("#nodeStart").value, deadline: $("#nodeDeadline").value };
  try {
    await api(id ? `/api/milestones/${id}` : "/api/milestones", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
    $("#nodeDialog").close(); toast(id ? "节点已更新" : "节点已创建"); await loadItems();
  } catch (error) { $("#nodeFormError").textContent = error.message; }
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
  document.querySelectorAll(".view").forEach((el) => el.classList.remove("active"));
  $(`#${view}View`).classList.add("active");
  $("#pageTitle").textContent = { calendar: "日历视图", dashboard: "倒计时看板", nodes: "事项管理" }[view];
}

function escapeHtml(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }
function formatDate(value) { const d = parseDate(value); return `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())}`; }
function toast(message) { const el = $("#toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 1800); }

async function reloadAndKeepDrawer() {
  const keepDrawer = $("#dayDrawer").classList.contains("open") && state.drawerDate;
  const date = state.drawerDate;
  const scrollTop = $("#drawerItems").scrollTop;
  await loadItems();
  if (keepDrawer) {
    openDayDrawer(date);
    $("#drawerItems").scrollTop = scrollTop;
  }
}

document.addEventListener("change", async (event) => {
  const timelineToggle = event.target.closest("[data-timeline-toggle]");
  if (!timelineToggle) return;
  const id = timelineToggle.dataset.timelineToggle;
  const url = timelineToggle.dataset.timelineKind === "milestone" ? `/api/milestones/${id}/toggle` : `/api/countdowns/${id}/toggle`;
  timelineToggle.disabled = true;
  try {
    await api(url, { method: "PATCH" });
    toast("完成状态已更新");
    await loadItems();
  } catch (error) {
    timelineToggle.checked = !timelineToggle.checked;
    timelineToggle.disabled = false;
    toast(error.message);
  }
});

document.addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit]"); const toggle = event.target.closest("[data-toggle]"); const remove = event.target.closest("[data-delete]"); const dayDetails = event.target.closest("[data-day-details]"); const itemDetails = event.target.closest("[data-item-details]");
  const nodeEdit = event.target.closest("[data-node-edit]"); const nodeToggle = event.target.closest("[data-node-toggle]"); const nodeDelete = event.target.closest("[data-node-delete]");
  const nodeAdd = event.target.closest("[data-node-add]"); const groupToggle = event.target.closest("[data-node-group-toggle]"); const drawerToggle = event.target.closest("[data-drawer-toggle]");
  if (edit) { closeDayDrawer(); openDialog(state.items.find((i) => i.id === Number(edit.dataset.edit))); }
  if (toggle) { await api(`/api/countdowns/${toggle.dataset.toggle}/toggle`, { method: "PATCH" }); await reloadAndKeepDrawer(); }
  if (remove && confirm("确定删除这个倒计时吗？")) { await api(`/api/countdowns/${remove.dataset.delete}`, { method: "DELETE" }); toast("事项已删除"); await reloadAndKeepDrawer(); }
  if (itemDetails) openDayDrawer(itemDetails.dataset.date, itemDetails.dataset.itemDetails);
  else if (dayDetails) openDayDrawer(dayDetails.dataset.dayDetails);
  else if (event.target.closest(".day") && !edit && !nodeEdit) openDayDrawer(event.target.closest(".day").dataset.date);
  if (nodeEdit) openNodeDialog(allNodes().find((node) => node.id === Number(nodeEdit.dataset.nodeEdit)));
  if (nodeToggle) { await api(`/api/milestones/${nodeToggle.dataset.nodeToggle}/toggle`, { method: "PATCH" }); toast("节点状态已更新"); await reloadAndKeepDrawer(); }
  if (nodeDelete && confirm("确定删除这个时间节点吗？所属主事项不会被删除。")) { await api(`/api/milestones/${nodeDelete.dataset.nodeDelete}`, { method: "DELETE" }); toast("节点已删除"); await reloadAndKeepDrawer(); }
  if (nodeAdd) openNodeDialog(null, nodeAdd.dataset.nodeAdd);
  if (drawerToggle) {
    const id = Number(drawerToggle.dataset.drawerToggle);
    state.collapsedDrawerItems.has(id) ? state.collapsedDrawerItems.delete(id) : state.collapsedDrawerItems.add(id);
    const card = drawerToggle.closest(".drawer-card");
    const collapsed = state.collapsedDrawerItems.has(id);
    card?.classList.toggle("collapsed", collapsed);
    drawerToggle.setAttribute("aria-expanded", String(!collapsed));
    if (!collapsed && card) {
      requestAnimationFrame(() => card.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }
  if (groupToggle) {
    const id = Number(groupToggle.dataset.nodeGroupToggle);
    state.collapsedNodeGroups.has(id) ? state.collapsedNodeGroups.delete(id) : state.collapsedNodeGroups.add(id);
    renderNodes();
  }
});
$("#newButton").addEventListener("click", () => openDialog());
$("#eventForm").addEventListener("submit", saveEvent);
$("#closeDialog").addEventListener("click", () => $("#eventDialog").close());
$("#cancelDialog").addEventListener("click", () => $("#eventDialog").close());
$("#addMilestone").addEventListener("click", () => addMilestoneRow());
$("#closeDrawer").addEventListener("click", closeDayDrawer);
$("#drawerBackdrop").addEventListener("click", closeDayDrawer);
$("#dayDrawer").addEventListener("wheel", (event) => event.stopPropagation(), { passive: true });
$("#drawerAdd").addEventListener("click", () => { const date = state.drawerDate; closeDayDrawer(); openDialog(null, date); });
$("#newTaskButton").addEventListener("click", () => openDialog());
$("#nodeForm").addEventListener("submit", saveNode);
$("#closeNodeDialog").addEventListener("click", () => $("#nodeDialog").close());
$("#cancelNodeDialog").addEventListener("click", () => $("#nodeDialog").close());
$("#nodeParent").addEventListener("change", () => updateNodeRangeHint(true));
$("#nodeParentFilter").addEventListener("change", renderNodes);
$("#deleteEventButton").addEventListener("click", async () => {
  const id = $("#eventId").value;
  if (id && confirm("确定删除这个事项吗？它下面的所有时间节点也会一并删除。")) {
    await api(`/api/countdowns/${id}`, { method: "DELETE" });
    $("#eventDialog").close(); toast("事项已删除"); await loadItems();
  }
});
$("#deleteNodeButton").addEventListener("click", async () => {
  const id = $("#nodeId").value;
  if (id && confirm("确定删除这个时间节点吗？所属主事项不会被删除。")) {
    await api(`/api/milestones/${id}`, { method: "DELETE" });
    $("#nodeDialog").close(); toast("节点已删除"); await loadItems();
  }
});
$("#editParentFromNode").addEventListener("click", () => {
  const parent = state.items.find((item) => item.id === Number($("#nodeParent").value));
  if (!parent) { toast("所属主事项不存在"); return; }
  $("#nodeDialog").close();
  openDialog(parent);
});
$("#prevMonth").addEventListener("click", () => { state.cursor.setMonth(state.cursor.getMonth() - 1); renderCalendar(); });
$("#nextMonth").addEventListener("click", () => { state.cursor.setMonth(state.cursor.getMonth() + 1); renderCalendar(); });
$("#todayButton").addEventListener("click", () => { state.cursor = new Date(); renderCalendar(); });
$("#statusFilter").addEventListener("change", renderDashboard);
$("#timelineSort").addEventListener("change", renderDashboard);
document.querySelectorAll(".nav-item").forEach((el) => el.addEventListener("click", () => switchView(el.dataset.view)));
$("#todayLabel").textContent = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }).format(new Date());
loadItems().catch((error) => toast(error.message));
