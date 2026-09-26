"""Stage an allowlisted deployment, excluding credentials, datasets and test caches."""
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
stage = ROOT/'artifacts'/f'deploy-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
stage.mkdir(parents=True, exist_ok=False)
for name in ('src','public','backend','api','models'):
    shutil.copytree(ROOT/name, stage/name, ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pt'))
for name in ('package.json','package-lock.json','index.html','vite.config.ts','tsconfig.json','components.json','requirements.txt','pyproject.toml','.python-version','vercel.json','.vercelignore'):
    shutil.copy2(ROOT/name, stage/name)
print(stage)
