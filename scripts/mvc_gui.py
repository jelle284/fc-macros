from mvc.core import MiniVC, MVCError
from mvc.helpers import JSONBase, FileOperation, FileID
import os
from dataclasses import dataclass

from PySide.QtWidgets import (QFileSystemModel, QTreeView,
                              QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLineEdit, QLabel, QPushButton,
                              QFileDialog, QWidget,
                              QComboBox, QInputDialog,
                              QDialog, QDialogButtonBox)
from PySide.QtCore import Qt, QTimer, QDir, QModelIndex
from PySide.QtGui import QColor



##########################################################################
#================= User settings, persistent storage ====================#
@dataclass
class UserConfig(JSONBase):
    backend_path: str
    user_name: str
    user_paths: list[str]
    
class SettingsDialog(QDialog):
    def __init__(self, default: UserConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.backend_edit = QLineEdit(default.backend_path)
        self.user_edit = QLineEdit(default.user_name)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_backend)
        form_layout = QFormLayout()
        backend_layout = QHBoxLayout()
        backend_layout.addWidget(self.backend_edit)
        backend_layout.addWidget(self.browse_button)
        form_layout.addRow("Backend Path:", backend_layout)
        form_layout.addRow("User Name:", self.user_edit)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

    def _browse_backend(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backend Directory")
        if path:
            self.backend_edit.setText(path)

##########################################################################
#======================== Confirmation dialog ===========================#

class ConfirmationDialog(QDialog):
    def __init__(self, files: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm action")
        form_layout = QFormLayout()
        form_layout.addWidget(QLabel("The following files will be overwritten!"))
        fileLabel = QLabel()
        fileLabel.setStyleSheet("border: 1px solid black;")
        fileLabel.setWordWrap(True)
        fileLabel.setText("\n".join(files))  
        form_layout.addWidget(fileLabel)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

##########################################################################
#======================== Unclaim dialog ===========================#

class UnclaimDialog(QDialog):
    def __init__(self, files: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm action")
        form_layout = QFormLayout()
        form_layout.addWidget(QLabel("One or more files are claimed by another user.")) 
        form_layout.addWidget(QLabel("Force unclaim?")) 
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

##########################################################################
#=========================== Restore dialog =============================#

class RestoreDialog(QDialog):
    def __init__(self, avaiable: list[FileID], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore")
        form_layout = QFormLayout()
        self.combo = QComboBox()
        for fid in avaiable:
            self.combo.addItem(f"{fid}")
        form_layout.addWidget(self.combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

##########################################################################
#===================== Workspace file browser ===========================#

class CheckableFileSystemModel(QFileSystemModel):
    def _check_file_type(self, index):
        filepath = self.fileName(index)
        exclude_by_filename = filepath in (
            ".mvc",
            "changelog.md",
        )
        exclude_by_extension = any(filepath.endswith(extension) for extension in (
            ".FCBak",
        ))
        file_is_forbidden = exclude_by_filename or exclude_by_extension
        return file_is_forbidden
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked_files = set()
        self.changed_files = set()
        self.claimed_files = set()
        self.file_colors = {'red': [],
                            'orange': [],
                            'green': []}

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if index in self.checked_files:
                return Qt.Checked
            else:
                return Qt.Unchecked
        if role == Qt.ForegroundRole and index.column() == 0:
            if not self.isDir(index):
                filename = os.path.basename(self.filePath(index))
                if filename in self.claimed_files:
                    return QColor("red")
                if filename in self.changed_files:
                    return QColor("orange")
                for color in self.file_colors:
                    if filename in self.file_colors[color]:
                        return QColor(color)
        return super().data(index, role)
    
    def setData(self, index, value, role=Qt.CheckStateRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if value == Qt.Checked.value:
                self.checked_files.add(index)
            else:
                self.checked_files.discard(index)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return super().setData(index, value, role)
    
    def flags(self, index):
        if self.isDir(index):
            return super().flags(index) & (~Qt.ItemIsUserCheckable)
        return super().flags(index) | Qt.ItemIsUserCheckable

    def set_files_status(self, changed_files, claimed_files):
        self.changed_files = set(changed_files)
        self.claimed_files = set(claimed_files)
        self.layoutChanged.emit()
    
    def index(self, *args):
        index = super().index(*args)
        if index.isValid() and self._check_file_type(index):
            return QModelIndex()
        return index
    
    def open_directory(self, index):
        if self.isDir(index):
            return self.filePath(index)
        return None

##########################################################################
#====================== Load or create dialog ===========================#
class LoadOrCreateDialog(QDialog):
    def __init__(self, mvc: MiniVC, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load or create project")
        form_layout = QFormLayout()
        self.projects_combo = QComboBox()
        self.projects_combo.addItems([k for k in mvc.list_projects()])
        form_layout.addWidget(self.projects_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

##########################################################################
#========================= Main GUI widget ==============================#

class MVCGui(QWidget): 
    def __init__(self, appdata_path = None):
        super(MVCGui, self).__init__()
        if not appdata_path:
            appdata_path = QDir.homePath()
        self.appdata_path = appdata_path
        try:
            self.user_config = UserConfig.load(self.appdata_path)
        except Exception as e:
            self.user_config = UserConfig(
                backend_path = f"{QDir.rootPath()}mvc-files",
                user_name = "user",
                user_paths = [QDir.rootPath(),]
            )
            print(f"Exception in load config {e}, using defaults.")
        self._file_extension_callbacks = {}
        self.initUI()
        self._updateGUI()

    def initUI(self):
        LINE_WIDTH = QLabel().sizeHint().height()
        # Buttons
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._settings)
        self.create_button = QPushButton("Create Project")
        self.create_button.clicked.connect(self._create_proj)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._submit)
        self.accept_button = QPushButton("Accept")
        self.accept_button.clicked.connect(self._accept)
        self.restore_button = QPushButton("Restore")
        self.restore_button.clicked.connect(self._restore)
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self._load)
        self.review_button = QPushButton("Review")
        self.review_button.clicked.connect(self._review)
        self.release_button = QPushButton("Release")
        self.release_button.clicked.connect(self._release)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove)
        self.claim_button = QPushButton("Claim")
        self.claim_button.clicked.connect(self._claim)
        self.unclaim_button = QPushButton("Unclaim")
        self.unclaim_button.clicked.connect(self._unclaim)

        # File browser
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self._select_all)
        self.deselect_all_button = QPushButton("Deselect All")
        self.deselect_all_button.clicked.connect(self._deselect_all)
        self.model = CheckableFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self._open_tree)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.homePath()))
        self.tree.setColumnHidden(1, True)  # Hide the 'Size' column
        self.tree.setColumnHidden(2, True)  # Hide the 'Type' column
        self.tree.setColumnHidden(3, True)  # Hide the 'Date Modified' column
        self.tree.setMinimumWidth(200)

        # Text inputs
        self.desc_edit = QLineEdit()
        self.desc_edit.setMinimumHeight(LINE_WIDTH * 5)
        self.desc_edit.setAlignment(Qt.AlignTop)

        # Text outputs
        self.infoLabel = QLabel()
        self.infoLabel.setStyleSheet("border: 1px solid black;")
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setMinimumHeight(LINE_WIDTH * 8)
        self.infoLabel.setMinimumWidth(200)
        self.projectLabel = QLabel()
        self.errLabel = QLabel()
        self.file_label = QLabel()

        # Combo boxes
        self.workspace_combo = QComboBox()
        self.workspace_combo.activated.connect(self._workspace_combo_change)

        # Left column layout
        left_col = QVBoxLayout()
        left_col.addWidget(self.settings_button)
        left_col.addWidget(self.errLabel)
        left_col.addSpacing(LINE_WIDTH)

        vbox1 = QVBoxLayout()
        vbox1.addWidget(self.create_button)
        vbox1.addWidget(self.load_button)
        left_col.addLayout(vbox1)
        left_col.addStretch(1)
        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Project status"))
        vbox2.addWidget(self.infoLabel)
        vbox2.addWidget(self.review_button)
        vbox2.addWidget(self.accept_button)
        vbox2.addWidget(self.restore_button)
        vbox2.addWidget(self.release_button)
        left_col.addLayout(vbox2)
        left_col.addStretch(3)
        
        # File column layout
        right_col = QVBoxLayout()
        right_col.addWidget(browse_button)
        right_col.addWidget(self.projectLabel)
        right_col.addWidget(self.workspace_combo)
        button_layout1 = QHBoxLayout()
        button_layout1.addWidget(self.select_all_button)
        button_layout1.addWidget(self.deselect_all_button)
        right_col.addLayout(button_layout1)
        right_col.addWidget(self.tree)
        right_col.addWidget(self.file_label)
        button_layout2 = QHBoxLayout()
        button_layout2.addWidget(self.claim_button)
        button_layout2.addWidget(self.unclaim_button)
        right_col.addLayout(button_layout2)
        right_col.addWidget(self.open_button)
        right_col.addWidget(QLabel("Description"))
        right_col.addWidget(self.desc_edit)
        right_col.addWidget(self.submit_button)
        right_col.addWidget(self.remove_button)
        
        # Main layout with columns
        mainLayout = QHBoxLayout()
        mainLayout.addLayout(left_col)
        mainLayout.addLayout(right_col)
        self.setLayout(mainLayout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)
        self.timer.start(1000)

    def _get_mvc(self):
        return MiniVC(self.user_config.backend_path, self.user_config.user_paths[0], self.user_config.user_name)
    
    def _updateGUI(self):
        current_path = self.user_config.user_paths[0]
        self.tree.setRootIndex(self.model.index(current_path))
        self.workspace_combo.clear()
        for path in self.user_config.user_paths:
            self.workspace_combo.addItem(path)
        self.workspace_combo.setCurrentIndex(0)
        allow_create = True
        allow_load = True
        workspace = None
        try:
            mvc = self._get_mvc()
            workspace = mvc._get_workspace()
            allow_load = False
            project, _= mvc._get_project(workspace.project)
            allow_create = False
            self.projectLabel.setText(f"{project.name} {project.id}")
            self.errLabel.setText("")
        except MVCError as err:
            self.errLabel.setText(f"{err}")
            self.projectLabel.setText("")
            if workspace:
                self.projectLabel.setText(workspace.project)
        self.create_button.setEnabled(allow_create)
        self.load_button.setEnabled(allow_load)

    def _set_user_path(self, path):
        try:
            self.user_config.user_paths.remove(path)
        except ValueError:
            pass
        self.user_config.user_paths.insert(0, path)
        while len(self.user_config.user_paths) > 5:
            self.user_config.user_paths.pop()
        self.user_config.save(self.appdata_path)

    def _on_timer_tick(self):
        infoText = ""
        changed_files = []
        claimed_by_others = []
        claimed_by_user = []
        try:
            mvc = self._get_mvc()
            status = mvc.status()
            if status:
                if len(status) > 10:
                    status = status[:10]
                infoText = "\n".join(status)
            changed_files = mvc.changes()
            claims = mvc.get_claims()
            for file in claims:
                if self.user_config.user_name == claims[file]:
                    claimed_by_user.append(file)
                else:
                    claimed_by_others.append(file)
            selected = self.tree.selectedIndexes()
            file_was_claimed = False
            if selected:
                selected_filename = self.model.fileName(selected[0])
                if selected_filename in claimed_by_others:
                    self.file_label.setText(f"Claimed by {claims[selected_filename]}")
                    file_was_claimed = True
            if not file_was_claimed:
                self.file_label.setText("")
        except MVCError:
            pass
        self.infoLabel.setText(infoText)
        #self.model.set_files_status(changed_files, claimed_files)
        self.model.file_colors['orange'] = changed_files
        self.model.file_colors['red'] = claimed_by_others
        self.model.file_colors['green'] = claimed_by_user

    def _workspace_combo_change(self, index):
        path = self.workspace_combo.itemText(index)
        self._set_user_path(path)
        self._updateGUI()

    def _settings(self):
        dlg = SettingsDialog(self.user_config, self)
        if dlg.exec() == QDialog.Accepted:
            self.user_config.backend_path = dlg.backend_edit.text()
            self.user_config.user_name = dlg.user_edit.text()
            self.user_config.save(self.appdata_path)
            self._updateGUI()

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.user_config.user_paths[0])
        self._set_user_path(path)
        self._updateGUI()

    def _select_all(self):
        self._set_all_checked(True)

    def _deselect_all(self):
        self._set_all_checked(False)

    def _set_all_checked(self, checked):
        root_index = self.tree.rootIndex()
        for row in range(self.model.rowCount(root_index)):
            child_index = self.model.index(row, 0, root_index)
            self._set_checked_recursive(child_index, checked)

    def _set_checked_recursive(self, index, checked):
        if not index.isValid():
            return
        flags = self.model.flags(index)
        if flags & Qt.ItemIsUserCheckable:
            if checked:
                self.model.checked_files.add(index)
            else:
                self.model.checked_files.discard(index)
            self.model.dataChanged.emit(index, index, [Qt.CheckStateRole])
        for row in range(self.model.rowCount(index)):
            child_index = self.model.index(row, 0, index)
            self._set_checked_recursive(child_index, checked)

    def _get_selected_files(self):
        selected_files = []
        for index in self.model.checked_files:
            selected_files.append(self.model.fileName(index))
        return selected_files

    def _create_proj(self):
        project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name")
        if not ok: return
        try:
            mvc = self._get_mvc()
            mvc.create(project_name)
        except MVCError as e:
            self.errLabel.setText(f"{e}")
        self._updateGUI()

    def _submit(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files to submit.")
            return
        description = self.desc_edit.text()
        try:
            mvc = self._get_mvc()
            mvc.submit(files, description)
            self.desc_edit.clear()
            self._deselect_all()
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _accept(self):
        description = self.desc_edit.text()
        try:
            mvc = self._get_mvc()
            mvc.accept(description)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _load(self):
        mvc = self._get_mvc()
        dlg = LoadOrCreateDialog(mvc, self)
        status = dlg.exec()
        if not status: return
        project = dlg.projects_combo.currentText()
        if not project: return
        print("loading", project)
        try:
            mvc = self._get_mvc()
            recipe = mvc.load(project)
            if self._prompt_confirmation(recipe):
                mvc.load_finalize(recipe)
        except MVCError as e:
            self.errLabel.setText(f"{e}")
        self._updateGUI()
            
    def _review(self):
        try:
            mvc = self._get_mvc()
            recipe = mvc.review()
            if self._prompt_confirmation(recipe):
                mvc.review_finalize(recipe)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _restore(self):
        try:
            mvc = self._get_mvc()
            available = mvc.restore_available()
            dlg = RestoreDialog(available)
            if dlg.exec() == QDialog.Accepted:
                i = dlg.combo.currentIndex()
                recipe = mvc.restore(available[i])
                if self._prompt_confirmation(recipe):
                    mvc.review_finalize(recipe)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _release(self):
        try:
            mvc = self._get_mvc()
            mvc.release()
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _claim(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files selected.")
            return
        try:
            mvc = self._get_mvc()
            mvc.claim(files)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _unclaim(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files selected.")
            return
        try:
            mvc = self._get_mvc()
            try:
                mvc.unclaim(files)
            except MVCError:
                dlg = UnclaimDialog(files, self)
                if dlg.exec() == QDialog.Accepted:
                    mvc.unclaim(files, force=True)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _remove(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files selected.")
            return
        try:
            mvc = self._get_mvc()
            mvc.remove(files)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _open_tree(self):
        selected = self._get_selected_files()
        for file in selected:
            filepath: str = os.path.join(self.user_config.user_paths[0], file)
            if os.path.isfile(filepath):
                for k in self._file_extension_callbacks:
                    if file.endswith(f".{k}"):
                        self._file_extension_callbacks[k](filepath)

    def _prompt_confirmation(self, recipe: FileOperation):
        overwritten_files = recipe.check_dir(self.user_config.user_paths[0])
        if overwritten_files:
            dlg = ConfirmationDialog(overwritten_files, self)
            if dlg.exec() == QDialog.Rejected: return False
        return True  

    def register_file_handler(self, extension: str, handler: callable):
        self._file_extension_callbacks[extension] = handler


if __name__ == '__main__':
    from PySide.QtGui import QApplication
    import sys

    class AppDlg(QDialog):
        def __init__(self):
            super(AppDlg, self).__init__()
            self.initUI()

        def initUI(self):
            self.mvc_gui = MVCGui()
            self.mvc_gui.register_file_handler("FCStd", self.user_open)
            mainLayout = QVBoxLayout()
            mainLayout.addWidget(self.mvc_gui)
            self.setLayout(mainLayout)

        def user_open(self, file):
            print("Open function for", file)

    if __name__ == '__main__':
        print("mvc gui running from app")
        app = QApplication(sys.argv)
        form = AppDlg()
        form.exec()
