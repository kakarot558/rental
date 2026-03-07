/* ================================================================
   SOUNDLIGHT EVENTS — Main JS
   ================================================================ */

// ── Loading Screen ────────────────────────────────────────────────
window.addEventListener('load', () => {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) setTimeout(() => overlay.classList.add('hidden'), 280);
});

// ── Navbar: scroll style ──────────────────────────────────────────
const navbar = document.getElementById('navbar');
if (navbar) {
  const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 30);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ── Burger / Mobile Drawer ────────────────────────────────────────
const burger  = document.getElementById('navBurger');
const drawer  = document.getElementById('navDrawer');
const overlay = document.getElementById('navOverlay');

function openDrawer() {
  burger.classList.add('open');
  drawer.classList.add('open');
  overlay.classList.add('visible');
  drawer.setAttribute('aria-hidden', 'false');
  burger.setAttribute('aria-expanded', 'true');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
  burger.classList.remove('open');
  drawer.classList.remove('open');
  overlay.classList.remove('visible');
  drawer.setAttribute('aria-hidden', 'true');
  burger.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
}

if (burger && drawer) {
  burger.addEventListener('click', () => {
    drawer.classList.contains('open') ? closeDrawer() : openDrawer();
  });
  overlay?.addEventListener('click', closeDrawer);

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
  });

  // Close drawer when a link is clicked
  drawer.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', closeDrawer);
  });
}

// ── Auto-dismiss Alerts ───────────────────────────────────────────
document.querySelectorAll('.alert').forEach((alert, i) => {
  setTimeout(() => {
    alert.style.transition = 'opacity .4s ease, transform .4s ease, margin .3s ease';
    alert.style.opacity    = '0';
    alert.style.transform  = 'translateX(14px)';
    alert.style.marginBottom = '0';
    setTimeout(() => alert.remove(), 400);
  }, 4500 + i * 300);
});

// ── Scroll-in Animations ──────────────────────────────────────────
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity   = '1';
        e.target.style.transform = 'translateY(0)';
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });

  document.querySelectorAll('.eq-card, .step, .hero-card, .stat-card').forEach((el, i) => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(18px)';
    el.style.transition = `opacity .5s ease ${i * 0.06}s, transform .5s ease ${i * 0.06}s`;
    io.observe(el);
  });
}

// ── Admin: Live Clock ─────────────────────────────────────────────
const clock = document.getElementById('liveClock');
if (clock) {
  const tick = () => {
    clock.textContent = new Date().toLocaleTimeString('en-PH', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };
  tick();
  setInterval(tick, 1000);
}

// ── Admin: Sidebar Toggle ─────────────────────────────────────────
const sidebarToggle  = document.querySelector('.sidebar-toggle, .topbar-toggle');
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.querySelector('.sidebar-overlay');
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    sidebarOverlay?.classList.toggle('visible');
  });
  sidebarOverlay?.addEventListener('click', () => {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('visible');
  });
}
