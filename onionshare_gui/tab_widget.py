# -*- coding: utf-8 -*-
"""
OnionShare | https://onionshare.org/

Copyright (C) 2014-2018 Micah Lee <micah@micahflee.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from PyQt5 import QtCore, QtWidgets, QtGui

from onionshare import strings
from onionshare.mode_settings import ModeSettings

from .tab import Tab


class TabWidget(QtWidgets.QTabWidget):
    """
    A custom tab widget, that has a "+" button for adding new tabs
    """

    def __init__(self, common, system_tray, status_bar):
        super(TabWidget, self).__init__()
        self.common = common
        self.common.log("TabWidget", "__init__")

        self.system_tray = system_tray
        self.status_bar = status_bar

        # Keep track of tabs in a dictionary
        self.tabs = {}
        self.current_tab_id = 0  # Each tab has a unique id

        # Define the new tab button
        self.new_tab_button = QtWidgets.QPushButton("+", parent=self)
        self.new_tab_button.setFlat(True)
        self.new_tab_button.setAutoFillBackground(True)
        self.new_tab_button.setFixedSize(30, 30)
        self.new_tab_button.clicked.connect(self.new_tab_clicked)
        self.new_tab_button.setStyleSheet(
            self.common.gui.css["tab_widget_new_tab_button"]
        )
        self.new_tab_button.setToolTip(strings._("gui_new_tab_tooltip"))

        # Use a custom tab bar
        tab_bar = TabBar()
        tab_bar.move_new_tab_button.connect(self.move_new_tab_button)
        self.setTabBar(tab_bar)

        # Set up the tab widget
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setUsesScrollButtons(True)

        self.tabCloseRequested.connect(self.close_tab)

        self.move_new_tab_button()

    def move_new_tab_button(self):
        # Find the width of all tabs
        tabs_width = sum(
            [self.tabBar().tabRect(i).width() for i in range(self.count())]
        )

        # The current positoin of the new tab button
        pos = self.new_tab_button.pos()

        # If there are so many tabs it scrolls, move the button to the left of the scroll buttons
        if tabs_width > self.width():
            pos.setX(self.width() - 61)
        else:
            # Otherwise move the button to the right of the tabs
            pos.setX(self.tabBar().sizeHint().width())

        self.new_tab_button.move(pos)
        self.new_tab_button.raise_()

    def new_tab_clicked(self):
        # Create a new tab
        self.add_tab()

    def load_tab(self, mode_settings_id):
        # Load the tab's mode settings
        mode_settings = ModeSettings(self.common, id=mode_settings_id)
        self.add_tab(mode_settings)

    def add_tab(self, mode_settings=None):
        tab = Tab(self.common, self.current_tab_id, self.system_tray, self.status_bar)
        tab.change_title.connect(self.change_title)
        tab.change_icon.connect(self.change_icon)
        tab.change_persistent.connect(self.change_persistent)

        self.tabs[self.current_tab_id] = tab
        self.current_tab_id += 1

        index = self.addTab(tab, strings._("gui_new_tab"))
        self.setCurrentIndex(index)

        tab.init(mode_settings)
        # If it's persistent, set the persistent image in the tab
        self.change_persistent(tab.tab_id, tab.settings.get("persistent", "enabled"))

    def change_title(self, tab_id, title):
        index = self.indexOf(self.tabs[tab_id])
        self.setTabText(index, title)

    def change_icon(self, tab_id, icon_path):
        index = self.indexOf(self.tabs[tab_id])
        self.setTabIcon(index, QtGui.QIcon(self.common.get_resource_path(icon_path)))

    def change_persistent(self, tab_id, is_persistent):
        index = self.indexOf(self.tabs[tab_id])
        if is_persistent:
            self.tabBar().setTabButton(
                index,
                QtWidgets.QTabBar.LeftSide,
                self.tabs[tab_id].persistent_image_label,
            )
        else:
            invisible_widget = QtWidgets.QWidget()
            invisible_widget.setFixedSize(0, 0)
            self.tabBar().setTabButton(
                index, QtWidgets.QTabBar.LeftSide, invisible_widget
            )

        self.save_persistent_tabs()

    def save_persistent_tabs(self):
        # Figure out the order of persistent tabs to save in settings
        persistent_tabs = []
        for index in range(self.count()):
            tab = self.widget(index)
            if tab.settings.get("persistent", "enabled"):
                persistent_tabs.append(tab.settings.id)
        self.common.settings.set("persistent_tabs", persistent_tabs)
        self.common.settings.save()

    def close_tab(self, index):
        self.common.log("TabWidget", "close_tab", f"{index}")
        tab = self.widget(index)
        if tab.close_tab():
            # If the tab is persistent, delete the settings file from disk
            if tab.settings.get("persistent", "enabled"):
                tab.settings.delete()

            # Remove the tab
            self.removeTab(index)
            del self.tabs[tab.tab_id]

            # If the last tab is closed, open a new one
            if self.count() == 0:
                self.new_tab_clicked()

        self.save_persistent_tabs()

    def are_tabs_active(self):
        """
        See if there are active servers in any open tabs
        """
        for tab_id in self.tabs:
            mode = self.tabs[tab_id].get_mode()
            if mode:
                if mode.server_status.status != mode.server_status.STATUS_STOPPED:
                    return True
        return False

    def changeEvent(self, event):
        # TODO: later when I have internet, figure out the right event for re-ordering tabs

        # If tabs get move
        super(TabWidget, self).changeEvent(event)
        self.save_persistent_tabs()

    def resizeEvent(self, event):
        # Make sure to move new tab button on each resize
        super(TabWidget, self).resizeEvent(event)
        self.move_new_tab_button()


class TabBar(QtWidgets.QTabBar):
    """
    A custom tab bar
    """

    move_new_tab_button = QtCore.pyqtSignal()

    def __init__(self):
        super(TabBar, self).__init__()

    def tabLayoutChange(self):
        self.move_new_tab_button.emit()