(() => {
  const canvas = document.getElementById("sparkles-canvas");
  if (!canvas) {
    return;
  }

  const host = canvas.parentElement;
  if (!host) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const prefersReducedMotion =
    globalThis.matchMedia && globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let width = 0;
  let height = 0;
  let particles = [];
  let embers = [];
  const count = prefersReducedMotion ? 24 : 62;
  const emberCount = prefersReducedMotion ? 1 : 4;

  function resize() {
    const rect = host.getBoundingClientRect();
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(1, Math.floor(rect.height));
    const dpr = Math.max(1, Math.min(2, globalThis.devicePixelRatio || 1));
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: 0.7 + Math.random() * 1.8,
      vx: (Math.random() - 0.5) * 0.25,
      vy: -0.22 - Math.random() * 0.42,
      tw: Math.random() * Math.PI * 2,
      hue: 42 + Math.random() * 18,
    }));

    embers = Array.from({ length: emberCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height * 0.6,
      vx: 1.7 + Math.random() * 1.8,
      vy: -0.4 + Math.random() * 0.25,
      life: 0.4 + Math.random() * 0.5,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.tw += 0.055;

      if (p.y < -8) {
        p.y = height + 8;
        p.x = Math.random() * width;
      }
      if (p.x < -8) {
        p.x = width + 8;
      }
      if (p.x > width + 8) {
        p.x = -8;
      }

      const alpha = 0.46 + 0.44 * Math.sin(p.tw);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${p.hue}, 92%, 76%, ${alpha})`;
      ctx.fill();
    }

    for (const e of embers) {
      e.x += e.vx;
      e.y += e.vy;

      if (e.x > width + 34 || e.y < -20) {
        e.x = -30;
        e.y = height * (0.22 + Math.random() * 0.62);
        e.vx = 1.6 + Math.random() * 1.7;
        e.vy = -0.45 + Math.random() * 0.28;
        e.life = 0.45 + Math.random() * 0.45;
      }

      ctx.beginPath();
      ctx.moveTo(e.x, e.y);
      ctx.lineTo(e.x - 20, e.y - 4);
      ctx.strokeStyle = `hsla(190, 90%, 74%, ${e.life})`;
      ctx.lineWidth = 1.1;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(e.x, e.y, 1.6, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(48, 96%, 74%, ${Math.min(1, e.life + 0.2)})`;
      ctx.fill();
    }

    requestAnimationFrame(draw);
  }

  resize();
  draw();

  let resizeTimer;
  globalThis.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 90);
  });
})();
