// ── Sidebar Toggle ────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const adminMain = document.getElementById('adminMain');
const overlay = document.getElementById('sidebarOverlay');

function toggleSidebar() {
    const isMobile = window.innerWidth <= 1024;
    if (isMobile) {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('visible');
    } else {
        sidebar.classList.toggle('collapsed');
        adminMain.classList.toggle('expanded');
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    }
}

const sidebarToggle = document.getElementById('sidebarToggle');
const topbarToggle = document.getElementById('topbarToggle');
if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
if (topbarToggle) topbarToggle.addEventListener('click', toggleSidebar);
if (overlay) overlay.addEventListener('click', () => {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('visible');
});

// Restore sidebar state on desktop
if (window.innerWidth > 1024 && localStorage.getItem('sidebarCollapsed') === 'true') {
    sidebar?.classList.add('collapsed');
    adminMain?.classList.add('expanded');
}

// ── Live Clock ────────────────────────────────────────────────
const timeEl = document.getElementById('topbarTime');
if (timeEl) {
    function updateTime() {
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    updateTime();
    setInterval(updateTime, 1000);
}

// ── Confirm Delete Buttons ────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
});

// ── Auto-dismiss Flash ────────────────────────────────────────
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
});

// ── Table Row Hover ───────────────────────────────────────────
document.querySelectorAll('.admin-table tbody tr').forEach(row => {
    row.style.transition = 'background 0.15s ease';
});
