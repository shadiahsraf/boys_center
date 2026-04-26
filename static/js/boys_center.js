/* Boys Center — Main JavaScript */

// ── Sidebar Toggle (mobile) ──
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay && overlay.classList.toggle('show');
    });
    overlay && overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
    });
  }

  // Active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') && currentPath.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/') {
      link.classList.add('active');
    }
  });

  // Auto-dismiss alerts
  document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });

  // Star rating inputs
  document.querySelectorAll('.star-input-group').forEach(group => {
    const stars = group.querySelectorAll('.star-btn');
    const input = group.querySelector('input[type="hidden"]');
    stars.forEach((star, idx) => {
      star.addEventListener('click', () => {
        input && (input.value = idx + 1);
        stars.forEach((s, i) => s.classList.toggle('filled', i <= idx));
      });
      star.addEventListener('mouseenter', () => {
        stars.forEach((s, i) => s.classList.toggle('hover', i <= idx));
      });
      star.addEventListener('mouseleave', () => {
        stars.forEach(s => s.classList.remove('hover'));
      });
    });
  });
});

// ── QR Scanner ──
let qrScanner = null;

function initQRScanner(videoId, onResult) {
  if (typeof jsQR === 'undefined') {
    console.warn('jsQR not loaded');
    return;
  }
  const video = document.getElementById(videoId);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    .then(stream => {
      video.srcObject = stream;
      video.play();
      requestAnimationFrame(function tick() {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
          canvas.height = video.videoHeight;
          canvas.width = video.videoWidth;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const code = jsQR(imageData.data, imageData.width, imageData.height);
          if (code) { onResult(code.data); return; }
        }
        requestAnimationFrame(tick);
      });
    })
    .catch(err => console.error('Camera error:', err));
}

function markAttendance(userId, sessionId, lat, lon) {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  return fetch('/attendance/api/mark/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ user_id: userId, session_id: sessionId, latitude: lat, longitude: lon })
  }).then(r => r.json());
}

// ── Language switcher ──
function switchLanguage(lang) {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/i18n/set_language/';
  const csrf = document.createElement('input');
  csrf.type = 'hidden'; csrf.name = 'csrfmiddlewaretoken';
  csrf.value = document.querySelector('[name=csrfmiddlewaretoken]') ?
    document.querySelector('[name=csrfmiddlewaretoken]').value : getCookie('csrftoken');
  const langInput = document.createElement('input');
  langInput.type = 'hidden'; langInput.name = 'language'; langInput.value = lang;
  const next = document.createElement('input');
  next.type = 'hidden'; next.name = 'next'; next.value = window.location.pathname;
  form.appendChild(csrf); form.appendChild(langInput); form.appendChild(next);
  document.body.appendChild(form); form.submit();
}

function getCookie(name) {
  const val = `; ${document.cookie}`;
  const parts = val.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

// ── Chart helpers ──
function renderAttendanceChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === 'undefined') return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Attendance',
        data,
        backgroundColor: 'rgba(37,99,168,0.75)',
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } }
    }
  });
}
