#
# Copyright 2017 Pixar
#
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#
# 6. Trademarks. This License does not grant permission to use the trade
#    names, trademarks, service marks, or product names of the Licensor
#    and its affiliates, except as required to comply with Section 4(c) of
#    the License and to reproduce the content of the NOTICE file.
#
# You may obtain a copy of the Apache License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

from pxr import Sdf

from ._Qt import QtCore, QtWidgets

if False:
    from typing import *


class TreeView(QtWidgets.QTreeView):
    """Specialization of QTreeView to add selection edit based functionality.

    Selection edits allow editing of all selected attriutes simultaneously.

    This class should be as sparse as possible.  In general, all models and
    functionality should work with QTreeView natively.

    This exists because commitData seems like the best place for selection
    based overrides. Neither the delegate nor the model have access to the
    selection model. To avoid breaking encapsulation, we use this wrapper
    class instead.
    """
    SelectedEditOff = 0
    SelectedEditColumnsOnly = 1

    def __init__(self, parent=None):
        """
        Parameters
        ----------
        parent : Optional[QtWidgets.QWidget]
        """
        super(TreeView, self).__init__(parent)
        self._selectionEditMode = TreeView.SelectedEditColumnsOnly

    def SetSelectedEditMode(self, mode):
        self._selectionEditMode = mode

    def commitData(self, editor):
        """overriden to support multiple selected index edits"""

        # TODO: Add an UndoBlock
        if self.indexWidget(self.currentIndex()) == editor:
            editorIndex = self.currentIndex()
        else:
            editorIndex = None

        if not editorIndex:
            super(TreeView, self).commitData(editor)
            return

        if self._selectionEditMode == TreeView.SelectedEditColumnsOnly:
            selection = [i for i in self.selectionModel().selectedIndexes()
                         if i.column() == editorIndex.column()
                         and i != editorIndex]
        else:
            selection = None

        # It's important to put all edits inside of an Sdf Change Block so
        # they happen in a single pass and no signals are emitted that may
        # change state
        with Sdf.ChangeBlock():
            super(TreeView, self).commitData(editor)
            if selection:
                value = editor.value
                for index in selection:
                    # This try / except is covering for a very ugly and hard
                    # to isolate bug.  It appears that when commitData
                    # raises an exception, Qt holds onto some indices that
                    # should safely expire, trigging a deferred but hard
                    # crash.  I haven't found a reliable repro case, but
                    # this seems to make it go away.  A better solution
                    # likely involves better detection on the model side.
                    try:
                        self.model().setData(index, value, QtCore.Qt.EditRole)
                    except Exception, e:
                        # TODO: We should do something better than printing to
                        # stderr
                        print("Exception during multi-edit:", e,
                            file=sys.stderr)
