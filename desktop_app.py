import sys
import sqlite3
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QSplitter, QGroupBox
)

DB_NAME = "flower_shop.db"


# ---------------- DB Helpers ----------------
def get_conn():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = get_conn()
    c = con.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        phone TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS flowers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS flower_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flower_id INTEGER NOT NULL,
        price_date TEXT NOT NULL,  -- YYYY-MM-DD
        price REAL NOT NULL,
        UNIQUE(flower_id, price_date),
        FOREIGN KEY(flower_id) REFERENCES flowers(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        flower_id INTEGER,  -- optional but recommended
        entry_date TEXT NOT NULL,  -- YYYY-MM-DD
        particular TEXT,
        qty INTEGER,
        flower_price REAL,  -- rate actually used
        ded_credit TEXT,  -- note / text / number as text
        amount REAL,
        balance REAL,
        FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY(flower_id) REFERENCES flowers(id) ON DELETE SET NULL
    )""")

    con.commit()
    con.close()


def fetch_today_price(flower_id: int, ymd: str) -> float or None:
    """
    Return the most recent price for the flower on or before the given date.
    """
    con = get_conn()
    c = con.cursor()
    c.execute("""SELECT price FROM flower_prices
                 WHERE flower_id=? AND price_date<=?
                 ORDER BY price_date DESC LIMIT 1""", (flower_id, ymd))
    row = c.fetchone()
    con.close()
    return None if not row else float(row[0])


def info(w, msg):
    QMessageBox.information(w, "Info", msg)


def warn(w, msg):
    QMessageBox.warning(w, "Warning", msg)


# ---------------- Customer Master ----------------
class CustomerMasterTab(QWidget):
    def __init__(self, font):
        super().__init__()
        self.font = font
        self.editing_id = None
        self.build_ui()
        self.load_table()

    def build_ui(self):
        lay = QVBoxLayout(self)

        title = QLabel("👤 Customer Master / வாடிக்கையாளர்கள்")
        title.setFont(self.font)
        lay.addWidget(title)

        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setFont(self.font)
        self.addr = QTextEdit()
        self.addr.setFont(self.font)
        self.addr.setFixedHeight(60)
        self.phone = QLineEdit()
        self.phone.setFont(self.font)
        form.addRow("Name / பெயர்", self.name)
        form.addRow("Address / முகவரி", self.addr)
        form.addRow("Phone / தொலைபேசி", self.phone)

        btns = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save")
        self.btn_update = QPushButton("✏️ Update")
        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_clear = QPushButton("🧹 Clear")
        for b in (self.btn_save, self.btn_update, self.btn_delete, self.btn_clear):
            b.setFont(self.font)
            btns.addWidget(b)
        btns.addStretch()

        self.btn_save.clicked.connect(self.save_customer)
        self.btn_update.clicked.connect(self.update_customer)
        self.btn_delete.clicked.connect(self.delete_customer)
        self.btn_clear.clicked.connect(self.clear_form)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Address"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.on_row)

        lay.addLayout(form)
        lay.addLayout(btns)
        lay.addWidget(self.table)

    def load_table(self):
        con = get_conn()
        c = con.cursor()
        c.execute("SELECT id, name, phone, address FROM customers ORDER BY name")
        rows = c.fetchall()
        con.close()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for col, val in enumerate(row):
                self.table.setItem(r, col, QTableWidgetItem("" if val is None else str(val)))

    def on_row(self, r, _c):
        self.editing_id = int(self.table.item(r, 0).text())
        self.name.setText(self.table.item(r, 1).text())
        self.phone.setText(self.table.item(r, 2).text())
        self.addr.setPlainText(self.table.item(r, 3).text())

    def clear_form(self):
        self.editing_id = None
        self.name.clear()
        self.addr.clear()
        self.phone.clear()
        self.table.clearSelection()

    def save_customer(self):
        n = self.name.text().strip()
        if not n:
            return warn(self, "Name required")
        con = get_conn()
        c = con.cursor()
        try:
            c.execute("INSERT INTO customers (name, address, phone) VALUES (?, ?, ?)",
                      (n, self.addr.toPlainText().strip(), self.phone.text().strip()))
            con.commit()
            info(self, "Saved")
            self.clear_form()
            self.load_table()
        except sqlite3.IntegrityError:
            warn(self, "Customer already exists")
        finally:
            con.close()

    def update_customer(self):
        if not self.editing_id:
            return warn(self, "Select a row")
        n = self.name.text().strip()
        if not n:
            return warn(self, "Name required")
        con = get_conn()
        c = con.cursor()
        try:
            c.execute("UPDATE customers SET name=?, address=?, phone=? WHERE id=?",
                      (n, self.addr.toPlainText().strip(), self.phone.text().strip(), self.editing_id))
            con.commit()
            info(self, "Updated")
            self.clear_form()
            self.load_table()
        except sqlite3.IntegrityError:
            warn(self, "Duplicate name")
        finally:
            con.close()

    def delete_customer(self):
        if not self.editing_id:
            return warn(self, "Select a row")
        if QMessageBox.question(self, "Confirm", "Delete this customer?") != QMessageBox.Yes:
            return
        con = get_conn()
        c = con.cursor()
        c.execute("DELETE FROM customers WHERE id=?", (self.editing_id,))
        con.commit()
        con.close()
        info(self, "Deleted")
        self.clear_form()
        self.load_table()


# ---------------- Flower Master (with Price History) ----------------
class FlowerMasterTab(QWidget):
    def __init__(self, font):
        super().__init__()
        self.font = font
        self.flower_editing_id = None
        self.build_ui()
        self.load_flowers()

    def build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("🌼 Flower Master + Price History / மலர் பட்டியல் + விலை வரலாறு")
        title.setFont(self.font)
        root.addWidget(title)

        splitter = QSplitter()
        # Left: flower list + form
        left = QWidget()
        left_lay = QVBoxLayout(left)

        grp = QGroupBox("Flower Form")
        grp_lay = QFormLayout(grp)
        self.f_name = QLineEdit()
        self.f_name.setFont(self.font)
        grp_lay.addRow("Flower Name / மலர் பெயர்", self.f_name)
        fbtns = QHBoxLayout()
        self.f_save = QPushButton("💾 Save")
        self.f_update = QPushButton("✏️ Update")
        self.f_delete = QPushButton("🗑️ Delete")
        self.f_clear = QPushButton("🧹 Clear")
        for b in (self.f_save, self.f_update, self.f_delete, self.f_clear):
            b.setFont(self.font)
            fbtns.addWidget(b)
        fbtns.addStretch()
        left_lay.addWidget(grp)
        left_lay.addLayout(fbtns)

        self.f_save.clicked.connect(self.save_flower)
        self.f_update.clicked.connect(self.update_flower)
        self.f_delete.clicked.connect(self.delete_flower)
        self.f_clear.clicked.connect(self.clear_flower_form)

        self.table_flowers = QTableWidget(0, 2)
        self.table_flowers.setHorizontalHeaderLabels(["ID", "Flower"])
        self.table_flowers.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_flowers.horizontalHeader().setStretchLastSection(True)
        self.table_flowers.cellClicked.connect(self.on_flower_row)
        left_lay.addWidget(self.table_flowers)

        # Right: price history
        right = QWidget()
        right_lay = QVBoxLayout(right)
        ph_form = QFormLayout()
        self.ph_date = QDateEdit(QDate.currentDate())
        self.ph_date.setCalendarPopup(True)
        self.ph_date.setFont(self.font)
        self.ph_price = QDoubleSpinBox()
        self.ph_price.setRange(0, 1_000_000)
        self.ph_price.setDecimals(2)
        self.ph_price.setFont(self.font)
        ph_form.addRow("Date / தேதி", self.ph_date)
        ph_form.addRow("Price / விலை", self.ph_price)
        ph_btns = QHBoxLayout()
        self.ph_add = QPushButton("➕ Add/Update Price")
        self.ph_del = QPushButton("🗑️ Delete Price Row")
        for b in (self.ph_add, self.ph_del):
            b.setFont(self.font)
            ph_btns.addWidget(b)
        ph_btns.addStretch()
        self.ph_add.clicked.connect(self.add_price)
        self.ph_del.clicked.connect(self.delete_price)

        self.table_prices = QTableWidget(0, 3)
        self.table_prices.setHorizontalHeaderLabels(["ID", "Date", "Price"])
        self.table_prices.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_prices.horizontalHeader().setStretchLastSection(True)

        right_lay.addLayout(ph_form)
        right_lay.addLayout(ph_btns)
        right_lay.addWidget(self.table_prices)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([300, 500])
        root.addWidget(splitter)

    def load_flowers(self):
        con = get_conn()
        c = con.cursor()
        c.execute("SELECT id, name FROM flowers ORDER BY name")
        rows = c.fetchall()
        con.close()
        self.table_flowers.setRowCount(len(rows))
        for r, (fid, name) in enumerate(rows):
            self.table_flowers.setItem(r, 0, QTableWidgetItem(str(fid)))
            self.table_flowers.setItem(r, 1, QTableWidgetItem(name))
        # After reload, refresh price table if a flower is selected
        if self.table_flowers.rowCount() > 0 and self.table_flowers.currentRow() >= 0:
            self.on_flower_row(self.table_flowers.currentRow(), 0)
        else:
            self.table_prices.setRowCount(0)

    def on_flower_row(self, r, _c):
        self.flower_editing_id = int(self.table_flowers.item(r, 0).text())
        self.f_name.setText(self.table_flowers.item(r, 1).text())
        self.load_price_history(self.flower_editing_id)

    def clear_flower_form(self):
        self.flower_editing_id = None
        self.f_name.clear()
        self.table_flowers.clearSelection()
        self.table_prices.setRowCount(0)

    def save_flower(self):
        n = self.f_name.text().strip()
        if not n:
            return warn(self, "Flower name required")
        con = get_conn()
        c = con.cursor()
        try:
            c.execute("INSERT INTO flowers (name) VALUES (?)", (n,))
            con.commit()
            info(self, "Saved")
            self.load_flowers()
            self.f_name.clear()
        except sqlite3.IntegrityError:
            warn(self, "Flower already exists")
        finally:
            con.close()

    def update_flower(self):
        if not self.flower_editing_id:
            return warn(self, "Select a flower")
        n = self.f_name.text().strip()
        if not n:
            return warn(self, "Flower name required")
        con = get_conn()
        c = con.cursor()
        try:
            c.execute("UPDATE flowers SET name=? WHERE id=?", (n, self.flower_editing_id))
            con.commit()
            info(self, "Updated")
            self.load_flowers()
        except sqlite3.IntegrityError:
            warn(self, "Duplicate name")
        finally:
            con.close()

    def delete_flower(self):
        if not self.flower_editing_id:
            return warn(self, "Select a flower")
        if QMessageBox.question(self, "Confirm", "Delete this flower (and its prices)?") != QMessageBox.Yes:
            return
        con = get_conn()
        c = con.cursor()
        c.execute("DELETE FROM flowers WHERE id=?", (self.flower_editing_id,))
        con.commit()
        con.close()
        info(self, "Deleted")
        self.clear_flower_form()
        self.load_flowers()

    def load_price_history(self, flower_id):
        con = get_conn()
        c = con.cursor()
        c.execute("""SELECT id, price_date, price FROM flower_prices
                     WHERE flower_id=? ORDER BY price_date DESC""", (flower_id,))
        rows = c.fetchall()
        con.close()
        self.table_prices.setRowCount(len(rows))
        for r, (pid, d, p) in enumerate(rows):
            self.table_prices.setItem(r, 0, QTableWidgetItem(str(pid)))
            self.table_prices.setItem(r, 1, QTableWidgetItem(d))
            self.table_prices.setItem(r, 2, QTableWidgetItem(f"{p:.2f}"))

    def add_price(self):
        if not self.flower_editing_id:
            return warn(self, "Select a flower first")
        d = self.ph_date.date().toString("yyyy-MM-dd")
        p = float(self.ph_price.value())
        con = get_conn()
        c = con.cursor()
        try:
            # Upsert by (flower_id, date)
            c.execute("""INSERT INTO flower_prices (flower_id, price_date, price)
                         VALUES (?, ?, ?)
                         ON CONFLICT(flower_id, price_date) DO UPDATE SET price=excluded.price""",
                      (self.flower_editing_id, d, p))
            con.commit()
            info(self, "Price saved")
            self.load_price_history(self.flower_editing_id)
        finally:
            con.close()

    def delete_price(self):
        row = self.table_prices.currentRow()
        if row < 0:
            return warn(self, "Select a price row")
        pid = int(self.table_prices.item(row, 0).text())
        if QMessageBox.question(self, "Confirm", "Delete this price entry?") != QMessageBox.Yes:
            return
        con = get_conn()
        c = con.cursor()
        c.execute("DELETE FROM flower_prices WHERE id=?", (pid,))
        con.commit()
        con.close()
        info(self, "Deleted")
        if self.flower_editing_id:
            self.load_price_history(self.flower_editing_id)


# ---------------- Daily Entry ----------------
class DailyEntryTab(QWidget):
    def __init__(self, font):
        super().__init__()
        self.font = font
        self.build_ui()
        self.reload_lists()
        self.load_table()

    def build_ui(self):
        lay = QVBoxLayout(self)
        title = QLabel("🗓️ Daily Entry / தினசரி பதிவு")
        title.setFont(self.font)
        lay.addWidget(title)

        top = QHBoxLayout()
        self.d_date = QDateEdit(QDate.currentDate())
        self.d_date.setCalendarPopup(True)
        self.d_date.setFont(self.font)
        self.d_date.dateChanged.connect(self.on_date_or_flower_change)
        self.filter_customer = QComboBox()
        self.filter_customer.setFont(self.font)
        self.filter_customer.currentIndexChanged.connect(self.load_table)
        self.filter_flower = QComboBox()
        self.filter_flower.setFont(self.font)
        self.filter_flower.currentIndexChanged.connect(self.load_table)
        top.addWidget(QLabel("Date"))
        top.addWidget(self.d_date)
        top.addSpacing(15)
        top.addWidget(QLabel("Filter: Customer"))
        top.addWidget(self.filter_customer)
        top.addSpacing(10)
        top.addWidget(QLabel("Flower"))
        top.addWidget(self.filter_flower)
        top.addStretch()
        lay.addLayout(top)

        # Form
        form = QFormLayout()
        self.cb_customer = QComboBox()
        self.cb_customer.setFont(self.font)
        self.cb_flower = QComboBox()
        self.cb_flower.setFont(self.font)
        self.cb_flower.currentIndexChanged.connect(self.on_date_or_flower_change)

        self.particular = QLineEdit()
        self.particular.setFont(self.font)
        self.qty = QSpinBox()
        self.qty.setRange(0, 1_000_000)
        self.qty.setFont(self.font)
        self.rate = QDoubleSpinBox()
        self.rate.setRange(0, 1_000_000)
        self.rate.setDecimals(2)
        self.rate.setFont(self.font)
        self.rate.setToolTip("Auto-fills from Flower Price for selected date; you can override.")
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1_000_000)
        self.amount.setDecimals(2)
        self.amount.setFont(self.font)
        self.balance = QDoubleSpinBox()
        self.balance.setRange(-1_000_000, 1_000_000)
        self.balance.setDecimals(2)
        self.balance.setFont(self.font)
        self.ded_credit = QLineEdit()
        self.ded_credit.setFont(self.font)

        form.addRow("Customer / வாடிக்கையாளர்", self.cb_customer)
        form.addRow("Flower / மலர்", self.cb_flower)
        form.addRow("Particular / விவரம்", self.particular)
        form.addRow("Qty / அளவு", self.qty)
        form.addRow("Rate / விலை", self.rate)
        form.addRow("Amount / தொகை", self.amount)
        form.addRow("Balance / பற்று", self.balance)
        form.addRow("Deduction/Credit / குறிப்பு", self.ded_credit)

        btns = QHBoxLayout()
        self.btn_calc = QPushButton("🧮 Compute Amount (Qty × Rate)")
        self.btn_save = QPushButton("💾 Add Entry")
        self.btn_clear = QPushButton("🧹 Clear")
        for b in (self.btn_calc, self.btn_save, self.btn_clear):
            b.setFont(self.font)
            btns.addWidget(b)
        btns.addStretch()
        self.btn_calc.clicked.connect(self.compute_amount)
        self.btn_save.clicked.connect(self.save_entry)
        self.btn_clear.clicked.connect(self.clear_form)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Customer", "Flower", "Particular",
            "Qty", "Rate", "Amount", "Ded/Credit", "Balance"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        lay.addLayout(form)
        lay.addLayout(btns)
        lay.addWidget(self.table)

    def reload_lists(self):
        # Customers
        con = get_conn()
        c = con.cursor()
        c.execute("SELECT id, name FROM customers ORDER BY name")
        cust = c.fetchall()
        c.execute("SELECT id, name FROM flowers ORDER BY name")
        flow = c.fetchall()
        con.close()

        def fill_combo(cb, rows):
            cb.blockSignals(True)
            cb.clear()
            for _id, name in rows:
                cb.addItem(name, _id)
            cb.blockSignals(False)

        fill_combo(self.cb_customer, cust)
        fill_combo(self.cb_flower, flow)

        # Filters
        self.filter_customer.blockSignals(True)
        self.filter_customer.clear()
        self.filter_customer.addItem("All", None)
        for _id, name in cust:
            self.filter_customer.addItem(name, _id)
        self.filter_customer.blockSignals(False)

        self.filter_flower.blockSignals(True)
        self.filter_flower.clear()
        self.filter_flower.addItem("All", None)
        for _id, name in flow:
            self.filter_flower.addItem(name, _id)
        self.filter_flower.blockSignals(False)

        # Also refresh auto-rate (in case new flowers/prices added)
        self.on_date_or_flower_change()

    def on_date_or_flower_change(self):
        if self.cb_flower.count() == 0:
            return
        fid = self.cb_flower.currentData()
        ymd = self.d_date.date().toString("yyyy-MM-dd")
        price = fetch_today_price(fid, ymd)
        if price is not None:
            self.rate.setValue(price)

    def compute_amount(self):
        self.amount.setValue(self.qty.value() * self.rate.value())

    def clear_form(self):
        self.particular.clear()
        self.qty.setValue(0)
        # Rate will stay (useful)
        self.amount.setValue(0.0)
        self.balance.setValue(0.0)
        self.ded_credit.clear()

    def save_entry(self):
        if self.cb_customer.count() == 0:
            return warn(self, "Add a customer first")
        if self.cb_flower.count() == 0:
            return warn(self, "Add a flower first")

        entry_date = self.d_date.date().toString("yyyy-MM-dd")
        customer_id = self.cb_customer.currentData()
        flower_id = self.cb_flower.currentData()
        particular = self.particular.text().strip()
        qty = int(self.qty.value())
        rate = float(self.rate.value())
        amount = float(self.amount.value()) if self.amount.value() else qty * rate
        balance = float(self.balance.value())
        ded = self.ded_credit.text().strip()

        con = get_conn()
        c = con.cursor()
        c.execute("""INSERT INTO daily_entries
                     (customer_id, flower_id, entry_date, particular, qty, flower_price, ded_credit, amount, balance)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (customer_id, flower_id, entry_date, particular, qty, rate, ded, amount, balance))
        con.commit()
        con.close()
        info(self, "Entry saved")
        self.clear_form()
        self.load_table()

    def load_table(self):
        ymd = self.d_date.date().toString("yyyy-MM-dd")
        cid = self.filter_customer.currentData()
        fid = self.filter_flower.currentData()

        sql = """SELECT e.id, e.entry_date, c.name, f.name, e.particular,
                        e.qty, e.flower_price, e.amount, e.ded_credit, e.balance
                 FROM daily_entries e
                 JOIN customers c ON c.id = e.customer_id
                 LEFT JOIN flowers f ON f.id = e.flower_id
                 WHERE e.entry_date = ?"""
        params = [ymd]
        if cid:
            sql += " AND e.customer_id = ?"
            params.append(cid)
        if fid:
            sql += " AND e.flower_id = ?"
            params.append(fid)
        sql += " ORDER BY e.id DESC"

        con = get_conn()
        c = con.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        con.close()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for col, val in enumerate(row):
                self.table.setItem(r, col, QTableWidgetItem("" if val is None else str(val)))


# ---------------- Main Window ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌸 Flower Shop (Offline) — Tamil/English")
        self.resize(1200, 750)

        font = QFont("Noto Sans Tamil", 11)  # Change to "Latha" on Windows if needed

        tabs = QTabWidget()
        self.tab_customers = CustomerMasterTab(font)
        self.tab_flowers = FlowerMasterTab(font)
        self.tab_daily = DailyEntryTab(font)

        tabs.addTab(self.tab_customers, "Customers / வாடிக்கையாளர்கள்")
        tabs.addTab(self.tab_flowers, "Flowers & Prices / மலர் & விலை")
        tabs.addTab(self.tab_daily, "Daily Entry / தினசரி பதிவு")

        self.setCentralWidget(tabs)
        self.build_menu()

    def build_menu(self):
        m = self.menuBar().addMenu("Data")
        act_reload = m.addAction("Reload lists")
        act_reload.triggered.connect(self.reload_all)

    def reload_all(self):
        self.tab_customers.load_table()
        self.tab_flowers.load_flowers()
        self.tab_daily.reload_lists()
        self.tab_daily.load_table()
        info(self, "Reloaded")


# ---------------- App Entry ----------------
def main():
    init_db()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()