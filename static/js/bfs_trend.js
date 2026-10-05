(function () {
  const dataEl = document.getElementById("bfs-trend-data");
  if (!dataEl || typeof Chart === "undefined") return;

  const charts = JSON.parse(dataEl.textContent);

  // 最多 4 條線，由舊到新依序取色（跟經絡儀趨勢圖同色系）
  const COLORS = ["#6a807a", "#c19a6d", "#c0504d", "#4a6fa5"];

  // 部位名稱很長，tooltip 依字數切成多行，避免一行拉得太寬
  function wrap(text, size) {
    const lines = [];
    for (let i = 0; i < text.length; i += size) {
      lines.push(text.slice(i, i + size));
    }
    return lines;
  }

  charts.forEach((chart, index) => {
    const canvas = document.getElementById("bfs-trend-chart-" + index);
    if (!canvas) return;

    // X 軸只放編號，完整名稱在 tooltip 和下方對照表
    const labels = chart.captions.map((_, i) => String(i + 1));

    const datasets = chart.series.map((s, i) => ({
      label: s.label,
      data: s.values,
      borderColor: COLORS[i % COLORS.length],
      backgroundColor: COLORS[i % COLORS.length],
      borderWidth: 2,
      pointRadius: 4,
      tension: 0.2,
      spanGaps: false, // null（該次測試沒有這個部位）讓折線斷開
    }));

    new Chart(canvas, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: {
            min: 0,
            max: 6,
            ticks: { stepSize: 1 },
            title: { display: true, text: "平均等級（越高越差）" },
          },
          x: {
            title: { display: true, text: "部位編號（對照下表）" },
          },
        },
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              title(items) {
                if (!items.length) return "";
                const i = items[0].dataIndex;
                return wrap(`${i + 1}. ${chart.captions[i]}`, 22);
              },
            },
          },
        },
      },
    });
  });
})();
