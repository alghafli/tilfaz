from gi.repository import Gdk
from gi.repository import GLib
import sys
import ctypes

def get_monitors():
    disp = Gdk.Display.get_default()
    return [disp.get_monitor(c) for c in range(disp.get_n_monitors())]

def get_default_screen():
    return Gdk.Display.get_default().get_default_screen()

def get_largest_monitor():
    monitors = get_monitors()
    largest = monitors[0]
    a0 = largest.get_width_mm() * largest.get_height_mm()
    for c in monitors[1:]:
        a1 = c.get_width_mm() * c.get_height_mm()
        if a1 >= a0:
            largest = c
            a0 = a1
    
    return largest

def get_largest_monitor_index():
    monitors = get_monitors()
    largest = get_largest_monitor()
    return monitors.index(largest)

def fullscreen_on_largest(win):
    print('checking largest')
    largest = get_largest_monitor_index()
    fullscreen_on_monitor(win, largest)
    return largest

def fullscreen_on_monitor(win, n):
    print('moving to monitor', n)
    monitor = get_monitors()[n]
    rect = monitor.get_geometry()
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    wx, wy = win.get_position()
    ww, wh = win.get_size()
    
    #not using decorations because the window is always on fullscreen
    #doing fullscreen without calling window.fullscreen() because the window
    #manager moves the window to another monitor if the font or its size is
    #changed and even after db update.
    if wx != x or wy != y or ww != w or wh != h:
        print('updating')
        
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, win.resize, w, h)
        #must move after some delay because window manager on my linux mint
        #ignores the move request for some reason if we do not delay
        Gdk.threads_add_timeout_seconds(GLib.PRIORITY_DEFAULT, 0.1,
            win.move, x, y)

def get_wid(win):
    if sys.platform == 'win32':
        #copied and modified from
        #https://stackoverflow.com/questions/23021327/how-i-can-get-drawingarea-window-handle-in-gtk3/27236258#27236258
        
        #make sure to call ensure_native before e.g. on realize
        if not win.has_native():
            print("Your window is gonna freeze as soon as you move or resize it...")
        
        ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
        ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
        drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(win.__gpointer__, None)            
        #get the win32 handle
        gdkdll = ctypes.CDLL ("libgdk-3-0.dll")
        hnd = gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer)
        return hnd
    else:
        return win.get_xid()
    
