import csv
import io
import sys

import sqlite3
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtCore import QDate, QTime, QRectF, QTimer, QDateTime, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPixmap, QIcon
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableWidgetItem, QDialog, QGraphicsScene, \
    QGraphicsTextItem, QMessageBox, QFileDialog


class AddTransactWidget(QDialog):
    def __init__(self, parent, lst):
        super().__init__(parent)
        self.file_path = None
        uic.loadUi('AddTransactionWidget.ui', self)
        self.comboBox.addItems(lst)
        self.dateTimeEdit.setMinimumDate(QDate.currentDate().addDays(-365 * 5))
        self.dateTimeEdit.setMaximumDate(QDate.currentDate())
        self.dateTimeEdit.setDate(QDate.currentDate())
        self.dateTimeEdit.setTime(QTime.currentTime())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.dateTimeEdit.setDisplayFormat("dd MM yyyy hh:mm")
        self.addImage.clicked.connect(self.load_image)

    def load_image(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter('Images (*.png *.jpg *.jpeg *.bmp *.gif)')
        self.file_path, _ = file_dialog.getOpenFileName(self, "Выберите изображение")
        self.image_loaded.setText(f"{self.file_path.split('/')[-1]} {self.file_path}")

    def get_input(self):
        return [self.lineEdit.text(), self.dateTimeEdit.text(), self.comboBox.currentText(), self.lineEdit_2.text(),
                self.file_path]


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
        self.buttonGroup_graphic.setId(self.expenseRadioBtn, 0)
        self.buttonGroup_graphic.setId(self.incomeRadioBtn, 1)
        self.monthBtn.setChecked(True)
        self.expenseRadioBtn.setChecked(True)
        self.buttonGroup.buttonToggled.connect(self.graphic_expenses)
        self.buttonGroup_graphic.buttonToggled.connect(self.graphic_expenses)
        self.refreshBtn.clicked.connect(self.refresh)
        self.leftBtn.setEnabled(False)
        self.leftBtn.clicked.connect(self.countClicks)
        self.rightBtn.clicked.connect(self.countClicks)
        self.deleteBtn.clicked.connect(self.deleteTran)
        self.addExpenseBtn.clicked.connect(self.addExpense)
        self.addIncomeBtn.clicked.connect(self.addIncome)
        self.saveBtn.clicked.connect(self.save_to_csv)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_date_time)
        self.timer.start(1000)

        self.refresh()

    def save_to_csv(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "CSV Files (*.csv);;All Files (*)")

        if fileName:
            with open(fileName, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for row in range(self.tableWidget.rowCount()):
                    row_data = []
                    for col in range(self.tableWidget.columnCount()):
                        item = self.tableWidget.item(row, col)
                        row_data.append(item.text() if item else "")

                    writer.writerow(row_data)
            print("Данные сохранены в", fileName)

    def deleteTran(self):
        selected_row = self.tableWidget.currentRow()

        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите запись для удаления.")
            return

        item = self.tableWidget.item(selected_row, 5)
        record_id = item.text()
        cursor = self.connection.cursor()
        sql = "select amount, date from transactions where id = ?"
        a = cursor.execute(sql, (record_id,)).fetchall()
        amount, date = a[0]

        reply = QMessageBox.question(self, 'Подтверждение удаления',
                                     f"Вы действительно хотите удалить транзакцию ID: {record_id}; сумма: {amount}; дата: {date}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                cursor.execute("DELETE FROM transactions WHERE id = ?", (record_id,))
                self.connection.commit()

                self.tableWidget.removeRow(selected_row)

                QMessageBox.information(self, "Успех", f"Запись с ID {record_id} удалена.")
                self.refresh()
            except Exception as e:
                self.error(f"Не удалось удалить запись: {str(e)}")

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
            self.balanceLabel.setStyleSheet('color: rgb(100, 0, 0)')
        else:
            self.balanceLabel.setStyleSheet('color: rgb(0, 100, 0)')

    def amount_expenses(self, date, date1, is_expense):
        sql = f'''select SUM(amount) from transactions where is_expense = {1 if is_expense else 0} and date >= "{date}" and date <= "{date1}"'''

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
            t.description,
            t.id,
            t.image_path, 
            t.image_data
        FROM 
            transactions t
        LEFT JOIN 
            expenses e ON t.expenses_id = e.id
        LEFT JOIN 
            incomes i ON t.incomes_id = i.id
        ORDER BY 
            t.date DESC;'''

        res = self.connection.cursor().execute(query).fetchall()

        self.tableWidget.setColumnCount(7)
        self.tableWidget.setRowCount(len(res))

        expense_color = QColor(100, 0, 0)
        income_color = QColor(0, 100, 0)

        for i, row in enumerate(res):
            expense = row[2] not in self.incomes

            image_path = row[5] if len(row) > 5 else None
            image_data = row[6] if len(row) > 6 else None

            if image_path:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio))
                    item = QTableWidgetItem()
                    item.setIcon(icon)
                    self.tableWidget.setItem(i, 0, item)
            elif image_data:
                image_stream = io.BytesIO(image_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_stream.read())
                if not pixmap.isNull():
                    icon = QIcon(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio))
                    item = QTableWidgetItem()
                    item.setIcon(icon)
                    self.tableWidget.setItem(i, 0, item)

            for j, elem in enumerate(row[:-2]):
                item = QTableWidgetItem(str(elem))

                if j == 0:
                    if expense:
                        elem = f"-{elem}"
                        item.setForeground(expense_color)
                    else:
                        elem = f"+{elem}"
                        item.setForeground(income_color)
                    item.setText(str(elem))

                elif j == 1:
                    try:
                        date_obj = datetime.strptime(elem, "%Y-%m-%d %H:%M")
                        elem = date_obj.strftime("%d %b %Y, %H:%M")
                        item.setText(str(elem))
                    except ValueError:
                        item.setText(str(elem))

                else:
                    item.setText(str(elem))

                self.tableWidget.setItem(i, j + 1, item)

            item = QTableWidgetItem(str(row[4]))
            self.tableWidget.setItem(i, 6, item)

        self.tableWidget.setColumnWidth(0, 60)
        self.tableWidget.setColumnWidth(1, 80)
        self.tableWidget.setColumnWidth(2, 125)
        self.tableWidget.setColumnWidth(3, 130)
        self.tableWidget.setColumnWidth(4, 150)
        self.tableWidget.setColumnWidth(5, 60)

        self.refresh_graph()

    def addExpense(self):
        widget = AddTransactWidget(self, self.expenses)
        if widget.exec() == 1:
            values = widget.get_input()
            image_path = values[-1]
            try:
                if values[0] == "0":
                    raise ValueError
                date_obj = datetime.strptime(values[1], "%d %m %Y %H:%M")
                values[1] = date_obj.strftime("%Y-%m-%d %H:%M")

                if image_path:
                    with open(image_path, 'rb') as file:
                        img_data = file.read()

                    sql = """INSERT INTO transactions (date, amount, expenses_id, description, is_expense, image_path, image_data)
                                    VALUES (?, ?, (SELECT id FROM expenses WHERE name = ?), ?, ?, ?, ?)"""
                    cursor = self.connection.cursor()
                    cursor.execute(sql, (values[1], values[0], values[2], values[3], 1, image_path, img_data))
                    self.connection.commit()

                else:
                    sql = """INSERT INTO transactions (date, amount, expenses_id, description, is_expense)
                                    VALUES (?, ?, (SELECT id FROM expenses WHERE name = ?), ?, ?)"""
                    cursor = self.connection.cursor()
                    cursor.execute(sql, (values[1], values[0], values[2], values[3], 1))
                    self.connection.commit()

            except ValueError:
                self.error(f"Не удалось записать данные: сумма не может быть нулевой")
            except Exception as e:
                self.error(f"Не удалось записать данные: {str(e)}")
            else:
                self.connection.commit()
                self.refresh()

    def addIncome(self):
        widget = AddTransactWidget(self, self.incomes)
        if widget.exec() == 1:
            values = widget.get_input()
            image_path = values[-1]
            try:
                if values[0] == "0":
                    raise ValueError
                date_obj = datetime.strptime(values[1], "%d %m %Y %H:%M")
                values[1] = date_obj.strftime("%Y-%m-%d %H:%M")

                if image_path:
                    with open(image_path, 'rb') as file:
                        img_data = file.read()

                    sql = """INSERT INTO transactions (date, amount, incomes_id, description, is_expense, image_path, image_data)
                                                VALUES (?, ?, (SELECT id FROM expenses WHERE name = ?), ?, ?, ?, ?)"""
                    cursor = self.connection.cursor()
                    cursor.execute(sql, (values[1], values[0], values[2], values[3], 0, image_path, img_data))
                    self.connection.commit()

                else:
                    sql = """INSERT INTO transactions (date, amount, expenses_id, description, is_expense)
                                                VALUES (?, ?, (SELECT id FROM expenses WHERE name = ?), ?, ?)"""
                    cursor = self.connection.cursor()
                    cursor.execute(sql, (values[1], values[0], values[2], values[3], 1))
                    self.connection.commit()
            except Exception:
                self.error('не верно введены значения')
            else:
                self.connection.commit()
                self.refresh()

    def graphic_expenses(self):
        cursor = self.connection.cursor()
        id = self.buttonGroup.checkedId()
        is_expense = True if self.buttonGroup_graphic.checkedId() == 0 else False

        dates = [QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() - 7 * self.countclicks),
                 QDate.currentDate().addDays(-QDate.currentDate().day() + 1).addMonths(-self.countclicks),
                 QDate.currentDate().addDays(-QDate.currentDate().day() + 1).addMonths(
                     -QDate.currentDate().month() + 1).addYears(-self.countclicks)]
        dates1 = [dates[0].addDays(7), dates[1].addMonths(1), dates[2].addYears(1)]

        date1 = dates1[id].toString("yyyy-MM-dd")
        date = dates[id].toString("yyyy-MM-dd")

        self.first_date.setText(f"от {dates[id].toString("d MMM yyyy")}")
        self.last_date.setText(f"до {dates1[id].toString("d MMM yyyy")}")
        if is_expense:
            query = f"""SELECT e.name, SUM(amount) AS total_amount
                        FROM transactions t
                        JOIN expenses e ON t.expenses_id = e.id
                        WHERE date >= "{date}" and date <= "{date1}" and is_expense = 1
                        GROUP BY e.name
                        ORDER BY total_amount DESC
                        LIMIT 5;
                    """
        else:
            query = f"""SELECT i.name, SUM(amount) AS total_amount
                        FROM transactions t
                        JOIN incomes i ON t.incomes_id = i.id
                        WHERE date >= "{date}" and date <= "{date1}" and is_expense = 0
                        GROUP BY i.name
                        ORDER BY total_amount DESC
                        LIMIT 5;
                    """
        self.amount_expenses(date, date1, is_expense)
        self.select_graphics_transactions(date, date1, is_expense)
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
            colors = [[54, 162, 235],
                      [255, 99, 132],
                      [75, 192, 192],
                      [153, 102, 255],
                      [255, 159, 64]]
            for index, (category, amount) in enumerate(zip(categories, amounts)):
                bar_height = (amount / max_amount) * max_bar_height

                rect = self.scene.addRect(
                    index * (bar_width + spacing),
                    max_bar_height - bar_height,
                    bar_width,
                    bar_height,
                    brush=QBrush(QColor(*colors[index]))
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

    def select_graphics_transactions(self, date, date1, is_expense):
        if is_expense:
            query = f'''SELECT t.amount, t.date, e.name, t.description, t.id FROM transactions t
                LEFT JOIN 
                    expenses e ON t.expenses_id = e.id
                    WHERE date >= "{date}" and date <= "{date1}" and is_expense = 1
                ORDER BY 
                    t.date DESC;'''
        else:
            query = f'''SELECT t.amount, t.date, i.name, t.description, t.id
                FROM 
                    transactions t
                LEFT JOIN 
                    incomes i ON t.incomes_id = i.id
                    WHERE date >= "{date}" and date <= "{date1}" and is_expense = 0
                ORDER BY 
                    t.date DESC;'''

        res = self.connection.cursor().execute(query).fetchall()
        self.tableWidget2.setColumnCount(5)
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
