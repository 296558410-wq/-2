import re
src=open(r'C:\AIQuant\research\hermes\trader_v1\engine.py',encoding='utf-8',errors='replace').read()
for kw in ['--decide','decisions','glob','newest','register','def main','consume','TRIGGER','trigger_condition']:
    idxs=[m.start() for m in re.finditer(re.escape(kw),src)][:6]
    print('###',kw,idxs)
