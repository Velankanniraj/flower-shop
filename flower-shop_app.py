import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Set page configuration for full-screen layout
st.set_page_config(layout="wide", page_title="Flower Shop Application", page_icon="🌸")

# Initialize the database
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
                 (Name TEXT PRIMARY KEY, Address TEXT, ContactNo TEXT, DisplayName TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS BuyerMaster
                 (Name TEXT PRIMARY KEY, Address TEXT, ContactNo TEXT, DisplayName TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS DailySheet
                 (Id INTEGER PRIMARY KEY AUTOINCREMENT, Date TEXT, Name TEXT, FlowerName TEXT, 
                  Qty REAL, Rate REAL, Amount REAL, DebitCredit TEXT, Debt REAL, BuyerName TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS DailyFlowerPrice
                 (FlowerName TEXT, Date TEXT, Price REAL, PRIMARY KEY (FlowerName, Date))''')
    
    conn.commit()
    return conn

# Helper functions
def get_flowers(conn):
    df = pd.read_sql("SELECT concat(DisplayName,'-',Name) as DisplayName FROM FlowerMaster", conn)
    return df['DisplayName'].tolist()

def get_customers(conn):
    df = pd.read_sql("SELECT Name FROM CustomerMaster", conn)
    return df['Name'].tolist()

def get_buyers(conn):
    df = pd.read_sql("SELECT Name FROM BuyerMaster", conn)
    return df['Name'].tolist()

def get_display_name(conn, table_name, name):
    c = conn.cursor()
    c.execute(f"SELECT DisplayName FROM {table_name} WHERE Name = ?", (name,))
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

# Translation helper function
def translate_to_tamil(name):
    try:
        from googletrans import Translator
        translator = Translator()
        tamil_trans = translator.translate(name, src='en', dest='ta').text
        suggested_words = tamil_trans.split()
        selected_words = st.multiselect("Select Tamil Words", suggested_words, default=suggested_words, key=f"word_select_{name}")
        return " ".join(selected_words) if selected_words else tamil_trans
    except ImportError:
        st.warning("Please install googletrans: `pip install googletrans==3.1.0a0`")
        return name

# Main app
st.title("Flower Shop Application (PoC)")

conn = init_db()

# Sidebar navigation
#sections = ["Flower Master", "Customer Master", "Buyer Master", "Daily Flower Price", "Daily Sheet", "Reports"]
#choice = st.sidebar.selectbox("Select Section", sections)

# Sidebar with combined navigation
with st.sidebar:
    st.title("Navigation")
    
    # Initialize choice if not set
    if 'choice' not in st.session_state:
        st.session_state['choice'] = "Flower Master"
    
    # Master Data group
    st.subheader("Master Data")
    if st.button("Flower Master"):
        st.session_state['choice'] = "Flower Master"
    if st.button("Customer Master"):
        st.session_state['choice'] = "Customer Master"
    if st.button("Buyer Master"):
        st.session_state['choice'] = "Buyer Master"
    
    # Other Sections group
    st.subheader("Other Sections")
    if st.button("Daily Flower Price"):
        st.session_state['choice'] = "Daily Flower Price"
    if st.button("Daily Sheet"):
        st.session_state['choice'] = "Daily Sheet"
    if st.button("Reports"):
        st.session_state['choice'] = "Reports"

choice = st.session_state['choice']
# Flower Master section
if choice == "Flower Master":
    st.header("Flower Master")
    
    # Translation input and search button at the top
    name_input = st.text_input("Name (English)", key="flower_name_input")
    if st.button("Search"):
        if name_input:
            st.session_state['flower_display_name'] = translate_to_tamil(name_input)
        else:
            st.warning("Please enter a name to search.")
    
    # Display the translated name for verification
    if 'flower_display_name' in st.session_state:
        st.write(f"Translated Display Name (Tamil): {st.session_state['flower_display_name']}")

    # Add form
    with st.form(key="add_flower_form"):
        name = st.text_input("Name (English)", value=name_input, key="add_flower_name")
        display_name_input = st.text_input("Display Name (Tamil)", value=st.session_state.get('flower_display_name', ''), key="add_flower_display_name")
        submit_add = st.form_submit_button("Add")
        if submit_add and name:
            if not display_name_input.strip():
                st.error("Display Name (Tamil) cannot be empty.")
            else:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO FlowerMaster (Name, DisplayName) VALUES (?, ?)", 
                              (name, display_name_input))
                    conn.commit()
                    st.success("Flower added successfully!")
                    name_input = ""  # Reset input after successful add
                    st.session_state.pop('flower_display_name', None)  # Clear translation
                except sqlite3.IntegrityError:
                    st.error("Flower name already exists!")
    
    # View
    df = pd.read_sql("SELECT * FROM FlowerMaster", conn)
    st.dataframe(df, key="flower_master_df")

    # Select record for edit/delete
    if not df.empty:
        selected_name = st.selectbox("Select Flower to Edit/Delete", df['Name'].tolist(), key="select_flower")
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT DisplayName FROM FlowerMaster WHERE Name = ?", (selected_name,))
            current_display = c.fetchone()[0]
            
            with st.form(key="edit_flower_form"):
                new_display_name = st.text_input("New Display Name (Tamil)", value=current_display, key="edit_flower_display_name")
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

elif choice == "Customer Master":
    st.header("Customer Master")
    
    # Translation input and search button at the top
    customer_name_input = st.text_input("Name (English)", key="customer_name_input")
    if st.button("Search"):
        if customer_name_input:
            st.session_state['customer_display_name'] = translate_to_tamil(customer_name_input)
        else:
            st.warning("Please enter a name to search.")
    
    # Display the translated name for verification
    if 'customer_display_name' in st.session_state:
        st.write(f"Translated Display Name (Tamil): {st.session_state['customer_display_name']}")
    # Add form with transliteration
    with st.form(key="add_customer_form"):
        name = st.text_input("Name (English)", value=customer_name_input, key="add_customer_name")
        #display_name = translate_to_tamil(name) if name else ""
        display_name_input = st.text_input("Display Name (Tamil)", value=st.session_state.get('customer_display_name',''), key="customer_display_name_input")
        address = st.text_input("Address", key="customer_address_input")
        contact_no = st.text_input("Contact No", key="customer_contact_input")
        submit_add = st.form_submit_button("Add")
        if submit_add and name:
            if not display_name_input.strip():
                st.error("Display Name (Tamil) cannot be empty.")
            else:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO CustomerMaster (Name, DisplayName, Address, ContactNo) VALUES (?, ?, ?, ?)", 
                              (name, display_name_input, address, contact_no))
                    conn.commit()
                    st.success("Customer added successfully!")
                    name = ""  # Reset after successful add
                    display_name_input = ""  # Reset display name
                    address = ""  # Reset address
                    contact_no = ""  # Reset contact
                except sqlite3.IntegrityError:
                    st.error("Customer name already exists!")
    
    # View
    df = pd.read_sql("SELECT * FROM CustomerMaster", conn)
    st.dataframe(df, key="customer_master_df")

    # Select record for edit/delete
    
    if not df.empty:
        selected_name = st.selectbox("Select Customer to Edit/Delete", df['Name'].tolist(), key="select_customer")
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT DisplayName, Address, ContactNo FROM CustomerMaster WHERE Name = ?", (selected_name,))
            current_data = c.fetchone()
            
            with st.form(key="edit_customer_form"):
                new_display_name = st.text_input("New Display Name (Tamil)", value=current_data[0], key="new_customer_display_name")
                new_address = st.text_input("New Address", value=current_data[1], key="new_customer_address")
                new_contact_no = st.text_input("New Contact No", value=current_data[2], key="new_customer_contact")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        if not new_display_name.strip():
                            st.error("New Display Name (Tamil) cannot be empty.")
                        else:
                            c.execute("UPDATE CustomerMaster SET DisplayName = ?, Address = ?, ContactNo = ? WHERE Name = ?", 
                                      (new_display_name, new_address, new_contact_no, selected_name))
                            conn.commit()
                            st.success("Customer updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM CustomerMaster WHERE Name = ?", (selected_name,))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes

elif choice == "Buyer Master":
    st.header("Buyer Master")
    
    # Translation input and search button at the top
    buyer_name_input = st.text_input("Name (English)", key="buyer_name_input")
    if st.button("Search"):
        if buyer_name_input:
            st.session_state['buyer_display_name'] = translate_to_tamil(buyer_name_input)
        else:
            st.warning("Please enter a name to search.")
    # Add form with transliteration
    with st.form(key="add_buyer_form"):
        name = st.text_input("Name (English)", value=buyer_name_input, key="add_buyer_name")
        #display_name = translate_to_tamil(name) if name else ""
        display_name_input = st.text_input("Display Name (Tamil)", value=st.session_state.get('buyer_display_name',''), key="buyer_display_name_input")
        address = st.text_input("Address", key="buyer_address_input")
        contact_no = st.text_input("Contact No", key="buyer_contact_input")
        submit_add = st.form_submit_button("Add")
        if submit_add and name:
            if not display_name_input.strip():
                st.error("Display Name (Tamil) cannot be empty.")
            else:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO BuyerMaster (Name, DisplayName, Address, ContactNo) VALUES (?, ?, ?, ?)", 
                              (name, display_name_input, address, contact_no))
                    conn.commit()
                    st.success("Buyer added successfully!")
                    name = ""  # Reset after successful add
                    display_name_input = ""  # Reset display name
                    address = ""  # Reset address
                    contact_no = ""  # Reset contact
                except sqlite3.IntegrityError:
                    st.error("Buyer name already exists!")
    
    # View
    df = pd.read_sql("SELECT * FROM BuyerMaster", conn)
    st.dataframe(df, key="buyer_master_df")

    # Select record for edit/delete
    
    if not df.empty:
        selected_name = st.selectbox("Select Buyer to Edit/Delete", df['Name'].tolist(), key="select_buyer")
        if selected_name:
            c = conn.cursor()
            c.execute("SELECT DisplayName, Address, ContactNo FROM BuyerMaster WHERE Name = ?", (selected_name,))
            current_data = c.fetchone()
            
            with st.form(key="edit_buyer_form"):
                new_display_name = st.text_input("New Display Name (Tamil)", value=current_data[0], key="new_buyer_display_name")
                new_address = st.text_input("New Address", value=current_data[1], key="new_buyer_address")
                new_contact_no = st.text_input("New Contact No", value=current_data[2], key="new_buyer_contact")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        if not new_display_name.strip():
                            st.error("New Display Name (Tamil) cannot be empty.")
                        else:
                            c.execute("UPDATE BuyerMaster SET DisplayName = ?, Address = ?, ContactNo = ? WHERE Name = ?", 
                                      (new_display_name, new_address, new_contact_no, selected_name))
                            conn.commit()
                            st.success("Buyer updated successfully!")
                with col2:
                    if st.form_submit_button("Delete"):
                        c.execute("DELETE FROM BuyerMaster WHERE Name = ?", (selected_name,))
                        conn.commit()
                        st.rerun()  # Refresh the page to reflect changes

elif choice == "Daily Flower Price":
    st.header("Daily Flower Price")
    flowers = get_flowers(conn)
    
    # Add form
    with st.form(key="set_price_form"):
        flower_name = st.selectbox("Flower Name", flowers, key="price_flower_name")
        selected_date = st.date_input("Date", value=date.today(), key="price_date")
        price = st.number_input("Price", min_value=0.0, key="price_input")
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
    
    
    # View
    df = pd.read_sql("SELECT * FROM DailyFlowerPrice ORDER BY Date DESC", conn)
    st.dataframe(df, key="daily_flower_price_df")

    # Select record for edit/delete
    
    if not df.empty:
        selected_key = st.selectbox("Select Price Entry to Edit/Delete", 
                                   [f"{row['FlowerName']} - {row['Date']}" for _, row in df.iterrows()], key="select_price")
        if selected_key:
            flower_name, date_str = selected_key.split(" - ")
            c = conn.cursor()
            c.execute("SELECT Price FROM DailyFlowerPrice WHERE FlowerName = ? AND Date = ?", (flower_name, date_str))
            current_price = c.fetchone()[0]
            
            with st.form(key="edit_price_form"):
                new_price = st.number_input("New Price", min_value=0.0, value=current_price, key="new_price")
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
    

elif choice == "Daily Sheet":
    st.header("Daily Sheet")
    customers = get_customers(conn)
    flowers = get_flowers(conn)
    buyers = get_buyers(conn)
    
    # Add form
    with st.form(key="add_transaction_form"):
        col1, col2 = st.columns(2)
        with col1: 
            selected_date = st.date_input("Date", value=date.today(), key="transaction_date")
            name = st.selectbox("Customer Name", [""] + customers, index=0, key="transaction_customer")
            flower_name = st.selectbox("Flower Name", [""] + flowers, index=0, key="transaction_flower")
            qty = st.number_input("Quantity (in KGs)", min_value=0.0, key="transaction_qty")
            date_str = selected_date.strftime("%Y-%m-%d")
            c = conn.cursor()
            c.execute("SELECT Price FROM DailyFlowerPrice WHERE FlowerName = ? AND Date = ?", (flower_name, date_str))
            result = c.fetchone()
            default_rate = result[0] if result else 0.0
            rate = st.number_input("Rate", min_value=0.0, value=default_rate, key="transaction_rate")
            amount = qty * rate
            st.write(f"Calculated Amount: {amount}")
        with col2:
            debit_credit = st.selectbox("Debit/Credit", ["Debit", "Credit"], key="transaction_debit_credit")
            buyer_name = st.selectbox("Buyer Name", [""] + buyers, index=0, key="transaction_buyer")
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
    st.dataframe(df, key="daily_sheet_df")

    if not df.empty:
        selected_id = st.selectbox("Select Transaction to Edit/Delete", df['Id'].tolist(), key="select_transaction")
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
            
            with st.form(key="edit_transaction_form"):
                selected_date = st.date_input("Date", value=date_obj, key="edit_transaction_date")
                name = st.selectbox("Customer Name", customers, index=customers.index(current_data[1]), key="edit_transaction_customer")
                flower_name = st.selectbox("Flower Name", flowers, index=flowers.index(current_data[2]), key="edit_transaction_flower")
                qty = st.number_input("Quantity (in KGs)", min_value=0.0, value=current_data[3], key="edit_transaction_qty")
                rate = st.number_input("Rate", min_value=0.0, value=current_data[4], key="edit_transaction_rate")
                amount = qty * rate
                st.write(f"Calculated Amount: {amount}")
                debit_credit = st.selectbox("Debit/Credit", ["Debit", "Credit"], 
                                          index=0 if current_data[6] == "Debit" else 1, key="edit_transaction_debit_credit")
                buyer_name = st.selectbox("Buyer Name", buyers, index=buyers.index(current_data[8]), key="edit_transaction_buyer")
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
    report_choice = st.selectbox("Select Report", report_types, key="report_select")
    
    if report_choice == "Daily Sales":
        selected_date = st.date_input("Select Date", value=date.today(), key="report_date")
        date_str = selected_date.strftime("%Y-%m-%d")
        df = pd.read_sql("SELECT * FROM DailySheet WHERE Date = ?", conn, params=(date_str,))
        if not df.empty:
            total_amount = df['Amount'].sum()
            st.write(f"Total Sales Amount for {date_str}: {total_amount}")
            st.dataframe(df, key="daily_sales_df")
        else:
            st.write("No transactions for this date.")
    
    elif report_choice == "Customer Balance":
        df = pd.read_sql("SELECT Date, Name, Sum(Amount) as CurrentDebt FROM DailySheet GROUP BY Date, Name", conn)
        if not df.empty:
            st.dataframe(df, key="customer_balance_df")
        else:
            st.write("No debt records.")

    elif report_choice == "Buyer Debts":
        df = pd.read_sql("""SELECT d.BuyerName, d.Debt as CurrentDebt 
                            FROM DailySheet d 
                            INNER JOIN (SELECT BuyerName, MAX(Id) as MaxId FROM DailySheet GROUP BY BuyerName) sub 
                            ON d.BuyerName = sub.BuyerName AND d.Id = sub.MaxId""", conn)
        if not df.empty:
            st.dataframe(df, key="buyer_debts_df")
        else:
            st.write("No debt records.")
    
    elif report_choice == "Flower Sales Summary":
        selected_date = st.date_input("Select Date", value=date.today(), key="flower_sales_date")
        date_str = selected_date.strftime("%Y-%m-%d")
        df = pd.read_sql("SELECT FlowerName, SUM(Qty) as TotalQty, SUM(Amount) as TotalAmount FROM DailySheet WHERE Date = ? GROUP BY FlowerName", conn, params=(date_str,))
        if not df.empty:
            st.dataframe(df, key="flower_sales_summary_df")
        else:
            st.write("No sales for this date.")

# Close connection at the end
conn.close()