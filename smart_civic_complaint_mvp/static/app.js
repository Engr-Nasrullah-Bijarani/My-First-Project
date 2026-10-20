const complaintForm = document.querySelector("#complaintForm");
const submitResult = document.querySelector("#submitResult");
const trackForm = document.querySelector("#trackForm");
const trackResult = document.querySelector("#trackResult");

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;" }[ch]));
}
function statusClass(status) { return String(status || "").toLowerCase().replaceAll(" ", "-"); }

complaintForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = complaintForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.innerHTML = "Submitting…";
  submitResult.classList.add("hidden");
  try {
    const response = await fetch("/api/complaints", { method: "POST", body: new FormData(complaintForm) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not submit report.");
    submitResult.className = "result-panel success";
    submitResult.innerHTML = `<div class="success-mark">✓</div><div><strong>Report submitted successfully</strong><p>Your tracking ID is <b>#${data.id}</b>. Save it to check updates.</p><div class="result-tags"><span>${escapeHtml(data.category)}</span><span class="priority-${data.priority.toLowerCase()}">${escapeHtml(data.priority)} priority</span></div>${data.possible_duplicate_of ? `<p class="duplicate-note">Possible duplicate of report #${data.possible_duplicate_of}; staff will review it.</p>` : ""}<button class="copy-id" type="button" id="copyTracking">Copy tracking ID</button></div>`;
    complaintForm.reset();
    document.querySelector("#trackingId").value = data.id;
    document.querySelector("#copyTracking")?.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(String(data.id)); document.querySelector("#copyTracking").textContent = "Copied!"; }
      catch { document.querySelector("#copyTracking").textContent = `ID: ${data.id}`; }
    });
    submitResult.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    submitResult.className = "result-panel error";
    submitResult.textContent = error.message;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Submit report <span>→</span>';
  }
});

trackForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = document.querySelector("#trackingId").value;
  trackResult.innerHTML = '<div class="loading">Looking up your report…</div>';
  try {
    const response = await fetch(`/api/complaints/${encodeURIComponent(id)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Report not found.");
    trackResult.innerHTML = `<div class="track-result-card"><div class="track-result-top"><strong>#${data.id} · ${escapeHtml(data.title)}</strong><span class="status-pill ${statusClass(data.status)}">${escapeHtml(data.status)}</span></div><div class="track-meta"><span><small>Category</small>${escapeHtml(data.category)}</span><span><small>Priority</small><b class="priority-${data.priority.toLowerCase()}">${escapeHtml(data.priority)}</b></span><span><small>Location</small>${escapeHtml(data.location)}</span></div>${data.duplicate_of ? `<p class="duplicate-note">Flagged as a possible duplicate of #${data.duplicate_of}.</p>` : ""}${data.admin_note ? `<p class="admin-note"><b>Latest update:</b> ${escapeHtml(data.admin_note)}</p>` : ""}<small class="updated-at">Last updated ${escapeHtml(data.updated_at)}</small></div>`;
  } catch (error) {
    trackResult.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
});
