from mvc.core import MiniVC, MVCError
from mvc.helpers import JSONBase, FileID
import os
from dataclasses import dataclass

from PySide.QtWidgets import (QListWidget, QListWidgetItem,
                              QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLineEdit, QLabel, QPushButton,
                              QFileDialog, QWidget,
                              QComboBox, QInputDialog,
                              QDialog, QDialogButtonBox)
from PySide.QtCore import Qt, QTimer, QDir
from PySide.QtGui import QColor



##########################################################################
#================= User settings, persistent storage ====================#
@dataclass
class UserConfig(JSONBase):
    base_path: str
    user_name: str
    user_paths: list[str]
    
class SettingsDialog(QDialog):
    def __init__(self, default: UserConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.base_edit = QLineEdit(default.base_path)
        self.user_edit = QLineEdit(default.user_name)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_base)
        form_layout = QFormLayout()
        base_layout = QHBoxLayout()
        base_layout.addWidget(self.base_edit)
        base_layout.addWidget(self.browse_button)
        form_layout.addRow("Base Path:", base_layout)
        form_layout.addRow("User Name:", self.user_edit)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        form_layout.addWidget(button_box)
        self.setLayout(form_layout)

    def _browse_base(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Path")
        if path:
            self.base_edit.setText(path)

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

class CollectDialog(QDialog):
    def __init__(self, avaiable: list[FileID], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Collect")
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

class CheckableFileList(QListWidget):
    def _scan(self):
        files = []
        for filename in os.listdir(self.current_path):
            exclude_by_filename = filename in (
                ".mvc",
                "changelog.md",
            )
            exclude_by_extension = any(filename.endswith(extension) for extension in (
                ".FCBak",
            ))
            is_dir = os.path.isdir(os.path.join(self.current_path, filename))
            excluded = exclude_by_filename or exclude_by_extension or is_dir
            if not excluded:
                files.append(filename)
        return files

    def _create_item(self, filename):
        item = QListWidgetItem(filename)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Unchecked)
        return item
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_colors = {'red': [],
                            'orange': [],
                            'green': []}
        self.current_path = ""

    def load_directory(self, path):
        self.clear()
        self.current_path = path
        for file in self._scan():
            item = self._create_item(file)
            self.addItem(item)

    def update_directory(self):
        user_files = self._scan()
        list_files = [self.item(row).text() for row in range(self.count())]
        for row in range(self.count()):
            item = self.item(row)
            if item.text() not in user_files:
                self.takeItem(row)
        for filename in user_files:
            if filename not in list_files:
                item = self._create_item(filename)
                self.addItem(item)


    def update_colors(self):
        for row in range(self.count()):
            item = self.item(row)
            filename = item.text()
            color = None
            for color_name in self.file_colors:
                if filename in self.file_colors[color_name]:
                    color = QColor(color_name)
                    break
            item.setForeground(color if color else QColor("black"))

    def set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.count()):
            self.item(row).setCheckState(state)

    def get_checked_files(self):
        return [self.item(row).text() for row in range(self.count())
                if self.item(row).checkState() == Qt.Checked]
    
    def get_selection(self):
        selected = self.selectedItems()
        if selected:
            return selected[0].text()
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
                base_path = f"{QDir.rootPath()}mvc-files",
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
        self.create_button.clicked.connect(self._create)
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self._load)
        self.collect_button = QPushButton("Collect")
        self.collect_button.clicked.connect(self._collect)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._submit)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove)
        self.accept_button = QPushButton("Accept")
        self.accept_button.clicked.connect(self._accept)
        self.release_button = QPushButton("Release")
        self.release_button.clicked.connect(self._release)
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
        self.file_list = CheckableFileList()
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self._open_tree)
        self.file_list.setMinimumWidth(200)

        # Text inputs
        self.desc_edit = QLineEdit()
        self.desc_edit.setMinimumHeight(LINE_WIDTH * 5)
        self.desc_edit.setAlignment(Qt.AlignTop)

        # Text outputs
        self.infoLabel = QLabel()
        self.infoLabel.setStyleSheet("border: 1px solid black;")
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setMinimumHeight(LINE_WIDTH * 10)
        self.infoLabel.setMinimumWidth(200)
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
        vbox2.addWidget(self.accept_button)
        vbox2.addWidget(self.release_button)
        left_col.addLayout(vbox2)
        left_col.addStretch(3)
        
        # File column layout
        right_col = QVBoxLayout()
        right_col.addWidget(browse_button)
        right_col.addWidget(self.workspace_combo)
        right_col.addWidget(self.collect_button)
        button_layout1 = QHBoxLayout()
        button_layout1.addWidget(self.select_all_button)
        button_layout1.addWidget(self.deselect_all_button)
        right_col.addLayout(button_layout1)
        right_col.addWidget(self.file_list)
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
        return MiniVC(self.user_config.base_path, self.user_config.user_paths[0], self.user_config.user_name)
    
    def _updateGUI(self):
        current_path = self.user_config.user_paths[0]
        self.file_list.load_directory(current_path)
        self.workspace_combo.clear()
        for path in self.user_config.user_paths:
            self.workspace_combo.addItem(path)
        self.workspace_combo.setCurrentIndex(0)
        allow_create = True
        allow_load = True
        try:
            mvc = self._get_mvc()
            workspace = mvc._get_workspace()
            allow_load = False
            mvc._get_project(workspace.project)
            allow_create = False
            self.errLabel.setText("")
        except MVCError as err:
            self.errLabel.setText(f"{err}")
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
        new_files = []
        claimed_by_others = []
        claimed_by_user = []
        try:
            mvc = self._get_mvc()
            status = mvc.status()
            if status:
                if len(status) > 10: status = status[:10]
                infoText = "\n".join(status)
            new_files, changed_files = mvc.changes()
            claims = mvc.get_claims()
            for file in claims:
                if self.user_config.user_name == claims[file]:
                    claimed_by_user.append(file)
                else:
                    claimed_by_others.append(file)
            selected = self.file_list.get_selection()
            file_was_claimed = False
            if selected:
                if selected in claimed_by_others:
                    self.file_label.setText(f"Claimed by {claims[selected]}")
                    file_was_claimed = True
            if not file_was_claimed:
                self.file_label.setText("")
        except MVCError:
            pass
        self.infoLabel.setText(infoText)
        self.file_list.file_colors['orange'] = changed_files
        self.file_list.file_colors['blue'] = new_files
        self.file_list.file_colors['red'] = claimed_by_others
        self.file_list.file_colors['green'] = claimed_by_user
        self.file_list.update_directory()
        self.file_list.update_colors()
        

    def _workspace_combo_change(self, index):
        path = self.workspace_combo.itemText(index)
        self._set_user_path(path)
        self._updateGUI()

    def _settings(self):
        dlg = SettingsDialog(self.user_config, self)
        if dlg.exec() == QDialog.Accepted:
            self.user_config.base_path = dlg.base_edit.text()
            self.user_config.user_name = dlg.user_edit.text()
            self.user_config.save(self.appdata_path)
            self._updateGUI()

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.user_config.user_paths[0])
        if os.path.isdir(path):
            self._set_user_path(path)
            self._updateGUI()

    def _select_all(self):
        self.file_list.set_all_checked(True)

    def _deselect_all(self):
        self.file_list.set_all_checked(False)

    def _create(self):
        project_name, ok = QInputDialog.getText(self, "Create Project", "Enter project name")
        if not ok: return
        try:
            mvc = self._get_mvc()
            mvc.create(project_name)
        except MVCError as e:
            self.errLabel.setText(f"{e}")
        self._updateGUI()

    def _load(self):
        mvc = self._get_mvc()
        dlg = LoadOrCreateDialog(mvc, self)
        status = dlg.exec()
        if not status: return
        project = dlg.projects_combo.currentText()
        if not project: return
        try:
            mvc = self._get_mvc()
            mvc.load(project)
        except MVCError as e:
            self.errLabel.setText(f"{e}")
        self._updateGUI()

    def _collect(self):
        try:
            mvc = self._get_mvc()
            available = mvc.available()
            dlg = CollectDialog(available)
            if dlg.exec() == QDialog.Accepted:
                i = dlg.combo.currentIndex()
                file_id = available[i]
                new_files, overwritten_files = mvc.changes(file_id)
                if self._prompt_confirmation(overwritten_files):
                    mvc.collect(file_id)
        except MVCError as e:
            self.errLabel.setText(f"{e}")
            
    def _submit(self):
        files = self.file_list.get_checked_files()
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

    def _remove(self):
        files = self.file_list.get_checked_files()
        if files == []:
            self.errLabel.setText("No files selected.")
            return
        try:
            mvc = self._get_mvc()
            mvc.remove(files)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _accept(self):
        description = self.desc_edit.text()
        try:
            mvc = self._get_mvc()
            mvc.accept(description)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _release(self):
        try:
            mvc = self._get_mvc()
            mvc.release()
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _claim(self):
        files = self.file_list.get_checked_files()
        if files == []:
            self.errLabel.setText("No files selected.")
            return
        try:
            mvc = self._get_mvc()
            mvc.claim(files)
        except MVCError as e:
            self.errLabel.setText(f"{e}")

    def _unclaim(self):
        files = self.file_list.get_checked_files()
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

    def _open_tree(self):
        checked_files = self.file_list.get_checked_files()
        for file in checked_files:
            filepath: str = os.path.join(self.user_config.user_paths[0], file)
            if os.path.isfile(filepath):
                for k in self._file_extension_callbacks:
                    if file.endswith(f".{k}"):
                        self._file_extension_callbacks[k](filepath)

    def _prompt_confirmation(self, overwritten_files):
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
