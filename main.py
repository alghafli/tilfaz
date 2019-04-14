import os
import pathlib
import locale
import db, utils
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tilfaz import Tilfaz
import codi
import json
import ctypes
import appdirs

DEFAULT_CONFIG = {'language': 'en', 'max_n': 100, 'vid_font_family': 'Sans',
    'vid_font_size': 60, 'vid_font_weight': 'bold', 'vid_font_style': 'normal',
    'vid_font_color': '#ffffff', 'vid_background_color': '#000000',
    'vid_side_margin': 0, 'vid_top_bottom_margin': 0, 'video_monitor': 0}

N_ = lambda w: w

N_('normal')
N_('repeat')
N_('random')

config_dirs = [pathlib.Path(__file__).parent]
portable_config = pathlib.Path(__file__).parent / 'tilfaz.cfg'
if not portable_config.exists():
    config_dirs.insert(0, appdirs.user_config_dir('tilfaz', 'mhghafli'))

cdirs = codi.Codi(*config_dirs)

config = codi.Config()
for c in DEFAULT_CONFIG:
    config.set_default(c, DEFAULT_CONFIG[c])

try:
    config.update(json.loads(cdirs.read('tilfaz.cfg')))
except Exception:
    pass

os.putenv('LANGUAGE', config['language'])
mo_path = pathlib.Path(__file__).parent / 'locale' / 'mo'
locale.bindtextdomain('tilfaz', mo_path)
locale.textdomain('tilfaz')

cdirs.path('tilfaz.db', writable=True).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine('sqlite:///{}'.format(cdirs.path('tilfaz.db', writable=True)))
db.Base.metadata.create_all(engine)
Sessionmaker = sessionmaker(bind=engine)
session = Sessionmaker()

s = Tilfaz(Sessionmaker)

ctypes.cdll.LoadLibrary('libX11.so.6').XInitThreads()

import gui
try:
    gui.do_main(Sessionmaker, s, config, cdirs)
except Exception as e:
    print(e)
    s.stop()
    raise

try:
    cdirs.write('tilfaz.cfg', json.dumps(config))
except Exception:
    pass
