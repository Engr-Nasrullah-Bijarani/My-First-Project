const list = document.querySelector("#complaintsList");
const statuses = ["Submitted", "Under review", "In progress", "Resolved", "Rejected"];
const priorities = ["Low", "Medium", "High"];
function esc(v = "") { return String(v).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;" }[c])); }
function statusSlug(v = "") { return v.toLowerCase().replaceAll(" ", "-"); }
async function getJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}
async function loadStats() {
  const s = await getJSON("/api/admin/stats");
  document.querySelector("#statTotal").textContent = s.total;
  document.querySelector("#statOpen").textContent = s.open;
  document.querySelector("#statHigh").textContent = s.high_priority;
  document.querySelector("#statResolved").textContent = s.resolved;
}
function optionList(items, selected) {
  return items.map(item => `<option ${item === selected ? "selected" : ""}>${esc(item)}</option>`).join("");
}
function card(c) {
  const duplicate = c.duplicate_of ? `<div class="duplicate-banner">⚑ Possible duplicate of report #${c.duplicate_of}</div>` : "";
  const photo = c.photo_filename ? `<a class="attachment-link" href="/uploads/${encodeURIComponent(c.photo_filename)}" target="_blank" rel="noopener">View submitted photo ↗</a>` : "";
  const evidence = c.resolution_filename ? `<a class="attachment-link" href="/uploads/${encodeURIComponent(c.resolution_filename)}" target="_blank" rel="noopener">View resolution evidence ↗</a>` : "";
  return `<article class="complaint-card" data-id="${c.id}">
    <div class="complaint-card-main"><div class="complaint-card-top"><span class="complaint-id">#${c.id}</span><span class="category-pill">${esc(c.category)}</span><span class="priority-pill priority-${c.priority.toLowerCase()}">${esc(c.priority)} priority</span><span class="status-pill ${statusSlug(c.status)}">${esc(c.status)}</span></div>
    <h3>${esc(c.title)}</h3><p class="complaint-description">${esc(c.description)}</p><div class="complaint-location">⌖ ${esc(c.location)}</div><div class="complaint-extra"><span>Reported by ${esc(c.reporter_name || "Anonymous")}</span><span>${esc(c.created_at)}</span>${photo}${evidence}</div>${duplicate}</div>
    <div class="manage-panel"><label>Status<select class="edit-status">${optionList(statuses, c.status)}</select></label><label>Priority<select class="edit-priority">${optionList(priorities, c.priority)}</select></label><label>Public update / resolution note<textarea class="edit-note" rows="2" maxlength="1000" placeholder="Write an update residents can see…">${esc(c.admin_note || "")}</textarea></label><div class="evidence-control"><label>Resolution photo<input class="evidence-file" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"></label></div><button class="button primary save-btn">Save update</button><span class="save-message" aria-live="polite"></span></div>
  </article>`;
}
async function loadComplaints() {
  list.innerHTML = '<div class="loading">Loading reports…</div>';
  try {
    const params = new URLSearchParams();
    if (document.querySelector("#filterStatus").value) params.set("status", document.querySelector("#filterStatus").value);
    if (document.querySelector("#filterCategory").value) params.set("category", document.querySelector("#filterCategory").value);
    const rows = await getJSON(`/api/admin/complaints?${params.toString()}`);
    list.innerHTML = rows.length ? rows.map(card).join("") : '<div class="empty-state">No reports match these filters.</div>';
    list.querySelectorAll(".save-btn").forEach(button => button.addEventListener("click", saveCard));
  } catch (error) {
    list.innerHTML = `<div class="inline-error">${esc(error.message)} — please sign in again.</div>`;
  }
}
async function saveCard(event) {
  const cardEl = event.currentTarget.closest(".complaint-card");
  const id = cardEl.dataset.id;
  const button = event.currentTarget;
  const message = cardEl.querySelector(".save-message");
  button.disabled = true;
  message.textContent = "Saving…";
  try {
    await getJSON(`/api/admin/complaints/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: cardEl.querySelector(".edit-status").value,
        priority: cardEl.querySelector(".edit-priority").value,
        admin_note: cardEl.querySelector(".edit-note").value
      })
    });
    const file = cardEl.querySelector(".evidence-file").files[0];
    if (file) {
      const form = new FormData(); form.append("evidence", file);
      await getJSON(`/api/admin/complaints/${id}/resolution`, { method: "POST", body: form });
    }
    message.textContent = "Saved ✓";
    await loadStats();
    await loadComplaints();
  } catch (error) {
    message.textContent = error.message;
  } finally { button.disabled = false; }
}
document.querySelector("#filterStatus").addEventListener("change", loadComplaints);
document.querySelector("#filterCategory").addEventListener("change", loadComplaints);
document.querySelector("#refreshBtn").addEventListener("click", async () => { await loadStats(); await loadComplaints(); });
(async () => { try { await loadStats(); await loadComplaints(); } catch (error) { list.innerHTML = `<p class="inline-error">${esc(error.message)}</p>`; } })();
