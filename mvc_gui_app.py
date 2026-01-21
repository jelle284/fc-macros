from PySide import QtGui, QtCore
from mvc_gui import MVCGui
import sys

class MyDlg(QtGui.QDialog):
	""""""
	def __init__(self):
		super(MyDlg, self).__init__()
		self.initUI()
	def initUI(self):
		#
		self.mvc_gui = MVCGui()
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.mvc_gui)
		self.setLayout(mainLayout)
		
if __name__ == '__main__':
    print("mvc gui running from app")
    app = QtGui.QApplication(sys.argv)
    form = MyDlg()
    form.exec_()
