#back up project files

import pathlib
import zipfile
import datetime

globs = [
    '*.py',
    'readme.txt',
    'glade/*',
    'locale/**/*',
]

execlude = [
    'vlc.py',
    '**/*~'
]

cwd = pathlib.Path(__file__).parent

execlude_paths = []
for c in execlude:
    execlude_paths.extend(cwd.glob(c))

fname = 'backup/tilfaz_{:%Y%m%d}.zip'.format(datetime.datetime.now())
with zipfile.ZipFile(fname, 'w', zipfile.ZIP_DEFLATED) as z:
    for c in globs:
        for f in cwd.glob(c):
            if f not in execlude_paths and f.is_file():
                print('adding', f)
                z.write(f.relative_to(cwd))

    
