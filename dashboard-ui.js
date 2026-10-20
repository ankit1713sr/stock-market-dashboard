// TradePulse AI - 3D UI, Lighting & Micro-Interactions Engine

document.addEventListener('DOMContentLoaded', () => {
  initBackgroundCanvas();
  initMouseLighting();
  init3DTiltCards();
  initMagneticButtons();
  initSidebarToggle();
  initPlotlyThemeDefaults();
});

/* 1. Interactive Ambient Grid & Particle Canvas */
function initBackgroundCanvas() {
  const canvas = document.getElementById('bgCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const mouse = { x: width / 2, y: height / 2, targetX: width / 2, targetY: height / 2 };

  window.addEventListener('mousemove', (e) => {
    mouse.targetX = e.clientX;
    mouse.targetY = e.clientY;
  });

  const numParticles = 45;
  const particles = [];

  for (let i = 0; i < numParticles; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.4 + 0.1
    });
  }

  function render() {
    // Smooth lerp mouse
    mouse.x += (mouse.targetX - mouse.x) * 0.05;
    mouse.y += (mouse.targetY - mouse.y) * 0.05;

    ctx.clearRect(0, 0, width, height);

    // Render faint moving grid
    const gridSize = 60;
    const offsetX = (mouse.x * 0.02) % gridSize;
    const offsetY = (mouse.y * 0.02) % gridSize;

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
    ctx.lineWidth = 1;

    for (let x = offsetX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    for (let y = offsetY; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Render floating particles
    particles.forEach((p, index) => {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height;
      if (p.y > height) p.y = 0;

      // Mouse influence
      const dx = mouse.x - p.x;
      const dy = mouse.y - p.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 150) {
        const angle = Math.atan2(dy, dx);
        p.x -= Math.cos(angle) * 0.5;
        p.y -= Math.sin(angle) * 0.5;
      }

      ctx.fillStyle = `rgba(56, 189, 248, ${p.alpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();

      // Connect close particles
      for (let j = index + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const pdx = p.x - p2.x;
        const pdy = p.y - p2.y;
        const pdist = Math.sqrt(pdx * pdx + pdy * pdy);

        if (pdist < 100) {
          ctx.strokeStyle = `rgba(6, 182, 212, ${0.1 * (1 - pdist / 100)})`;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    });

    requestAnimationFrame(render);
  }

  render();
}

/* 2. Dynamic Mouse Ambient Lighting & Parallax */
function initMouseLighting() {
  const root = document.documentElement;

  window.addEventListener('mousemove', (e) => {
    const x = e.clientX;
    const y = e.clientY;

    root.style.setProperty('--mouse-x', `${x}px`);
    root.style.setProperty('--mouse-y', `${y}px`);
  });
}

/* 3. Lightweight 3D Card Tilt & Cursor Spotlight */
function init3DTiltCards() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const cards = document.querySelectorAll('.kpi-card, .chart-card, .calc-card, .ai-insight-box');

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // Subtle tilt output
      const rotateX = ((y - centerY) / centerY) * -4; // Max tilt deg
      const rotateY = ((x - centerX) / centerX) * 4;

      card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(4px)`;

      // Dynamic card cursor highlight
      card.style.setProperty('--card-mouse-x', `${x}px`);
      card.style.setProperty('--card-mouse-y', `${y}px`);
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
    });
  });
}

/* 4. Magnetic Micro-Interaction on Primary Action Buttons */
function initMagneticButtons() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const magneticBtns = document.querySelectorAll('.btn-add-trade, .btn-secondary-action');

  magneticBtns.forEach(btn => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      btn.style.transform = `translate(${x * 0.25}px, ${y * 0.25}px)`;
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'translate(0px, 0px)';
    });
  });
}

/* 5. Collapsible Sidebar Dock */
function initSidebarToggle() {
  const toggleBtn = document.getElementById('toggleSidebarBtn');
  const sidebar = document.querySelector('.sidebar-dock');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      window.dispatchEvent(new Event('resize'));
    });
  }
}

/* 6. Dark Terminal Plotly Theme Styling */
function initPlotlyThemeDefaults() {
  if (typeof Plotly === 'undefined') return;

  const originalNewPlot = Plotly.newPlot;

  Plotly.newPlot = function(target, data, layout, config) {
    const darkLayout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { family: 'Inter, sans-serif', color: '#94a3b8' },
      margin: { l: 45, r: 20, t: 25, b: 40 },
      xaxis: { gridcolor: 'rgba(255, 255, 255, 0.05)', linecolor: 'rgba(255, 255, 255, 0.1)' },
      yaxis: { gridcolor: 'rgba(255, 255, 255, 0.05)', linecolor: 'rgba(255, 255, 255, 0.1)' },
      hoverlabel: {
        bgcolor: '#0f172a',
        bordercolor: '#06b6d4',
        font: { family: 'JetBrains Mono, monospace', color: '#ffffff' }
      },
      ...layout
    };

    const defaultConfig = {
      responsive: true,
      displayModeBar: false,
      ...config
    };

    return originalNewPlot.call(Plotly, target, data, darkLayout, defaultConfig);
  };
}
