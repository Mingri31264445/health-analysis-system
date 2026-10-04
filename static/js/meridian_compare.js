(function () {
  const btn = document.getElementById("meridian-compare-btn");
  const boxes = Array.from(
    document.querySelectorAll(".meridian-compare-checkbox"),
  );
  if (!btn || boxes.length === 0) return;

  const MIN = 2;
  const MAX = 4;

  // 核心防呆邏輯
  function refresh() {
    const checked = boxes.filter((b) => b.checked);
    // 已選的第一筆決定「受測者」，之後只能選同一位
    const lockedUser = checked.length ? checked[0].dataset.user : null;

    boxes.forEach((b) => {
      if (b.checked) {
        b.disabled = false;
        return;
      }
      const reachedMax = checked.length >= MAX; // 數量上限鎖定
      const otherUser = lockedUser !== null && b.dataset.user !== lockedUser; // 受測者不同鎖定
      b.disabled = reachedMax || otherUser;
    });

    btn.textContent = `比較趨勢（已選 ${checked.length}/${MAX}）`; // 按鈕的文字會即時顯示目前進度
    btn.disabled = checked.length < MIN; //如果選不到2筆，按鈕就會被停用
  }

  boxes.forEach((b) => b.addEventListener("change", refresh)); // 監聽勾選框狀態，變化後立刻觸發refresh()

  btn.addEventListener("click", () => {
    const ids = boxes.filter((b) => b.checked).map((b) => b.value);
    if (ids.length < MIN || ids.length > MAX) return;
    window.location.href = `${btn.dataset.compareUrl}?ids=${ids.join(",")}`; // ?ids=5,8,12
  });

  // 從比較頁按瀏覽器「上一頁」回來時，瀏覽器可能還記得勾選狀態，同步一次
  window.addEventListener("pageshow", refresh);
  refresh(); // 頁面一載入就先刷新一次，避免按鈕文字顯示錯誤
})();
