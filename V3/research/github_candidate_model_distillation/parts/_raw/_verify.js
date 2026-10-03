// READ-ONLY existence verification. HTML (unmetered) + API /repos (may 403 if quota drained).
const slugs = process.argv.slice(2);
const H = { 'User-Agent': 'Mozilla/5.0 (readonly-audit)' };
(async () => {
  for (const s of slugs) {
    let html = 'ERR';
    try {
      const r = await fetch('https://github.com/' + s, { headers: H, redirect: 'follow' });
      html = String(r.status);
    } catch (e) { html = 'FETCHFAIL'; }
    let api = '?';
    try {
      const r2 = await fetch('https://api.github.com/repos/' + s, { headers: { 'User-Agent': 'ro', 'Accept': 'application/vnd.github+json' } });
      if (r2.ok) { const d = await r2.json(); api = '200 size=' + d.size + 'KB stars=' + d.stargazers_count + ' lang=' + d.language + ' pushed=' + d.pushed_at; }
      else api = String(r2.status);
    } catch (e) { api = 'FETCHFAIL'; }
    console.log([s, 'html=' + html, 'api=' + api].join('  |  '));
    await new Promise(s2 => setTimeout(s2, 400));
  }
})();
