// READ-ONLY GitHub API helper (no mutations). Usage: node _gh2.js <delayMs> <mode> <arg...>
// mode=search -> args are queries; mode=repo -> args are slugs; mode=readme -> args are slugs
const delayMs = Number(process.argv[2] || 8000);
const mode = process.argv[3];
const args = process.argv.slice(4);
const H = { 'User-Agent': 'readonly-audit', 'Accept': 'application/vnd.github+json' };

async function j(u) {
  const r = await fetch(u, { headers: H });
  const t = await r.text();
  if (!r.ok) return { __err: r.status, __body: t.slice(0, 300) };
  try { return JSON.parse(t); } catch { return { __raw: t.slice(0, 20000) }; }
}

(async () => {
  let first = true;
  for (const a of args) {
    if (!first) await new Promise(s => setTimeout(s, delayMs));
    first = false;
    if (mode === 'search') {
      const j1 = await j('https://api.github.com/search/repositories?q=' + encodeURIComponent(a) + '&sort=stars&per_page=12');
      if (j1.__err) { console.log('=== Q: ' + a + ' ERR ' + j1.__err); continue; }
      console.log('=== Q: ' + a + ' total=' + j1.total_count);
      for (const i of (j1.items || [])) console.log([i.full_name, i.stargazers_count, i.language || '-', (i.description || '').replace(/\s+/g, ' ').slice(0, 150)].join(' | '));
    } else if (mode === 'repo') {
      const r = await j('https://api.github.com/repos/' + a);
      if (r.__err) { console.log('=== REPO ' + a + ' ERR ' + r.__err); continue; }
      console.log('=== REPO ' + a + ' OK size=' + r.size + 'KB stars=' + r.stargazers_count + ' lang=' + r.language + ' pushed=' + r.pushed_at + ' default=' + r.default_branch);
      console.log('DESC: ' + (r.description || ''));
    } else if (mode === 'readme') {
      for (const br of ['main', 'master']) {
        const r = await fetch('https://raw.githubusercontent.com/' + a + '/' + br + '/README.md', { headers: { 'User-Agent': 'readonly-audit' } });
        if (r.ok) { console.log('=== README ' + a + ' (' + br + ')'); console.log((await r.text()).slice(0, 14000)); break; }
        if (br === 'master') console.log('=== README ' + a + ' NOT FOUND');
      }
    }
  }
})();
