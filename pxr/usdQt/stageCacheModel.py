#
# Copyright 2016 Pixar
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

from ._Qt import QtCore

if False:
    from typing import *
    from pxr import Usd


class StageCacheModel(QtCore.QAbstractTableModel):
    """A stage cache model exposes the stages a cache is holding to Qt.

    The stage cache model by default exposes the root layer in column 0 and
    the session layer in column 1.  Even though this is an abstract table model,
    this code often will be paired with a QListItemView to selection a stage
    from a stage cache to edit.

    Currently, this isn't very efficient as it makes repeated queries to
    GetAllStages.  There are rarely all that many stages open so this shouldn't
    be problmatic, but we should reevaluate the implementation.

    Storing the cache membership directly doesn't work, as this can
    change over time.  However, if stage cache membership changes were backed
    by an UsdNotice, we could know when to flush and update our own internal
    cache membership list.
    """
    def __init__(self, stageCache, parent=None):
        # type: (Usd.StageCache, Optional[QtCore.QObject]) -> None
        """
        Parameters
        ----------
        stageCache : Usd.StageCache
        parent : Optional[QtCore.QObject]
        """
        super(StageCacheModel, self).__init__(parent=parent)
        self._stageCache = stageCache

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._stageCache.GetAllStages())

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return self._stageCache.GetAllStages()[index.row()].GetRootLayer().identifier
            elif index.column() == 1:
                return self._stageCache.GetAllStages()[index.row()].GetSessionLayer().identifier
        # return super(StageCacheModel, self).data(index, role)

    def GetStageForIndex(self, index):
        # type: (QtCore.QModelIndex) -> Usd.Stage
        """Retrieve the UsdStage associated with the row of index

        Parameters
        ----------
        index : QtCore.QModelIndex

        Returns
        -------
        Usd.Stage
        """
        return self._stageCache.GetAllStages()[index.row()]


if __name__ == '__main__':
    """
    Sample usage
    """
    import os
    from pxr import Usd, UsdUtils
    from ._Qt import QtWidgets
    import sys
    app = QtWidgets.QApplication([])

    stageCache = UsdUtils.StageCache.Get()
    dir = os.path.split(__file__)[0]
    path = os.path.join(
        dir, 'testenv', 'testUsdQtOpinionModel', 'simple.usda')
    with Usd.StageCacheContext(stageCache):
        stage1 = Usd.Stage.CreateInMemory()
        stage2 = Usd.Stage.Open(path)
        stage3 = Usd.Stage.CreateInMemory()

    comboBox = QtWidgets.QComboBox()
    model = StageCacheModel(stageCache)
    comboBox.setModel(model)
    comboBox.show()

    sys.exit(app.exec_())
