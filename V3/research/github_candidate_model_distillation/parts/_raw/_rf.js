// READ-ONLY raw fetch of specific paths: node _rf.js <slug> <branch> <path> [<path>...]
const slug = process.argv[2], br = process.argv[3];
const paths = process.argv.slice(4);
(async () => {
  for (const p of paths) {
    const r = await fetch('https://raw.githubusercontent.com/' + slug + '/' + br + '/' + p, { headers: { 'User-Agent': 'ro' } });
    if (!r.ok) { console.log('--- ' + p + ' ERR ' + r.status); continue; }
    const t = await r.text();
    console.log('--- FILE ' + p + ' (' + t.length + ' bytes) ---');
    console.log(t.slice(0, 12000));
  }
})();
