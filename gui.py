import os
import threading

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
import sqlalchemy
import utils
import db
import pathlib
import datetime
import display
import gettext
import locale
import re
import urllib.parse

search_filter = None
edited_program = db.Program()
edited_subprogram = None
label_css = Gtk.CssProvider()
vid_win_css = Gtk.CssProvider()

class Handler:
    next_page_callback_id = None
    next_page_thumb_path = None
    next_page_thumb_mtime = datetime.datetime.utcfromtimestamp(0)
    
    def on_main_win_destroy(*args):
        Gtk.main_quit()
        
    def on_search_entry_activate(entry):
        ui.get_object('search_popover').popdown()
    
    def on_search_radio_toggled(button):
        if button.get_active():
            global search_filter
            
            if button is ui.get_object('search_radio_all'):
                search_filter = None
            elif button is ui.get_object('search_radio_running'):
                search_filter = db.Program.stopped == False
            elif button is ui.get_object('search_radio_stopped'):
                search_filter = db.Program.stopped == True
            
            populate_search_tree()
    
    def on_search_popover_hide(popover):
        populate_search_tree()
    
    def on_edit_program_clicked(button):
        selection = ui.get_object('search_selection')
        model, selected = selection.get_selected()
        
        if selected is not None:
            global edited_program
            edited_program = session.query(db.Program).get(model[selected][0])
            populate_program_edit()
            stack = ui.get_object('toplevel_stack')
            stack.set_visible_child_name('edit')
        
    def on_add_program_clicked(button):
        global edited_program
        edited_program = db.Program(name='', dir='',
            days=utils.Weekdays(datetime.time(), 0), mode='normal', n=1,
            opening='', ending='', stopped=False, last_file='', last_files=[],
            next_datetime=datetime.datetime.now() + datetime.timedelta(days=1))
        
        populate_program_edit()
        stack = ui.get_object('toplevel_stack')
        stack.set_visible_child_name('edit')
    
    def on_edit_delete_clicked(button):
        if edited_program.id is not None:
            db.delete_program(edited_program)
            populate_search_tree()
            
        ui.get_object('toplevel_stack').set_visible_child_name('main')
    
    def on_edit_cancel_clicked(button):
        populate_program_edit()
        
    def on_edit_apply_clicked(button):
        global edited_program
        
        name = ui.get_object('name_entry').get_text()
        dir = ui.get_object('dir_entry').get_text()
        
        hour = int(ui.get_object('hour_entry').get_text())
        minute = int(ui.get_object('minute_entry').get_text())
        t = datetime.time(hour=hour, minute=minute)
        
        grid = ui.get_object('days_grid')
        day_values = [c.value for c in grid.get_children() if c.get_active()]
        
        if ui.get_object('period_button').get_active():
            days = utils.Monthdays(t, *day_values)
        else:
            days = utils.Weekdays(t, *day_values)
        
        mode = ui.get_object('mode_combo').get_active_id()
        n = ui.get_object('n_spinbutton').get_value_as_int()
        stopped = ui.get_object('stopped_checkbutton').get_active()
        last_file = ui.get_object('last_file_combo').get_child().get_text()
        opening = ui.get_object('opening_combo').get_child().get_text()
        ending = ui.get_object('ending_combo').get_child().get_text()
        edited_program = db.edit_program_no_commit(program=edited_program.id, name=name,
            dir=dir, days=days, mode=mode, n=n, opening=opening, ending=ending,
            stopped=stopped, last_file=last_file, session=session)
        
        model = ui.get_object('programs_liststore')
        subprogram_ids = []
        for c in model:
            if c[0]:
                subprogram_ids.append(c[0])
        
        #!= null filter to make sure main programs are not deleted
        #if removed and we are adding a new program, this query will return all
        #main programs and all programs will be deleted in the following loop
        subprograms = session.query(db.Program).filter(
            db.Program.linked_to_id != None,
            db.Program.linked_to_id == edited_program.id)
        if subprogram_ids:
            subprograms = subprograms.filter(db.Program.id.notin_(subprogram_ids))
        
        for c in subprograms:
            session.delete(c)
        
        for c in model:
            hour, minute = c[2], c[3]
            t = datetime.time(hour=hour, minute=minute)
            
            day_values = [int(d) for d in c[4].split(',')]
            if c[1] == 'monthly':
                days = utils.Monthdays(t, *day_values)
            else:
                days = utils.Weekdays(t, *day_values)
            
            mode = c[5]
            n = c[6]
            linked_to = edited_program
            stopped = c[7]
            db.edit_program_no_commit(program=c[0], name=name, dir=dir,
                days=days, mode=mode, n=n, linked_to=linked_to, stopped=stopped,
                session=session)
        
        db.commit_session(session)
        
        thumb = ui.get_object('edit_thumb').path
        if thumb is not None:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(thumb), 512, 512)
                thumb_path = pathlib.Path(dir) / '__thumb__.png'
                pixbuf.savev(str(thumb_path), 'png', [], [])
            except Exception as e:
                thumb_path = None
                print(e)
        else:
            thumb_path = None
        
        try:
            old_thumbs = pathlib.Path(edited_program.dir).glob('__thumb__.*')
            for c in old_thumbs:
                if c != thumb_path:
                    c.unlink()
        except Exception as e:
            print(e)
        
        populate_search_tree()
        ui.get_object('toplevel_stack').set_visible_child_name('main')
    
    def on_subprogram_add_clicked(button):
        global edited_subprogram
        
        edited_subprogram = db.Program(days=utils.Weekdays(datetime.time(), 0),
            mode='normal', n=1, stopped=False, last_file='', last_files=[],
            next_datetime=datetime.datetime.now() + datetime.timedelta(days=1))
        
        ui.get_object('subprogram_edit_popover').popup()
        
    def on_subprogram_edit_clicked(button=None):
        global edited_subprogram
        
        model, row = ui.get_object('subprograms_selection').get_selected()
        if row is not None:
            row = model[row]
            id_ = str(row.path)
            linked_to = edited_program
            hour, minute = row[2], row[3]
            
            try:
                day_values = [int(c) for c in row[4].split(',')]
            except Exception:
                if row[1] == 'monthly':
                    day_values = [1]
                else:
                    day_values = [0]
            
            if row[1] == 'monthly':
                days = utils.Monthdays(
                    datetime.time(hour=hour, minute=minute), *day_values)
            else:
                days = utils.Weekdays(
                    datetime.time(hour=hour, minute=minute), *day_values)
            
            mode = row[5]
            n = row[6]
            stopped = row[7]
            
            edited_subprogram = db.Program(id=id_, days=days, mode=mode, n=n,
                stopped=stopped, last_file='', last_files=[],
                next_datetime=datetime.datetime.now())
            ui.get_object('subprogram_edit_popover').popup()
        
    def on_subprogram_delete_clicked(button):
        model, row = ui.get_object('subprograms_selection').get_selected()
        if row is not None:
            del model[row]
    
    def on_subprogram_edit_apply_clicked(button):
        global edited_subprogram
        
        model = ui.get_object('programs_liststore')
        if edited_subprogram.id is None:
            itr = model.append(14*[None])
            edited_subprogram.id = model[itr].path
        try:
            edit_subprograms_tree_row(model[edited_subprogram.id])
        except Exception as e:
            print('faild to edit subprogram', e, sep='\n')
            return
        
        ui.get_object('subprogram_edit_popover').popdown()
    
    def on_subprogram_edit_cancel_clicked(button):
        ui.get_object('subprogram_edit_popover').popdown()
    
    def on_edit_back_clicked(button):
        ui.get_object('toplevel_stack').set_visible_child_name('main')
    
    def on_period_button_toggled(button):
        global edited_subprogram
        if button is ui.get_object('period_button'):
            grid = ui.get_object('days_grid')
            edited_subprogram = edited_program
        else:
            grid = ui.get_object('subprogram_days_grid')
    
        if not button.get_active():
            button.set_label(_('Weekly'))
            days_type = utils.Weekdays
            days = range(7)
        else:
            button.set_label(_('Monthly'))
            days_type = utils.Monthdays
            days = range(1, 32)
        
        for c in grid.get_children():
            c.destroy()
        
        day_values = edited_subprogram.days.days
        
        row = 0
        column = 0
        for c in days:
            if days_type is utils.Weekdays:
                check = Gtk.CheckButton.new_with_label(_(utils.wd[c]))
            else:
                check = Gtk.CheckButton.new_with_label(str(c))
            
            check.value = c
            if type(edited_subprogram.days) is days_type and c in day_values:
                check.set_active(True)
            
            grid.attach(check, row, column, 1, 1)
            row += 1
            if row >= 7:
                row = 0
                column += 1
        
        grid.show_all()
    
    def on_subprogram_edit_popover_show(popover):
        populate_subprogram_popover()
    
    def on_is_stopped_cell_toggled(renderer, path):
        model = ui.get_object('programs_liststore')
        model[path][7] = not model[path][7]
        
        if model[path][7]:
            bgcolor = 'light grey'
        else:
            bgcolor = None
        
        model[path][13] = bgcolor
    
    def on_dir_edit_button_clicked(button):
        dial = ui.get_object('program_dir_dialog')
        entry = ui.get_object('dir_entry')
        
        try:
            path = pathlib.Path(entry.get_text()) / '__some_file__'
            dial.set_filename(str(path))
        except Exception as e:
            print(e)
        
        response = dial.run()
        if response == Gtk.ResponseType.OK:
            fname = dial.get_filename()
            entry.set_text(fname)
        
        dial.hide()
        
    def on_edit_thumb_clicked(button):
        dial = ui.get_object('thumb_open_dialog')
        entry = ui.get_object('dir_entry')
        
        try:
            path = pathlib.Path(entry.get_text()) / '__some_file__'
            dial.set_filename(str(path))
        except Exception as e:
            print(e)
        
        response = dial.run()
        if response == Gtk.ResponseType.OK:
            fname = dial.get_filename()
            try:
                thumb = GdkPixbuf.Pixbuf.new_from_file_at_size(fname, 128, 128)
            except:
                thumb = None
            
            thumb_image = ui.get_object('edit_thumb')
            thumb_image.set_from_pixbuf(thumb)
            thumb_image.path = pathlib.Path(fname)
        elif response == Gtk.ResponseType.REJECT:
            thumb_image = ui.get_object('edit_thumb')
            thumb_image.set_from_pixbuf(None)
            thumb_image.path = None
        
        dial.hide()
    
    def on_subprograms_treeview_row_activated(tree, path, column):
        Handler.on_subprogram_edit_clicked()
        ui.get_object('subprogram_edit_popover').popup()
    
    def on_before_play(tilfaz=None):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            ui.get_object('vid_drawingarea').queue_draw)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            ui.get_object('vid_stack').set_visible_child_name, 'vid_page')
    
    def on_list_ended(tilfaz=None):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            Handler.go_to_next_page)
    
    def go_to_next_page():
        ui.get_object('vid_stack').set_visible_child_name('next_page')
    
    def on_vid_stack_visible_child_notify(widget, *args):
        if Handler.next_page_callback_id is not None:
            GLib.source_remove(Handler.next_page_callback_id)
            Handler.next_page_callback_id = None
        
        if widget.get_visible_child_name() == 'next_page':
            Handler.update_next_program_page()
    
    def on_vid_drawingarea_draw(widget, cr):
        x1, y1, x2, y2 = cr.clip_extents()
        
        cr.set_source_rgb(0, 0, 0)
        cr.move_to(x1, y1)
        cr.line_to(x1, y2)
        cr.line_to(x2, y2)
        cr.line_to(x2, y1)
        cr.line_to(x1, y1)
        cr.fill()
    
    def on_stop_button_clicked(widget):
        tilfaz.stop_player()
    
    def on_pause_button_clicked(widget):
        tilfaz.pause_player()
    
    def on_play_button_clicked(widget):
        tilfaz.play_player()
    
    def on_forward_button_clicked(widget):
        tilfaz.forward_player()
    
    def on_playlist_file_edit_button_clicked(widget):
        dial = ui.get_object('open_dialog')
        
        response = dial.run()
        if response == Gtk.ResponseType.OK:
            fname = dial.get_filename()
            ui.get_object('playlist_file_entry').set_text(fname)
        
        dial.hide()
    
    def on_playlist_file_add_button_clicked(widget):
        fname = ui.get_object('playlist_file_entry').get_text()
        if fname:
            tilfaz.append_media([fname])
    
    def on_vid_drawingarea_realize(widget):
        widget.get_window().ensure_native()
    
    def on_vid_win_realize(widget):
        if config['video_monitor'] is None:
            config['video_monitor'] = 0
        try:
            display.fullscreen_on_monitor(widget, config['video_monitor'])
        except Exception:
            pass
        win = widget.get_window()
        cursor = Gdk.Cursor.new_for_display(
            win.get_display(), Gdk.CursorType.BLANK_CURSOR)
        win.set_cursor(cursor)
    
    def init_gui(*args):
        #this should be set on glade file. however, i did not see the option to
        #do it.
        ui.get_object('program_time_box').set_direction(Gtk.TextDirection.LTR)
        ui.get_object('subprogram_time_box').set_direction(
            Gtk.TextDirection.LTR)
        
        lang_combo = ui.get_object('config_language_combo')
        locale_dir = cdirs.path('locale/mo/')
        for c in [c for c in locale_dir.glob('*') if c.is_dir()]:
            lang_combo.append_text(c.name)
        
        lang_combo.get_child().set_text(
            config['language'])
        ui.get_object('config_max_n_spin').set_value(config['max_n'])
        ui.get_object('config_font_button').set_font(
            '{0[vid_font_family]} {0[vid_font_size]}px'.format(config))
        ui.get_object('config_font_wieght_combo').set_active_id(
            config['vid_font_weight'])
        ui.get_object('config_font_style_combo').set_active_id(
            config['vid_font_style'])
        ui.get_object('config_side_margin_spin').set_value(
            config['vid_side_margin'])
        ui.get_object('config_top_bottom_margin_spin').set_value(
            config['vid_top_bottom_margin'])
        
        color = config['vid_font_color']
        color = [int(color[c:c+2], 16) / 255 for c in range(1, len(color), 2)]
        ui.get_object('config_font_color_button').set_rgba(
            Gdk.RGBA(*color, 1))
        
        color = config['vid_background_color']
        color = [int(color[c:c+2], 16) / 255 for c in range(1, len(color), 2)]
        ui.get_object('config_vid_background_color_button').set_rgba(
            Gdk.RGBA(*color, 1))
        
        print('init vid')
        
        for c in ['after_insert', 'after_update', 'after_delete']:
            sqlalchemy.event.listen(db.Program, c, Handler.after_db_update)
            sqlalchemy.event.listen(db.Program, c, Handler.update_next_program_status_bar)
        
        Handler.do_after_db_update()
        
        vid_draw = ui.get_object('vid_drawingarea')
        vid_draw.realize()
        tilfaz.set_wid(display.get_wid(vid_draw.get_window()))
        tilfaz.listen('before-play', Handler.on_before_play)
        tilfaz.listen('list-ended', Handler.on_list_ended)
        tilfaz.listen('position-changed', Handler.on_vid_position_changed)
        tilfaz.listen('media-list-changed', Handler.on_media_list_changed)
        tilfaz.start()
    
    def on_media_list_changed(*args, **kwargs):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            Handler.update_playlist_liststore)
    
    def update_playlist_liststore(*args, **kwargs):
        model = ui.get_object('playlist_liststore')
        model.clear()
        files = [pathlib.Path('/') / c.split(':', 1)[1].strip('/')
            for c in tilfaz.playlist]
        for c in files:
            print(c)
            print(c.name)
            model.append([urllib.parse.unquote(c.name)])
    
    def uninit_gui(*args):
        print('unint vid')
        tilfaz.stop()
        tilfaz.unlisten('before-play', Handler.on_before_play)
        tilfaz.unlisten('list-ended', Handler.on_list_ended)
        tilfaz.unlisten('position-changed', Handler.on_vid_position_changed)
        tilfaz.unlisten('media-list-changed', Handler.on_media_list_changed)
        
        for c in ['after_insert', 'after_update', 'after_delete']:
            sqlalchemy.event.remove(db.Program, c, Handler.after_db_update)
    
    def after_db_update(*args):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            Handler.do_after_db_update)
    
    def do_after_db_update():
        if Handler.next_page_callback_id is not None:
            print('removing', GLib.source_remove(Handler.next_page_callback_id))
        
        session.expire_all()
        Handler.update_next_program_page()
        Handler.do_update_next_program_status_bar()
    
    def update_next_program_page():
        Handler.next_page_callback_id = None
        next_program = db.next_check(session)
        now = datetime.datetime.now()
        
        if next_program is None:
            tl = ''
            pl = ''
            al = ''
            th = None
            nc = None
            thumb = None
            th = None
        else:
            next_time = next_program.next_datetime
            dif = next_time - now
            if next_program.linked_to is not None:
                program = next_program.linked_to
            else:
                program = next_program
            
            pl = program.name
            try:
                thumb = sorted(
                    pathlib.Path(program.dir).glob('__thumb__.*'))[0]
                th = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    str(thumb), 512, 512)
            except Exception:
                thumb = None
                th = None
            
            if dif > datetime.timedelta(days=1):
                tl = _('{:%d/%m/%Y}').format(next_time)
                al = ngettext('After one days',
                    'After {} days', dif.days).format(dif.days)
                nc = (now.replace(hour=0, minute=0, second=0, microsecond=0) +
                    datetime.timedelta(days=1) - now).total_seconds()
                nc = max(nc, 1)
            elif dif > datetime.timedelta(seconds=60):
                tl = '{:%H:%M}'.format(next_time)
                ds = round(dif.total_seconds())
                dh = ds // 3600
                dm = ds // 60 % 60
                al = _('After {:02}:{:02}').format(dh, dm)
                nc = (now.replace(second=0, microsecond=0) +
                    datetime.timedelta(seconds=60) - now).total_seconds()
                nc = max(nc, 1)
            else:
                tl = '{:%H:%M}'.format(next_time)
                ds = round(dif.total_seconds())
                ds = max(ds, 0)
                al = ngettext('After one second',
                    'After {} seconds', ds).format(ds)
                nc = (now.replace(microsecond=0) +
                    datetime.timedelta(seconds=1) - now).total_seconds()
                nc = max(nc, 1)
        
        tl = replace_numerals(tl)
        pl = replace_numerals(pl)
        al = replace_numerals(al)
        
        if ui.get_object('time_label').get_label() != tl:
            ui.get_object('time_label').set_label(tl)
        if ui.get_object('program_label').get_label() != pl:
            ui.get_object('program_label').set_label(pl)
        if ui.get_object('timedelta_label').get_label() != al:
            ui.get_object('timedelta_label').set_label(al)
        
        if (thumb != Handler.next_page_thumb_path or
                thumb is not None and
                thumb.stat().st_mtime != Handler.next_page_thumb_mtime):
            if thumb is not None:
                try:
                    th = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        str(thumb), 512, 512)
                except Exception:
                    th = None
            
            if th is not None:
                Handler.next_page_thumb_path = thumb
                Handler.next_page_thumb_mtime = thumb.stat().st_mtime
            else:
                Handler.next_page_thumb_path = None
                Handler.next_page_thumb_mtime = datetime.datetime.utcfromtimestamp(0)
            ui.get_object('next_thumb').set_from_pixbuf(th)
        
        if nc is not None:
            Handler.next_page_callback_id = Gdk.threads_add_timeout(
                GLib.PRIORITY_DEFAULT, 1000 * nc,
                Handler.update_next_program_page)
    
    def update_next_program_status_bar(*args):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
            Handler.do_update_next_program_status_bar)
    
    def do_update_next_program_status_bar():
        program = session.query(db.Program).order_by(db.Program.next_datetime).first()
        if program is not None:
            if program.linked_to is not None:
                name = program.linked_to.name
            else:
                name = program.name
            
            t = program.next_datetime
            
            txt = _('Next: <i>{}</i> on <b>{:%Y-%m-%d %H:%M}</b>')
            txt = txt.format(name, t)
        else:
            txt = ''
        
        ui.get_object('next_program_status_bar').set_label(txt)
    
    def on_dir_entry_changed(entry):
        print('checking thumb')
        if entry.get_text():
            try:
                print('not emptry dir')
                thumb_path = pathlib.Path(entry.get_text()).resolve()
                print(sorted(thumb_path.glob('__thumb__.*')))
                thumb_path = sorted(thumb_path.glob('__thumb__.*'))[0]
                thumb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(thumb_path), 128, 128)
                path = thumb_path
            except Exception as e:
                print('exception')
                print(e)
                thumb = None
                path = None
        else:
            print('empty dir')
            thumb = None
            path = None
        
        thumb_image = ui.get_object('edit_thumb')
        thumb_image.set_from_pixbuf(thumb)
        thumb_image.path = path
        
        populate_last_file_combo()
    
    def on_vid_position_changed(s):
        scale = ui.get_object('vid_position_scale')
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, scale.set_value,
            s.percentage)
    
    def on_config_language_combo_changed(combo):
        config['language'] = combo.get_child().get_text()
    
    def on_config_max_n_spin_value_changed(button):
        config['max_n'] = button.get_value_as_int()
    
    def populate_monitors_combo(stack, args):
        if stack.get_visible_child_name() == 'config_page':
            combo = ui.get_object('config_video_monitor')
            monitors = display.get_monitors()
            for c in combo.get_model():
                i = int(c[1])
                if i < 0:
                    continue
                elif i >= len(monitors):
                    combo.remove(c[1])
                elif c[0] != monitors[i].get_model():
                    c[0] = monitors[i].get_model()
            
            ids = [int(c[1]) for c in combo.get_model()]
            for c, d in enumerate(monitors):
                if c not in ids:
                    combo.append(str(c), d.get_model())
            
            ids = [int(c[1]) for c in combo.get_model()]
            active = combo.get_active_id()
            if (active != str(config['video_monitor']) and
                    config['video_monitor'] in ids):
                print('here')
                combo.set_active_id(str(config['video_monitor']))
    
    def on_config_video_monitor_changed(combo):
        config['video_monitor'] = int(combo.get_active_id())
        if config['video_monitor'] is not None:
            win = ui.get_object('vid_win')
            display.fullscreen_on_monitor(win,
                config['video_monitor'])
    
    def on_font_button_font_set(button):
        groups = re.match('(.*?) ([0-9]*?)px', button.get_font())
        font, size = groups.groups()
        config['vid_font_family'] = font
        config['vid_font_size'] = size
        update_vid_labels_css()
    
    def on_config_font_wieght_combo_changed(combo):
        config['vid_font_wieght'] = combo.get_active_id()
        update_vid_labels_css()
    
    def on_config_font_style_combo_changed(combo):
        config['vid_font_style'] = combo.get_active_id()
        update_vid_labels_css()
    
    def on_font_color_button_color_set(button):
        color = [255 * c for c in button.get_rgba()]
        color = [hex(int(c))[2:] for c in color[0:3]]
        config['vid_font_color'] = '#{:>02}{:>02}{:>02}'.format(*color)
        update_vid_labels_css()
    
    def on_vid_background_color_button_color_set(button):
        color = [255 * c for c in button.get_rgba()]
        color = [hex(int(c))[2:] for c in color[0:3]]
        config['vid_background_color'] = '#{:>02}{:>02}{:>02}'.format(*color)
        update_vid_win_css()
    
    def on_config_side_margin_spin_value_changed(button):
        config['vid_side_margin'] = button.get_value_as_int()
        ui.get_object('vid_stack').set_margin_start(config['vid_side_margin'])
        ui.get_object('vid_stack').set_margin_end(config['vid_side_margin'])
    
    def on_config_top_bottom_margin_spin_value_changed(button):
        config['vid_top_bottom_margin'] = button.get_value_as_int()
        ui.get_object('vid_stack').set_margin_top(
            config['vid_top_bottom_margin'])
        ui.get_object('vid_stack').set_margin_bottom(
            config['vid_top_bottom_margin'])
    
def replace_numerals(s):
    for c, d in enumerate(_('0123456789')):
        s = s.replace(str(c), d)
    
    return s
    
def populate_search_tree():
    model = ui.get_object('search_liststore')
    model.clear()
    q = session.query(
        db.Program
    ).filter(
        db.Program.linked_to == None
    ).order_by(db.Program.name)
    
    search_text = ui.get_object('search_entry').get_text()
    if search_text:
        q = q.filter(db.Program.name.contains(search_text))
    if search_filter is not None:
        q = q.filter(search_filter)
    
    for c in q:
        id_ = c.id
        try:
            thumb_path = pathlib.Path(c.dir).resolve()
            thumb_path = thumbs = sorted(thumb_path.glob('__thumb__.*'))[0]
            thumb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(thumb_path), 128, 128)
        except Exception:
            thumb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 128, 128)
            thumb.fill(0x00000000)
        
        info = '{0.name}\n{0.dir}\n{1} subprograms'.format(c, len(c.linked))
        if not c.stopped:
            bgcolor = None
        else:
            bgcolor = 'light grey'
        
        model.append([id_, thumb, info, bgcolor])

def populate_program_edit():
    ui.get_object('name_entry').set_text(edited_program.name)
    ui.get_object('dir_entry').set_text(edited_program.dir)
    ui.get_object('stopped_checkbutton').set_active(edited_program.stopped)
    
    populate_last_file_combo()
    
    period_button = ui.get_object('period_button')
    period = period_button.get_active()
    if type(edited_program.days) is utils.Monthdays:
        period_button.set_active(True)
    else:
        period_button.set_active(False)
    
    if period == period_button.get_active():
        Handler.on_period_button_toggled(period_button)
    
    t = edited_program.time
    hour, minute = str(t.hour), str(t.minute)
    ui.get_object('hour_entry').set_text(hour)
    ui.get_object('minute_entry').set_text(minute)
    
    ui.get_object('mode_combo').set_active_id(edited_program.mode)
    ui.get_object('n_spinbutton').set_value(edited_program.n)
    ui.get_object('last_file_combo').get_child().set_text(edited_program.last_file)
    opening = ui.get_object('opening_combo').get_child().set_text(edited_program.opening)
    ending = ui.get_object('ending_combo').get_child().set_text(edited_program.ending)
    
    Handler.on_dir_entry_changed(ui.get_object('dir_entry'))
    
    populate_subprograms_tree()
    
def populate_subprograms_tree():
    model = ui.get_object('programs_liststore')
    model.clear()
    for c in edited_program.linked:
        append_subprograms_tree(model, c)

def populate_subprogram_popover():
    period_button = ui.get_object('subprogram_period_button')
    period = period_button.get_active()
    if type(edited_subprogram.days) is utils.Monthdays:
        period_button.set_active(True)
    else:
        period_button.set_active(False)
    
    if period == period_button.get_active():
        Handler.on_period_button_toggled(period_button)
    
    t = edited_subprogram.time
    hour, minute = str(t.hour), str(t.minute)
    ui.get_object('subprogram_hour_entry').set_text(hour)
    ui.get_object('subprogram_minute_entry').set_text(minute)
    
    ui.get_object('subprogram_mode_combo').set_active_id(edited_subprogram.mode)
    print(repr(edited_subprogram.n))
    ui.get_object('subprogram_n_spinbutton').set_value(edited_subprogram.n)
    
def populate_last_file_combo():
    model = ui.get_object('files_liststore')
    model.clear()
    model.append([''])
    
    path = ui.get_object('dir_entry').get_text()
    if path:
        path = pathlib.Path(path)
        files = sorted(
            [c for c in path.glob('*') 
                if not c.name.startswith('__') and c.is_file()])
        for c in files:
            model.append([c.name])

def edit_subprograms_tree_row(row):
    if ui.get_object('subprogram_period_button').get_active():
        row[1] = 'monthly'
        row[9] = _('Monthly')
    else:
        row[1] = 'weekly'
        row[9] = _('Weekly')
    
    hour = int(ui.get_object('subprogram_hour_entry').get_text())
    minute = int(ui.get_object('subprogram_minute_entry').get_text())
    
    row[2] = hour
    row[3] = minute
    row[10] = '{:02}:{:02}'.format(hour, minute)
    
    days = ui.get_object('subprogram_days_grid').get_children()
    days = [c for c in days if c.get_active()]
    days.sort(key=lambda w: w.value)
    day_values = [str(c.value) for c in days]
    days = [c.get_label() for c in days]
    if len(days) > 7:
        days = days[0:6] + ['..']
    
    row[4] = ','.join(day_values)
    row[11] = ', '.join(days)
    
    row[5] = ui.get_object('subprogram_mode_combo').get_active_id()
    row[12] = ui.get_object('subprogram_mode_combo').get_active_text()
    
    row[6] = ui.get_object('subprogram_n_spinbutton').get_value_as_int()
    if row[7]:
        row[13] = 'light grey'
    else:
        row[13] = None

def append_subprograms_tree(model, obj, parent=None):
    id_ = obj.id
    if type(obj.days) is utils.Weekdays:
        period_value = 'weekly'
        period = _('Weekly')
    else:
        period_value = 'monthly'
        period = _('Monthly')
    
    hour = obj.days.time.hour
    minute = obj.days.time.minute
    t = '{:02}:{:02}'.format(hour, minute)
    
    day_values = ','.join([str(d) for d in obj.days.days])
    if type(obj.days) is utils.Monthdays:
        days = [str(d) for d in obj.days.days]
    else:
        days = [_(utils.wd[d]) for d in obj.days.days]
    
    if len(days) > 7:
        days = days[0:6] + ['..']
    
    days = ', '.join(days)
    mode_value = obj.mode
    mode = _(obj.mode)
    n = obj.n
    is_stopped = obj.stopped
    if is_stopped:
        bgcolor = 'light grey'
    else:
        bgcolor = None
    
    return model.append([id_, period_value, hour, minute, day_values,
        mode_value, n, is_stopped, '', period, t, days, mode, bgcolor])

def check_largest_monitor(recheck=False):
    vid_win = ui.get_object('vid_win')
    idx = display.fullscreen_on_largest(vid_win)
    if idx is not None:
        print('moved video window to monitor', idx)
    
    return recheck

def update_vid_win_css():
    vcss = '''
    window {{
        background: {0[vid_background_color]};
    }}
    '''.format(config)
    
    vid_win_css.load_from_data(vcss.encode('utf-8'))

def update_vid_labels_css():
    global label_css
    
    lcss = '''
    label {{
        font-family: {0[vid_font_family]};
        font-size: {0[vid_font_size]}px;
        font-weight: {0[vid_font_weight]};
        font-style: {0[vid_font_style]};
        color: {0[vid_font_color]};
    }}
    '''
    
    lcss = lcss.format(config)
    
    label_css.load_from_data(lcss.encode('utf-8'))

def main(maker, tilfaz_obj):
    t = threading.Thread(target=do_main, args=(maker,))
    t.start()
    return t

def do_main(maker, tilfaz_obj, config_obj, codi_obj):
    global session, ui, tilfaz, config, cdirs, _, ngettext
    
    tilfaz = tilfaz_obj
    config = config_obj
    cdirs = codi_obj
    
    try:
        mo_path = cdirs.path('locale/mo/{}'.format(config['language'])).parent
    except FileNotFoundError:
        mo_path = ''
    locale_obj = gettext.translation(
        'tilfaz', mo_path, [config['language']], fallback=True)
    _ = locale_obj.gettext
    ngettext = locale_obj.ngettext
    
    session = maker()
    glade_file = pathlib.Path(__file__).parent / 'glade/main.glade'
    ui = Gtk.Builder()
    ui.set_translation_domain('tilfaz')
    ui.add_from_file(str(glade_file))
    ui.connect_signals(Handler)
    
    ui.get_object('vid_win').get_style_context().add_provider(vid_win_css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    for c in ['next_label', 'time_label', 'program_label', 'timedelta_label']:
        ui.get_object(c).get_style_context().add_provider(label_css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    update_vid_win_css()
    update_vid_labels_css()
    
    populate_search_tree()
    
    vid_win = ui.get_object('vid_win')
    vid_win.set_keep_above(True)
    # vid_win.fullscreen()
    vid_win.show_all()
    
    #on previous versions, video was only on largest monitor. this has changed
    #now so the few following lines are commented
    
    #check_largest_monitor()
    
    #Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT,
    #    check_largest_monitor, False)
    #Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT, 30,
    #    check_largest_monitor, True)
    
    main_win = ui.get_object('main_win')
    main_win.show_all()
    
    Gtk.main()
    
    session.close()

def stop():
    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, Gtk.main_quit)

