from datetime import datetime
import sys

import sqlite3
from PyQt6 import uic
from PyQt6.QtCore import QDate, QTime, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableWidgetItem, QDialog, QGraphicsRectItem, QGraphicsScene, \
    QVBoxLayout, QGraphicsView, QGraphicsTextItem, QButtonGroup


class AddExpenseWidget(QDialog):
    def __init__(self, parent, lst):
        super().__init__(parent)
        uic.loadUi('AddExpensesWidget.ui', self)
        self.comboBox.addItems(lst)
        self.dateTimeEdit.setMinimumDate(QDate.currentDate().addDays(-365 * 5))
        self.dateTimeEdit.setMaximumDate(QDate.currentDate())
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
        self.buttonGroup.setId(self.weekBtn, 0)
        self.buttonGroup.setId(self.monthBtn, 1)
        self.buttonGroup.setId(self.yearBtn, 2)
        self.buttonGroup.buttonToggled.connect(self.plot_expenses)

        self.addExpenseBtn.clicked.connect(self.addExpense)
        self.addIncomeBtn.clicked.connect(self.addIncome)

        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.plot_expenses()
        self.select_data()


    def select_data(self):
        query = '''SELECT 
    t.date, 
    t.amount, 
    CASE 
        WHEN t.is_expense = 1 THEN c.name
        ELSE i.name
    END AS category_name, 
    t.description
FROM 
    transactions t
LEFT JOIN 
    categories c ON t.category_id = c.id
LEFT JOIN 
    income i ON t.category_id = i.id
WHERE 
    t.is_expense IN (0, 1)
ORDER BY 
    t.date DESC;'''
        res = self.connection.cursor().execute(query).fetchall()
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)

        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))
        self.refresh_graph()

    def addExpense(self):
        widget = AddExpenseWidget(self, self.categories)
        if widget.exec() == 1:
            values = widget.get_input()
            if values != 0:
                sql = f"""insert into transactions(date, amount, category_id, description, is_expense) 
                    values("{values[1]}", {values[0]}, (select id from categories where name = "{values[2]}"), "{values[3]}", 1)"""
                self.connection.cursor().execute(sql)
                self.connection.commit()
                self.select_data()

    def addIncome(self):
        ...

    def tableChanged(self):
        ...

    def plot_expenses(self):
        cursor = self.connection.cursor()
        dates = [QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek()), QDate.currentDate().addDays(-QDate.currentDate().day() + 1),
                 QDate.currentDate().addDays(-QDate.currentDate().day() + 1).addMonths(-QDate.currentDate().month() + 1)]
        date = dates[self.buttonGroup.checkedId()].toString("dd.MM.yyyy")
        print(date)
        query = f"""
                    SELECT c.name, SUM(amount) AS total_amount
                    FROM transactions e
                    JOIN categories c ON category_id = c.id
                    WHERE date >= "{date}" and is_expense = 1
                    GROUP BY c.name
                    ORDER BY total_amount DESC
                    LIMIT 5;
                """
        a = cursor.execute(query).fetchall()
        categories = []
        amounts = []
        for row in a:
            categories.append(row[0])
            amounts.append(row[1])

        max_amount = max(amounts) if amounts else 1

        bar_width = 70
        spacing = 15

        max_bar_height = 170

        self.scene.clear()

        for index, (category, amount) in enumerate(zip(categories, amounts)):
            bar_height = (amount / max_amount) * max_bar_height

            rect = self.scene.addRect(
                index * (bar_width + spacing),
                max_bar_height - bar_height,
                bar_width,
                bar_height,
                brush=QBrush(QColor(100, 150, 255))
            )

            text_item = QGraphicsTextItem(category)
            text_item.setFont(QFont('Arial', 10))
            text_item.setTextWidth(bar_width)
            text_item.setPos(index * (bar_width + spacing), max_bar_height + 5)

            amount_text_item = QGraphicsTextItem(f"{amount:.2f}")
            amount_text_item.setFont(QFont('Arial', 10))
            amount_text_item.setPos(
                index * (bar_width + spacing) + (bar_width // 2) - (amount_text_item.boundingRect().width() / 2),
                max_bar_height - bar_height - 20)
            self.scene.addItem(amount_text_item)

            self.scene.addItem(text_item)

        self.scene.setSceneRect(QRectF(0, 0, len(categories) * (bar_width + spacing), max_bar_height + 50))

    def refresh_graph(self):
        self.plot_expenses()

    def closeEvent(self, event):
        self.connection.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
