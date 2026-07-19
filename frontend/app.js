const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const state = {
  servers: [],
  selected: null,
  inbounds: [],
  version: null,
  connections: [],
  view: "servers",
};
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (tg?.initData) headers.set("X-Telegram-Init-Data", tg.initData);
  const response = await fetch(`/api${path}`, { ...options, headers });
  const text = await response.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return data;
}

function showToast(message, timeout = 2800) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), timeout);
}

async function waitForOperation(job, progressMessage) {
  const serverId = job?.server_id || state.selected?.id;
  if (!job?.id || !serverId) throw new Error("Backend не вернул идентификатор операции");
  const deadline = Date.now() + 2 * 60 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise(resolve => window.setTimeout(resolve, 2000));
    const current = await api(`/servers/${serverId}/jobs/${job.id}`);
    if (current.status === "succeeded") return current.result || {};
    if (current.status === "failed") throw new Error(current.error || "Операция завершилась с ошибкой");
    if (progressMessage) showToast(progressMessage, 2400);
  }
  throw new Error("Истекло время ожидания операции. Проверьте состояние сервера.");
}

function bytes(value) {
  const n = Number(value || 0);
  const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  let i = 0, result = n;
  while (result >= 1024 && i < units.length - 1) { result /= 1024; i += 1; }
  return `${result.toFixed(i > 1 ? 1 : 0)} ${units[i]}`;
}

function duration(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return days ? `${days} д ${hours} ч` : `${hours} ч`;
}

function dateValue(ms) {
  if (!ms) return "Без срока";
  return new Date(ms).toLocaleDateString("ru-RU");
}

function releaseDate(value) {
  if (!value) return "Дата публикации недоступна";
  return `Опубликовано ${new Date(value).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}`;
}

function cleanReleaseNotes(value) {
  const source = String(value || "").replace(/\r\n?/g, "\n");
  if (!source.trim()) return "Описание релиза пока недоступно.";

  const withBreaks = source
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<li[^>]*>/gi, "• ")
    .replace(/<\/(?:p|div|h[1-6]|li|ul|ol|blockquote|details|summary)>/gi, "\n")
    .replace(/<[^>]+>/g, "");

  const decoder = document.createElement("textarea");
  decoder.innerHTML = withBreaks;

  return decoder.value
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\((?:https?:\/\/|\/)[^)]*\)/g, "$1")
    .replace(/^\s*#{1,6}\s*/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/^\s*\d+\.\s+/gm, "• ")
    .replace(/`{1,3}([^`]+)`{1,3}/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\s*\(https?:\/\/[^)]+\)/g, "")
    .replace(/^\s*https?:\/\/\S+\s*$/gm, "")
    .replace(/[ \t]+$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

function displayVersion(value) {
  return String(value || "—").replace(/^v/i, "");
}

function osShort(server) {
  const id = String(server.os?.id || "").toLowerCase();
  const version = String(server.os?.version || "").trim();
  if (!id && !version) return "ОС —";
  const prefix = id === "ubuntu" ? "U" : (id.charAt(0).toUpperCase() || "ОС");
  return `${prefix}${version ? ` ${version}` : ""}`;
}

function countValue(value) {
  return value === null || value === undefined ? "—" : String(value);
}

function serverIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="4" width="16" height="6" rx="2" stroke="currentColor" stroke-width="1.6"/><rect x="4" y="14" width="16" height="6" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M8 7h.01M8 17h.01M12 7h5M12 17h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
}

function metricIcon(index) {
  const icons = [
    `<path d="M8 12.5 10.5 15 16 9.5M12 3l7 3v5c0 4.4-2.8 8.1-7 10-4.2-1.9-7-5.6-7-10V6l7-3Z"/>`,
    `<path d="M12 7v5l3 2M21 12a9 9 0 1 1-9-9 9 9 0 0 1 9 9Z"/>`,
    `<path d="M4 17l4-5 4 3 4-8 4 4"/>`,
    `<path d="M5 15V9a7 7 0 0 1 14 0v6M8 21h8a3 3 0 0 0 3-3v-3H5v3a3 3 0 0 0 3 3Z"/>`,
    `<path d="M4 6h16v12H4V6Zm4 4h8M8 14h5"/>`,
    `<path d="m12 3 2.2 4.6 5.1.7-3.7 3.6.9 5.1-4.5-2.4L7.5 17l.9-5.1-3.7-3.6 5.1-.7L12 3Z"/>`,
  ];
  return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">${icons[index] || icons[0]}</g></svg>`;
}

function inboundIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 7h14M5 12h14M5 17h14M8 7h.01M8 12h.01M8 17h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
}

function showView(view) {
  state.view = view;
  $("serverView").classList.toggle("hidden", view !== "servers");
  $("dashboard").classList.toggle("hidden", view !== "dashboard");
  $("usersView").classList.toggle("hidden", view !== "users");
  $("versionView").classList.toggle("hidden", view !== "version");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function serverSkeletons() {
  $("servers").innerHTML = Array.from({ length: 2 }, () => `
    <div class="server-card server-card--loading loading-shimmer">
      <div class="server-card__headline"><span class="server-card__icon">${serverIcon()}</span><div><h3>Получение данных…</h3><p>Проверка сервера</p></div></div>
    </div>`).join("");
}

async function loadServers() {
  serverSkeletons();
  state.servers = await api("/servers");
  $("servers").innerHTML = state.servers.map(server => {
    const active = Boolean(server.active);
    return `
      <button class="server-card" data-server="${escapeHtml(server.id)}">
        <div class="server-card__headline">
          <span class="server-card__icon">${serverIcon()}</span>
          <div class="server-card__identity">
            <h3>${escapeHtml(server.name)}</h3>
            <p>${escapeHtml(server.location || "")}</p>
          </div>
          <span class="server-card__arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path d="m9 18 6-6-6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <div class="server-card__facts">
          <span class="server-fact server-fact--os">${escapeHtml(osShort(server))}</span>
          <span class="server-fact"><b>${countValue(server.total_users)}</b> всего</span>
          <span class="server-fact"><b>${countValue(server.online_users)}</b> активны</span>
        </div>
        <div class="server-card__footer">
          <span class="badge">${escapeHtml(server.panel_type)}</span>
          <span class="server-card__status ${active ? "is-active" : "is-inactive"}"><i></i>${active ? "Активен" : "Неактивен"}</span>
        </div>
      </button>`;
  }).join("");
  document.querySelectorAll("[data-server]").forEach(button => button.addEventListener("click", () => openServer(button.dataset.server)));
  if (!tg?.initData) {
    $("notice").textContent = "Страница открыта вне Telegram. Доступ сработает только при включённом DEV_BYPASS_AUTH.";
    $("notice").classList.remove("hidden");
  }
}

async function openServer(serverId) {
  state.selected = state.servers.find(item => item.id === serverId);
  if (!state.selected) return;
  state.version = null;
  $("serverTitle").textContent = state.selected.name;
  $("serverLocation").textContent = state.selected.location || "";
  $("usersServerTitle").textContent = `${state.selected.name}: пользователи`;
  $("usersServerLocation").textContent = state.selected.location || "";
  $("versionServerTitle").textContent = `${state.selected.name}: 3x-ui`;
  $("versionServerLocation").textContent = state.selected.location || "";
  $("updateSystemBtn").classList.toggle("hidden", !state.selected.system_update_enabled);
  setDashboardStatus(state.selected.active);
  showView("dashboard");
  await refreshDashboard();
}

function setDashboardStatus(active) {
  const pill = $("dashboardStatus");
  pill.classList.toggle("is-inactive", !active);
  pill.innerHTML = `<i></i>${active ? "Активен" : "Неактивен"}`;
}

async function refreshDashboard() {
  if (!state.selected) return loadServers();
  $("statusCards").innerHTML = Array.from({ length: 6 }, (_, index) => `<div class="metric metric--compact loading-shimmer"><div class="metric-head"><span>Загрузка</span><div class="metric-icon">${metricIcon(index)}</div></div><strong>Получение данных…</strong></div>`).join("");

  const [statusResult, versionResult] = await Promise.allSettled([
    api(`/servers/${state.selected.id}/status`),
    fetchXuiVersion(false),
  ]);

  if (statusResult.status === "fulfilled") {
    renderStatus(statusResult.value);
  } else {
    showToast(statusResult.reason.message);
    $("statusCards").innerHTML = `<div class="metric"><span>Ошибка</span><strong>${escapeHtml(statusResult.reason.message)}</strong></div>`;
  }
  if (versionResult.status === "rejected") showToast(versionResult.reason.message);
}

function renderStatus(status) {
  const ssh = status.ssh?.data || {};
  const memoryPercent = ssh.memory?.total ? Math.round(ssh.memory.used / ssh.memory.total * 100) : 0;
  const serviceActive = ["active", "running"].includes(String(ssh.xui_service || "").toLowerCase());
  setDashboardStatus(serviceActive && status.panel?.ok !== false);
  const version = state.version;
  const versionClass = version?.update_available === true ? "version-warning" : version?.update_available === false ? "version-ok" : "version-muted";
  const cards = [
    { label: "Сервис x-ui", value: ssh.xui_service || "н/д", className: serviceActive ? "metric--ok" : "metric--warning" },
    { label: "Uptime", value: duration(ssh.uptime_seconds || 0) },
    { label: "Load 1m", value: ssh.load?.one ?? "—" },
    { label: "Память", value: `${memoryPercent}% · ${bytes(ssh.memory?.used)}` },
    { label: "Диск", value: `${ssh.disk?.percent ?? 0}% · ${bytes(ssh.disk?.used)}` },
  ];

  $("statusCards").innerHTML = cards.map((item, index) => `
    <div class="metric metric--compact ${item.className || ""}">
      <div class="metric-head"><span>${escapeHtml(item.label)}</span><div class="metric-icon">${metricIcon(index)}</div></div>
      <strong>${escapeHtml(item.value)}</strong>
    </div>`).join("") + `
    <button id="versionMetric" class="metric metric--compact metric--link ${versionClass}" type="button">
      <div class="metric-head"><span>3x-ui</span><div class="metric-icon">${metricIcon(5)}</div></div>
      <strong>${escapeHtml(displayVersion(version?.installed || ssh.xui_version))}</strong>
      <small>${version?.update_available === true ? "Доступно обновление" : version?.update_available === false ? "Актуальная версия" : "Открыть сведения"}</small>
    </button>`;
  $("versionMetric").addEventListener("click", openVersionPage);
}

async function fetchXuiVersion(showErrorToast = true) {
  if (!state.selected) return null;
  try {
    state.version = await api(`/servers/${state.selected.id}/xui/version`);
    if (state.view === "version") renderVersionPage();
    return state.version;
  } catch (error) {
    if (showErrorToast) showToast(error.message);
    throw error;
  }
}

async function openVersionPage() {
  if (!state.selected) return;
  showView("version");
  renderVersionPage(true);
  if (!state.version) {
    try { await fetchXuiVersion(true); } catch { renderVersionPage(); }
  }
}

function renderVersionPage(loading = false) {
  const version = state.version;
  $("versionInstalled").textContent = loading && !version ? "…" : displayVersion(version?.installed);
  $("versionLatest").textContent = loading && !version ? "…" : displayVersion(version?.latest);
  $("releaseName").textContent = version?.release_name || "Последняя версия 3x-ui";
  $("releaseDate").textContent = releaseDate(version?.published_at);
  $("releaseNotes").textContent = version?.error
    ? `Не удалось получить описание релиза: ${version.error}`
    : cleanReleaseNotes(version?.release_summary || version?.release_notes);

  const badge = $("versionBadge");
  badge.className = "release-status";
  if (loading && !version) {
    badge.textContent = "Проверка…";
  } else if (version?.update_available === true) {
    badge.textContent = "Есть обновление";
    badge.classList.add("is-warning");
  } else if (version?.update_available === false) {
    badge.textContent = "Актуальная";
    badge.classList.add("is-current");
  } else {
    badge.textContent = "Неизвестно";
    badge.classList.add("is-muted");
  }
  $("updatePanelBtn").classList.toggle("hidden", !(version?.update_available && version?.update_enabled));
}

async function openUsers() {
  if (!state.selected) return;
  showView("users");
  await refreshUsers();
}

async function refreshUsers() {
  if (!state.selected) return;
  $("inbounds").innerHTML = `<div class="panel empty loading-shimmer">Получение пользователей…</div>`;
  try {
    state.inbounds = await api(`/servers/${state.selected.id}/inbounds`);
    fillInboundSelect();
    renderInbounds();
  } catch (error) {
    showToast(error.message);
    $("inbounds").innerHTML = `<div class="panel empty">${escapeHtml(error.message)}</div>`;
  }
}

function fillInboundSelect() {
  const select = $("inboundSelect");
  select.innerHTML = state.inbounds.map(item => `<option value="${item.id}">${escapeHtml(item.remark)} · ${escapeHtml(item.protocol)}:${item.port}</option>`).join("");
  select.disabled = state.inbounds.length === 0;
}

function renderInbounds() {
  const container = $("inbounds");
  if (!state.inbounds.length) {
    container.innerHTML = `<div class="panel empty">Inbound не найден.</div>`;
    return;
  }
  container.innerHTML = state.inbounds.map(inbound => `
    <article class="inbound-card">
      <div class="inbound-summary">
        <div class="inbound-title">
          <div class="inbound-icon">${inboundIcon()}</div>
          <div>
            <h4>${escapeHtml(inbound.remark)}</h4>
            <div class="inbound-meta"><b>${escapeHtml(inbound.protocol)}</b><span>•</span><span>порт ${inbound.port}</span><span>•</span><span>${inbound.clients.length} пользователей</span></div>
          </div>
        </div>
        <div class="traffic-badge"><strong>${bytes(inbound.up + inbound.down)}</strong><span>общий трафик</span></div>
      </div>
      <div class="client-list">
        ${inbound.clients.length ? inbound.clients.map(client => `
          <div class="client-row">
            <div class="client-person">
              <div class="client-avatar">${escapeHtml(String(client.email || "?").charAt(0))}<span class="status-dot ${client.online ? "online" : ""}"></span></div>
              <div class="client-name"><strong>${escapeHtml(client.email)}</strong><div class="muted">до ${dateValue(client.expiry_time)} · IP ${client.limit_ip || "∞"}</div></div>
            </div>
            <div class="client-traffic"><strong>${bytes(client.total)}</strong><div class="muted">↑ ${bytes(client.up)} · ↓ ${bytes(client.down)}</div></div>
            <div class="actions">
              <button class="secondary qr-button" data-link="${inbound.id}|${escapeHtml(client.email)}" aria-label="Показать QR-код" title="QR-код">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm11 0h2v2h-2v-2Zm3 0h2v5h-2v-5Zm-3 4h2v2h-2v-2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
              </button>
              <button class="danger-outline" data-delete="${inbound.id}|${escapeHtml(client.email)}" aria-label="Удалить пользователя" title="Удалить">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
            </div>
          </div>`).join("") : `<div class="empty">Пользователей пока нет.</div>`}
      </div>
    </article>`).join("");

  document.querySelectorAll("[data-link]").forEach(button => button.addEventListener("click", () => showConnection(...button.dataset.link.split("|"))));
  document.querySelectorAll("[data-delete]").forEach(button => button.addEventListener("click", () => removeClient(...button.dataset.delete.split("|"))));
}

async function showConnection(inboundId, email) {
  try {
    const data = await api(`/servers/${state.selected.id}/clients/${inboundId}/${encodeURIComponent(email)}/connection`);
    openConnectionDialog(data.connections || (data.connection ? [data.connection] : [data]));
  } catch (error) { showToast(error.message); }
}

function openConnectionDialog(connections) {
  state.connections = Array.isArray(connections) ? connections.filter(item => item?.uri) : [];
  if (!state.connections.length) return showToast("3x-ui не вернула ссылку подключения");

  const select = $("connectionSelect");
  select.innerHTML = state.connections.map((item, index) => {
    const protocol = String(item.protocol || "config").toUpperCase();
    return `<option value="${index}">${escapeHtml(protocol)} · ${escapeHtml(item.label || `Конфигурация ${index + 1}`)}</option>`;
  }).join("");
  $("connectionSelectField").classList.toggle("hidden", state.connections.length < 2);
  showSelectedConnection(0);
  $("connectionDialog").showModal();
}

function showSelectedConnection(index) {
  const item = state.connections[Number(index) || 0];
  if (!item) return;
  $("connectionUri").value = item.uri;
  $("qrImage").src = item.qr_data_url;
}

async function removeClient(inboundId, email) {
  if (!confirm(`Удалить пользователя ${email}?`)) return;
  try {
    await api(`/servers/${state.selected.id}/clients/${inboundId}/${encodeURIComponent(email)}`, { method: "DELETE" });
    showToast("Пользователь удалён");
    await refreshUsers();
  } catch (error) { showToast(error.message); }
}

$("clientForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    inbound_id: Number($("inboundSelect").value),
    email: $("clientEmail").value.trim(),
    total_gb: Number($("clientTotal").value || 0),
    expiry_days: Number($("clientDays").value || 0),
    limit_ip: Number($("clientIpLimit").value || 0),
  };
  try {
    const result = await api(`/servers/${state.selected.id}/clients`, { method: "POST", body: JSON.stringify(payload) });
    $("clientEmail").value = "";
    openConnectionDialog(result.connections || [result.connection]);
    await refreshUsers();
  } catch (error) { showToast(error.message); }
});

function collectVersions(value, output = []) {
  if (typeof value === "string" && /^v?\d+(?:\.\d+)+(?:[-+._A-Za-z0-9]*)?$/.test(value.trim())) output.push(value.trim());
  else if (Array.isArray(value)) value.forEach(item => collectVersions(item, output));
  else if (value && typeof value === "object") Object.values(value).forEach(item => collectVersions(item, output));
  return [...new Set(output)];
}

$("updateXrayBtn").addEventListener("click", async () => {
  try {
    const response = await api(`/servers/${state.selected.id}/xray/versions`);
    const versions = collectVersions(response.versions);
    const version = prompt(`Версия Xray для установки${versions.length ? `\nДоступные: ${versions.slice(0, 10).join(", ")}` : ""}`, versions[0] || "");
    if (!version) return;
    const expected = `XRAY ${state.selected.id} ${version}`;
    const confirmation = prompt(`Для установки введите: ${expected}`);
    if (confirmation !== expected) return showToast("Обновление отменено");
    await api(`/servers/${state.selected.id}/xray/install`, { method: "POST", body: JSON.stringify({ version, confirm: confirmation }) });
    showToast("Xray обновлён");
    await refreshDashboard();
  } catch (error) { showToast(error.message); }
});

$("updateSystemBtn").addEventListener("click", async () => {
  const expected = `APT ${state.selected.id}`;
  const confirmation = prompt(`Будут выполнены apt-get update и apt-get upgrade -y.\nДля запуска введите: ${expected}`);
  if (confirmation !== expected) return showToast("Обновление отменено");

  const button = $("updateSystemBtn");
  const oldHtml = button.innerHTML;
  button.disabled = true;
  button.textContent = "Обновление…";
  showToast("Обновление запущено. Это может занять несколько минут.", 5000);
  try {
    const job = await api(`/servers/${state.selected.id}/system/update`, {
      method: "POST",
      body: JSON.stringify({ confirm: confirmation }),
    });
    const result = await waitForOperation(job, "Обновление сервера выполняется…");
    $("operationTitle").textContent = "Обновление сервера завершено";
    $("operationSummary").textContent = result.reboot_required
      ? "Серверу требуется перезагрузка. Она не выполнялась автоматически."
      : "Перезагрузка не требуется.";
    $("operationOutput").textContent = result.output || "Команда завершилась без текстового вывода.";
    $("operationDialog").showModal();
    tg?.HapticFeedback?.notificationOccurred("success");
    await refreshDashboard();
  } catch (error) {
    showToast(error.message, 6000);
  } finally {
    button.disabled = false;
    button.innerHTML = oldHtml;
  }
});

$("updatePanelBtn").addEventListener("click", async () => {
  const expected = `UPDATE ${state.selected.id}`;
  const confirmText = prompt(`Будет создана резервная копия базы. Для обновления введите: ${expected}`);
  if (confirmText !== expected) return showToast("Обновление отменено");
  const button = $("updatePanelBtn");
  const oldText = button.textContent;
  button.disabled = true;
  button.textContent = "Обновление…";
  try {
    showToast("Запущено обновление 3x-ui с резервной копией", 5000);
    const job = await api(`/servers/${state.selected.id}/panel/update`, { method: "POST", body: JSON.stringify({ confirm: confirmText }) });
    await waitForOperation(job, "Обновление 3x-ui выполняется…");
    showToast("3x-ui обновлена");
    state.version = null;
    await fetchXuiVersion(true);
    renderVersionPage();
  } catch (error) {
    showToast(error.message, 6000);
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
});

$("copyUriBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("connectionUri").value);
  tg?.HapticFeedback?.notificationOccurred("success");
  showToast("Скопировано");
});

$("connectionSelect").addEventListener("change", event => showSelectedConnection(event.target.value));

$("usersBtn").addEventListener("click", openUsers);
$("backBtn").addEventListener("click", () => {
  state.selected = null;
  state.inbounds = [];
  state.version = null;
  showView("servers");
  loadServers().catch(error => showToast(error.message));
});
$("usersBackBtn").addEventListener("click", () => showView("dashboard"));
$("versionBackBtn").addEventListener("click", () => showView("dashboard"));
async function refreshCurrentView() {
  const button = $("refreshBtn");
  if (button.disabled) return;

  button.disabled = true;
  button.classList.add("is-loading");

  try {
    if (state.view === "dashboard") await refreshDashboard();
    else if (state.view === "users") await refreshUsers();
    else if (state.view === "version") {
      await fetchXuiVersion(true);
      renderVersionPage();
    } else {
      await loadServers();
    }
  } catch (error) {
    showToast(error.message, 5000);
  } finally {
    button.classList.remove("is-loading");
    button.disabled = false;
  }
}

$("refreshBtn").addEventListener("click", refreshCurrentView);

loadServers().catch(error => {
  $("notice").textContent = error.message;
  $("notice").classList.remove("hidden");
});
