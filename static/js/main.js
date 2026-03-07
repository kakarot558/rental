// ── Loading Screen ────────────────────────────────────────────
window.addEventListener('load', () => {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) setTimeout(() => overlay.classList.add('hidden'), 300);
});

// ── Navbar Scroll ─────────────────────────────────────────────
const navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });
}

// ── Auto-dismiss Alerts ───────────────────────────────────────
document.querySelectorAll('.alert').forEach(alert => {
  setTimeout(() => {
    alert.style.transition = 'opacity .4s ease, transform .4s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(12px)';
    setTimeout(() => alert.remove(), 400);
  }, 5000);
});

// ── Scroll-in Animations ──────────────────────────────────────
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = '1';
      e.target.style.transform = 'translateY(0)';
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.eq-card, .step, .hero-card, .stat-card').forEach((el, i) => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = `opacity .5s ease ${i * 0.07}s, transform .5s ease ${i * 0.07}s`;
  io.observe(el);
});

// ── Admin: Live Clock ─────────────────────────────────────────
const clock = document.getElementById('liveClock');
if (clock) {
  const tick = () => {
    clock.textContent = new Date().toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  tick(); setInterval(tick, 1000);
}

// ── Admin: Sidebar Toggle ─────────────────────────────────────
const sidebarToggle = document.querySelector('.sidebar-toggle');
const sidebar = document.getElementById('sidebar');
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.querySelector('.sidebar-overlay')?.addEventListener('click', () => sidebar.classList.remove('open'));
}
