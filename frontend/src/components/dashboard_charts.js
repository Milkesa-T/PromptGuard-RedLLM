const COLORS = {
  blue: "#38bdf8",
  red: "#fb7185",
  green: "#34d399",
  muted: "#94a3b8",
  grid: "#334155",
  text: "#e2e8f0",
};

function drawBars(ctx, title, labels, values, colors, x, y, width, height) {
  ctx.fillStyle = COLORS.text;
  ctx.font = "bold 15px system-ui";
  ctx.fillText(title, x, y + 16);

  const top = y + 35;
  const chartHeight = height - 65;
  const barWidth = Math.min(62, width / Math.max(labels.length * 1.8, 1));
  const slot = width / Math.max(labels.length, 1);

  ctx.strokeStyle = COLORS.grid;
  ctx.fillStyle = COLORS.muted;
  ctx.font = "11px system-ui";
  for (let tick = 0; tick <= 100; tick += 25) {
    const gy = top + chartHeight - (tick / 100) * chartHeight;
    ctx.beginPath();
    ctx.moveTo(x, gy);
    ctx.lineTo(x + width, gy);
    ctx.stroke();
    ctx.fillText(`${tick}%`, x, gy - 4);
  }

  labels.forEach((label, i) => {
    const value = Math.max(0, Math.min(100, Number(values[i]) || 0));
    const bx = x + i * slot + (slot - barWidth) / 2 + 18;
    const bh = (value / 100) * chartHeight;
    ctx.fillStyle = colors[i] || COLORS.blue;
    ctx.fillRect(bx, top + chartHeight - bh, barWidth, bh);
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = "center";
    ctx.fillText(`${value.toFixed(1)}%`, bx + barWidth / 2, top + chartHeight - bh - 7);
    ctx.fillStyle = COLORS.muted;
    ctx.fillText(label, bx + barWidth / 2, top + chartHeight + 17);
    ctx.textAlign = "left";
  });
}

export function drawBenchmarkCharts(canvas, { baseline, protectedRun, results = [] }) {
  if (!canvas) return;
  const width = Math.max(canvas.clientWidth || 600, 320);
  const height = 510;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.width = "100%";
  canvas.style.height = `${height}px`;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0b1324";
  ctx.fillRect(0, 0, width, height);

  const margin = 20;
  const chartWidth = width - margin * 2;
  drawBars(
    ctx,
    "Attack Success Rate: baseline vs PromptGuard",
    ["Without Guard", "With PromptGuard"],
    [baseline?.attack_success_rate ?? 0, protectedRun?.attack_success_rate ?? 0],
    [COLORS.red, COLORS.green],
    margin,
    10,
    chartWidth,
    220,
  );

  const categories = [
    ["direct", "Direct"],
    ["cipher", "Cipher"],
    ["tool", "Tool Misuse"],
    ["system", "System Theft"],
  ];
  const counts = categories.map(([key]) => {
    const matching = results.filter((row) => {
      const type = String(row.attack_type || "").toLowerCase();
      if (key === "direct") return type.includes("direct");
      if (key === "cipher") return type.includes("cipher") || type.includes("rot") || type.includes("base64") || type.includes("encoding");
      if (key === "tool") return type.includes("tool");
      return type.includes("system") || type.includes("theft") || type.includes("leak");
    });
    if (!matching.length) return 0;
    return matching.filter((row) => row.is_success === true).length / matching.length * 100;
  });

  drawBars(
    ctx,
    "Attack Success Rate by Category (latest run)",
    categories.map(([, label]) => label),
    counts,
    [COLORS.blue, COLORS.red, "#fbbf24", "#c084fc"],
    margin,
    265,
    chartWidth,
    230,
  );
}
