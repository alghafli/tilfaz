import db
import datetime
import queue
from threading import Thread, Timer
import sqlalchemy
import sqlalchemy.event
import vlc
import sys
import time
import pathlib

class Tilfaz:
    __signals__ = [
            'media-changed',
            'paused',
            'before-play',
            'played',
            'position-changed',
            'stopped',
            'media-list-changed',
            'list-ended',
        ]
    def __init__(self, Sessionmaker, instance=None, daemon=False, max_media=100):
        self.Sessionmaker = Sessionmaker
        if instance is None:
            instance = vlc.Instance()
        
        self.listeners = {}
        for c in type(self).__signals__:
            self.listeners[c] = []
        
        self.list = instance.media_list_new()
        # self.fblist = []
        self.player = instance.media_player_new()
        self.list_player = instance.media_list_player_new()
        
        self.is_started = False
        self.queue = queue.Queue()
        self.thread = Thread(target=self.do_start, daemon=daemon)
        self.session = None
        self.next_check = datetime.datetime.now()
        self.max_media = max_media
        
        self.list_player.set_media_list(self.list)
        self.list_player.set_media_player(self.player)
        
        event_manager = self.player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self.on_media_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self.on_paused)
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self.on_played)
        event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self.on_position_changed)
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_end_reached)
        event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self.on_stopped)
        event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_error)
        
        event_manager = self.list.event_manager()
        event_manager.event_attach(vlc.EventType.MediaListItemAdded, self.on_media_list_changed)
        event_manager.event_attach(vlc.EventType.MediaListItemDeleted, self.on_media_list_changed)
    
    def on_end_reached(self, event=None):
        self.emit('stopped')
        print('end reached')
    
    def on_error(self, event=None):
        print('on error')
        self.on_end_reached()
    
    def on_media_list_changed(self, event=None):
        print('media list changed')
        self.emit('media-list-changed')
        self.check_media()
    
    def on_media_changed(self, event=None):
        self.emit('media-changed')
        md = self.player.get_media()
        idx = self.list.index_of_item(md)
        if idx > 0:
            Thread(target=self.pop_media).start()
    
    def on_paused(self, event=None):
        self.emit('paused')
    
    def on_played(self, event=None):
        self.emit('played')
    
    def on_position_changed(self, event=None):
        self.emit('position-changed')
    
    def on_stopped(self, event=None):
        #apparantly, this condition is always true for when the player is
        #attached to a media list player, which is the case here
        #this condition is checked just because i am not sure of vlc
        #MediaPlayerStopped event behaviour
        if len(self.list) == 1:
            self.pop_media()
        self.emit('stopped')
    
    def check_media(self):
        if len(self.list) > 0 and not self.player.is_playing():
            self.play()
        elif len(self.list) <= 0:
            self.emit('list-ended')
    
    @property
    def playlist(self):
        return [c.get_mrl() for c in self.list]
    
    @property
    def current_media(self):
        return self.player.get_media()
    
    @property
    def position(self):
        return self.player.get_time() / 1000
    
    @property
    def duration(self):
        return self.player.get_media().get_duration() / 1000
    
    @property
    def ratio(self):
        return self.position / self.duration
    
    @property
    def percentage(self):
        return int(100 * self.ratio)
    
    def do_start(self):
        print('starting tilfaz')
        
        self.empty_queue()
        self.session = self.Sessionmaker()
        
        for c in ['after_insert', 'after_update', 'after_delete']:
            sqlalchemy.event.listen(db.Program, c, self.after_db_update)
        
        while self.is_started:
            print('checking')
            now = datetime.datetime.now()
            db.update_programs_time(self.session,
                now-datetime.timedelta(seconds=60))
            
            parent_program = sqlalchemy.orm.aliased(db.Program)
            root_cond = sqlalchemy.and_(db.Program.linked_to_id == None,
                db.Program.stopped == False, db.Program.next_datetime <= now)
            sub_cond = sqlalchemy.and_(db.Program.linked_to_id != None,
                parent_program.stopped == False, db.Program.next_datetime <= now)
            
            q = self.session.query(db.Program).filter(
                    sqlalchemy.or_(root_cond, sub_cond)
                ).outerjoin(
                    parent_program, parent_program.id == db.Program.linked_to_id
                ).order_by(
                    db.Program.next_datetime,
                    db.Program.name
                )
            
            new_list = []
            print('found', q.count(), 'programs to play')
            for c in q:
                try:
                    files = c.next(True)
                    if c.opening or c.ending:
                        opening = pathlib.Path(c.dir) / c.opening
                        ending = pathlib.Path(c.dir) / c.ending
                        idx = 0
                        while idx < len(files):
                            if c.opening:
                                files.insert(idx, opening)
                                idx += 1
                            if c.ending:
                                files.insert(idx+1, ending)
                                idx += 1
                            idx += 1
                    new_list.extend([str(path) for path in files])
                except Exception as e:
                    print('could not get next files from {}:'.format(c),
                        e)
                c.advance()
            
            db.commit_session(self.session)
            
            if new_list:
                print(new_list)
                self.append_media(new_list)
            
            now = datetime.datetime.now()
            next_program = db.next_check(self.session)
            if next_program is not None:
                self.next_check = next_program.next_datetime
            else:
                self.next_check = None
            
            if self.next_check is None:
                print('no new programs')
                self.next_check = (now + datetime.timedelta(
                    seconds=60)).replace(second=0, microsecond=0)
            
            print('will check in', self.next_check - now)
            
            try:
                delay = self.remaining(now).total_seconds()
                delay = max(delay, 0)
                while self.is_started:
                    f = self.queue.get(timeout=delay)
                    if f is not None:
                        try:
                            if callable(f):
                                f()
                            else:
                                f[0](*f[1], **f[2])
                        except Exception as e:
                            print('error {}: {}'.format(type(e).__name__, e))
                    else:
                        break
                    delay = 0
            except queue.Empty:
                pass
        
        for c in ['after_insert', 'after_update', 'after_delete']:
            sqlalchemy.event.remove(db.Program, c, self.after_db_update)
        
        print('stopping')
        
        self.session.close()
        self.session = None
    
    def start(self, daemon=False):
        if not self.is_running:
            self.is_started = True
            self.thread = Thread(target=self.do_start, daemon=daemon)
            self.thread.start()
    
    def play(self):
        if len(self.list) > 0 and not self.player.is_playing():
            self.emit('before-play')
            Timer(1, self.do_play).start()
    
    def do_play(self):
        self.next()
        self.player.play()
    
    def stop_player(self):
        self.player.stop()
    
    def pause_player(self):
        self.player.pause()
    
    def play_player(self):
        self.player.play()
    
    def forward_player(self):
        self.stop_player()
        self.pop_media()
        self.next()
    
    def do_stop(self):
        self.stop_player()
        self.is_started = False
    
    def stop(self):
        self.queue.put(self.do_stop)
    
    def call(self, f, delay=0):
        Thread(target=self.do_call, args=(f, delay), daemon=True).start()
            
    def do_call(self, f, delay=0):
        if delay > 0:
            time.sleep(delay)
        self.queue.put(f)
    
    @property
    def is_running(self):
        return self.thread.is_alive()
    
    def append_media(self, new_list):
        for c in new_list:
            if len(self.list) < self.max_media:
                # self.fblist.append(c)
                self.list.add_media(c)
            else:
                print('will have too many media to play. ignoring `{}`'.format(
                    c))
    
    def pop_media(self):
        # self.fblist.pop(0)
        if len(self.list) > 0:
            self.list.remove_index(0)
    
    def clear_media(self):
        while len(self.list):
            self.pop_media(0)
    
    def empty_queue(self, q=None):
        if q == None:
            q = self.queue
        try:
            while True:
                q.get(False)
        except queue.Empty:
            pass
    
    def after_db_update(self, *args):
        self.update()
    
    def update(self):
        self.queue.put(None)
    
    def remaining(self, now=None):
        if now is None:
            now = datetime.datetime.now()
        return self.next_check - now
    
    def listen(self, signal, f, *args, **kwargs):
        self.listeners[signal].append((f, args, kwargs))
    
    def unlisten(self, signal, f, *args, **kwargs):
        index = self.listeners[signal].index((f, args, kwargs))
        self.listeners[signal].pop(index)
    
    def unlisten_function(self, signal, f):
        c = 0
        while c < len(self.listeners[signal]):
            if self.listeners[signal][c][0] == f:
                self.unlisten(self.listeners[signal][c])
            else:
                c += 1
    
    def unlisten_all(self, signal):
        while self.listener[signal]:
            f, args, kwargs = self.listener[signal][-1]
            self.unlisten(f, *args, **kwargs)
    
    def emit(self, signal):
        if signal not in type(self).__signals__:
            raise RuntimeError('invalid signal: `{}`'.format(signal))
        for c in self.listeners[signal]:
            f, args, kwargs = c
            f(self, *args, **kwargs)
    
    def set_wid(self, wid):
        if sys.platform == 'win32':
            self.player.set_hwnd(wid)
        else:
            self.player.set_xwindow(wid)
    
    def next(self):
        self.do_next()
    
    def do_next(self):
        # self.player.set_mrl(self.fblist[0])
        if len(self.list) > 0:
            self.list_player.play_item_at_index(0)
