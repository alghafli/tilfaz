#generate mo translation files

from pathlib import Path
from collections import defaultdict
import subprocess

cwd = Path(__file__).parent.resolve()
locale_path = cwd / 'locale'
po_path = locale_path / 'po'
mo_path = locale_path / 'mo'

try:
    po_dirs = sorted([c for c in po_path.iterdir() if c.is_dir()])
    po_dirs.sort()
    mo_dirs = [mo_path / c.name / 'LC_MESSAGES' for c in po_dirs]
    for pod, mod in zip(po_dirs, mo_dirs):
        mod.mkdir(parents=True, exist_ok=True)
        po_fpath = pod / 'tilfaz.po'
        mo_fpath = mod / 'tilfaz.mo'
        mo_fpath.touch()
        print('creating {}'.format(mo_fpath.relative_to(cwd)))
        subprocess.run(['msgfmt', '-o', str(mo_fpath),
            str(po_fpath)], check=True)
except subprocess.CalledProcessError as e:
    print(type(e))
    print(e.output)

