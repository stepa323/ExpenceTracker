from datetime import datetime
import sys

import sqlite3
from PyQt6 import uic
from PyQt6.QtCore import QDate, QTime, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QMainWindow, QApplication, QTableWidgetItem, QDialog, QGraphicsRectItem, QGraphicsScene, \
    QVBoxLayout, QGraphicsView, QGraphicsTextItem


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

        self.tableWidget.cellChanged.connect(self.tableChanged)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)  # view - это QGraphicsView из Qt Designer

        # Рисуем график самых затратных категорий
        self.plot_expenses()


        self.select_data()


    def select_data(self):
        query = ("select date, amount, name, description from expenses\n"
                 "inner join categories on categories.id = expenses.category_id")
        res = sorted(self.connection.cursor().execute(query).fetchall(),
                     key=lambda x: datetime.strptime(x[0], "%d.%m.%Y %H:%M"), reverse=True)
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)

        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))
        self.refresh_graph()


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


    def tableChanged(self):
        ...


    def plot_expenses(self):
        cursor = self.connection.cursor()

        # Запрос к базе данных
        query = """
                    SELECT c.name, SUM(e.amount) AS total_amount
                    FROM expenses e
                    JOIN categories c ON e.category_id = c.id
                    WHERE e.date >= date(2024)
                    GROUP BY c.name
                    ORDER BY total_amount DESC
                    LIMIT 5;
                """
        a = cursor.execute(query).fetchall()
        print(a)
        # Получаем результаты
        categories = []
        amounts = []
        for row in a:
            categories.append(row[0])  # имя категории
            amounts.append(row[1])  # сумма расходов


        # Определение максимальной суммы для масштаба графика
        max_amount = max(amounts) if amounts else 1  # избегаем деления на 0, если данных нет

        bar_width = 70  # Ширина столбца
        spacing = 15  # Интервал между столбцами

        max_bar_height = 170

        self.scene.clear()

        for index, (category, amount) in enumerate(zip(categories, amounts)):
            # Нормализуем значение для отображения в графике (по отношению к max_amount)
            bar_height = (amount / max_amount) * max_bar_height  # Высота столбца

            # Создаем прямоугольник для столбца
            rect = self.scene.addRect(
                index * (bar_width + spacing),  # X-координата
                max_bar_height - bar_height,  # Y-координата (чтобы столбец был "снизу вверх")
                bar_width,  # Ширина столбца
                bar_height,  # Высота столбца
                brush=QBrush(QColor(100, 150, 255))  # Цвет столбца
            )

            # Создаем текст с названием категории и располагируем его строго под столбцом
            text_item = QGraphicsTextItem(category)
            text_item.setFont(QFont('Arial', 10))  # Устанавливаем шрифт и размер
            text_item.setTextWidth(bar_width)  # Ограничиваем ширину текста размером столбца
            text_item.setPos(index * (bar_width + spacing), max_bar_height + 5) # Позиция текста

            amount_text_item = QGraphicsTextItem(f"{amount:.2f}")  # Форматируем число до двух знаков
            amount_text_item.setFont(QFont('Arial', 10))  # Устанавливаем шрифт
            amount_text_item.setPos(
                index * (bar_width + spacing) + (bar_width // 2) - (amount_text_item.boundingRect().width() / 2),
                max_bar_height - bar_height - 20)  # Позиция суммы по центру # Черный цвет для суммы
            self.scene.addItem(amount_text_item)

            # Добавляем текст в сцену
            self.scene.addItem(text_item)

            # Устанавливаем область видимости сцены, чтобы все столбцы были видны
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
