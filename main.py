import tkinter as tk
from datetime import datetime
from functools import partial
from tkinter import messagebox, ttk

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebaseKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


# Function to generate unique log ID based on current time and date:
def getLogID():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"log-{current_time}"


# Function to retrieve the username from their PSU IDs:
def getUsername(userID):
    flag = db.collection('all_users').document(userID)
    user_data = flag.get().to_dict()
    return user_data['name'] if user_data else ""


# Function to check whether the user exists in the database:
def checkUser(userID):
    flag = db.collection('all_users')
    query = flag.where("id", "==", userID).limit(1)
    result = query.stream()
    user_data = next(result, None)

    if user_data:
        user_data = user_data.to_dict()
        return True, user_data.get('accessibility', 'N/A')
    else:
        return False, 'N/A'


# Function to handle user swiping actions:
def swipe(swipeType, userID, selection_page):
    history_flag = db.collection('history_log')
    if swipeType == "in":
        log_id = getLogID()
        log_ref = history_flag.document(log_id)
        log_data = {"user_id": userID, "name": getUsername(userID), "time_in": datetime.now()}
        log_ref.set(log_data)
        messagebox.showinfo("Swipe Successful!", "Swipe In Successful!")
        main_page.destroy()
    else:
        query = history_flag.where("user_id", "==", userID).limit(1)
        result = query.stream()
        matching_records = list(result)
        if matching_records:
            log_record = matching_records[0].to_dict()
            if "time_out" not in log_record:
                log_id = matching_records[0].id
                log_ref = history_flag.document(log_id)
                log_data = {"time_out": datetime.now()}
                log_ref.set(log_data, merge=True)
                messagebox.showinfo("Swipe Successful!", "Swipe Out Successful!")
                main_page.destroy()
            else:
                messagebox.showerror("Error", "User has already swiped out.")
        else:
            messagebox.showerror("Error", "No matching swipe-in record found.")


# Function to handle accessibility status of each user:
def accessibility(event, table):
    selected = table.selection()
    if not selected:
        return
    rowVals = table.item(selected[0], "values")
    userID = rowVals[0]

    # Get the row and column clicked
    rowIDs = table.identify_row(event.y)
    colIDs = table.identify_column(event.x)

    # Check if the 'Accessibility' column was clicked
    if colIDs == "#4":
        # Retrieve the user ID from the clicked row
        rowVals = table.item(rowIDs, 'values')
        userID = rowVals[0]

        # Fetch the current accessibility status from Firebase
        flag = db.collection('all_users').document(userID)
        user_data = flag.get().to_dict()
        current_status = user_data['accessibility']

        # Toggle the accessibility status
        new_status = 'active' if current_status == 'suspended' else 'suspended'

        # Update Firebase
        flag.update({'accessibility': new_status})

        # Update the Treeview
        table.item(rowIDs, values=(rowVals[0], rowVals[1], rowVals[2], new_status))


# Function to populate user data:
def populatingAuthorizedUsers(table):
    table.delete(*table.get_children())
    all_users_ref = db.collection('all_users')
    all_users = all_users_ref.stream()

    for user in all_users:
        user_data = user.to_dict()
        table.insert('', 'end', values=(
        user_data['id'], user_data['name'], user_data['position'], user_data.get('accessibility', 'N/A')))

    # Bind the click event to toggle_accessibility
    table.bind('<ButtonRelease-1>', partial(accessibility, table=table))


# Function to validate PSU ID entry:
def validateID(event=None):
    userID = id_entry.get()
    if userID.isdigit() and len(userID) == 9:
        if userID == '123456789':
            adminPage()
        else:
            user_exists, accessibility_status = checkUser(userID)
            if user_exists:
                welcome_label.config(text=f"Welcome {userID}", bg="#87CEFA")
                id_entry.config(state="disabled", bg="#87CEFA")
                enter_button.config(state="disabled", bg="#87CEFA", fg="black")
                if accessibility_status == 'active':
                    selectionPage(userID)
                elif accessibility_status == 'suspended':
                    messagebox.showerror("Error", "User is suspended.")
                else:
                    messagebox.showerror("Error", "Invalid accessibility status.")
            else:
                messagebox.showerror("Error", "User not found in the database")
    else:
        messagebox.showerror("Error", "Please enter a valid 9-digit PSU ID")


# Function to create and display the admin page:
def adminPage():
    admin_page = tk.Toplevel(root)
    admin_page.title("Admin Page")
    setWindowStyle(admin_page)

    welcome_admin_label = tk.Label(admin_page, text="Welcome Admin!", font=("Helvetica", 30, "bold"), bg="#87CEFA",
                                   fg="#00205B")
    welcome_admin_label.pack(pady=20)

    edit_button = createButton(admin_page, "Edit Authorized Users", "#000080", "white", ("Helvetica", 14),
                               editUsersPage)
    view_button = createButton(admin_page, "View User History", "#FF5733", "white", ("Helvetica", 14), viewHistoryPage)
    cancel_button = createButton(admin_page, "Cancel", "white", "black", ("Helvetica", 14), root.quit)

    edit_button.pack(pady=10)
    view_button.pack(pady=10)
    cancel_button.pack(pady=10)


# Function to create and display the edit users page:
def editUsersPage():
    edit_page = tk.Toplevel(root)
    edit_page.title("Edit Users")
    setWindowStyle(edit_page)
    heading = tk.Label(edit_page, text="Edit Users", font=("Helvetica", 23, "bold"), bg="#87CEFA",
                       fg="#00145A")
    heading.pack(pady=20)
    table = ttk.Treeview(edit_page, columns=("PSU ID", "Name", "Position", "Accessibility"), show="headings")
    table.heading("PSU ID", text="PSU ID", anchor="center")
    table.heading("Name", text="Name", anchor="center")
    table.heading("Position", text="Position", anchor="center")
    table.heading("Accessibility", text="Accessibility", anchor="center")
    table.column("PSU ID", width=120, anchor="center")
    table.column("Name", width=120, anchor="center")
    table.column("Position", width=120, anchor="center")
    table.column("Accessibility", width=120, anchor="center")
    populatingAuthorizedUsers(table)
    table.pack(padx=10, pady=10, fill="both", expand=True)
    scrollbar = ttk.Scrollbar(edit_page, orient="vertical", command=table.yview)
    scrollbar.pack(side="right", fill="y")
    table.configure(yscrollcommand=scrollbar.set)

    back_button_edit_users = createButton(edit_page, "Back", "light gray", "#00145A", ("Helvetica", 14),
                                          edit_page.destroy)
    back_button_edit_users.pack(padx=10, pady=10, anchor="nw")


# Function for clearing the placeholder text:
def clearPlaceholder(event):
    if event.widget.get() == 'Search...':
        event.widget.delete(0, tk.END)


# Function for restoring the placeholder text:
def restorePlaceholder(event):
    if not event.widget.get():
        event.widget.insert(0, 'Search...')


# Function to format datetime:
def datetimeFormat(datetime_obj):
    return datetime_obj.strftime("%m-%d-%Y %I:%M:%S %p")


# Function to perform search on the user history:
def historySearch(user_history_table, master_search_entry):
    searchTerm = master_search_entry.get().lower()
    historyFlag = db.collection('history_log')
    userHistory = historyFlag.stream()

    # Clearing existing table data
    user_history_table.delete(*user_history_table.get_children())

    print("Search Term:", searchTerm)

    for log in userHistory:
        log_data = log.to_dict()

        print("Log Data:", log_data)

        formatted_time_in = datetimeFormat(log_data['time_in']) if log_data.get('time_in') else "N/A"
        formatted_time_out = datetimeFormat(log_data['time_out']) if log_data.get('time_out') else "N/A"

        print("Formatted Time In:", formatted_time_in)
        print("Formatted Time Out:", formatted_time_out)

        if searchTerm == "search..." or \
                searchTerm in log_data['user_id'].lower() or \
                searchTerm in log_data['name'].lower() or \
                searchTerm in formatted_time_in.lower() or \
                searchTerm in formatted_time_out.lower():
            user_history_table.insert('', 'end', values=(
            log_data['user_id'], log_data['name'], formatted_time_in, formatted_time_out))
            print("Inserted into table")


# Function creates and displays the user history:
def viewHistoryPage():
    history_page = tk.Toplevel(root)
    history_page.title("User History")
    setWindowStyle(history_page)

    heading = tk.Label(history_page, text="User History", font=("Helvetica", 23, "bold"), bg="#87CEFA", fg="#00205B")
    heading.pack(pady=20)

    search_frame = tk.Frame(history_page, bg="#87CEFA")
    search_frame.pack(pady=(10, 20))

    master_search_entry = tk.Entry(search_frame, font=("Helvetica", 12), bg="white")
    master_search_entry.grid(row=0, column=1, padx=10, pady=5)
    master_search_entry.insert(0, "Search...")
    master_search_entry.bind("<FocusIn>", clearPlaceholder)
    master_search_entry.bind("<FocusOut>", restorePlaceholder)

    master_search_button = createButton(search_frame, "Search", "#4CAF50", "black", ("Helvetica", 12),
                                        lambda: historySearch(history_table, master_search_entry))
    master_search_button.grid(row=1, columnspan=2, pady=(10, 0))

    history_table = ttk.Treeview(history_page, columns=("PSU ID", "Name", "Swipe-in Time", "Swipe-out Time"),
                                 show="headings")
    history_table.heading("PSU ID", text="PSU ID", anchor="center")
    history_table.heading("Name", text="Name", anchor="center")
    history_table.heading("Swipe-in Time", text="Swipe-in Time", anchor="center")
    history_table.heading("Swipe-out Time", text="Swipe-out Time", anchor="center")

    history_table.column("PSU ID", width=120, anchor="center")
    history_table.column("Name", width=120, anchor="center")
    history_table.column("Swipe-in Time", width=150, anchor="center")
    history_table.column("Swipe-out Time", width=150, anchor="center")

    historySearch(history_table, master_search_entry)

    history_table.pack(padx=10, pady=10, fill="both", expand=True)

    back_button_edit_users = createButton(history_page, "Back", "light gray", "#00145A", ("Helvetica", 14),
                                          history_page.destroy)
    back_button_edit_users.pack(padx=10, pady=10, anchor="nw")


# Function to create a button:
def createButton(parent, text, bg, fg, font, command):
    button = tk.Button(parent, text=text, bg=bg, fg=fg, font=font, command=command)
    return button


# Function to quit tkinter application
def escape(event):
    root.quit()


# Function to style and initialize Tkinter window:
def setWindowStyle(window):
    window.geometry("800x600")
    window.configure(bg="#87CEFA")


# Function to create and display the selection page:
def selectionPage(userID):
    selection_page = tk.Toplevel(root)
    selection_page.title("Selection Page")
    setWindowStyle(selection_page)

    username = getUsername(userID)

    welcome_label = tk.Label(selection_page, text=f"Welcome {username}!", font=("Helvetica", 35, "bold"),
                             bg="#87CEFA", fg="#003366")
    welcome_label.pack(pady=(20, 10))

    swipe_in_button = createButton(selection_page, "Swipe In", "#4CAF50", "#004d00", ("Helvetica", 20),
                                   lambda: swipe("in", userID, selection_page))
    swipe_out_button = createButton(selection_page, "Swipe Out", "#FF5733", "#800000", ("Helvetica", 20),
                                    lambda: swipe("out", userID, selection_page))

    swipe_in_button.pack(pady=10)
    swipe_out_button.pack(pady=10)


root = tk.Tk()
root.title("SUN Lab")
root.geometry("800x600")
root.configure(bg="#87CEFA")

root.bind('<Return>', validateID)
root.bind('<Escape>', escape)

welcome_label = tk.Label(root, text="Welcome to the SUN Lab", font=("Helvetica", 30, "bold"), bg="#87CEFA",
                         fg="#00205B")
welcome_label.pack(pady=(100, 20))

id_label = tk.Label(root, text="Please enter your 9-digit PSU ID:", font=("Helvetica", 18), bg="#87CEFA", fg="#00205B")
id_label.pack()

id_entry = tk.Entry(root, font=("Helvetica", 18), bg="#87CEFA", fg="black")
id_entry.pack(pady=10)

enter_button = tk.Button(root, text="Enter", bg="#4CAF50", fg="black", font=("Helvetica", 16))
enter_button.pack(pady=10)
enter_button.config(command=validateID)

main_page = root

root.protocol("WM_DELETE_WINDOW", lambda: root.quit())
root.mainloop()
