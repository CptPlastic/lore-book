(() => {
  const canvas = document.getElementById("sparkles");
  const legacyHome = document.querySelector(".legacy-home");

  if (legacyHome) {
    document.body.classList.add("legacy-home-page");
  }

  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const reduced = globalThis.matchMedia && globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let width = 0;
  let height = 0;
  let particles = [];
  const glyphs = ["✦", "✧", "⋆", "·", "✵", "✴", "⚝", "∗"];
  const count = reduced ? 20 : 55;

  function rand(min, max) {
    return Math.random() * (max - min) + min;
  }

  function resize() {
    width = canvas.width = globalThis.innerWidth;
    height = canvas.height = globalThis.innerHeight;
  }

  function spawn() {
    return {
      x: rand(0, width),
      y: rand(-height * 0.6, height * 0.2),
      vy: rand(0.12, 0.45),
      vx: rand(-0.15, 0.15),
      life: 0,
      maxLife: rand(140, 320),
      size: rand(9, 18),
      glyph: glyphs[Math.floor(Math.random() * glyphs.length)],
      hue: rand(38, 52),
    };
  }

  function init() {
    particles = [];
    for (let index = 0; index < count; index += 1) {
      const particle = spawn();
      particle.life = rand(0, particle.maxLife);
      particles.push(particle);
    }
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (const particle of particles) {
      const t = particle.life / particle.maxLife;
      let alpha = 1;

      if (t < 0.15) {
        alpha = t / 0.15;
      } else if (t > 0.75) {
        alpha = (1 - t) / 0.25;
      }

      ctx.globalAlpha = alpha * 0.75;
      ctx.fillStyle = `hsl(${particle.hue}, 90%, 72%)`;
      ctx.font = `${particle.size}px serif`;
      ctx.fillText(particle.glyph, particle.x, particle.y);

      particle.x += particle.vx;
      particle.y += particle.vy;
      particle.life += 1;

      if (particle.life >= particle.maxLife) {
        Object.assign(particle, spawn(), { life: 0 });
      }
    }

    ctx.globalAlpha = 1;
    globalThis.requestAnimationFrame(draw);
  }

  globalThis.addEventListener("resize", () => {
    resize();
    init();
  });

  resize();
  init();
  draw();
})();
