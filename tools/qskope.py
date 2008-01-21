#!/usr/bin/python

"""The qskope script visualizes the structure of PyFFI structures and arrays."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2008, Python File Format Interface
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the Python File Format Interface
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENCE BLOCK *****

try:
    from PyQt4 import QtGui, QtCore
except ImportError:
    raw_input("""PyQt4 not found. Please download and install from
http://www.riverbankcomputing.co.uk/pyqt/download.php""")
    raise

from PyFFI.NIF import NifFormat
from PyFFI.CGF import CgfFormat

# implementation references:
# http://doc.trolltech.com/4.3/model-view-programming.html
# http://doc.trolltech.com/4.3/model-view-model-subclassing.html
class BaseModel(QtCore.QAbstractItemModel):
    """General purpose model for QModelIndexed access to data loaded with
    PyFFI."""
    # column definitions
    NUM_COLUMNS = 3
    COL_NAME  = 0
    COL_TYPE  = 1
    COL_VALUE = 2

    def __init__(self, parent = None, blocks = None):
        """Initialize the model to display the given blocks."""
        QtCore.QAbstractItemModel.__init__(self, parent)
        # this list stores the blocks in the view
        # is a list of NiObjects for the nif format, and a list of Chunks for
        # the cgf format
        self.blocks = blocks if not blocks is None else []

    def flags(self, index):
        """Return flags for the given index: all indices are enabled and
        selectable."""
        if not index.isValid():
            return 0
        # all items are enabled and selectable
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        # determine whether item value can be set
        if index.column() == self.COL_VALUE:
            try:
                index.internalPointer().getValue()
            except AttributeError:
                pass
            except NotImplementedError:
                pass
            else:
                flags |= QtCore.Qt.ItemIsEditable
        return QtCore.Qt.ItemFlags(flags)

    def data(self, index, role):
        """Return the data of model index in a particular role."""
        # check if the index is valid
        # check if the role is supported
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        # get the data for display
        data = index.internalPointer()

        # the name column
        if index.column() == self.COL_NAME:
            # only structures have named attributes
            if data.qParent():
                # has a parent, so has a name
                return QtCore.QVariant(data.qParent().qName(data))
            else:
                # has no parent, so has no name
                return QtCore.QVariant("[%i]" % self.blocks.index(data))

        # the type column
        elif index.column() == self.COL_TYPE:
            return QtCore.QVariant(data.__class__.__name__)

        # the value column
        elif index.column() == self.COL_VALUE:
            # get the data value
            try:
                datavalue = data.getValue()
            except NotImplementedError:
                # not implemented, so there is no value
                # but there should be a string representation
                datavalue = str(data)
            except AttributeError:
                # no getValue attribute: so no value
                return QtCore.QVariant()
            try:
                # see if the data is in the blocks list
                # if so, it is a reference
                blocknum = self.blocks.index(datavalue)
            except (ValueError, TypeError):
                # not a reference: return the datavalue QVariant
                return QtCore.QVariant(str(datavalue).replace("\n", " ").replace("\r", " "))
            else:
                # handle references
                return QtCore.QVariant(
                    "[%i] %s" % (blocknum,
                                 datavalue.__class__.__name__))

        # other colums: invalid
        else:
            return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        """Return header data."""
        if (orientation == QtCore.Qt.Horizontal
            and role == QtCore.Qt.DisplayRole):
            if section == self.COL_TYPE:
                return QtCore.QVariant("Type")
            elif section == self.COL_NAME:
                return QtCore.QVariant("Name")
            if section == self.COL_VALUE:
                return QtCore.QVariant("Value")
        return QtCore.QVariant()

    def rowCount(self, parent = QtCore.QModelIndex()):
        """Calculate a row count for the given parent index."""
        if not parent.isValid():
            # top level: one row for each block
            return len(self.blocks)
        else:
            # get the parent child count
            return parent.internalPointer().qChildCount()

    def columnCount(self, parent = QtCore.QModelIndex()):
        """Return column count."""
        # column count is constant everywhere
        return self.NUM_COLUMNS

    def index(self, row, column, parent):
        """Create an index to item (row, column) of object parent.
        Internal pointers consist of the BasicBase, StructBase, or Array
        instance."""
        # check if the parent is valid
        if not parent.isValid():
            # parent is not valid, so we need a top-level object
            # return the index with row'th block as internal pointer
            data = self.blocks[row]
        else:
            # parent is valid, so we need to go get the row'th attribute
            # get the parent pointer
            data = parent.internalPointer().qChild(row)
        return self.createIndex(row, column, data)

    def parent(self, index):
        """Calculate parent of a given index."""
        # get parent structure
        parentData = index.internalPointer().qParent()
        # if no parent, then index must be top level object
        if parentData is None:
            return QtCore.QModelIndex()
        # if parent's parent is None, then index must be a member of a top
        # level object, so the parent is that top level object, so
        # parent row is index of this parent block
        elif parentData.qParent() is None:
            row = self.blocks.index(parentData)
        # finally, if parent's parent is not None, then it must be member of
        # some deeper nested structure, so calculate the row as usual
        else:
            row = parentData.qParent().qRow(parentData)
        # construct the index
        return self.createIndex(row, 0, parentData)

    def setData(self, index, value, role):
        """Set data of a given index from given QVariant value."""
        return False
        # TODO
        if role == QtCore.Qt.EditRole:
            pass

import sys
from optparse import OptionParser

def main():
    """The main script function. Does argument parsing, file type checking,
    and builds the qskope interface."""
    # parse options and positional arguments
    usage = "%prog [options] <file>"
    description = """Parse and display the file <file>."""

    parser = OptionParser(usage,
                          version = "%prog $Rev$",
                          description = description)
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("incorrect number of arguments (one required)")

    # get file
    filename = args[0]

    stream = open(filename, "rb")
    version, user_version = NifFormat.getVersion(stream)
    if version >= 0:
        blocks = NifFormat.read(stream, version, user_version,
                                rootsonly = False)
    else:
        filetype, fileversion, game = CgfFormat.getVersion(stream)
        if filetype >= 0:
            blocks, versions = CgfFormat.read(stream,
                                              fileversion = fileversion,
                                              game = game)
        else:
            app = QtGui.QApplication(sys.argv)
            label = QtGui.QLabel('File format of %s not recognized' % filename)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setMargin(10)
            label.setWindowTitle("QSkope - Error")
            label.show()
            app.exec_()
            raise RuntimeError('File format of %s not recognized' % filename)

    app = QtGui.QApplication(sys.argv)
    view = QtGui.QTreeView()
    model = BaseModel(blocks = blocks)
    view.setModel(model)
    view.setWindowTitle("QSkope - %s" % filename)
    view.setAlternatingRowColors (True)
    view.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
