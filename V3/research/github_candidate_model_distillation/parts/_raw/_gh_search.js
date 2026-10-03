// READ-ONLY GitHub search helper. No mutations.
const queries = process.argv.slice(2);
const H = { 'User-Agent': 'readonly-audit', 'Accept': 'application/vnd.github+json' };

async function g(u) {
  const r = await fetch(u, { headers: H });
  if (!r.ok) throw new Error(u + ' -> ' + r.status);
  return r.json();
}

(async () => {
  for (const q of queries) {
    try {
      const j = await g('https://api.github.com/search/repositories?q=' + encodeURIComponent(q) + '&sort=stars&per_page=12');
      console.log('=== QUERY: ' + q + '  total=' + j.total_count);
      for (const i of (j.items || [])) {
        console.log([i.full_name, i.stargazers_count, (i.language || '-'), (i.description || '').replace(/\s+/g, ' ').slice(0, 150)].join(' | '));
      }
    } catch (e) {
      console.log('=== QUERY: ' + q + '  ERROR ' + e.message);
    }
    await new Promise(s => setTimeout(s, 1200));
  }
})();
