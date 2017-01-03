"""
*Author* `Mateusz Wojt <mailto:mateusz.wojt@outlook.com>`_
*Version* 0.1
"""

import os

from functools import partial

# PySide
from PySide import QtCore, QtGui
from shiboken import wrapInstance

# Maya API
import maya.OpenMayaUI as omui

# PyMEL
import pymel.core as pm

# poster icons
coraline_path = os.path.join(os.path.dirname(__file__) + os.path.sep + "posters/Coraline_poster.jpg")
paranorman_path = os.path.join(os.path.dirname(__file__) + os.path.sep + "posters/ParaNorman_poster.jpg")
boxtrolls_path = os.path.join(os.path.dirname(__file__) + os.path.sep + "posters/The_Boxtrolls_poster.jpg")
kubo_path = os.path.join(os.path.dirname(__file__) + os.path.sep + "posters/Kubo_and_the_Two_Strings_poster.png")
cameraIcon = QtGui.QPixmap(os.path.join(os.path.dirname(__file__) + os.path.sep + "posters/camera.png"))


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtGui.QWidget)


class CameraRig(object):
    def __init__(self, image):
        self._image = image
        self._lock_attrs = [
            'visibility',
            'translateX',
            'translateY',
            'translateZ',
            'rotateX',
            'rotateY',
            'rotateZ',
            'scaleX',
            'scaleY',
            'scaleZ'
        ]

        self.create_rig()

    def create_rig(self):
        # create nodes
        camera_grp = pm.group(em=True, name="cameraGroup")
        camera_xform = pm.group(em=True, name="cameraMover")
        camera_node, camera_shape = pm.camera(name="camera")

        # parent under camera_grp
        pm.parent(camera_xform, camera_grp)
        pm.parent(camera_node, camera_grp)

        # connect and lock attributes
        for attr in self._lock_attrs:
            camera_xform.attr(attr).connect(camera_node.attr(attr))
            camera_node.attr(attr).lock()
            camera_node.attr(attr).setKeyable(False)

        # create image plane
        img_plane = pm.imagePlane(camera=camera_node, fileName =self._image)


class CustomItem(object):
    def __init__(self, name, release_date, domestic_gross, poster):

        self._name = name
        self._release_date = release_date
        self._domestic_gross = domestic_gross
        self._poster = poster

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def release_date(self):
        return self._release_date.toString("MMMM d, yyyy")

    @release_date.setter
    def release_date(self, value):
        self._release_date = value

    @property
    def domestic_gross(self):
        return self._domestic_gross

    @domestic_gross.setter
    def domestic_gross(self, value):
        self._domestic_gross = value

    @property
    def poster(self):
        if os.path.exists(self._poster):
            return QtGui.QPixmap(self._poster).scaledToWidth(64)

    @poster.setter
    def poster(self, value):
        self._poster = value

    @property
    def poster_path(self):
        return self._poster


class CustomButtonDelegate(QtGui.QItemDelegate):
    def __init__(self, parent=None):
        super(CustomButtonDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):

        if not self.parent().indexWidget(index):
            button = QtGui.QPushButton(
                "Create",
                self.parent(),
                clicked=partial(self.parent().buttonClicked, index)
            )
            button.setIcon(cameraIcon)

            self.parent().setIndexWidget(
                index,
                button
            )


class CustomTableView(QtGui.QTableView):
    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent=None)

        self.current_source = None

        self.setSelectionMode(self.ExtendedSelection)
        self.setDragEnabled(True)
        self.acceptDrops()
        self.setDragDropMode(self.DragDrop)
        self.setDropIndicatorShown(True)
        self.setSortingEnabled(True)
        self.setItemDelegateForColumn(4, CustomButtonDelegate(self))

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMovable(True)
        self.verticalHeader().setDefaultSectionSize(80)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setMovable(False)

        self.update()

    def buttonClicked(self, index):
        model = index.model().sourceModel()
        item = model.item(index.row())
        camera_rig = CameraRig(item.poster_path)

    def dragEnterEvent(self, event):
        event.accept()

    def startDrag(self, dropActions):
        index = self.currentIndex()
        self.current_source = index
        drag = QtGui.QDrag(self)
        mimedata = QtCore.QMimeData()
        mimedata.setData("application/x-maya-data", "laika")
        drag.setMimeData(mimedata)

        vis_rect = self.visualRect(index)
        vis_rect.translate(self.verticalHeader().sizeHint().width(), self.horizontalHeader().sizeHint().height())
        pixmap = QtGui.QPixmap()
        pixmap = pixmap.grabWidget(self, vis_rect)
        drag.setPixmap(pixmap)

        drag.start(QtCore.Qt.MoveAction)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-maya-data"):
            print "drag move event"
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-maya-data"):

            if event.source() == self:
                print "self"
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                print "not self"
                event.acceptProposedAction()

        else:
            event.ignore()



class CustomSortModel(QtGui.QSortFilterProxyModel):
    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)

        if left.column() == 0:
            return leftData < rightData
        elif left.column() == 1:
            dateLeft = QtCore.QDate.fromString(leftData, "MMMM d, yyyy")
            dateRight = QtCore.QDate.fromString(rightData, "MMMM d, yyyy")

            return dateLeft < dateRight


class CustomModel(QtCore.QAbstractTableModel):
    def __init__(self, items):
        super(CustomModel, self).__init__()
        self._items = items
        self._headers = ['Name', 'Release Date', 'Domestic gross', 'Poster', 'Create scene']

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self._items)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self._headers)

    def item(self, index):
        return self._items[index]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():

            row = index.row()
            col = index.column()

            if role == QtCore.Qt.DisplayRole:

                if col == 0:
                    return self._items[row].name
                elif col == 1:
                    return self._items[row].release_date
                elif col == 2:
                    return self._items[row].domestic_gross

            elif role == QtCore.Qt.DecorationRole:
                if col == 3:
                    return self._items[row].poster

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable
        else:
            return QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._headers[section]
            else:
                return "  {}  ".format(section)


class LaikaWidget(QtGui.QWidget):

    def __init__(self, parent=None):

        super(LaikaWidget, self).__init__(parent=parent)

        # layout
        main_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)

        # item model
        self.item_model = CustomModel(self.add_items())
        # sort model
        self.sort_model = CustomSortModel()
        self.sort_model.setSourceModel(self.item_model)

        # table view
        self.tableView = CustomTableView()
        self.tableView.setModel(self.sort_model)

        # add table to main layout
        main_layout.addWidget(self.tableView)

        self.configure_instance()

    def configure_instance(self):
        self.setWindowFlags(QtCore.Qt.Tool)
        self.resize(600, 400)
        self.setWindowTitle("Laika Movies")

    def add_items(self):
        item1 = CustomItem("Coraline", QtCore.QDate(2009, 2, 6), "124.6", coraline_path)
        item2 = CustomItem("ParaNorman", QtCore.QDate(2012, 8, 17), "107.1", paranorman_path)
        item3 = CustomItem("The Boxtrolls", QtCore.QDate(2014, 9, 28), "109.3", boxtrolls_path)
        item4 = CustomItem("Kubo and the Two Strings", QtCore.QDate(2016, 8, 19), "69.9", kubo_path)

        data = [item1, item2, item3, item4]

        return data


def show_dialog():
    dialog = LaikaWidget(parent=maya_main_window())
    dialog.show()
    return dialog

if __name__ == '__main__':
    show_dialog()