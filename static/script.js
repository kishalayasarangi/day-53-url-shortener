let currentShortUrl = '';
let currentQR = '';

async function shortenUrl() {
  const url = document.getElementById('urlInput').value.trim();
  const custom = document.getElementById('customCode').value.trim();

  if (!url) { alert('Please enter a URL!'); return; }

  try {
    const res = await fetch('/api/shorten', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, custom })
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Something went wrong!');
      return;
    }

    currentShortUrl = data.short_url;
    currentQR = data.qr;

    document.getElementById('resultCard').classList.remove('hidden');
    document.getElementById('resultShort').textContent = data.short_url;
    document.getElementById('resultOriginal').textContent = data.original_url;
    document.getElementById('qrCode').src = `data:image/png;base64,${data.qr}`;
    document.getElementById('visitBtn').onclick = () =>
      window.open(data.short_url, '_blank');
    document.getElementById('resultMeta').textContent =
      data.existing
        ? `⚡ Already shortened · ${data.clicks} click(s)`
        : `✅ New short URL created · 0 clicks so far`;

    document.getElementById('urlInput').value = '';
    document.getElementById('customCode').value = '';
    loadUrls();
  } catch(e) {
    alert('Failed to connect to server!');
  }
}

function copyShortUrl() {
  navigator.clipboard.writeText(currentShortUrl).then(() => {
    const btn = document.querySelector('.btn-copy');
    btn.textContent = '✅ Copied!';
    setTimeout(() => btn.textContent = '📋 Copy URL', 1500);
  });
}

function downloadQR() {
  const a = document.createElement('a');
  a.href = `data:image/png;base64,${currentQR}`;
  a.download = 'qr-code.png';
  a.click();
}

async function loadUrls() {
  try {
    const res = await fetch('/api/urls');
    const urls = await res.json();

    const tbody = document.getElementById('urlTableBody');
    if (urls.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No URLs yet — shorten one above!</td></tr>';
      document.getElementById('totalUrls').textContent = '0';
      document.getElementById('totalClicks').textContent = '0';
      document.getElementById('topClicks').textContent = '0';
      return;
    }

    const totalClicks = urls.reduce((s, u) => s + u.clicks, 0);
    const topClicks = Math.max(...urls.map(u => u.clicks));

    document.getElementById('totalUrls').textContent = urls.length;
    document.getElementById('totalClicks').textContent = totalClicks;
    document.getElementById('topClicks').textContent = topClicks;

    tbody.innerHTML = urls.map(u => `
      <tr>
        <td>
          <a class="code-link"
             href="/${u.short_code}" target="_blank">
            /${u.short_code}
          </a>
        </td>
        <td title="${u.original_url}">
          <a href="${u.original_url}" target="_blank"
             style="color:#a0a0b0;text-decoration:none;">
            ${u.original_url}
          </a>
        </td>
        <td><span class="click-badge">${u.clicks}</span></td>
        <td>${u.created_at?.slice(0, 10) || '—'}</td>
        <td>${u.last_clicked || 'Never'}</td>
        <td>
          <button class="del-btn"
                  onclick="deleteUrl('${u.short_code}')">✕</button>
        </td>
      </tr>`).join('');
  } catch(e) {
    console.error('Failed to load URLs', e);
  }
}

async function deleteUrl(code) {
  if (!confirm(`Delete /${code}?`)) return;
  await fetch(`/api/urls/${code}`, { method: 'DELETE' });
  loadUrls();
}

document.getElementById('urlInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') shortenUrl();
});

window.onload = () => loadUrls();