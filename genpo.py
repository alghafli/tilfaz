#generate po translation files

from pathlib import Path
from collections import defaultdict
import subprocess

globs = [
    '*.py',
    'glade/*',
]

execlude = [
    'vlc.py',
    'genpo.py',
    'genmo.py',
    'bu.py',
    '*~',
    'glade/*~',
]

cwd = Path(__file__).parent.resolve()
locale_path = cwd / 'locale'
po_path = locale_path / 'po'

execlude_paths = []
for c in execlude:
    execlude_paths.extend(cwd.glob(c))

langs = sorted(
    [
        'ar',
    ]
)

print('languages:')
for c in langs:
    print('\t{}'.format(c))

files = []
for c in globs:
    files.extend([f for f in cwd.glob(c) if f not in execlude_paths])

files.sort()

print('files:')
print('\t', end='')
print(*[c.relative_to(cwd) for c in files], sep='\n\t')

fpath = po_path / 'tilfaz.pot'
try:
    print('generating pot file')
    subprocess.run(['xgettext', '-k_', '-kN_', '-ktranslate', '-o', str(fpath),
        '--from-code=utf-8'] + [str(c) for c in files], check=True)
except Exception as e:
    print(e.output)
else:
    lang_dirs = [po_path / c for c in langs]
    for c in lang_dirs:
        c.mkdir(parents=True, exist_ok=True)
        old_fpath = c / 'tilfaz.po'
        if old_fpath.exists():
            print('merging', old_fpath.relative_to(cwd))
            subprocess.run(['msgmerge', old_fpath, fpath, '-o', old_fpath], check=True)
        else:
            print('creating', old_fpath.relative_to(cwd))
            old_fpath.write_text(fpath.read_text())
