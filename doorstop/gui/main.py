#!/usr/bin/env python

"""Graphical interface for Doorstop."""

import os
import sys
from unittest.mock import Mock
try:  # pragma: no cover (manual test)
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog
    from tkinter import messagebox as tkMessageBox
except ImportError as _exc:  # pragma: no cover (manual test)
    sys.stderr.write("WARNING: {}\n".format(_exc))
    tk = Mock()
    ttk = Mock()

import argparse
import functools
from itertools import chain
import logging

from typing import Any
from typing import Optional
from typing import Sequence

from doorstop.gui import widget
from doorstop.gui import utilTkinter

from doorstop import common
from doorstop.common import HelpFormatter, WarningFormatter, DoorstopError
from doorstop import settings
from doorstop.core.types import UID

from doorstop.gui.action import Action_ChangeProjectPath
from doorstop.gui.action import Action_LoadProject
from doorstop.gui.action import Action_SaveProject
from doorstop.gui.action import Action_CloseProject
from doorstop.gui.action import Action_ChangeCWD
from doorstop.gui.action import Action_ChangeSelectedDocument
from doorstop.gui.action import Action_ChangeSelectedItem
from doorstop.gui.action import Action_ChangeItemText
from doorstop.gui.action import Action_ChangeItemReference
from doorstop.gui.action import Action_ChangeItemActive
from doorstop.gui.action import Action_ChangeItemDerived
from doorstop.gui.action import Action_ChangeItemNormative
from doorstop.gui.action import Action_ChangeItemHeading
from doorstop.gui.action import Action_ChangeLinkInception
from doorstop.gui.action import Action_ChangeItemAddLink
from doorstop.gui.action import Action_ChangeSelectedLink
from doorstop.gui.action import Action_ChangeItemRemoveLink
from doorstop.gui.action import Action_ChangeExtendedName
from doorstop.gui.action import Action_ChangeExtendedValue

from doorstop.gui.reducer import Reducer_GUI
from doorstop.gui.store import Store
from doorstop.gui.state import State

log = common.logger(__name__)


def main(args: Sequence[str] = tuple()) -> int:
    """Process command-line arguments and run the program."""
    from doorstop import GUI, VERSION

    # Shared options
    debug = argparse.ArgumentParser(add_help=False)
    debug.add_argument('-V', '--version', action='version', version=VERSION)
    debug.add_argument('-v', '--verbose', action='count', default=0,
                       help="enable verbose logging")
    shared = {'formatter_class': HelpFormatter, 'parents': [debug]}
    parser = argparse.ArgumentParser(prog=GUI, description=__doc__, **shared)

    # Build main parser
    parser.add_argument('-j', '--project', metavar="PATH",
                        help="path to the root of the project")

    # Parse arguments
    args = parser.parse_args(args=args)

    # Configure logging
    _configure_logging(args.verbose)

    # Run the program
    try:
        success = run(args, os.getcwd(), parser.error)
    except KeyboardInterrupt:
        log.debug("program interrupted")
        success = False
    if success:
        log.debug("program exited")
        return 0
    else:
        log.debug("program exited with error")
        return 1


def _configure_logging(verbosity: int = 0) -> None:
    """Configure logging using the provided verbosity level (0+)."""
    # Configure the logging level and format
    if verbosity == 0:
        level = settings.VERBOSE_LOGGING_LEVEL
        default_format = settings.VERBOSE_LOGGING_FORMAT
        verbose_format = settings.VERBOSE_LOGGING_FORMAT
    elif verbosity == 1:
        level = settings.VERBOSE2_LOGGING_LEVEL
        default_format = settings.VERBOSE_LOGGING_FORMAT
        verbose_format = settings.VERBOSE_LOGGING_FORMAT
    else:
        level = settings.VERBOSE2_LOGGING_LEVEL
        default_format = settings.TIMED_LOGGING_FORMAT
        verbose_format = settings.TIMED_LOGGING_FORMAT

    # Set a custom formatter
    logging.basicConfig(level=level)
    formatter = WarningFormatter(default_format, verbose_format)
    logging.root.handlers[0].setFormatter(formatter)


def run(args: argparse.Namespace, cwd: str, error):
    """Start the GUI.

    :param args: Namespace of CLI arguments (from this module or the CLI)
    :param cwd: current working directory
    :param error: function to call for CLI errors

    """
    from doorstop import __project__, __version__
    # Exit if tkinter is not available
    if isinstance(tk, Mock) or isinstance(ttk, Mock):
        return error("tkinter is not available")

    else:  # pragma: no cover (manual test)

        store = Store(Reducer_GUI(), State())

        # Load values provided by parameters
        store.dispatch(Action_ChangeCWD(cwd))
        store.dispatch(Action_ChangeProjectPath(args.project))

        root = widget.Tk()

        if True:  # Load the icon
            from sys import platform as _platform
            if _platform in ("linux", "linux2"):
                # linux
                from doorstop.gui import resources
                root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(data=resources.b64_doorstopicon_png))  # pylint: disable=W0212
            elif _platform == "darwin":
                # MAC OS X
                pass  # TODO
            elif _platform in ("win32", "win64"):
                # Windows
                from doorstop.gui import resources
                import base64
                import tempfile
                try:
                    with tempfile.TemporaryFile(mode='w+b', suffix=".ico", delete=False) as theTempIconFile:
                        theTempIconFile.write(base64.b64decode(resources.b64_doorstopicon_ico))
                        theTempIconFile.flush()
                    root.iconbitmap(theTempIconFile.name)
                finally:
                    try:
                        os.unlink(theTempIconFile.name)
                    except Exception:  # pylint: disable=W0703
                        pass

        if True:  # Set the application title
            def refreshTitle(store: Optional[Store]) -> None:
                project_path = ""
                pending_change = False
                if store:
                    state = store.state
                    if state:
                        project_path = state.project_path
                        pending_change = state.session_pending_change
                root.title("{} ({}){}{}".format(__project__, __version__, "*" if pending_change else "", (" - " + project_path) if project_path else ""))
            store.add_observer(lambda store: refreshTitle(store))

        app = Application(root, store)

        root.update()
        root.minsize(root.winfo_width(), root.winfo_height())
        app.mainloop()

        return True


def _log(func):  # pragma: no cover (manual test)
    """Log name and arguments."""
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        sargs = "{}, {}".format(', '.join(repr(a) for a in args),
                                ', '.join("{}={}".format(k, repr(v))
                                          for k, v in kwargs.items()))
        msg = "log: {}: {}".format(func.__name__, sargs.strip(", "))
        if not isinstance(self, ttk.Frame):
            log.debug(msg.strip())
        return func(self, *args, **kwargs)
    return wrapped


class Application(ttk.Frame):  # pragma: no cover (manual test), pylint: disable=R0901,R0902
    """Graphical application for Doorstop."""

    def __init__(self, parent: tk.Frame, store: Store) -> None:
        ttk.Frame.__init__(self, parent)

        # Create Doorstop variables
        self.store = store  # TODO: Remove this attribute

        def do_close_project() -> bool:
            current_state = store.state
            if current_state and current_state.session_pending_change:
                result = tkMessageBox.askyesnocancel("Pending changes", "There are unsaved changes, do you want to save them?", icon='warning', default=tkMessageBox.YES, parent=self)
                if result is None:  # Cancel
                    return False
                elif result:  # Yes
                    store.dispatch(Action_SaveProject())
                else:  # NO
                    pass
            store.dispatch(Action_CloseProject())
            return True

        def do_open_project() -> bool:
            requested_path = filedialog.askdirectory()
            if requested_path:
                if do_close_project():
                    store.dispatch(Action_ChangeProjectPath(requested_path))
                    return True
            return False

        def do_load_project() -> bool:
            if do_close_project():
                store.dispatch(Action_LoadProject())
                return True
            return False

        def do_quit() -> bool:
            if do_close_project():
                parent.quit()
                return True
            return False

        def do_save_all_project() -> None:
            store.dispatch(Action_SaveProject())

        if True:  # Set the menu
            menubar = tk.Menu(parent)
            filemenu = tk.Menu(menubar, tearoff=0)
            filemenu.add_command(label="Open Project", command=do_open_project)
            filemenu.add_command(label="Reload Project", command=do_load_project)
            filemenu.add_command(label="Save All", command=do_save_all_project)
            filemenu.add_command(label="Close Project", command=do_close_project)
            filemenu.add_separator()
            filemenu.add_command(label="Exit", command=do_quit)
            menubar.add_cascade(label="File", menu=filemenu)

            viewmenu = tk.Menu(menubar, tearoff=0)
            viewmenu.add_command(label="Reduce font size", command=lambda: widget.adjustFontSize(-1))
            viewmenu.add_command(label="Increase font size", command=lambda: widget.adjustFontSize(1))
            viewmenu.add_command(label="Reset font size", command=lambda: widget.resetFontSize())
            menubar.add_cascade(label="View", menu=viewmenu)

            parent.config(menu=menubar)

            def refreshMenu(store: Optional[Store]) -> None:
                project_path = None
                state = None
                if store:
                    state = store.state
                    if state:
                        project_path = state.project_path
                filemenu.entryconfig("Reload Project", state=tk.NORMAL if project_path else tk.DISABLED)
                filemenu.entryconfig("Save All", state=tk.NORMAL if project_path else tk.DISABLED)
                filemenu.entryconfig("Close Project", state=tk.NORMAL if project_path else tk.DISABLED)
            store.add_observer(lambda store: refreshMenu(store))

        # TODO The following variables should be remove (use store instead)
        self.document = None
        self.item = None

        self.stringvar_extendedkey = tk.StringVar()
        self.stringvar_extendedkey.trace('w', self.display_extended)
        self.stringvar_extendedvalue = tk.StringVar()
        self.stringvar_extendedvalue.trace('w', self.update_item)

        # Create widget variables
        self.combobox_extended = None
        self.text_extendedvalue = None

        # Initialize the GUI
        frame = self.init(parent, store)
        frame.pack(fill=tk.BOTH, expand=1)

    def init(self, root: tk.Frame, store: Store) -> ttk.Frame:
        """Initialize and return the main frame."""
        # Shared arguments
        width_text = 30
        width_uid = 10
        height_text = 10
        height_ext = 5

        # Shared keyword arguments
        kw_f = {'padding': 5}  # constructor arguments for frames
        kw_gp = {'padx': 2, 'pady': 2}  # grid arguments for padded widgets
        kw_gs = {'sticky': tk.NSEW}  # grid arguments for sticky widgets
        kw_gsp = dict(chain(kw_gs.items(), kw_gp.items()))  # grid arguments for sticky padded widgets

        root.bind_all("<Control-minus>", lambda arg: widget.adjustFontSize(-1))
        root.bind_all("<Control-equal>", lambda arg: widget.adjustFontSize(1))
        root.bind_all("<Control-0>", lambda arg: widget.resetFontSize())

        # Configure grid
        result_frame = ttk.Frame(root, **kw_f)
        result_frame.rowconfigure(0, weight=0)
        result_frame.columnconfigure(0, weight=1)
        result_frame.columnconfigure(1, weight=1)
        result_frame.columnconfigure(2, weight=1)

        def frame_document(root) -> ttk.Frame:
            """Frame for current document's outline."""
            # Configure grid
            frame = ttk.Frame(root, **kw_f)
            frame.rowconfigure(0, weight=0)  # Label
            frame.rowconfigure(1, weight=0)  # Combobox
            frame.rowconfigure(2, weight=1)  # TreeView
            frame.rowconfigure(3, weight=0)  # Button
            frame.columnconfigure(0, weight=0)  # Slider
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(2, weight=1)
            frame.columnconfigure(3, weight=1)
            frame.columnconfigure(4, weight=1)
            frame.columnconfigure(5, weight=1)
            frame.columnconfigure(6, weight=1)

            @_log
            def treeview_outline_treeviewselect(event):
                """Handle selecting an item in the tree view."""
                store.dispatch(Action_ChangeSelectedItem(event.widget.selection()))

            # Place widgets
            widget.Label(frame, text="Document:").grid(row=0, column=0, columnspan=7, sticky=tk.W, **kw_gp)

            combobox_documents = widget.Combobox(frame, state="readonly")
            combobox_documents.grid(row=1, column=1, columnspan=6, **kw_gsp)

            # Display the information
            def refreshDocumentComboboxContent(store: Optional[Store]) -> None:
                state = None
                project_tree = None
                if store:
                    state = store.state
                    if state:
                        project_tree = state.project_tree
                documents = [document for document in project_tree] if project_tree else []
                combobox_documents['values'] = ["{} ({})".format(document.prefix, document.relpath) for document in documents]

                def handle_document_combobox_selectionchange(*event: Any) -> None:
                    if store:
                        store.dispatch(Action_ChangeSelectedDocument(documents[combobox_documents.current()].prefix))
                combobox_documents.bind("<<ComboboxSelected>>", handle_document_combobox_selectionchange)

                # Set the document Selection
                selected_document_prefix = state.session_selected_document if state else None
                for index, item in enumerate(documents):
                    if selected_document_prefix == item.prefix:
                        combobox_documents.current(index)
                        break
                else:
                    logging.warning("no documents to display")
                    combobox_documents.set("")

            store.add_observer(lambda store: refreshDocumentComboboxContent(store))

            c_columnId = ("Id",)
            treeview_outline = widget.TreeView(frame, columns=c_columnId)  # pylint: disable=W0201
            for col in c_columnId:
                treeview_outline.heading(col, text=col)

            def refresh_document_outline(store: Optional[Store]) -> None:  # Refresh the document outline
                state = store.state if store else None

                # Record the currently opened items.
                c_openItem = []
                for c_currUID in utilTkinter.getAllChildren(treeview_outline):
                    if treeview_outline.item(c_currUID)["open"]:
                        c_openItem.append(c_currUID)

                # Clear the widgets
                treeview_outline.delete(*treeview_outline.get_children())

                # Display the items in the document
                c_levelsItem = [""]
                project_tree = None if state is None else state.project_tree
                for item in [] if project_tree is None else project_tree.find_document(state.session_selected_document).items:
                    theParent = next(iter(reversed([x for x in c_levelsItem[:item.depth]])), "")

                    while len(c_levelsItem) < item.depth:
                        c_levelsItem.append(item.uid)
                    c_levelsItem = c_levelsItem[:item.depth]
                    for _ in range(item.depth):
                        c_levelsItem.append(item.uid)

                    # Add the item to the document outline
                    treeview_outline.insert(theParent, tk.END, item.uid, text=item.level, values=(item.uid,), open=item.uid in c_openItem)

                # Set tree view selection
                c_selectedItem = state.session_selected_item if state else []
                if c_selectedItem:
                    # Restore selection
                    session_selected_item_principal = state.session_selected_item_principal
                    treeview_outline.selection_set(c_selectedItem)
                    treeview_outline.focus(session_selected_item_principal)
                    treeview_outline.see(session_selected_item_principal)
                else:
                    # Select the first item
                    for uid in utilTkinter.getAllChildren(treeview_outline):
                        assert False, uid
                        break
                    else:
                        logging.warning("no items to display")

            store.add_observer(lambda store: refresh_document_outline(store))

            # Add a Vertical scrollbar to the Treeview Outline
            treeview_outline_verticalScrollBar = widget.ScrollbarV(frame, command=treeview_outline.yview)
            treeview_outline_verticalScrollBar.grid(row=2, column=0, columnspan=1, **kw_gs)
            treeview_outline.configure(yscrollcommand=treeview_outline_verticalScrollBar.set)
            treeview_outline.bind("<<TreeviewSelect>>", treeview_outline_treeviewselect)
            treeview_outline.bind("<Delete>", self.remove)
            treeview_outline.grid(row=2, column=1, columnspan=6, **kw_gsp)

            widget.Button(frame, text="<", width=0, command=self.left).grid(row=3, column=1, sticky=tk.EW, padx=(2, 0))
            widget.Button(frame, text="v", width=0, command=self.down).grid(row=3, column=2, sticky=tk.EW)
            widget.Button(frame, text="^", width=0, command=self.up).grid(row=3, column=3, sticky=tk.EW)
            widget.Button(frame, text=">", width=0, command=self.right).grid(row=3, column=4, sticky=tk.EW, padx=(0, 2))
            widget.Button(frame, text="Add Item", command=self.add).grid(row=3, column=5, sticky=tk.W, **kw_gp)
            widget.Button(frame, text="Remove Selected Item", command=self.remove).grid(row=3, column=6, sticky=tk.E, **kw_gp)

            return frame

        def frame_item(root):
            """Frame for the currently selected item."""
            # Configure grid
            frame = ttk.Frame(root, **kw_f)
            frame.rowconfigure(0, weight=0)
            frame.rowconfigure(1, weight=4)
            frame.rowconfigure(2, weight=0)
            frame.rowconfigure(3, weight=1)
            frame.rowconfigure(4, weight=1)
            frame.rowconfigure(5, weight=1)
            frame.rowconfigure(6, weight=1)
            frame.rowconfigure(7, weight=0)
            frame.rowconfigure(8, weight=0)
            frame.rowconfigure(9, weight=0)
            frame.rowconfigure(10, weight=0)
            frame.rowconfigure(11, weight=4)
            frame.columnconfigure(0, weight=0, pad=kw_f['padding'] * 2)
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(2, weight=1)

            @_log
            def text_item_focusout(event: Any) -> None:
                """Handle updated item text."""
                store = self.store
                state = store.state
                if state:
                    thewidget = event.widget
                    value = thewidget.get('1.0', tk.END)
                    item_uid = state.session_selected_item_principal
                    if item_uid:
                        self.store.dispatch(Action_ChangeItemText(item_uid, value))

            @_log
            def text_item_reference_focusout(event: Any) -> None:
                """Handle updated item reference text."""
                store = self.store
                if store is not None:
                    state = store.state
                    if state is not None:
                        thewidget = event.widget
                        value = thewidget.get()
                        item_uid = state.session_selected_item_principal
                        if item_uid:
                            self.store.dispatch(Action_ChangeItemReference(item_uid, value))

            @_log
            def text_extendedvalue_focusout(event) -> None:
                """Handle updated extended attributes."""
                store = self.store
                if store is not None:
                    state = store.state
                    if state is not None:
                        thewidget = event.widget
                        value = thewidget.get('1.0', tk.END)
                        item_uid = state.session_selected_item_principal
                        if item_uid:
                            self.store.dispatch(Action_ChangeExtendedValue(item_uid, state.session_extended_name, value))

            # Place widgets
            widget.Label(frame, text="Selected Item:").grid(row=0, column=0, columnspan=3, sticky=tk.W, **kw_gp)

            if True:  # Item text
                text_item = widget.Text(frame, width=width_text, height=height_text, wrap=tk.WORD)
                text_item.bind('<FocusOut>', text_item_focusout)
                text_item.grid(row=1, column=0, columnspan=3, **kw_gsp)

                def refreshItemText(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    log.info("displaying item {}...".format(session_selected_item_principal))
                    text_item.replace('1.0', tk.END, "" if item is None else item.text)
                store.add_observer(lambda store: refreshItemText(store))

            widget.Label(frame, text="Properties:").grid(row=2, column=0, sticky=tk.W, **kw_gp)
            widget.Label(frame, text="Links:").grid(row=2, column=1, columnspan=2, sticky=tk.W, **kw_gp)

            if True:  # CheckBox active
                checkbox_active_var = tk.BooleanVar()

                def doChangeActive() -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    if item:
                        store.dispatch(Action_ChangeItemActive(item, checkbox_active_var.get()))
                checkbox_active = widget.Checkbutton(frame, command=doChangeActive, variable=checkbox_active_var, text="Active")
                checkbox_active.grid(row=3, column=0, sticky=tk.W, **kw_gp)

                def refreshCheckButtonActive(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                        checkbox_active_var.set(bool(item and item.active))
                    except DoorstopError:
                        item = None
                store.add_observer(lambda store: refreshCheckButtonActive(store))

            if True:  # CheckBox derived
                checkbox_derived_var = tk.BooleanVar()

                def doChangeDerived() -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    if item:
                        store.dispatch(Action_ChangeItemDerived(item, checkbox_derived_var.get()))

                checkbox_derived = widget.Checkbutton(frame, command=doChangeDerived, variable=checkbox_derived_var, text="Derived")
                checkbox_derived.grid(row=4, column=0, sticky=tk.W, **kw_gp)

                def refreshCheckButtonDerived(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                        checkbox_derived_var.set(bool(item and item.derived))
                    except DoorstopError:
                        item = None
                store.add_observer(lambda store: refreshCheckButtonDerived(store))

            if True:  # CheckBox normative
                checkbox_normative_var = tk.BooleanVar()

                def doChangeNormative() -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    if item:
                        store.dispatch(Action_ChangeItemNormative(item, checkbox_normative_var.get()))
                checkbox_normative = widget.Checkbutton(frame, command=doChangeNormative, variable=checkbox_normative_var, text="Normative")
                checkbox_normative.grid(row=5, column=0, sticky=tk.W, **kw_gp)

                def refreshCheckButtonNormative(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                        checkbox_normative_var.set(bool(item and item.normative))
                    except DoorstopError:
                        item = None
                store.add_observer(lambda store: refreshCheckButtonNormative(store))

            if True:  # CheckBox heading
                checkbox_heading_var = tk.BooleanVar()

                def doChangeHeading() -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    if item:
                        store.dispatch(Action_ChangeItemHeading(item, checkbox_heading_var.get()))

                checkbox_heading = widget.Checkbutton(frame, command=doChangeHeading, variable=checkbox_heading_var, text="Heading")
                checkbox_heading.grid(row=6, column=0, sticky=tk.W, **kw_gp)

                def refreshCheckButtonHeading(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                        checkbox_heading_var.set(bool(item and item.heading))
                    except DoorstopError:
                        item = None
                store.add_observer(lambda store: refreshCheckButtonHeading(store))

            if True:  # Listbox Links
                listbox_links = widget.Listbox(frame, width=width_uid, height=6, selectmode=tk.EXTENDED, exportselection=tk.OFF)
                listbox_links.grid(row=3, column=1, rowspan=4, **kw_gsp)

                def refreshListBoxLinks(store: Optional[Store]) -> None:
                    previous_active_index = listbox_links.index(tk.ACTIVE)
                    previous_active_item = listbox_links.get(previous_active_index)

                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    session_selected_link = state.session_selected_link if state else []
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    listbox_links.delete(0, tk.END)
                    if item is not None:
                        v_new_index = -1
                        next_active = None
                        for uid in sorted([x for x in item.links if (("" == state.session_link_inception) or (state.session_link_inception in str(x)))], key=lambda x: str(x), reverse=False):
                            v_new_index += 1
                            listbox_links.insert(tk.END, uid)
                            if str(uid) in session_selected_link:
                                listbox_links.selection_set(listbox_links.index(tk.END) - 1)
                            if str(uid) == str(previous_active_item):
                                next_active = v_new_index

                        if next_active is None:
                            next_active = min(previous_active_index, listbox_links.size() - 1)
                        if 0 <= next_active:
                            listbox_links.activate(next_active)
                            listbox_links.see(next_active)

                store.add_observer(lambda store: refreshListBoxLinks(store))

                def handle_document_listbox_selectionchange(evt) -> None:
                    w = evt.widget
                    the_selection = w.curselection()

                    a = frozenset([w.get(int(i)) for i in the_selection])
                    b = frozenset([w.get(int(i)) for i in range(0, w.size()) if i not in [int(j) for j in the_selection]])
                    store.dispatch(Action_ChangeSelectedLink(selected_link=a, unselected_link=b))

                listbox_links.bind('<<ListboxSelect>>', handle_document_listbox_selectionchange)

            if True:  # Entry link inception

                entry_link_inception = widget.Entry(frame, width=width_uid)

                def doChangeInceptionLink():
                    store.dispatch(Action_ChangeLinkInception(entry_link_inception.get()))
                entry_link_inception.bind("<KeyRelease>", lambda event: doChangeInceptionLink())
                entry_link_inception.grid(row=3, column=2, sticky=tk.EW + tk.N, **kw_gp)

                def refreshEntryLinkInception(store: Optional[Store]) -> None:
                    the_link_inception = ""
                    state = store.state if store else None
                    if state is not None:
                        the_link_inception = state.session_link_inception
                    if the_link_inception != entry_link_inception.get():
                        entry_link_inception.delete('0', tk.END)
                        entry_link_inception.insert('0', state.session_link_inception)
                store.add_observer(lambda store: refreshEntryLinkInception(store))

            widget.Button(frame, text="<< Link Item", command=self.link).grid(row=4, column=2, **kw_gp)
            widget.Button(frame, text=">> Unlink Item", command=self.unlink).grid(row=6, column=2, **kw_gp)
            widget.Label(frame, text="External Reference:").grid(row=7, column=0, columnspan=3, sticky=tk.W, **kw_gp)

            if True:  # Item External Reference
                text_item_reference = widget.Entry(frame, width=width_text)
                text_item_reference.bind('<FocusOut>', text_item_reference_focusout)
                text_item_reference.grid(row=8, column=0, columnspan=3, **kw_gsp)

                def refreshItemReference(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None
                    text_item_reference.delete(0, tk.END)
                    text_item_reference.insert(0, "" if item is None else item.ref)
                store.add_observer(lambda store: refreshItemReference(store))

            widget.Label(frame, text="Extended Attributes:").grid(row=9, column=0, columnspan=3, sticky=tk.W, **kw_gp)

            if True:  # Combobox Extended attribute Name
                combobox_extended = widget.Combobox(frame)
                combobox_extended.grid(row=10, column=0, columnspan=3, **kw_gsp)

                def refreshComboboxExtendedName(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None

                    values = None if item is None else item.extended
                    combobox_extended['values'] = values or []
                    combobox_extended.delete(0, tk.END)
                    if state is not None and state.session_extended_name:
                        combobox_extended.insert(0, state.session_extended_name)

                store.add_observer(lambda store: refreshComboboxExtendedName(store))

                def handle_extended_name_combobox_selectionchange(*event: Any) -> None:
                    if store:
                        store.dispatch(Action_ChangeExtendedName(combobox_extended.get()))
                combobox_extended.bind("<<ComboboxSelected>>", handle_extended_name_combobox_selectionchange)
                combobox_extended.bind("<KeyRelease>", handle_extended_name_combobox_selectionchange)

            if True:  # Textbox Extended attribute Value
                text_extendedvalue = widget.Text(frame, width=width_text, height=height_ext, wrap=tk.WORD)
                text_extendedvalue.grid(row=11, column=0, columnspan=3, **kw_gsp)

                def refreshTextboxExtendedValue(store: Optional[Store]) -> None:
                    state = store.state if store else None
                    session_selected_item_principal = state.session_selected_item_principal if state else None
                    project_tree = state.project_tree if state else None
                    try:
                        item = project_tree.find_item(session_selected_item_principal) if project_tree else None
                    except DoorstopError:
                        item = None

                    value = "" if item is None else item.get(state.session_extended_name)
                    text_extendedvalue.delete(1.0, tk.END)
                    if state is not None and state.session_extended_name:
                        if value:
                            text_extendedvalue.insert(tk.END, value)

                store.add_observer(lambda store: refreshTextboxExtendedValue(store))

                text_extendedvalue.bind('<FocusOut>', text_extendedvalue_focusout)

            return frame

        def frame_family(root):
            """Frame for the parent and child document items."""
            # Configure grid
            frame = ttk.Frame(root, **kw_f)
            frame.rowconfigure(0, weight=0)
            frame.rowconfigure(1, weight=1)
            frame.rowconfigure(2, weight=0)
            frame.rowconfigure(3, weight=1)
            frame.columnconfigure(0, weight=1)

            # Place widgets Text Parents
            widget.Label(frame, text="Linked To:").grid(row=0, column=0, sticky=tk.W, **kw_gp)
            text_parents = widget.noUserInput_init(widget.Text(frame, width=width_text, wrap=tk.WORD))
            text_parents_hyperlink = utilTkinter.HyperlinkManager(text_parents)  # pylint: disable=W0201
            text_parents.grid(row=1, column=0, **kw_gsp)

            def refresh_text_parents(store: Optional[Store]) -> None:
                # Display the items this item links to
                store = self.store
                state = store.state
                if state is not None:
                    widget.noUserInput_delete(text_parents, '1.0', tk.END)
                    text_parents_hyperlink.reset()
                    if state.session_selected_item_principal is not None:
                        for uid in state.project_tree.find_item(state.session_selected_item_principal).links:
                            try:
                                item = state.project_tree.find_item(uid)
                            except DoorstopError:
                                text = "???"
                            else:
                                text = item.text or item.ref or '???'
                                uid = item.uid

                            widget.noUserInput_insert(text_parents, tk.END, "{t}".format(t=text))
                            widget.noUserInput_insert(text_parents, tk.END, " [")
                            widget.noUserInput_insert(text_parents, tk.END, uid, text_parents_hyperlink.add(lambda c_theURL: self.followlink(c_theURL), uid, ["refLink"]))  # pylint: disable=W0108
                            widget.noUserInput_insert(text_parents, tk.END, "]\n\n")
            store.add_observer(lambda store: refresh_text_parents(store))

            widget.Label(frame, text="Linked From:").grid(row=2, column=0, sticky=tk.W, **kw_gp)
            text_children = widget.noUserInput_init(widget.Text(frame, width=width_text, wrap=tk.WORD))
            text_children_hyperlink = utilTkinter.HyperlinkManager(text_children)  # pylint: disable=W0201
            text_children.grid(row=3, column=0, **kw_gsp)

            def refresh_text_children(store: Optional[Store]) -> None:
                # Display the items this item links to
                store = self.store
                state = store.state
                if state is not None:
                    # Display the items this item has links from
                    widget.noUserInput_delete(text_children, '1.0', 'end')
                    text_children_hyperlink.reset()
                    if state.session_selected_item_principal is not None:
                        parent_item = state.project_tree.find_item(state.session_selected_item_principal)
                        if parent_item is not None:
                            for uid in parent_item.find_child_links():
                                item = state.project_tree.find_item(uid)
                                text = item.text or item.ref or '???'
                                uid = item.uid

                                widget.noUserInput_insert(text_children, tk.END, "{t}".format(t=text))
                                widget.noUserInput_insert(text_children, tk.END, " [")
                                widget.noUserInput_insert(text_children, tk.END, uid, text_children_hyperlink.add(lambda c_theURL: self.followlink(c_theURL), uid, ["refLink"]))  # pylint: disable=W0108
                                widget.noUserInput_insert(text_children, tk.END, "]\n\n")
            store.add_observer(lambda store: refresh_text_children(store))

            return frame

        # Place widgets
        frame_document(result_frame).grid(row=0, column=0, columnspan=1, **kw_gs)
        frame_item(result_frame).grid(row=0, column=1, columnspan=1, **kw_gs)
        frame_family(result_frame).grid(row=0, column=2, columnspan=1, **kw_gs)

        return result_frame

    @_log
    def display_extended(self, *_):
        """Display the currently selected extended attribute."""
        name = self.stringvar_extendedkey.get()
        log.debug("displaying extended attribute '{}'...".format(name))
        self.text_extendedvalue.replace('1.0', tk.END, self.item.get(name, ""))

    @_log
    def update_item(self, *_):
        """Update the current item from the fields."""
        if not self.item:
            logging.warning("no item selected")
            return

        # Update the current item
        log.info("updating {}...".format(self.item))
        name = self.stringvar_extendedkey.get()
        if name:
            self.item.set(name, self.stringvar_extendedvalue.get())

        # Re-select this item
        self.display_document()

    @_log
    def left(self):
        """Dedent the current item's level."""
        self.item.level <<= 1
        self.document.reorder(keep=self.item)
        self.display_document()

    @_log
    def down(self):
        """Increment the current item's level."""
        self.item.level += 1
        self.document.reorder(keep=self.item)
        self.display_document()

    @_log
    def up(self):
        """Decrement the current item's level."""
        self.item.level -= 1
        self.document.reorder(keep=self.item)
        self.display_document()

    @_log
    def right(self):
        """Indent the current item's level."""
        self.item.level >>= 1
        self.document.reorder(keep=self.item)
        self.display_document()

    @_log
    def add(self):
        """Add a new item to the document."""
        logging.info("adding item to {}...".format(self.document))
        if self.item:
            level = self.item.level + 1
        else:
            level = None
        item = self.document.add_item(level=level)
        logging.info("added item: {}".format(item))
        # Refresh the document view
        self.display_document()
        # Set the new selection
        self.stringvar_item.set(item.uid)

    @_log
    def remove(self):
        """Remove the selected item from the document."""
        newSelection = ""
        for c_currUID in self.treeview_outline.selection():
            # Find the item which should be selected once the current selection is removed.
            for currNeighbourStrategy in (self.treeview_outline.next, self.treeview_outline.prev, self.treeview_outline.parent):
                newSelection = currNeighbourStrategy(c_currUID)
                if newSelection != "":
                    break
            # Remove the item
            item = self.tree.find_item(c_currUID)
            logging.info("removing item {}...".format(item))
            item = self.tree.remove_item(item)
            logging.info("removed item: {}".format(item))
            # Set the new selection
            self.stringvar_item.set(newSelection)
            # Refresh the document view
            self.display_document()

    @_log
    def link(self):
        """Add the specified link to the current item."""
        store = self.store
        state = store.state
        if state:
            self.store.dispatch(Action_ChangeItemAddLink(state.session_selected_item_principal, state.session_link_inception))

    @_log
    def unlink(self) -> None:
        """Remove the currently selected link from the current item."""
        store = self.store
        state = store.state
        if state:
            uid = state.session_selected_item_principal
            if uid is not None:
                self.store.dispatch(Action_ChangeItemRemoveLink(uid, state.session_selected_link))

    @_log
    def followlink(self, uid: UID) -> None:
        """Display a given uid."""
        # Load the good document.
        self.store.dispatch(Action_ChangeSelectedDocument(uid.prefix))

        # load the good Item
        self.store.dispatch(Action_ChangeSelectedItem((uid,)))


if "__main__" == __name__:  # pragma: no cover (manual test)
    sys.exit(main())
