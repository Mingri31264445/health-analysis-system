(function () {
  const list = document.querySelector("[data-record-list]");
  if (!list) return;

  const boxes = Array.from(list.querySelectorAll(".bfs-compare-checkbox, .meridian-compare-checkbox"));
  const params = new URLSearchParams(window.location.search);
  const key = `record-list:${list.dataset.listUser}:${window.location.pathname}:${params.get("subject") || "all"}`;
  const returning = window.location.hash === "#records";
  let saved = null;

  try {
    saved = JSON.parse(sessionStorage.getItem(key));
    if (!saved || Date.now() - saved.at > 30 * 60 * 1000) saved = null;
  } catch (_) {
    saved = null;
  }

  if (returning) {
    const ids = params.has("selected")
      ? params.get("selected").split(",")
      : (saved && saved.selected) || [];
    const selected = new Set(ids);
    let selectedUser = null;
    let selectedCount = 0;
    boxes.forEach((box) => {
      const canSelect = selected.has(box.value)
        && selectedCount < 4
        && (selectedUser === null || selectedUser === box.dataset.user);
      box.checked = canSelect;
      if (canSelect) {
        selectedUser = box.dataset.user;
        selectedCount += 1;
      }
    });
  }

  window.addEventListener("pagehide", () => {
    try {
      sessionStorage.setItem(key, JSON.stringify({
        at: Date.now(),
        scrollY: window.scrollY,
        selected: boxes.filter((box) => box.checked).map((box) => box.value),
      }));
    } catch (_) {
      // The #records anchor still works when session storage is unavailable.
    }
  });

  window.addEventListener("pageshow", () => {
    if (!returning || !saved || !Number.isFinite(saved.scrollY)) return;
    requestAnimationFrame(() => window.scrollTo(0, saved.scrollY));
  });
})();
