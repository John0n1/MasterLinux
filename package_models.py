from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtCore import QSortFilterProxyModel

class PackageListModel(QAbstractTableModel):
    def __init__(self, package_data=None):
        super().__init__()
        self._package_data = package_data if package_data else []
        self._headers = ["Remove", "Package Name", "Version"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._package_data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1:
                return self._package_data[row].get('name', '')
            elif col == 2:
                return self._package_data[row].get('version', '')
        elif role == Qt.ItemDataRole.CheckStateRole:
            if col == 0:
                return Qt.CheckState.Checked if self._package_data[row].get('remove') else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.BackgroundRole:
            status = self._package_data[row].get('status')
            if status == 'removing':
                pass
            elif status == 'removed':
                pass
            elif status == 'error':
                pass
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            self._package_data[index.row()]['remove'] = (value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        return False

    def get_checked_packages(self):
         return [pkg['name'] for pkg in self._package_data if pkg.get('remove')]

    def set_package_status(self, package_name, status):
        for row in range(len(self._package_data)):
            if self._package_data[row]['name'] == package_name:
                self._package_data[row]['status'] = status

    def clear_package_statuses(self):
        for pkg in self._package_data:
            if 'status' in pkg:
                pkg.pop('status')

class PackageSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_text = ""

    def setFilterText(self, text):
        self.filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.filter_text:
            return True
        model = self.sourceModel()
        package_name = model._package_data[source_row]['name']
        package_version = model._package_data[source_row]['version']
        return (self.filter_text in package_name.lower() or
                self.filter_text in package_version.lower())
