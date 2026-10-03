// READ-ONLY raw.githubusercontent fetcher. Writes per-repo dumps. No API rate limit.
const fs = require('fs');
const path = require('path');
const OUT = 'C:\\AIQuant\\research\\hermes\\trader_v3\\research\\github_candidate_model_distillation\\parts\\_raw';
fs.mkdirSync(OUT, { recursive: true });
const slugs = process.argv.slice(2);
const H = { 'User-Agent': 'readonly-audit' };
const BRANCHES = ['main', 'master'];
const PATHS = [
  'README.md', 'readme.md', 'README.rst', 'README.txt', 'docs/README.md',
  'requirements.txt', 'pyproject.toml', 'src/README.md',
];

async function tryFetch(u) {
  try {
    const r = await fetch(u, { headers: H, redirect: 'follow' });
    if (!r.ok) return null;
    return await r.text();
  } catch { return null; }
}

(async () => {
  for (const s of slugs) {
    const safe = s.replace(/[^a-zA-Z0-9._-]/g, '_');
    const out = [];
    let foundBranch = null, readme = null;
    for (const b of BRANCHES) {
      for (const p of PATHS) {
        const t = await tryFetch('https://raw.githubusercontent.com/' + s + '/' + b + '/' + p);
        if (t) { readme = t; foundBranch = b; out.push('### FILE ' + p + '\n' + t); break; }
      }
      if (readme) break;
    }
    // tree listing via codeload-free approach: github html is heavy; instead try common code paths
    const codePaths = [
      'main.py', 'strategy.py', 'config.py', 'simulator.py', 'execution.py',
      'src/main.py', 'src/strategy.py', 'backtest.py', 'engine.py',
      'src/execution.py', 'src/simulator.py', 'spread.py', 'src/features.py',
      'market_maker.py', 'src/market_maker.py', 'src/backtest.py',
      'src/engine.py', 'src/costs.py', 'costs.py', 'signals.py', 'src/signals.py',
    ];
    if (foundBranch) {
      for (const p of codePaths) {
        const t = await tryFetch('https://raw.githubusercontent.com/' + s + '/' + foundBranch + '/' + p);
        if (t) out.push('### CODE ' + p + '\n' + t.slice(0, 30000));
      }
    }
    const body = (foundBranch ? '' : '<<NO README FOUND -- repo may not exist or has no readme>>\n') + out.join('\n\n');
    fs.writeFileSync(path.join(OUT, safe + '.txt'), body);
    console.log('DUMP ' + s + ' branch=' + (foundBranch || 'NONE') + ' bytes=' + body.length);
  }
})();
