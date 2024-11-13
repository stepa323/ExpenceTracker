import sys

import sqlite3
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtCore import QDate, QTime, QRectF, QTimer, QDateTime
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableWidgetItem, QDialog, QGraphicsScene, \
     QGraphicsTextItem, QMessageBox


class AddTransactWidget(QDialog):
    def __init__(self, parent, lst):
        super().__init__(parent)
        uic.loadUi('AddTransactionWidget.ui', self)
        self.comboBox.addItems(lst)
        self.dateTimeEdit.setMinimumDate(QDate.currentDate().addDays(-365 * 5))
        self.dateTimeEdit.setMaximumDate(QDate.currentDate())
        self.dateTimeEdit.setDate(QDate.currentDate())
        self.dateTimeEdit.setTime(QTime.currentTime())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.dateTimeEdit.setDisplayFormat("dd MMMM yyyy hh:mm")

    def get_input(self):
        return [self.lineEdit.text(), self.dateTimeEdit.text(), self.comboBox.currentText(), self.lineEdit_2.text()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('MainWindow.ui', self)

        self.countclicks = 0
        self.scene = QGraphicsScene(self)
        self.connection = sqlite3.connect("DB.sqlite")
        self.expenses = [el[0] for el in self.connection.cursor().execute('select name from expenses').fetchall()]
        self.incomes = [el[0] for el in self.connection.cursor().execute('select name from incomes').fetchall()]
        self.initUi()

    def initUi(self):
        self.view.setScene(self.scene)

        self.buttonGroup.setId(self.weekBtn, 0)
        self.buttonGroup.setId(self.monthBtn, 1)
        self.buttonGroup.setId(self.yearBtn, 2)

        self.monthBtn.setChecked(True)
        self.buttonGroup.buttonToggled.connect(self.graphic_expenses)
        self.refreshBtn.clicked.connect(self.refresh)
        self.leftBtn.setEnabled(False)
        self.leftBtn.clicked.connect(self.countClicks)
        self.rightBtn.clicked.connect(self.countClicks)

        self.addExpenseBtn.clicked.connect(self.addExpense)
        self.addIncomeBtn.clicked.connect(self.addIncome)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_date_time)
        self.timer.start(1000)

        self.refresh()

    def update_date_time(self):
        date_time = QDateTime.currentDateTime()
        date = date_time.toString("d MMMM yyyy")
        time = date_time.toString("HH:mm:ss")
        self.time.setText(time)
        self.date.setText(date)

    def countClicks(self):
        if self.sender().text() == '>':
            self.countclicks += 1
            if self.countclicks == 1:
                self.leftBtn.setEnabled(True)
        else:
            self.countclicks -= 1
            if self.countclicks == 0:
                self.leftBtn.setEnabled(False)
        self.refresh_graph()

    def balance(self):
        sql = 'select SUM(amount) from transactions where is_expense = 1'
        sql1 = 'select SUM(amount) from transactions where is_expense = 0'

        expense_sum = self.connection.cursor().execute(sql).fetchall()[0][0]
        if not expense_sum:
            expense_sum = 0
        income_sum = self.connection.cursor().execute(sql1).fetchall()[0][0]
        if not income_sum:
            income_sum = 0
        summ = -int(expense_sum) + int(income_sum)
        self.balanceLabel.setText(f"{str(summ)} ₽")
        if summ < 0:
            self.balanceLabel.setStyleSheet('color: rgb(150, 50, 50)')
        else:
            self.balanceLabel.setStyleSheet('color: rgb(50, 150, 50)')

    def amount_expenses(self, date, date1):
        sql = f'''select SUM(amount) from transactions where is_expense = 1 and date >= "{date}" and date <= "{date1}"'''

        expense_sum = self.connection.cursor().execute(sql).fetchall()[0][0]
        if not expense_sum:
            expense_sum = 0
        summ = int(expense_sum)
        self.amountExpenses.setText(f"{str(summ)} ₽")

    def select_data(self):
        query = '''SELECT 
    t.amount, 
    t.date, 
    CASE 
        WHEN t.is_expense = 1 THEN e.name
        ELSE i.name
    END AS category_name, 
    t.description
FROM 
    transactions t
LEFT JOIN 
    expenses e ON t.expenses_id = e.id
LEFT JOIN 
    incomes i ON t.incomes_id = i.id
ORDER BY 
    t.date DESC;'''

        res = self.connection.cursor().execute(query).fetchall()
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)

        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            if row[2] in self.incomes:
                expense = False
            else:
                expense = True
            for j, elem in enumerate(row):
                if j == 0 and expense:
                    elem = f"-{elem}"
                    self.tableWidget.setItem(
                        i, j, QTableWidgetItem(str(elem)))
                    self.tableWidget.item(i, j).setForeground(QColor(100, 0, 0))
                elif j == 0 and not expense:
                    elem = f'+{elem}'
                    self.tableWidget.setItem(
                        i, j, QTableWidgetItem(str(elem)))
                    self.tableWidget.item(i, j).setForeground(QColor(0, 100, 0))
                else:
                    if j == 1:
                        date_obj = datetime.strptime(elem, "%Y-%m-%d %H:%M")
                        elem = date_obj.strftime("%d %b %Y, %H:%M")
                    self.tableWidget.setItem(
                        i, j, QTableWidgetItem(str(elem)))

        self.tableWidget.setColumnWidth(0, 80)
        self.tableWidget.setColumnWidth(1, 125)
        self.tableWidget.setColumnWidth(2, 130)
        self.tableWidget.setColumnWidth(3, 150)

        self.refresh_graph()

    def addExpense(self):
        widget = AddTransactWidget(self, self.expenses)
        if widget.exec() == 1:
            values = widget.get_input()
            try:
                if values[0] == "0":
                    raise Exception
                sql = f"""insert into transactions(date, amount, expenses_id, description, is_expense) 
                    values("{values[1]}", {values[0]}, (select id from expenses where name = "{values[2]}"), "{values[3]}", 1)"""
                self.connection.cursor().execute(sql)
                self.connection.commit()
                self.refresh()
            except Exception:
                self.error('не верно введены значения')

    def addIncome(self):
        widget = AddTransactWidget(self, self.incomes)
        if widget.exec() == 1:
            values = widget.get_input()
            try:
                if values[0] == "0":
                    raise Exception
                sql = f"""insert into transactions(date, amount, incomes_id, description, is_expense) 
                            values("{values[1]}", {values[0]}, (select id from incomes where name = "{values[2]}"), "{values[3]}", 0)"""
                self.connection.cursor().execute(sql)
                self.connection.commit()
                self.refresh()
            except Exception:
                self.error('не верно введены значения')

    def graphic_expenses(self):
        cursor = self.connection.cursor()
        id = self.buttonGroup.checkedId()

        dates = [QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() - 7 * self.countclicks),
                 QDate.currentDate().addDays(-QDate.currentDate().day() + 1).addMonths(-self.countclicks),
                 QDate.currentDate().addDays(-QDate.currentDate().day() + 1).addMonths(
                     -QDate.currentDate().month() + 1).addYears(-self.countclicks)]
        dates1 = [dates[0].addDays(7), dates[1].addMonths(1), dates[2].addYears(1)]

        date1 = dates1[id].toString("yyyy-MM-dd")
        date = dates[id].toString("yyyy-MM-dd")

        self.first_date.setText(f"от {dates[id].toString("d MMM yyyy")}")
        self.last_date.setText(f"до {dates1[id].toString("d MMM yyyy")}")

        query = f"""SELECT e.name, SUM(amount) AS total_amount
                    FROM transactions t
                    JOIN expenses e ON t.expenses_id = e.id
                    WHERE date >= "{date}" and date <= "{date1}" and is_expense = 1
                    GROUP BY e.name
                    ORDER BY total_amount DESC
                    LIMIT 5;
                """
        self.amount_expenses(date, date1)
        self.select_graphics_transactions(date, date1)
        a = cursor.execute(query).fetchall()
        self.scene.clear()
        if not a:
            text_item = QGraphicsTextItem("В этом промежутке не было расходов")
            text_item.setFont(QFont('Arial', 18))
            text_item.setTextWidth(150)
            text_item.setPos(0, 50)
            self.scene.addItem(text_item)
        else:
            categories = []
            amounts = []
            for row in a:
                categories.append(row[0])
                amounts.append(row[1])

            max_amount = max(amounts) if amounts else 1

            bar_width = 70
            spacing = 15

            max_bar_height = 170

            for index, (category, amount) in enumerate(zip(categories, amounts)):
                bar_height = (amount / max_amount) * max_bar_height

                rect = self.scene.addRect(
                    index * (bar_width + spacing),
                    max_bar_height - bar_height,
                    bar_width,
                    bar_height,
                    brush=QBrush(QColor(150, 150, 255))
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

    def select_graphics_transactions(self, date, date1):
        query = f'''SELECT 
    t.amount, 
    t.date, 
    CASE 
        WHEN t.is_expense = 1 THEN e.name
        ELSE i.name
    END AS category_name, 
    t.description
FROM 
    transactions t
LEFT JOIN 
    expenses e ON t.expenses_id = e.id
LEFT JOIN 
    incomes i ON t.incomes_id = i.id
    WHERE date >= "{date}" and date <= "{date1}"
ORDER BY 
    t.date DESC;'''
        res = self.connection.cursor().execute(query).fetchall()
        self.tableWidget2.setColumnCount(4)
        self.tableWidget2.setRowCount(0)

        for i, row in enumerate(res):
            self.tableWidget2.setRowCount(
                self.tableWidget2.rowCount() + 1)
            if row[2] in self.incomes:
                expense = False
            else:
                expense = True
            for j, elem in enumerate(row):
                if j == 0 and expense:
                    elem = f"-{elem}"
                    self.tableWidget2.setItem(
                        i, j, QTableWidgetItem(str(elem)))
                    self.tableWidget2.item(i, j).setForeground(QColor(100, 0, 0))
                elif j == 0 and not expense:
                    elem = f'+{elem}'
                    self.tableWidget2.setItem(
                        i, j, QTableWidgetItem(str(elem)))
                    self.tableWidget2.item(i, j).setForeground(QColor(0, 100, 0))
                else:
                    if j == 1:
                        date_obj = datetime.strptime(elem, "%Y-%m-%d %H:%M")
                        elem = date_obj.strftime("%d %b %Y, %H:%M")
                    self.tableWidget2.setItem(
                        i, j, QTableWidgetItem(str(elem)))

        self.tableWidget2.setColumnWidth(0, 80)
        self.tableWidget2.setColumnWidth(1, 125)
        self.tableWidget2.setColumnWidth(2, 130)
        self.tableWidget2.setColumnWidth(3, 150)

    def error(self, error):
        QMessageBox.critical(self, 'Ошибка', error)

    def refresh_graph(self):
        self.graphic_expenses()

    def refresh(self):
        self.graphic_expenses()
        self.select_data()
        self.balance()

    def closeEvent(self, event):
        self.connection.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
