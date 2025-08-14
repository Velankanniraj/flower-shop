import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Initialize the database
# Replace the init_db function in your existing app.py
def init_db():
    conn = sqlite3.connect('flower_shop.db')
    c = conn.cursor()
    
    # Drop existing tables if reinitializing
    if st.sidebar.button("Reinitialize Database"):
        c.execute("DROP TABLE IF EXISTS FlowerMaster")
        c.execute("DROP TABLE IF EXISTS CustomerMaster")
        c.execute("DROP TABLE IF EXISTS BuyerMaster")
        c.execute("DROP TABLE IF EXISTS DailySheet")
        c.execute("DROP TABLE IF EXISTS DailyFlowerPrice")
        st.warning("Database reinitialized. All data has been cleared.")
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS FlowerMaster
                 (Name TEXT PRIMARY KEY, DisplayName TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS CustomerMaster
                 (Name TEXT PRIMARY KEY, Address TEXT, ContactNo TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS BuyerMaster
                 (Name TEXT PRIMARY KEY, Address TEXT, ContactNo TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS DailySheet
                 (Id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, Name TEXT, FlowerName TEXT, 
                  Qty REAL, Rate REAL, Amount REAL, DebitCredit TEXT, Debt REAL, BuyerName TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS DailyFlowerPrice
                 (FlowerName TEXT, Date TEXT, Price REAL, PRIMARY KEY (FlowerName, Date))''')
    
    conn.commit()
    return conn

# Helper functions
def get_flowers(conn):
    df = pd.read_sql("SELECT Name FROM FlowerMaster", conn)
    return df['Name'].tolist()

def get_customers(conn):
    df = pd.read_sql("SELECT Name FROM CustomerMaster", conn)
    return df['Name'].tolist()

def get_buyers(conn):
    df = pd.read_sql("SELECT Name FROM BuyerMaster", conn)
    return df['Name'].tolist()

def get_display_name(conn, name):
    c = conn.cursor()
    c.execute("SELECT DisplayName FROM FlowerMaster WHERE Name = ?", (name,))
    result = c.fetchone()
    return result[0] if result else name

def recalculate_debts(conn, buyer_name):
    df = pd.read_sql("SELECT * FROM DailySheet WHERE DebitCredit = 'Credit' and BuyerName = ? ORDER BY Id", conn, params=(buyer_name,))
    if df.empty:
        return
    running_debt = 0.0
    c = conn.cursor()
    for index, row in df.iterrows():
        signed = row['Amount'] if row['DebitCredit'] == 'Credit' else -row['Amount']
        running_debt += signed
        c.execute("UPDATE DailySheet SET Debt = ? WHERE DebitCredit = 'Credit' and Id = ?", (running_debt, row['Id']))
    conn.commit()

# Main app
st.title("Flower Shop Application (PoC)")

conn = init_db()

# Sidebar navigation
sections = ["Flower Master", "Customer Master", "Buyer Master", "Daily Flower Price", "Daily Sheet", "Reports"]
choice = st.sidebar.selectbox("Select Section", sections)
# Replace the Flower Master section
if choice == "Flower Master":
    st.header("Flower Master")
    
    # Install googletrans if not already installed
    try:
        from googletrans import Translator, LANGUAGES
    except ImportError:
        st.warning("Please install googletrans: `pip install googletrans==3.1.0a0`")
        st.stop()

    # Initialize variables with persistence using st.session_state to retain values across reruns
    if 'name' not in st.session_state:
        st.session_state['name'] = ""
    if 'suggested_words' not in st.session_state:
        st.session_state['suggested_words'] = []
    if 'display_name' not in st.session_state:
        st.session_state['display_name'] = ""

    # Input and buttons
    st.session_state['name'] = st.text_input("Name (English)", value=st.session_state['name'], key="name_input")
    suggested_words = st.session_state['suggested_words']
    display_name = st.session_state['display_name']

    # Button to fetch suggested words
    if st.button("Fetch Words"):
        if st.session_state['name']:
            translator = Translator()
            tamil_trans = translator.translate(st.session_state['name'], src='en', dest='ta').text
            st.session_state['suggested_words'] = tamil_trans.split()
        else:
            st.warning("Please enter a name to fetch words.")

    # Button to translate and set display name
    if st.button("Translate to Tamil"):
        if st.session_state['suggested_words']:
            st.session_state['display_name'] = " ".join(st.session_state['suggested_words'])
        else:
            st.warning("Please fetch words first.")

    # Word selection
    if st.session_state['suggested_words']:
        selected_words = st.multiselect("Select Tamil Words", st.session_state['suggested_words'], 
                                       default=st.session_state['suggested_words'], key="word_select")
        st.session_state['display_name'] = " ".join(selected_words) if selected_words else st.session_state['display_name']

    # Add form with transliteration
    with st.form(key="add_flower_form"):
        display_name_input = st.text_input("Display Name (Tamil)", value=st.session_state['display_name'], key="display_name_input")
        submit_add = st.form_submit_button("Add")
        if submit_add and st.session_state['name']:
            if not display_name_input.strip():  # Check for empty or whitespace-only input
                st.error("Display Name (Tamil) cannot be empty.")
            else:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO FlowerMaster (Name, DisplayName) VALUES (?, ?)", 
                              (st.session_state['name'], display_name_input))
                    conn.commit()
                    st.success("Flower added successfully!")
                    st.session_state['name'] = ""
                    st.session_state['display_name'] = ""
                    st.session_state['suggested_words'] = []
                except sqlite3.IntegrityError:
                    st.error("Flower name already exists!")

    # Select record for edit/delete
    df = pd.read_sql("SELECT * FROM FlowerMaster", conn)
    if not df.empty:
        selected_name = st.selectbox("Select Flower to Edit/Delete", df['Name'].tolist(), key="select_flower")
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT DisplayName FROM FlowerMaster WHERE Name = ?", (selected_name,))
            current_display = c.fetchone()[0]
            
            with st.form(key="edit_flower_form"):
                new_display_name = st.text_input("New Display Name (Tamil)", value=current_display, key="new_display_name")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        if not new_display_name.strip():
                            st.error("New Display Name (Tamil) cannot be empty.")
                        else:
                            c.execute("UPDATE FlowerMaster SET DisplayName = ? WHERE Name = ?", 
                                      (new_display_name, selected_name))
                            conn.commit()
                            st.success("Flower updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM FlowerMaster WHERE Name = ?", (selected_name,))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes
    
    # View
    st.dataframe(df, key="flower_master_df")

elif choice == "Customer Master":
    st.header("Customer Master")
    
    # Add form
    with st.form(key="Add Customer"):
        name = st.text_input("Name")
        address = st.text_input("Address")
        contact_no = st.text_input("Contact No")
        submit_add = st.form_submit_button("Add")
        if submit_add and name:
            try:
                c = conn.cursor()
                c.execute("INSERT INTO CustomerMaster (Name, Address, ContactNo) VALUES (?, ?, ?)", 
                          (name, address, contact_no))
                conn.commit()
                st.success("Customer added successfully!")
            except sqlite3.IntegrityError:
                st.error("Customer name already exists!")
    
    # Select record for edit/delete
    df = pd.read_sql("SELECT * FROM CustomerMaster", conn)
    if not df.empty:
        selected_name = st.selectbox("Select Customer to Edit/Delete", df['Name'].tolist())
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT Address, ContactNo FROM CustomerMaster WHERE Name = ?", (selected_name,))
            current_data = c.fetchone()
            
            with st.form(key="Edit Customer"):
                new_address = st.text_input("New Address", value=current_data[0])
                new_contact_no = st.text_input("New Contact No", value=current_data[1])
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        c.execute("UPDATE CustomerMaster SET Address = ?, ContactNo = ? WHERE Name = ?", 
                                  (new_address, new_contact_no, selected_name))
                        conn.commit()
                        st.success("Customer updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM CustomerMaster WHERE Name = ?", (selected_name,))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes
    
    # View
    st.dataframe(df)

elif choice == "Buyer Master":
    st.header("Buyer Master")
    
    # Add form
    with st.form(key="Add Buyer"):
        name = st.text_input("Name")
        address = st.text_input("Address")
        contact_no = st.text_input("Contact No")
        submit_add = st.form_submit_button("Add")
        if submit_add and name:
            try:
                c = conn.cursor()
                c.execute("INSERT INTO BuyerMaster (Name, Address, ContactNo) VALUES (?, ?, ?)", 
                          (name, address, contact_no))
                conn.commit()
                st.success("Buyer added successfully!")
            except sqlite3.IntegrityError:
                st.error("Buyer name already exists!")
    
    # Select record for edit/delete
    df = pd.read_sql("SELECT * FROM BuyerMaster", conn)
    if not df.empty:
        selected_name = st.selectbox("Select Buyer to Edit/Delete", df['Name'].tolist())
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT Address, ContactNo FROM BuyerMaster WHERE Name = ?", (selected_name,))
            current_data = c.fetchone()
            
            with st.form(key="Edit Buyer"):
                new_address = st.text_input("New Address", value=current_data[0])
                new_contact_no = st.text_input("New Contact No", value=current_data[1])
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        c.execute("UPDATE BuyerMaster SET Address = ?, ContactNo = ? WHERE Name = ?", 
                                  (new_address, new_contact_no, selected_name))
                        conn.commit()
                        st.success("Buyer updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM BuyerMaster WHERE Name = ?", (selected_name,))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes
    
    # View
    st.dataframe(df)

elif choice == "Daily Flower Price":
    st.header("Daily Flower Price")
    flowers = get_flowers(conn)
    
    # Add form
    with st.form(key="Set Price"):
        flower_name = st.selectbox("Flower Name", flowers)
        selected_date = st.date_input("Date", value=date.today())
        price = st.number_input("Price", min_value=0.0)
        submit_add = st.form_submit_button("Set")
        if submit_add and flower_name:
            date_str = selected_date.strftime("%Y-%m-%d")
            try:
                c = conn.cursor()
                c.execute("INSERT INTO DailyFlowerPrice (FlowerName, Date, Price) VALUES (?, ?, ?)", 
                          (flower_name, date_str, price))
                conn.commit()
                st.success("Price set successfully!")
            except sqlite3.IntegrityError:
                c.execute("UPDATE DailyFlowerPrice SET Price = ? WHERE FlowerName = ? AND Date = ?", 
                          (price, flower_name, date_str))
                conn.commit()
                st.success("Price updated successfully!")
    
    # Select record for edit/delete
    df = pd.read_sql("SELECT * FROM DailyFlowerPrice ORDER BY Date DESC", conn)
    if not df.empty:
        selected_key = st.selectbox("Select Price Entry to Edit/Delete", 
                                   [f"{row['FlowerName']} - {row['Date']}" for _, row in df.iterrows()])
        if selected_key:
            flower_name, date_str = selected_key.split(" - ")
            c = conn.cursor()
            c.execute("SELECT Price FROM DailyFlowerPrice WHERE FlowerName = ? AND Date = ?", (flower_name, date_str))
            current_price = c.fetchone()[0]
            
            with st.form(key="Edit Price"):
                new_price = st.number_input("New Price", min_value=0.0, value=current_price)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        c.execute("UPDATE DailyFlowerPrice SET Price = ? WHERE FlowerName = ? AND Date = ?", 
                                  (new_price, flower_name, date_str))
                        conn.commit()
                        st.success("Price updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM DailyFlowerPrice WHERE FlowerName = ? AND Date = ?", 
                                  (flower_name, date_str))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes
    
    # View
    st.dataframe(df)
elif choice == "Daily Sheet":
    st.header("Daily Sheet")
    customers = get_customers(conn)
    flowers = get_flowers(conn)
    buyers = get_buyers(conn)
    
    # Add form
    with st.form(key="Add Transaction"):
        col1, col2 = st.columns(2)
        with col1: 
            selected_date = st.date_input("Date", value=date.today())
            name = st.selectbox("Customer Name", [""] + customers, index=0)
            flower_name = st.selectbox("Flower Name", [""] + flowers, index = 0)
            qty = st.number_input("Quantity (in KGs)", min_value=0.0)
            date_str = selected_date.strftime("%Y-%m-%d")
            c = conn.cursor()
            c.execute("SELECT Price FROM DailyFlowerPrice WHERE FlowerName = ? AND Date = ?", (flower_name, date_str))
            result = c.fetchone()
            default_rate = result[0] if result else 0.0
            rate = st.number_input("Rate", min_value=0.0, value=default_rate)
            amount = qty * rate
            st.write(f"Calculated Amount: {amount}")
        with col2:
            debit_credit = st.selectbox("Debit/Credit", ["Debit", "Credit"])
            buyer_name = st.selectbox("Buyer Name", [""] + buyers, index = 0)
            df_transactions = pd.read_sql("SELECT * FROM DailySheet WHERE BuyerName = ?", conn, params=(buyer_name,))
            if not df_transactions.empty:
                df_transactions['SignedAmount'] = df_transactions.apply(
                    lambda row: row['Amount'] if row['DebitCredit'] == 'Credit' else -row['Amount'], axis=1)
                current_debt = df_transactions['SignedAmount'].sum()
            else:
                current_debt = 0.0
            if debit_credit == "Credit":
                signed_amount = amount
                new_debt = current_debt + signed_amount
            else:
                new_debt = -amount
            st.write(f"Current Debt: {current_debt}")
            st.write(f"New Debt: {new_debt}")
        submit_add = st.form_submit_button("Add")
        if submit_add and name and flower_name:
            if debit_credit == "Credit" and not buyer_name:
                st.error("Buyer Name is required when Debit/Credit is set to 'Credit'.")
            else:
                c = conn.cursor()
                c.execute("""INSERT INTO DailySheet (Date, Name, FlowerName, Qty, Rate, Amount, DebitCredit, Debt, BuyerName) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                          (date_str, name, flower_name, qty, rate, amount, debit_credit, new_debt, buyer_name))
                conn.commit()
                recalculate_debts(conn, buyer_name)
                st.success("Transaction added successfully!")
    
    # Select record for edit/delete
    df = pd.read_sql("SELECT * FROM DailySheet ORDER BY Date DESC", conn)
    # View
    st.dataframe(df)

    if not df.empty:
        selected_id = st.selectbox("Select Transaction to Edit/Delete", df['Id'].tolist())
        if selected_id:
            c = conn.cursor()
            c.execute("SELECT Date, Name, FlowerName, Qty, Rate, Amount, DebitCredit, Debt, BuyerName FROM DailySheet WHERE Id = ?", 
                      (selected_id,))
            current_data = c.fetchone()
            old_buyer = current_data[8]
            old_amount = current_data[5]
            old_debit_credit = current_data[6]
            old_signed = old_amount if old_debit_credit == "Credit" else -old_amount
            date_obj = datetime.strptime(current_data[0], "%Y-%m-%d").date()
            
            with st.form(key="Edit Transaction"):
                selected_date = st.date_input("Date", value=date_obj)
                name = st.selectbox("Customer Name", customers, index=customers.index(current_data[1]))
                flower_name = st.selectbox("Flower Name", flowers, index=flowers.index(current_data[2]))
                qty = st.number_input("Quantity (in KGs)", min_value=0.0, value=current_data[3])
                rate = st.number_input("Rate", min_value=0.0, value=current_data[4])
                amount = qty * rate
                st.write(f"Calculated Amount: {amount}")
                debit_credit = st.selectbox("Debit/Credit", ["Debit", "Credit"], 
                                          index=0 if current_data[6] == "Debit" else 1)
                buyer_name = st.selectbox("Buyer Name", buyers, index=buyers.index(current_data[8]))
                df_transactions = pd.read_sql("SELECT * FROM DailySheet WHERE BuyerName = ?", conn, params=(buyer_name,))
                if not df_transactions.empty:
                    df_transactions['SignedAmount'] = df_transactions.apply(
                        lambda row: row['Amount'] if row['DebitCredit'] == 'Credit' else -row['Amount'], axis=1)
                    current_debt = df_transactions['SignedAmount'].sum()
                else:
                    current_debt = 0.0
                if buyer_name == old_buyer:
                    temp_debt = current_debt - old_signed
                else:
                    temp_debt = current_debt
                signed_amount = amount if debit_credit == "Credit" else -amount
                new_debt = temp_debt + signed_amount
                st.write(f"Current Debt: {temp_debt}")
                st.write(f"New Debt: {new_debt}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        date_str = selected_date.strftime("%Y-%m-%d")
                        c.execute("""UPDATE DailySheet SET Date = ?, Name = ?, FlowerName = ?, Qty = ?, Rate = ?, 
                                     Amount = ?, DebitCredit = ?, Debt = ?, BuyerName = ? WHERE Id = ?""", 
                                  (date_str, name, flower_name, qty, rate, amount, debit_credit, new_debt, buyer_name, selected_id))
                        conn.commit()
                        recalculate_debts(conn, old_buyer)
                        if buyer_name != old_buyer:
                            recalculate_debts(conn, buyer_name)
                        st.success("Transaction updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM DailySheet WHERE Id = ?", (selected_id,))
                        conn.commit()
                        recalculate_debts(conn, old_buyer)
                        st.rerun()  # Refresh the page to reflect changes
    
    

elif choice == "Reports":
    st.header("Reports")
    report_types = ["Daily Sales", "Customer Balance", "Buyer Debts", "Flower Sales Summary"]
    report_choice = st.selectbox("Select Report", report_types)
    
    if report_choice == "Daily Sales":
        selected_date = st.date_input("Select Date", value=date.today())
        date_str = selected_date.strftime("%Y-%m-%d")
        df = pd.read_sql("SELECT * FROM DailySheet WHERE Date = ?", conn, params=(date_str,))
        if not df.empty:
            total_amount = df['Amount'].sum()
            st.write(f"Total Sales Amount for {date_str}: {total_amount}")
            st.dataframe(df)
        else:
            st.write("No transactions for this date.")
    
    elif report_choice == "Customer Balance":
        df = pd.read_sql("SELECT Date, Name, Sum(Amount) as CurrentDebt FROM DailySheet GROUP BY Date, Name", conn)
        if not df.empty:
            st.dataframe(df)
        else:
            st.write("No debt records.")

    elif report_choice == "Buyer Debts":
        df = pd.read_sql("""SELECT d.BuyerName, d.Debt as CurrentDebt 
                            FROM DailySheet d 
                            INNER JOIN (SELECT BuyerName, MAX(Id) as MaxId FROM DailySheet GROUP BY BuyerName) sub 
                            ON d.BuyerName = sub.BuyerName AND d.Id = sub.MaxId""", conn)
        if not df.empty:
            st.dataframe(df)
        else:
            st.write("No debt records.")
    
    elif report_choice == "Flower Sales Summary":
        selected_date = st.date_input("Select Date", value=date.today())
        date_str = selected_date.strftime("%Y-%m-%d")
        df = pd.read_sql("SELECT FlowerName, SUM(Qty) as TotalQty, SUM(Amount) as TotalAmount FROM DailySheet WHERE Date = ? GROUP BY FlowerName", conn, params=(date_str,))
        if not df.empty:
            st.dataframe(df)
        else:
            st.write("No sales for this date.")

# Close connection at the end
conn.close()