import sys

import sqlite3
from PyQt6 import uic
from PyQt6.QtCore import QDate, QTime
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableWidgetItem, QWidget, QDialog


class AddExpensesWidget(QDialog):
    def __init__(self, parent, lst):
        super().__init__(parent)
        uic.loadUi('AddExpensesWidget.ui', self)
        self.comboBox.addItems(lst)
        self.dateTimeEdit.setMinimumDate(QDate.currentDate().addDays(-365 * 5))
        self.dateTimeEdit.setDate(QDate.currentDate())
        self.dateTimeEdit.setTime(QTime.currentTime())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def get_input(self):
        return [self.lineEdit.text(), self.dateTimeEdit.text(), self.comboBox.currentText(), self.lineEdit_2.text()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('MainWindow.ui', self)
        self.connection = sqlite3.connect("DB.sqlite")
        self.categories = [el[0] for el in self.connection.cursor().execute('select name from categories').fetchall()]
        self.addBtn.clicked.connect(self.addExpenses)
        self.select_data()

    def select_data(self):
        query = ("select date, amount, name, description from expenses\n"
                 "inner join categories on categories.id = expenses.category_id")
        res = self.connection.cursor().execute(query).fetchall()
        print(res, 12)

        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)

        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    def addExpenses(self):
        widget = AddExpensesWidget(self, self.categories)
        if widget.exec() == 1:
            values = widget.get_input()
            if values != 0:
                sql = f"""insert into expenses(date, amount, category_id, description) 
                values("{values[1]}", {values[0]}, (select id from categories where name = "{values[2]}"), "{values[3]}")"""
                self.connection.cursor().execute(sql)
                self.connection.commit()
                self.select_data()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
