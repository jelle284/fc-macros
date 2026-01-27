import sys
sys.path.append("D:/repos/mvc")
from mvc.core import MiniVC, MVCError
import os
import json

from PySide.QtWidgets import (QFileSystemModel, QTreeView,
                              QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLineEdit, QLabel, QPushButton,
                              QFileDialog, QWidget,
                              QListWidget, QListWidgetItem,
                              QDialog, QDialogButtonBox)
from PySide.QtCore import Qt, QTimer, QDir
from PySide.QtGui import QColor

def save_config(appdata_path, cfg):
    config_file = os.path.join(appdata_path, "mvc_config.json")
    with open(config_file, 'w') as fd:
        json.dump(cfg, fd)

def load_config(appdata_path):
    config_path = os.path.join(appdata_path, "mvc_config.json")
    try:
        with open(config_path, 'r') as fd:
            return json.load(fd)
    except:
        return {'backend_path': QDir.homePath() + "/mvc_files",
                        'username': 'user',
                        'workspace_path': QDir.homePath()}
    
class SettingsDialog(QDialog):
    def __init__(self, backend, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.backend_edit = QLineEdit(backend)
        self.user_edit = QLineEdit(user)
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

class CheckableFileSystemModel(QFileSystemModel):
    def _check_file_type(self, index):
        filepath = self.fileName(index)
        is_dir = self.isDir(index)
        exclude_by_filename = filepath in (
            ".mvc",
            "changelog.md",
        )
        exclude_by_extension = any(filepath.endswith(extension) for extension in (
            ".FCBak",
        ))
        file_is_forbidden = exclude_by_filename or exclude_by_extension or is_dir
        return file_is_forbidden
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked_files = set()
        self.changed_files = set()

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if index in self.checked_files:
                return Qt.Checked
            else:
                return Qt.Unchecked
        if role == Qt.ForegroundRole and index.column() == 0:
            file_is_forbidden = self._check_file_type(index)
            if not file_is_forbidden:
                filename = os.path.basename(self.filePath(index))
                if filename in self.changed_files:
                    return QColor("orange")
        return super().data(index, role)

    def setData(self, index, value, role=Qt.CheckStateRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if value == Qt.Checked:
                self.checked_files.add(index)
            else:
                self.checked_files.discard(index)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return super().setData(index, value, role)

    def flags(self, index):
        file_is_forbidden = self._check_file_type(index)
        if file_is_forbidden:
            return super().flags(index) & (~Qt.ItemIsEnabled)
        return super().flags(index) | Qt.ItemIsUserCheckable

    def set_changed_files(self, files):
        self.changed_files = set(files)
        # Emit layout changed to refresh the view
        self.layoutChanged.emit()

class MVCGui(QWidget): 
    def __init__(self, appdata_path = ""):
        super(MVCGui, self).__init__()
        self.appdata_path = appdata_path
        self.initUI()
        cfg = load_config(appdata_path)
        self.backend_path = cfg["backend_path"]
        self.workspace_path = cfg["workspace_path"]
        self.username = cfg["username"]
        self._file_extension_callbacks = {}

    def initUI(self):
        LINE_WIDTH = QLabel().sizeHint().height()
        # Buttons
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._settings)
        self.create_button = QPushButton("Create Project")
        self.create_button.clicked.connect(self._create_proj)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._submit)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save)
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self._load)
        self.review_button = QPushButton("Review")
        self.review_button.clicked.connect(self._review)
        self.release_button = QPushButton("Release")
        self.release_button.clicked.connect(self._release)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove)

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

        # List Box
        self.projectList = QListWidget()
        self.projectList.setMaximumHeight(LINE_WIDTH * 5)
        
        # Text inputs
        self.create_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        self.desc_edit.setMinimumHeight(LINE_WIDTH * 5)
        self.desc_edit.setAlignment(Qt.AlignTop)

        # Text outputs
        self.infoLabel = QLabel()
        self.infoLabel.setStyleSheet("border: 1px solid black;")
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setMinimumHeight(LINE_WIDTH * 8)
        self.versionLabel = QLabel()
        self.errLabel = QLabel()
        self.cwdLabel = QLabel()

        # Left column layout
        left_col = QVBoxLayout()
        left_col.addWidget(self.settings_button)
        left_col.addWidget(self.errLabel)
        left_col.addSpacing(LINE_WIDTH)

        vbox1 = QVBoxLayout()
        vbox1.addWidget(QLabel("Project Name"))
        vbox1.addWidget(self.create_edit)
        vbox1.addWidget(self.create_button)
        vbox1.addWidget(QLabel("Project List"))
        vbox1.addWidget(self.projectList)
        vbox1.addWidget(self.load_button)
        vbox1.addWidget(QLabel("Project Version"))
        vbox1.addWidget(self.versionLabel)
        left_col.addLayout(vbox1)
        left_col.addStretch(1)
        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Project status"))
        vbox2.addWidget(self.infoLabel)
        vbox2.addWidget(self.review_button)
        vbox2.addWidget(self.save_button)
        vbox2.addWidget(self.release_button)
        left_col.addLayout(vbox2)
        left_col.addStretch(3)
        

        # File column layout
        right_col = QVBoxLayout()
        right_col.addWidget(browse_button)
        right_col.addWidget(self.cwdLabel)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        right_col.addLayout(button_layout)
        right_col.addWidget(self.tree)
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

    def _on_timer_tick(self):
        versionText = ""
        errorText = self.errLabel.text()
        infoText = ""
        changed_files = []
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            workspace = mvc._get_workspace()
            if workspace:
                status = mvc.status()
                if status:
                    infoText = "\n".join(status)
                changed_files = mvc.changes()
            projects = mvc.list_projects()
            if len(projects) != self.projectList.count():
                self.projectList.clear()
                self.projectList.addItems([f"{name}" for name in projects])
            for item in self.projectList.selectedItems():
                if item.text() in projects:
                    versionText = projects[item.text()]
            project_name = self.create_edit.text()
            if project_name in projects:
                versionText = projects[project_name]
        except MVCError as e:
            errorText = f"{e}"
        
        self.errLabel.setText(errorText)
        self.versionLabel.setText(versionText)
        self.infoLabel.setText(infoText)
        self.model.set_changed_files(changed_files)

    @property
    def workspace_path(self):
        root_index = self.tree.rootIndex()
        return self.model.filePath(root_index)

    @workspace_path.setter
    def workspace_path(self, path):
        self.tree.setRootIndex(self.model.index(path))
        cfg = load_config(self.appdata_path)
        cfg["workspace_path"] = path
        save_config(self.appdata_path, cfg)
        self.cwdLabel.setText(path)
        try:
            mvc = MiniVC(self.backend_path, path)
            workspace = mvc._get_workspace()
            if workspace:
                self._set_gui_project(workspace.project)
            else:
                self._set_gui_project("")
        except MVCError as err:
            self.errLabel.setText(f"{err}")

    def _set_gui_project(self, project_name):
            self.create_edit.setText(project_name)

    def _settings(self):
        dlg = SettingsDialog(self.backend_path, self.username, self)
        if dlg.exec_() == QDialog.Accepted:
            self.backend_path = dlg.backend_edit.text()
            self.username = dlg.user_edit.text()
            save_config(self.appdata_path, 
                        {"backend_path": self.backend_path,
                         "username": self.username, 
                         "workspace_path": self.workspace_path})

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.workspace_path)
        if not path:
            return
        self.workspace_path = path

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
            file_path = os.path.basename(self.model.filePath(index))
            selected_files.append(file_path)
        return selected_files

    def _create_proj(self):
        project_name = self.create_edit.text()
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            mvc.create(project_name)
            self._set_gui_project(project_name)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _submit(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files to submit.")
            return
        description = self.desc_edit.text()
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            mvc.submit(files, description)
            self.desc_edit.clear()
            self._deselect_all()
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _save(self):
        description = self.desc_edit.text()
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            mvc.save(description)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _load(self):
        project = self.projectList.currentItem()
        if not project: return
        print("loading", project.text())
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            recipe = mvc.load(project.text())
            if len(recipe.files_to_add) > 0:
                print("adding files", ", ".join(recipe.files_to_add))
            if len(recipe.files_to_remove) > 0:
                print("removing files", ", ".join(recipe.files_to_remove))
            mvc.load_finalize(recipe)
            self._set_gui_project(project.text())
        except MVCError as e:
            self.errLabel.setText(f"{e}")
            
    def _review(self):
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            recipe = mvc.review()
            if len(recipe.files_to_add) > 0:
                print("adding files", ", ".join(recipe.files_to_add))
            if len(recipe.files_to_remove) > 0:
                print("removing files", ", ".join(recipe.files_to_remove))
            mvc.review_finalize(recipe)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _release(self):
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            mvc.release()
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _remove(self):
        files = self._get_selected_files()
        if files == []:
            self.errLabel.setText("No files to submit.")
            return
        try:
            mvc = MiniVC(self.backend_path, self.workspace_path)
            mvc.remove(files)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _open_tree(self):
        selected = self._get_selected_files()
        num_files = 0
        for file in selected:
            file: str
            filepath = os.path.join(self.workspace_path, file)
            if os.path.isfile(filepath):
                try:
                    self._file_extension_callbacks[file.split(".")[-1]](filepath)
                except KeyError:
                    pass
                num_files += 1
        if num_files > 0: return
        if len(selected) == 1:
            check_dir = os.path.join(self.workspace_path, selected[0])
            if os.path.isdir(check_dir):
                self.workspace_path = check_dir
                return

    def register_file_handler(self, extension: str, handler: callable):
        self._file_extension_callbacks[extension] = handler