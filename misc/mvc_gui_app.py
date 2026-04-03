from PySide import QtGui
from mvc_gui import MVCGui
import sys

class MyDlg(QtGui.QDialog):
	def __init__(self):
		super(MyDlg, self).__init__()
		self.initUI()
	def initUI(self):
		#
		self.mvc_gui = MVCGui()
		self.mvc_gui.register_file_handler("FCStd", self.user_open)
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.mvc_gui)
		self.setLayout(mainLayout)

	def user_open(self, file):
		print("Open function for", file)

if __name__ == '__main__':
	print("mvc gui running from app")
	app = QtGui.QApplication(sys.argv)
	form = MyDlg()
	form.exec_()
