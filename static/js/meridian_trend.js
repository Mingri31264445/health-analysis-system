(function () {
  const dataEl = document.getElementById("trend-data");
  const canvas = document.getElementById("meridian-trend-chart");
  if (!dataEl || !canvas || typeof Chart === "undefined") return; //如果有任何一個不存在就直接中斷，避免網頁噴錯

  const payload = JSON.parse(dataEl.textContent); //把後端傳過來的 JSON 資料轉成 JavaScript 物件
  const meridians = payload.meridians;
  const gapIndex = meridians.length; // 中間空白格的位置（index 12）

  // X 軸：左側 12 條 + 空白 + 右側 12 條
  const labels = [...meridians, "", ...meridians];

  // 最多 4 條線，由舊到新依序取色
  const COLORS = ["#6a807a", "#c19a6d", "#c0504d", "#4a6fa5"];

  const datasets = payload.series.map((s, i) => ({
    label: s.label,
    data: s.values,
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length],
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.25,
    spanGaps: false, // 中間的 null 讓折線在這裡斷開
  }));

  // 在空白格畫垂直虛線，並標示「左側 / 右側」
  const dividerPlugin = {
    id: "sideDivider",
    afterDatasetsDraw(chart) {
      const { ctx, chartArea, scales } = chart;
      const x = scales.x.getPixelForValue(gapIndex); // 中間空白格的 X 座標
      ctx.save();
      ctx.strokeStyle = "#b9b3a6";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.fillStyle = "#6b767c";
      ctx.font = "bold 13px sans-serif";
      ctx.textAlign = "center";
      const leftCenter = scales.x.getPixelForValue((meridians.length - 1) / 2);
      const rightCenter = scales.x.getPixelForValue(
        gapIndex + 1 + (meridians.length - 1) / 2,
      );
      ctx.fillText("左側", leftCenter, chartArea.top + 14);
      ctx.fillText("右側", rightCenter, chartArea.top + 14);
      ctx.restore();
    },
  };

  new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    plugins: [dividerPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        y: {
          beginAtZero: true,
          grace: "10%", // 上方留空間給「左側/右側」標題
          title: { display: true, text: "補償值" },
        },
        x: { ticks: { autoSkip: false } }, // 強迫 X 軸所有的經絡名稱全部顯示出來，不會自動省略
      },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            title(items) {
              if (!items.length) return "";
              const i = items[0].dataIndex;
              if (i === gapIndex) return ""; // 點到中間空白格就不顯示任何標題
              return `${labels[i]}（${i < gapIndex ? "左側" : "右側"}）`;
            },
          },
        },
      },
    },
  });
})();
