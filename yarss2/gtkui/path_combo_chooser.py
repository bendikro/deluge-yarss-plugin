#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import gobject
import os
import gettext
import datetime

import pygtk
import gtk
from gtk import gdk
import keysyms

pygtk.require('2.0')

def get_resource(r):
    return r
try:
    from yarss2.util.common import get_resource
except:
    pass

def key_is_up(keyval):
    return keyval == keysyms.Up or keyval == keysyms.KP_Up

def key_is_down(keyval):
    return keyval == keysyms.Down or keyval == keysyms.KP_Down

def key_is_up_or_down(keyval):
    return key_is_up(keyval) or key_is_down(keyval)

def key_is_enter(keyval):
    return keyval == keysyms.Return or keyval == keysyms.KP_Enter

class ValueList(object):

    def get_values(self):
        """
        Returns the values in the list.
        """
        values = []
        for row in self.tree_store:
            values.append(row[0])
        return values

    def add_values(self, paths, append=True, scroll_to_row=False,
                   clear=False, emit_signal=False):
        """
        Add paths to the liststore

        :param paths: the paths to add
        :type  paths: list
        :param append: if the values should be appended or inserted
        :type  append: boolean
        :param scroll_to_row: if the treeview should scroll to the new row
        :type  scroll_to_row: boolean

        """
        if clear:
            self.tree_store.clear()

        for path in paths:
            if append:
                tree_iter = self.tree_store.append([path])
            else:
                tree_iter = self.tree_store.insert(0, [path])
            if scroll_to_row:
                self.treeview.grab_focus()
                path = self.tree_store.get_path(tree_iter)
                # Scroll to path
                self.handle_list_scroll(path=path)

        if emit_signal:
            self.emit("list-value-added", paths)

    def get_selection_path(self):
        """Returns the (first) selected path from a treeview"""
        tree_selection = self.treeview.get_selection()
        model, tree_paths = tree_selection.get_selected_rows()
        if len(tree_paths) > 0:
            return tree_paths[0]
        return None

    def get_selected_value(self):
        path = self.get_selection_path()
        if path:
            return self.tree_store[path][0]
        return None

    def remove_selected_path(self):
        path = self.get_selection_path()
        if path:
            del self.tree_store[path]
            index = path[0]
            # The last row was deleted
            if index == len(self.tree_store):
                index -= 1
            if index >= 0:
                path = (index, )
            self.treeview.set_cursor(path)

    def set_selected_value(self, value, select_first=False):
        """
        Select the row of the list with value

        :param value: the value to be selected
        :type  value: str
        :param select_first: if the first item should be selected if the value if not found.
        :type  select_first: boolean

        """
        for i, row in enumerate(self.tree_store):
            if row[0] == value:
                self.treeview.set_cursor((i))
                return
        # The value was not found
        if select_first:
            self.treeview.set_cursor((0,))
        else:
            self.treeview.get_selection().unselect_all()

    def on_treeview_key_press_event(self, widget, event):
        """
        Mimics Combobox behavior

        Escape or Alt+Up: Close
        Enter or Return : Select
        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        if keyval == keysyms.Escape or\
                (key_is_up(keyval) and
                 state == gdk.MOD1_MASK): # ALT Key
            self.popdown()
            return True
        # Set entry value to the selected row
        elif key_is_enter(keyval):
            path = self.get_selection_path()
            if path:
                self.set_entry_value(path, popdown=True)
            return True
        return False

    def on_treeview_mouse_button_press_event(self, treeview, event):
        """
        Shows popup on selected row when right clicking
        When left clicking twice, the row value is set for the text entry
        and the popup is closed.

        """
        # This is left click
        if event.button != 3:
            # Double clicked a row, set this as the entry value
            # and close the popup
            if event.type == gtk.gdk._2BUTTON_PRESS:
                path = self.get_selection_path()
                if path:
                    self.set_entry_value(path, popdown=True)
                    return True
        return False

    def handle_list_scroll(self, next=None, path=None, set_entry=False, swap=False):
        """
        Handles changes to the row selection.

        :param next: the direction to change selection. None means no change. True means down
        and False means up.
        :type  next: boolean/None
        :param path: the current path. If None, the currently selected path is used.
        :type  path: tuple
        :param set_entry: if the new value should be set in the text entry.
        :type  set_entry: boolean
        :param swap: if the old and new value should be swapped
        :type  swap: boolean

        """
        if path is None:
            path = self.get_selection_path()
            if not path:
                # These options require a selected path
                if set_entry or swap:
                    return
                # This is a regular scroll, not setting value in entry or swapping rows,
                # so we find a path value anyways
                path = (0, )
                cursor = self.treeview.get_cursor()
                if cursor is not None:
                    path = cursor[0]
                else:
                    # Since cursor is none, we won't advance the index
                    next = None

        # If next is None, we won't change the selection
        if not next is None:
            # We move the selection either one up or down.
            # If we reach end of list, we wrap
            index = path[0] if path else 0
            index = index + 1 if next else index - 1
            if index >= len(self.tree_store):
                index = 0
            elif index < 0:
                index = len(self.tree_store) - 1

            # We have the index for the new path
            new_path = (index)
            if swap:
                self.tree_store.swap(self.tree_store.get_iter(path),
                                      self.tree_store.get_iter(new_path))
            path = new_path

        self.treeview.set_cursor(path)
        if set_entry:
            self.set_entry_value(path)

class StoredValuesList(ValueList):

    def __init__(self):
        self.tree_store = self.builder.get_object("stored_values_tree_store")
        self.tree_column = self.builder.get_object("stored_values_treeview_column")
        self.rendererText = self.builder.get_object("stored_values_cellrenderertext")

        # Add signal handlers
        self.signal_handlers["on_stored_values_treeview_mouse_button_press_event"] = \
            self.on_treeview_mouse_button_press_event

        self.signal_handlers["on_stored_values_treeview_key_press_event"] = \
            self.on_stored_values_treeview_key_press_event

        self.signal_handlers["on_cellrenderertext_edited"] = self.on_cellrenderertext_edited

    def on_cellrenderertext_edited(self, cellrenderertext, path, new_text):
        """
        Callback on the 'edited' signal.

        Sets the new text in the path and disables editing on the renderer.
        """
        self.tree_store[path][0] = new_text
        self.rendererText.set_property('editable', False)

    def on_edit_path(self, path, column):
        """
        Starts editing on the provided path

        :param path: the paths to edit
        :type  path: tuple
        :param column: the column to edit
        :type  column: gtk.TreeViewColumn

        """
        self.rendererText.set_property('editable', True)
        self.treeview.grab_focus()
        self.treeview.set_cursor(path, focus_column=column, start_editing=True)

    def on_treeview_mouse_button_press_event(self, treeview, event):
        """
        Shows popup on selected row when right clicking
        When left clicking twice, the row value is set for the text entry
        and the popup is closed.

        """
        # This is left click
        if event.button != 3:
            super(StoredValuesList, self).on_treeview_mouse_button_press_event(treeview, event)
            return False

        # This is right click, create popup menu for this row
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor(path, col, 0)

            self.path_list_popup = gtk.Menu()
            menuitem_edit = gtk.MenuItem("Edit path")
            self.path_list_popup.append(menuitem_edit)
            menuitem_remove = gtk.MenuItem("Remove path")
            self.path_list_popup.append(menuitem_remove)

            def on_edit_clicked(widget, path):
                self.on_edit_path(path, self.tree_column)
            def on_remove_clicked(widget, path):
                self.remove_selected_path()

            menuitem_edit.connect("activate", on_edit_clicked, path)
            menuitem_remove.connect("activate", on_remove_clicked, path)
            self.path_list_popup.popup(None, None, None, event.button, time, data=path)
            self.path_list_popup.show_all()

    def remove_selected_path(self):
        ValueList.remove_selected_path(self)
        # Resize popup
        PathChooserPopup.popup(self)

    def on_stored_values_treeview_key_press_event(self, widget, event):
        """
        Mimics Combobox behavior

        Escape or Alt+Up: Close
        Enter or Return : Select

        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        # Edit selected row
        if (keyval in [keysyms.Left, keysyms.Right, keysyms.space]):
            path = self.get_selection_path()
            if path:
                self.on_edit_path(path, self.tree_column)
                return True
        elif key_is_up_or_down(keyval):
            # Swap the row value
            if event.state & gtk.gdk.CONTROL_MASK:
                self.handle_list_scroll(next=key_is_down(keyval),
                                        swap=True)
            else:
                self.handle_list_scroll(next=key_is_down(keyval))
            return True

        return super(StoredValuesList, self).on_treeview_key_press_event(widget, event)

class CompletionList(ValueList):

    def __init__(self):
        self.tree_store = self.builder.get_object("completion_tree_store")
        self.tree_column = self.builder.get_object("completion_treeview_column")
        self.rendererText = self.builder.get_object("completion_cellrenderertext")

        self.signal_handlers["on_completion_treeview_key_press_event"] = \
            self.on_completion_treeview_key_press_event

        # Add super class signal handler
        self.signal_handlers["on_completion_treeview_mouse_button_press_event"] = \
            super(CompletionList, self).on_treeview_mouse_button_press_event

    def set_values(self, paths, scroll_to_row=False):
        """
        Add paths to the liststore

        :param paths: the paths to add
        :type  paths: list
        :param scroll_to_row: if the treeview should scroll to the new row
        :type  scroll_to_row: boolean

        """
        self.add_values(paths, scroll_to_row=scroll_to_row, clear=True)

    def reduce_values(self, prefix):
        """
        Reduce the values in the liststore to those starting with the prefix.

        :param prefix: the prefix to be matched
        :type  paths: string

        """
        values = self.get_values()
        matching_values = []
        for v in values:
            if v.startswith(prefix):
                matching_values.append(v)
        self.add_values(matching_values, clear=True)

    def on_completion_treeview_key_press_event(self, widget, event):
        """

        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        if key_is_up_or_down(keyval):
            self.handle_list_scroll(next=key_is_down(keyval))
            return True
        return super(CompletionList, self).on_treeview_key_press_event(widget, event)

class PathChooserPopup(object):
    """

    This creates the popop window for the ComboEntry

    """
    def __init__(self, min_visible_rows, max_visible_rows):
        self.min_visible_rows = min_visible_rows
        # Maximum number of rows to display without scrolling
        self.max_visible_rows = max_visible_rows
        self.popup_window.realize()

    def set_window_position_and_size(self):
        if len(self.tree_store) < self.min_visible_rows:
            return False
        x, y, width, height = self.get_position()
        self.popup_window.set_size_request(width, height)
        self.popup_window.resize(width, height)
        self.popup_window.move(x, y)
        self.popup_window.show_all()

    def popup(self):
        """
        Makes the popup visible.

        """
        # Entry is not yet visible
        if not (self.path_entry.flags() & gtk.REALIZED):
            return
        if not self.is_popped_up():
            toplevel = self.path_entry.get_toplevel()
            if isinstance(toplevel, gtk.Window) and toplevel.group:
                toplevel.group.add_window(self)
        self.set_window_position_and_size()

    def popdown(self):
        if not (self.path_entry.flags() & gtk.REALIZED):
            return
        self.popup_window.grab_remove()
        self.popup_window.hide_all()

    def is_popped_up(self):
        return bool(self.popup_window.flags() & gtk.MAPPED)

    def get_position(self):
        """
        Returns the size of the popup window and the coordinates on the screen.

        """
        self.popup_buttonbox = self.builder.get_object("buttonbox")

        # Necessary for the first call, to make treeview.size_request give sensible values
        #self.popup_window.realize()
        self.treeview.realize()

        # We start with the coordinates of the parent window
        x, y = self.path_entry.window.get_origin()

        # Add the position of the path_entry (hbox) relative to the parent window.
        x += self.entry.allocation.x
        y += self.entry.allocation.y

        height_extra = 8

        height = self.popup_window.size_request()[1]
        width = self.popup_window.size_request()[0]

        treeview_height = self.treeview.size_request()[1]
        treeview_width = self.treeview.size_request()[0]

        if treeview_height > height:
            height = treeview_height + height_extra

        butonbox_height = max(self.popup_buttonbox.size_request()[1], self.popup_buttonbox.allocation.height)
        butonbox_width = max(self.popup_buttonbox.size_request()[0], self.popup_buttonbox.allocation.width)

        if treeview_height > butonbox_height and treeview_height < height :
            height = treeview_height + height_extra

        # After removing a element from the tree store, self.treeview.size_request()[0]
        # returns -1 for some reason, so the requested width cannot be used until the treeview
        # has been displayed once.
        if treeview_width != -1:
            width = treeview_width + butonbox_width
        # The list is empty, so ignore initial popup width request
        # Will be set to the minimum width next
        elif len(self.tree_store) == 0:
            width = 0

        # Minimum width is the width of the path entry + width of buttonbox
        if width < self.entry.allocation.width + butonbox_width:
            width = self.entry.allocation.width + butonbox_width

        # 10 is extra spacing
        content_width = self.treeview.size_request()[0] + butonbox_width + 10

        # If self.max_visible_rows is -1, not restriction is set
        if len(self.tree_store) > 0 and self.max_visible_rows > 0:
            # The height for one row in the list
            row_height = self.treeview.size_request()[1] / len(self.tree_store)
            # Adjust the height according to the max number of rows
            max_height = row_height * self.max_visible_rows
            # Restrict height to max_visible_rows
            if max_height + height_extra < height:
                height = max_height
                height += height_extra
                # Increase width because of vertical scrollbar
                content_width += 15

        # Minimum height is the height of the button box
        if height < butonbox_height + height_extra:
            height = butonbox_height + height_extra

        if content_width > width:
            width = content_width

        screen = self.path_entry.get_screen()
        monitor_num = screen.get_monitor_at_window(self.path_entry.window)
        monitor = screen.get_monitor_geometry(monitor_num)

        if x < monitor.x:
            x = monitor.x
        elif x + width > monitor.x + monitor.width:
            x = monitor.x + monitor.width - width

        # Set the position
        if y + self.path_entry.allocation.height + height <= monitor.y + monitor.height:
            y += self.path_entry.allocation.height
        # Not enough space downwards on the screen
        elif y - height >= monitor.y:
            y -= height
        elif (monitor.y + monitor.height - (y + self.path_entry.allocation.height) >
              y - monitor.y):
            y += self.path_entry.allocation.height
            height = monitor.y + monitor.height - y
        else:
            height = y - monitor.y
            y = monitor.y

        return x, y, width, height

    def popup_grab_window(self):
        activate_time = 0L
        if gdk.pointer_grab(self.popup_window.window, True,
                            (gdk.BUTTON_PRESS_MASK |
                             gdk.BUTTON_RELEASE_MASK |
                             gdk.POINTER_MOTION_MASK),
                             None, None, activate_time) == 0:
            if gdk.keyboard_grab(self.popup_window.window, True, activate_time) == 0:
                return True
            else:
                self.popup_window.window.get_display().pointer_ungrab(activate_time);
                return False
        return False

    def set_entry_value(self, path, popdown=False):
        """

        Sets the text of the entry to the value in path
        """
        self.path_entry.set_text(self.tree_store[path][0], set_file_chooser_folder=True)
        if popdown:
            self.popdown()

###################################################
# Callbacks
###################################################

    def on_popup_window_button_press_event(self, window, event):
        # If we're clicking outside of the window close the popup
        hide = False

        # Also if the intersection of self and the event is empty, hide
        # the path_list
        if (tuple(self.popup_window.allocation.intersect(
              gdk.Rectangle(x=int(event.x), y=int(event.y),
                           width=1, height=1))) == (0, 0, 0, 0)):
            hide = True

        # Toplevel is the window that received the event, and parent is the
        # path_list window. If they are not the same, means the popup should
        # be hidden. This is necessary for when the event happens on another
        # widget
        toplevel = event.window.get_toplevel()
        parent = self.popup_window.window

        if toplevel != parent:
            hide = True

        if hide:
            self.popdown()


class StoredValuesPopup(StoredValuesList, PathChooserPopup):
    """

    This creates the popop window for the ComboEntry

    """
    def __init__(self, builder, path_entry, max_visible_rows):
        self.builder = builder
        self.treeview = self.builder.get_object("stored_values_treeview")
        self.popup_window = self.builder.get_object("stored_values_popup_window")
        self.popup_buttonbox = self.builder.get_object("buttonbox")

        self.path_entry = path_entry
        self.entry = path_entry.entry

        self.signal_handlers = {}
        PathChooserPopup.__init__(self, 0, max_visible_rows)
        StoredValuesList.__init__(self)

        # Add signal handlers
        self.signal_handlers["on_buttonbox_key_press_event"] = \
            self.on_buttonbox_key_press_event
        self.signal_handlers["on_stored_values_treeview_scroll_event"] = self.on_scroll_event
        self.signal_handlers["on_button_toggle_dropdown_scroll_event"] = \
            self.on_scroll_event
        self.signal_handlers["on_entry_text_scroll_event"] = self.on_scroll_event
        self.signal_handlers["on_stored_values_popup_window_focus_out_event"] = \
            self.on_stored_values_popup_window_focus_out_event
        # For when clicking outside the popup
        self.signal_handlers["on_stored_values_popup_window_button_press_event"] = \
            self.on_popup_window_button_press_event

        # Buttons for manipulating the list
        self.signal_handlers["on_button_add_clicked"] = self.on_button_add_clicked
        self.signal_handlers["on_button_edit_clicked"] = self.on_button_edit_clicked
        self.signal_handlers["on_button_remove_clicked"] = self.on_button_remove_clicked
        self.signal_handlers["on_button_up_clicked"] = self.on_button_up_clicked
        self.signal_handlers["on_button_down_clicked"] = self.on_button_down_clicked
        self.signal_handlers["on_button_properties_clicked"] = self.path_entry._on_button_properties_clicked

    def popup(self):
        """
        Makes the popup visible.

        """
        # Calling super popup
        PathChooserPopup.popup(self)

        self.popup_window.grab_focus()

        if not (self.treeview.flags() & gtk.HAS_FOCUS):
            self.treeview.grab_focus()

        if not self.popup_grab_window():
            self.popup_window.hide()
            return

        self.popup_window.grab_add()

        # Set value selected if it exists
        self.set_selected_value(self.path_entry.get_text())

###################################################
# Callbacks
###################################################

    def on_stored_values_popup_window_focus_out_event(self, entry, event):
        """
        Popup sometimes loses the focus to the text entry, e.g. when right click
        shows a popup menu on a row. This regains the focus.
        """
        self.popup_grab_window()
        return True

    def on_scroll_event(self, widget, event):
        """
        Handles scroll events from text entry, toggle button and treeview

        """
        state = event.state & gtk.accelerator_get_default_mod_mask()
        swap = event.state & gtk.gdk.CONTROL_MASK
        self.handle_list_scroll(next=event.direction == gdk.SCROLL_DOWN,
                                set_entry=widget != self.treeview, swap=swap)
        return True

    def on_buttonbox_key_press_event(self, widget, event):
        """
        Handles when Escape or ALT+arrow up is pressed when focus
        is on any of the buttons in the popup
        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()
        if (keyval == keysyms.Escape or
            (key_is_up(keyval) and
             state == gdk.MOD1_MASK)):
            self.popdown()
            return True
        return False

# --------------------------------------------------
# Callbacks on the buttons to manipulate the list
# --------------------------------------------------
    def on_button_add_clicked(self, widget):
        value = self.path_entry.get_text()
        values = self.get_values()
        for v in values:
            # Already exists, so return
            if value == v:
                return
        self.add_values([value], scroll_to_row=True, append=False, emit_signal=True)
        self.popup()

    def on_button_edit_clicked(self, widget):
        path = self.get_selection_path()
        if path:
            self.on_edit_path(path, self.tree_column)

    def on_button_remove_clicked(self, widget):
        self.remove_selected_path()
        return True

    def on_button_up_clicked(self, widget):
        self.handle_list_scroll(next=False, swap=True)

    def on_button_down_clicked(self, widget):
        self.handle_list_scroll(next=True, swap=True)


class PathCompletionPopup(CompletionList, PathChooserPopup):
    """

    This creates the popop window for the ComboEntry

    """
    def __init__(self, builder, path_entry, max_visible_rows):
        self.builder = builder
        self.treeview = self.builder.get_object("completion_treeview")
        self.popup_window = self.builder.get_object("completion_popup_window")
        self.path_entry = path_entry
        self.entry = path_entry.entry

        self.signal_handlers = {}
        PathChooserPopup.__init__(self, 1, max_visible_rows)
        CompletionList.__init__(self)

        # Add signal handlers
        self.signal_handlers["on_completion_treeview_scroll_event"] = self.on_scroll_event
        self.signal_handlers["on_completion_popup_window_focus_out_event"] = \
            self.on_completion_popup_window_focus_out_event

        # For when clicking outside the popup
        self.signal_handlers["on_completion_popup_window_button_press_event"] = \
            self.on_popup_window_button_press_event

    def popup(self):
        """
        Makes the popup visible.

        """
        PathChooserPopup.popup(self)
        self.entry.grab_focus()
        self.entry.set_position(len(self.path_entry.entry.get_text()))


###################################################
# Callbacks
###################################################

    def on_completion_popup_window_focus_out_event(self, entry, event):
        """
        Popup sometimes loses the focus to the text entry, e.g. when right click
        shows a popup menu on a row. This regains the focus.
        """
        self.popup_grab_window()
        return True

    def on_scroll_event(self, widget, event):
        """
        Handles scroll events from the treeview

        """
        state = event.state & gtk.accelerator_get_default_mod_mask()
        self.handle_list_scroll(next=event.direction == gdk.SCROLL_DOWN,
                                set_entry=widget != self.treeview)
        return True

class PathAutoCompleter(object):

    def __init__(self, builder, path_entry, max_visible_rows):
        self.completion_popup = PathCompletionPopup(builder, path_entry, max_visible_rows)
        self.path_entry = path_entry
        self.dirs_cache = {}
        self.use_popup = False
        self.auto_complete_enabled = True
        self.signal_handlers = self.completion_popup.signal_handlers

        self.signal_handlers["on_completion_popup_window_key_press_event"] = \
            self.on_completion_popup_window_key_press_event
        self.signal_handlers["on_entry_text_delete_text"] = \
            self.on_entry_text_delete_text
        self.signal_handlers["on_entry_text_insert_text"] = \
            self.on_entry_text_insert_text

        self.accelerator_string = gtk.accelerator_name(keysyms.Tab, 0)

    def on_entry_text_insert_text(self, entry, new_text, new_text_length, position):

        if (self.path_entry.flags() & gtk.REALIZED):
            cur_text = self.path_entry.get_text()
            pos = entry.get_position()
            new_complete_text = cur_text[:pos] + new_text + cur_text[pos:]
            # Remove all values from the list that do not start with new_complete_text
            self.completion_popup.reduce_values(new_complete_text)
            self.completion_popup.set_window_position_and_size()

    def on_entry_text_delete_text(self, entry, start, end):
        """
        Remove the popup when characters are removed

        """
        if self.completion_popup.is_popped_up():
            self.completion_popup.popdown()

    def set_use_popup(self, use):
        self.use_popup = use

    def on_completion_popup_window_key_press_event(self, entry, event):
        """
        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        if key_is_up_or_down(keyval):
            self.completion_popup.handle_list_scroll(next=key_is_down(keyval))
            return True
        elif key_is_enter(keyval):
            path = self.completion_popup.get_selection_path()
            if path:
                self.completion_popup.set_entry_value(path, popdown=True)
            return True

        if self.is_auto_completion_accelerator(keyval, state)\
                and self.auto_complete_enabled:
            cursor = self.completion_popup.treeview.get_cursor()
            value = self.completion_popup.get_selected_value()
            if value:
                pos = len(self.path_entry.get_text())
                self.path_entry.set_text(value, set_file_chooser_folder=False)
                self.do_completion()
                return True
        self.path_entry.entry.emit("key-press-event", event)

    def is_auto_completion_accelerator(self, keyval, state):
        return gtk.accelerator_name(keyval, state.numerator) == self.accelerator_string

    def do_completion(self):
        value = self.path_entry.get_text()
        paths = self.start_completion(value)

    def start_completion(self, value):

        def get_subdirs(dirname):
            try:
                return os.walk(dirname).next()[1]
            except StopIteration:
                # Invalid dirname
                return []

    	dirname = os.path.dirname(value)
    	basename = os.path.basename(value)

    	if not dirname in self.dirs_cache:
            subdirs = get_subdirs(dirname)
            if subdirs:
                self.dirs_cache[dirname] = subdirs

        # No completions available
        if not dirname in self.dirs_cache:
            return []

    	dirs = self.dirs_cache[dirname]
    	matching_dirs = []

    	for s in dirs:
    		if s.startswith(basename):
    			p = os.path.join(dirname, s)
    			if not p.endswith("/"):
    				p += "/"
    			matching_dirs.append(p)

    	matching_dirs = sorted(matching_dirs)
        self.end_completion(value, matching_dirs)

    def end_completion(self, value, paths):
        common_prefix = os.path.commonprefix(paths)

        if len(common_prefix) > len(value):
            self.path_entry.set_text(common_prefix, set_file_chooser_folder=True)

        self.path_entry.entry.set_position(len(self.path_entry.get_text()))
        if self.use_popup and len(paths) > 1:
            self.completion_popup.set_values(paths)
            self.completion_popup.popup()


class PathChooserComboBox(gtk.HBox, StoredValuesPopup, gobject.GObject):

    __gsignals__ = {
        "list-value-added": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (object, )),
        }

    def __init__(self, max_visible_rows=20, auto_complete=True, use_completer_popup=True):
        gtk.HBox.__init__(self)
        gobject.GObject.__init__(self)
        self._stored_values_popping_down = False
        self.filechooser_visible = True
        self.properties_enabled = True
        self.builder = gtk.Builder()
        self.popup_buttonbox = self.builder.get_object("buttonbox")
        self.builder.add_from_file(get_resource("path_combo_chooser.ui"))
        self.button_toggle = self.builder.get_object("button_toggle_dropdown")
        self.entry = self.builder.get_object("entry_text")
        self.filechooser_button = self.builder.get_object("filechooser_button")
        self.button_properties = self.builder.get_object("button_properties")
        combo_hbox = self.builder.get_object("entry_combox_hbox")
        # Change the parent of the hbox from the glade Window to this hbox.
        combo_hbox.reparent(self)
        StoredValuesPopup.__init__(self, self.builder, self, max_visible_rows)

        self.auto_completer = PathAutoCompleter(self.builder, self, max_visible_rows)
        self.auto_completer.set_use_popup(use_completer_popup)
        self.auto_completer.auto_complete_enabled = auto_complete
        self.setup_config_dialog()

        signal_handlers = {
            "on_button_toggle_dropdown_toggled": self._on_button_toggle_dropdown_toggled,
            'on_entry_text_key_press_event': self._on_entry_text_key_press_event,
            'on_stored_values_popup_window_hide': self._on_stored_values_popup_window_hide,
            "on_button_toggle_dropdown_button_press_event": self._on_button_toggle_dropdown_button_press_event,
            "on_filechooser_button_current_folder_changed": self._on_filechooser_button_current_folder_changed,
            "on_filechooser_button_show": self._on_filechooser_button_show,
            }
        signal_handlers.update(self.signal_handlers)
        signal_handlers.update(self.auto_completer.signal_handlers)
        signal_handlers.update(self.config_dialog_signal_handlers)
        self.builder.connect_signals(signal_handlers)

    def set_accelerator_string(self, accelerator):
        self.accelerator_string = accelerator

    def get_accelerator_string(self):
        return self.accelerator_string

    def set_auto_complete_enabled(self, enable):
        self.auto_completer.auto_complete_enabled = enable

    def get_auto_complete_enabled(self):
        return self.auto_completer.auto_complete_enabled

    def get_filechooser_visible(self):
        return self.filechooser_visible

    def set_filechooser_visible(self, enable):
        self.filechooser_visible = enable
        if enable:
            self.filechooser_button.show()
        else:
            self.filechooser_button.hide()

    def set_enable_properties(self, enable):
        self.properties_enabled = enable
        if self.properties_enabled:
            self.popup_buttonbox.add(self.button_properties)
        else:
            self.popup_buttonbox.remove(self.button_properties)

    def set_max_pop_down_rows(self, rows):
        self.max_visible_rows = rows
        self.auto_completer.completion_popup.max_visible_rows = rows

    def get_max_pop_down_rows(self):
        return self.max_visible_rows

    def set_auto_completer_func(self, func):
        """
        Set the function to be called when the auto completion
        accelerator is triggered.
        """
        self.auto_completer.start_completion = func

    def complete(self, value, paths):
        """
        Perform the auto completion with the provided paths
        """
        self.auto_completer.end_completion(value, paths)

    def set_text(self, text, set_file_chooser_folder=True):
        """
        Set the text for the entry.

        """
        self.entry.set_text(text)
        self.entry.select_region(0, 0)
        self.entry.set_position(len(text))
        self.set_selected_value(text, select_first=True)
        if set_file_chooser_folder:
            if os.path.isdir(text):
                self.filechooser_button.set_current_folder(text)

    def get_text(self):
        """
        Get the current text in the Entry
        """
        return self.entry.get_text()

    def _on_filechooser_button_current_folder_changed(self, widget):
        text = widget.get_filename()
        if not text.endswith(os.sep):
            text += os.sep
        self.set_text(text, set_file_chooser_folder=False)

    def _on_filechooser_button_show(self, widget):
        """Hide the filechooser button"""
        if not self.filechooser_visible:
            self.set_filechooser_visible(False)

    def _on_entry_text_key_press_event(self, widget, event):
        """
        Listen to key events on the entry widget.

        Arrow up/down will change the value of the entry according to the
        current selection in the list.
        Enter will show the popup.

        Return True whenever we want no other event listeners to be called.

        """
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        # Select new row with arrow up/down is pressed
        if key_is_up_or_down(keyval):
            self.handle_list_scroll(next=key_is_down(keyval),
                                    set_entry=True)
            return True
        elif self.auto_completer.is_auto_completion_accelerator(keyval, state):
            if self.auto_completer.auto_complete_enabled:
                self.auto_completer.do_completion()
                return True
        # Show popup when Enter is pressed
        elif key_is_enter(keyval):
            # This sets the toggle active which results in
            # on_button_toggle_dropdown_toggled being called which initiates the popup
            self.button_toggle.set_active(True)
            return True
        return False

    def _on_button_toggle_dropdown_toggled(self, button):
        """
        Shows the popup when clicking the toggle button.
        """
        if self._stored_values_popping_down:
            return
        self.popup()

    def _on_stored_values_popup_window_hide(self, popup):
        """Make sure the button toggle is removed when popup is closed"""
        self._stored_values_popping_down = True
        self.button_toggle.set_active(False)
        self._stored_values_popping_down = False

######################################
## Config dialog
######################################

    def _on_button_toggle_dropdown_button_press_event(self, widget, event):
        """Show config when right clicking dropdown toggle button"""
        if not self.properties_enabled:
            return False
        # This is right click
        if event.button == 3:
            self._on_button_properties_clicked(widget)
            return True

    def _on_button_properties_clicked(self, widget):
        self.popdown()
        self.enable_completion.set_active(self.get_auto_complete_enabled())
        # Set the value of the label to the current accelerator
        keyval, mask = gtk.accelerator_parse(self.auto_completer.accelerator_string)
        self.accelerator_label.set_text(gtk.accelerator_get_label(keyval, mask))
        self.visible_rows.set_value(self.get_max_pop_down_rows())

        self.config_dialog.show_all()

    def setup_config_dialog(self):
        self.config_dialog = self.builder.get_object("completion_config_dialog")
        close_button = self.builder.get_object("config_dialog_button_close")
        self.enable_completion = self.builder.get_object("enable_auto_completion_checkbutton")
        self.show_filechooser = self.builder.get_object("show_filechooser_checkbutton")
        set_key_button = self.builder.get_object("set_completion_accelerator_button")
        accelerator_name_label = self.builder.get_object("accelerator_name_label")
        self.accelerator_label = self.builder.get_object("completion_accelerator_label")
        self.visible_rows = self.builder.get_object("visible_rows_spinbutton")
        self.visible_rows_label = self.builder.get_object("visible_rows_label")
        self.config_dialog.set_transient_for(self.popup_window)

        self.show_filechooser.set_active(self.get_filechooser_visible())

        def on_close(widget, event=None):
            self.config_dialog.hide()
            return True

        def on_enable_completion_toggled(widget):
            self.set_auto_complete_enabled(self.enable_completion.get_active())

        def on_show_filechooser_toggled(widget):
            self.set_filechooser_visible(self.show_filechooser.get_active())

        def set_widgets_sensitive(val):
            self.enable_completion.set_sensitive(val)
            self.show_filechooser.set_sensitive(val)
            accelerator_name_label.set_sensitive(val)
            self.accelerator_label.set_sensitive(val)
            self.visible_rows.set_sensitive(val)
            self.visible_rows_label.set_sensitive(val)

        def set_accelerator(widget):
            set_widgets_sensitive(set_key_button.get_active())
            return True

        def on_max_rows_changed(widget):
            self.set_max_pop_down_rows(self.visible_rows.get_value_as_int())

        def on_completion_config_dialog_key_release_event(widget, event):
            # We are listening for a new key
            if set_key_button.get_active():
                state = event.state & gtk.accelerator_get_default_mod_mask()
                accelerator_mask = state.numerator
                # If e.g. only CTRL key is pressed.
                if not gtk.accelerator_valid(event.keyval, accelerator_mask):
                    accelerator_mask = 0
                self.auto_completer.accelerator_string = gtk.accelerator_name(event.keyval, accelerator_mask)
                self.accelerator_label.set_text(gtk.accelerator_get_label(event.keyval, accelerator_mask))
                # Reset widgets
                set_key_button.set_active(False)
                set_widgets_sensitive(True)

        self.config_dialog_signal_handlers = {
            "on_enable_auto_completion_checkbutton_toggled": on_enable_completion_toggled,
            "on_show_filechooser_checkbutton_toggled": on_show_filechooser_toggled,
            "on_config_dialog_button_close_clicked": on_close,
            "on_visible_rows_spinbutton_value_changed": on_max_rows_changed,
            "on_completion_config_dialog_delete_event": on_close,
            "on_set_completion_accelerator_button_pressed": set_accelerator,
            "on_completion_config_dialog_key_release_event": on_completion_config_dialog_key_release_event,
            }

gobject.type_register(PathChooserComboBox)

if __name__ == "__main__":
    w = gtk.Window()
    w.set_position(gtk.WIN_POS_CENTER)
    w.set_size_request(600, -1)
    w.set_title('ComboEntry example')
    w.connect('delete-event', gtk.main_quit)

    box1 = gtk.VBox(gtk.FALSE, 0)

    entry1 = PathChooserComboBox()
    entry2 = PathChooserComboBox()

    box1.add(entry1)
    box1.add(entry2)

    paths = ["/media/Movies-HD",
             "/storage/media/media/media/Series/Grounded for life/Season 2/",
             "/media/torrent/in",
             "/media/Live-show/Misc",
             "/media/Live-show/Consert",
             "/media/Series/1/",
             "/media/Series/2",
             "/media/Series/3",
             "/media/Series/4",
             "/media/Series/5",
             "/media/Series/6",
             "/media/Series/7",
             "/media/Series/8",
             "/media/Series/9",
             "/media/Series/10",
             "/media/Series/11",
             "/media/Series/12",
             "/media/Series/13",
             "/media/Series/14",
             "/media/Series/15",
             "/media/Series/16",
             "/media/Series/17",
             "/media/Series/18",
             "/media/Series/19"
             ]

    entry1.add_values(paths)
    #entry1.set_text("/media/Series/5")
    entry1.set_text("/")

    entry1.set_filechooser_visible(False)

    def list_value_added_event(widget, values):
        print "Current list values:", widget.get_values()

    entry1.connect("list-value-added", list_value_added_event)
    entry2.connect("list-value-added", list_value_added_event)
    w.add(box1)
    w.show_all()
    gtk.main()
