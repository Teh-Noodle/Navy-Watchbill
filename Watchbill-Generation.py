import random
import tkinter as tk
from tkinter import ttk  # Import ttk for Treeview
from tkinter import messagebox
from tkcalendar import DateEntry  # Import DateEntry for calendar widget
import sqlite3
import re
from datetime import datetime
qualification_listbox = None  # Initialize to None


# --- Database Setup ---
conn = sqlite3.connect('watchbill.db')  # Your database file
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sailors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank TEXT,
        last_name TEXT,
        qualifications TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS qualifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS watchstations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        display_order INTEGER
    )
''')

# --- Attempt to add display_order column only if it doesn't exist ---
try:
    cursor.execute("ALTER TABLE qualifications ADD COLUMN display_order INTEGER;")
    conn.commit()
    print("display_order column added to qualifications successfully!")
    # If adding the column succeeded, update existing data:
    cursor.execute("UPDATE qualifications SET display_order = id WHERE display_order IS NULL;")  # Initial order based on id
    conn.commit()

except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("display_order column already exists in qualifications.")
        # Now update any existing rows that might not have a display_order yet:
        cursor.execute("UPDATE watchstations SET display_order = (SELECT COUNT(*) FROM watchstations WHERE id <= watchstations.id) WHERE display_order IS NULL;")
        conn.commit()
        print("Existing watchstations updated with display_order values (if necessary).")


    else:
        print(f"Error adding display_order to qualifications table: {e}")



# Create the watch times table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS watch_times (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        end_time TEXT,
        UNIQUE(start_time, end_time)  -- Prevent duplicate entries
    )
''')

# Create the leaves table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sailor_id INTEGER,
        start_date DATE,
        end_date DATE,
        type TEXT,
        notes TEXT,
        FOREIGN KEY (sailor_id) REFERENCES sailors (id)
    )
''')

conn.commit()  # Commit after creating tables

conn.commit()  # Commit after creating tables

# --- Data Access Functions ---
def add_sailor(rank, last_name):
    cursor.execute("INSERT INTO sailors (rank, last_name, qualifications) VALUES (?, ?, ?)", (rank, last_name, ""))
    conn.commit()

def remove_sailor(last_name):
    cursor.execute("DELETE FROM sailors WHERE last_name=?", (last_name,))
    conn.commit()

def edit_sailor(old_last_name, new_rank, new_last_name):
    cursor.execute("UPDATE sailors SET rank=?, last_name=? WHERE last_name=?", (new_rank, new_last_name, old_last_name))
    conn.commit()

def get_sailors():
    cursor.execute("SELECT rank, last_name, qualifications FROM sailors")
    return cursor.fetchall()

def add_qualification(qualification):
    try:
        cursor.execute("INSERT INTO qualifications (name) VALUES (?)", (qualification,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_qualification(qualification):
    cursor.execute("DELETE FROM qualifications WHERE name=?", (qualification,))
    conn.commit()

def rename_qualification(old_name, new_name):
    try:
        cursor.execute("UPDATE qualifications SET name=? WHERE name=?", (new_name, old_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_qualifications():
    cursor.execute("SELECT name FROM qualifications ORDER BY display_order") # Add ORDER BY
    return [row[0] for row in cursor.fetchall()]

def get_sailor_qualifications(last_name):
    cursor.execute("SELECT qualifications FROM sailors WHERE last_name=?", (last_name,))
    result = cursor.fetchone()
    if result:
        return result[0].split(",") if result[0] else []
    else:
        return []

def update_sailor_qualifications(last_name, qualifications):
    cursor.execute("UPDATE sailors SET qualifications=? WHERE last_name=?", (",".join(qualifications), last_name))
    conn.commit()

def get_sailor_id(last_name):
    cursor.execute("SELECT id FROM sailors WHERE last_name=?", (last_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def add_leave(sailor_id, start_date, end_date, leave_type, notes):
    start_date_str = start_date.strftime('%Y-%m-%d')  # Format the date
    end_date_str = end_date.strftime('%Y-%m-%d')  # Format the date
    cursor.execute("INSERT INTO leaves (sailor_id, start_date, end_date, type, notes) VALUES (?, ?, ?, ?, ?)",
                   (sailor_id, start_date_str, end_date_str, leave_type, notes))
    conn.commit()


def remove_leave(leave_id):
    cursor.execute("DELETE FROM leaves WHERE id=?", (leave_id,))
    conn.commit()

def get_leaves():
    cursor.execute("SELECT l.id, s.last_name, l.start_date, l.end_date, l.type, l.notes, s.rank "
                   "FROM leaves l "
                   "JOIN sailors s ON l.sailor_id = s.id")
    return cursor.fetchall()  # Added rank to the query

def edit_leave(leave_id, new_start_date, new_end_date, new_leave_type, new_notes):
    new_start_date_str = new_start_date.strftime('%Y-%m-%d') # Format the date
    new_end_date_str = new_end_date.strftime('%Y-%m-%d')     # Format the date

    cursor.execute("UPDATE leaves SET start_date=?, end_date=?, type=?, notes=? WHERE id=?",
                   (new_start_date_str, new_end_date_str, new_leave_type, new_notes, leave_id))
    conn.commit()

def update_qualification_order_in_db():
    qualifications = qualification_listbox.get(0, tk.END)
    for index, qual_name in enumerate(qualifications):
        cursor.execute("UPDATE qualifications SET display_order = ? WHERE name = ?", (index, qual_name))
    conn.commit()

# --- GUI Functions ---

def manage_sailors():
    """Opens a new window to manage sailor information."""

    def add_sailor_to_db():
        """Adds a new sailor to the database."""
        rank = rank_entry.get()
        last_name = last_name_entry.get()
        if rank and last_name:
            add_sailor(rank, last_name)
            update_sailor_list()
            clear_entries()
        else:
            messagebox.showwarning("Missing Information", "Please enter both rank and last name.")

    def on_enter_pressed(event): # New function to handle Enter key
        add_sailor_to_db()

    def remove_sailor_from_db():
        """Removes the selected sailor from the database."""
        try:
            selection = sailor_listbox.curselection()[0]
            last_name = sailor_listbox.get(selection).split()[1]  # Get last name from listbox
            remove_sailor(last_name)
            update_sailor_list()
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a sailor to remove.")

    def edit_sailor_in_db():
        """Edits the details of the selected sailor in the database."""
        try:
            selection = sailor_listbox.curselection()[0]
            old_last_name = sailor_listbox.get(selection).split()[1]  # Get old last name

            def save_changes_to_db():
                """Saves the edited sailor details to the database."""
                new_rank = edit_rank_entry.get()
                new_last_name = edit_last_name_entry.get()
                edit_sailor(old_last_name, new_rank, new_last_name)
                update_sailor_list()
                edit_window.destroy()

            edit_window = tk.Toplevel(sailor_window)
            edit_window.title("Edit Sailor")

            tk.Label(edit_window, text="Rank:").grid(row=0, column=0)
            edit_rank_entry = tk.Entry(edit_window)
            edit_rank_entry.grid(row=0, column=1)

            tk.Label(edit_window, text="Last Name:").grid(row=1, column=0)
            edit_last_name_entry = tk.Entry(edit_window)
            edit_last_name_entry.grid(row=1, column=1)

            save_button = tk.Button(edit_window, text="Save Changes", command=save_changes_to_db)
            save_button.grid(row=2, column=0, columnspan=2, pady=10)

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a sailor to edit.")

    def clear_entries():
        """Clears the entry fields."""
        rank_entry.delete(0, tk.END)
        last_name_entry.delete(0, tk.END)

    def update_sailor_list():
        """Updates the listbox with the current sailor data from the database."""
        sailor_listbox.delete(0, tk.END)
        for rank, last_name, _ in get_sailors():  # Use get_sailors() to fetch data
            sailor_listbox.insert(tk.END, f"{rank} {last_name}")

    sailor_window = tk.Toplevel(root)
    sailor_window.title("Manage Sailors")

    # --- Create labels and entry fields for sailor details ---
    tk.Label(sailor_window, text="Rank:").grid(row=0, column=0)
    rank_entry = tk.Entry(sailor_window)
    rank_entry.grid(row=0, column=1)

    tk.Label(sailor_window, text="Last Name:").grid(row=1, column=0)
    last_name_entry = tk.Entry(sailor_window)
    last_name_entry.grid(row=1, column=1)

    # --- Create a listbox to display sailors ---
    sailor_listbox = tk.Listbox(sailor_window)
    sailor_listbox.grid(row=2, column=0, columnspan=2, pady=10)
    update_sailor_list()  # Initialize the listbox

    # --- Create buttons for actions ---
    add_button = tk.Button(sailor_window, text="Add Sailor", command=add_sailor_to_db)
    add_button.grid(row=3, column=0, pady=10)

    remove_button = tk.Button(sailor_window, text="Remove Sailor", command=remove_sailor_from_db)
    remove_button.grid(row=3, column=1, pady=10)

    edit_button = tk.Button(sailor_window, text="Edit Sailor", command=edit_sailor_in_db)
    edit_button.grid(row=4, column=0, columnspan=2, pady=10)

    last_name_entry.bind("<Return>", on_enter_pressed) # Bind Enter key to last_name_entry


def manage_qualifications():
    """Opens a new window to manage qualifications."""
    global qualification_listbox  # Declare you're using the global

    def move_qualification_up(listbox):
        try:
            selection = qualification_listbox.curselection()[0]
            if selection > 0:
                item = qualification_listbox.get(selection)  # Get selected item
                qualification_listbox.delete(selection)  # Delete selected item
                qualification_listbox.insert(selection - 1, item)  # Insert at new position
                update_qualification_order_in_db()
                qualification_listbox.selection_set(selection - 1)
                qualification_listbox.activate(selection - 1)
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a qualification to move.")


    def move_qualification_down(listbox):
        try:
            selection = qualification_listbox.curselection()[0]
            last_index = qualification_listbox.size() - 1
            if selection < last_index:
                item = qualification_listbox.get(selection) # Get selected item
                qualification_listbox.delete(selection)  # Delete selected item
                qualification_listbox.insert(selection + 1, item) # Insert item at new position below
                update_qualification_order_in_db()
                qualification_listbox.selection_set(selection + 1)
                qualification_listbox.activate(selection + 1)
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a qualification to move.")

    def update_qualification_order_in_db():
        """Updates the order of qualifications in the database to match the listbox."""
        qualifications = qualification_listbox.get(0, tk.END)
        for index, qual_name in enumerate(qualifications):
            cursor.execute("UPDATE qualifications SET display_order = ? WHERE name = ?", (index, qual_name))
        conn.commit()

    def add_qualification_to_db():
        """Adds a new qualification to the database."""
        qualification = qualification_entry.get()
        if not qualification:
            messagebox.showwarning("Missing Information", "Please enter a qualification.")
        elif not add_qualification(qualification):  # Use the database function
            messagebox.showwarning("Duplicate Entry", "This qualification already exists.")
        else:
            update_qualification_list()
            qualification_entry.delete(0, tk.END)

    def remove_qualification_from_db():
        """Removes the selected qualification from the database."""
        try:
            selection = qualification_listbox.curselection()[0]
            qualification = qualification_listbox.get(selection)
            remove_qualification(qualification)  # Use the database function
            update_qualification_list()
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a qualification to remove.")

    def rename_qualification_in_db():
        """Renames the selected qualification in the database."""
        try:
            selection = qualification_listbox.curselection()[0]
            old_name = qualification_listbox.get(selection)

            def save_rename_to_db():
                """Saves the renamed qualification to the database."""
                new_name = rename_entry.get()
                if not new_name:
                    messagebox.showwarning("Missing Information", "Please enter a new name.")
                elif not rename_qualification(old_name, new_name):  # Use the database function
                    messagebox.showwarning("Duplicate Entry", "This qualification already exists.")
                else:
                    update_qualification_list()
                    rename_window.destroy()

            rename_window = tk.Toplevel(qualification_window)
            rename_window.title("Rename Qualification")

            tk.Label(rename_window, text="New Name:").grid(row=0, column=0)
            rename_entry = tk.Entry(rename_window)
            rename_entry.grid(row=0, column=1)

            save_button = tk.Button(rename_window, text="Save", command=save_rename_to_db)
            save_button.grid(row=1, column=0, columnspan=2, pady=10)

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a qualification to rename.")

    def update_qualification_list():
        """Updates the listbox with the current qualifications from the database."""
        qualification_listbox.delete(0, tk.END)
        for qualification in get_qualifications():  # Use get_qualifications() to fetch data
            qualification_listbox.insert(tk.END, qualification)

    qualification_window = tk.Toplevel(root)
    qualification_window.title("Manage Qualifications")

    # --- Create entry field for qualification ---
    tk.Label(qualification_window, text="Qualification:").grid(row=0, column=0)
    qualification_entry = tk.Entry(qualification_window)
    qualification_entry.grid(row=0, column=1)

    # --- Create a listbox to display qualifications ---
    qualification_listbox = tk.Listbox(qualification_window)
    qualification_listbox.grid(row=1, column=0, columnspan=2, pady=10)
    update_qualification_list()  # Initialize the listbox

    # --- Create buttons for actions ---
    add_button = tk.Button(qualification_window, text="Add", command=add_qualification_to_db)
    add_button.grid(row=2, column=0, pady=10)

    remove_button = tk.Button(qualification_window, text="Remove", command=remove_qualification_from_db)
    remove_button.grid(row=2, column=1, pady=10)

    rename_button = tk.Button(qualification_window, text="Rename", command=rename_qualification_in_db)
    rename_button.grid(row=3, column=0, columnspan=2, pady=10)

    move_up_button = tk.Button(qualification_window, text="Move Up", command=lambda: move_qualification_up(qualification_listbox)) #Pass listbox
    move_up_button.grid(row=4, column=0, pady=5)  # Adjust grid position as needed

    move_down_button = tk.Button(qualification_window, text="Move Down", command=lambda: move_qualification_down(qualification_listbox)) #Pass listbox
    move_down_button.grid(row=4, column=1, pady=5)  # Adjust grid position as needed



def assign_qualifications():
    """Opens a new window to assign qualifications to sailors."""

    def update_qualification_checkboxes():
        """Updates the checkboxes based on available qualifications from the database, in display order."""
        for checkbox, var in checkboxes.items():  # Clear existing checkboxes
            checkbox.destroy()
        checkboxes.clear()

        # Get qualifications ordered by display_order (or id if no display_order is used)
        try:
            cursor.execute("SELECT name FROM qualifications ORDER BY display_order")  # Try display_order first
            ordered_qualifications = cursor.fetchall()
        except sqlite3.OperationalError as e: # If display_order column doesn't exist yet, fall back to id
            if "no such column: display_order" in str(e):
                cursor.execute("SELECT name FROM qualifications ORDER BY id")
                ordered_qualifications = cursor.fetchall()
            else:
                print("Database query error", e)  # handle other db error here, probably crash/messagebox
                return  # stop executing the function due to the error

        for qual_name in ordered_qualifications:
            qual = qual_name[0] # Extract the string from the fetched tuple
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(qualifications_frame, text=qual, variable=var)
            checkbox.pack(anchor="w")
            checkboxes[qual] = var

    def on_sailor_select(event):
        """Loads the qualifications of the selected sailor when the selection changes."""
        try:
            selection = sailor_listbox.curselection()[0]
            last_name = sailor_listbox.get(selection).split()[1]
            sailor_qualifications = get_sailor_qualifications(last_name)
            
            # Update checkboxes
            for qual, var in checkboxes.items():
                if qual in sailor_qualifications:
                    var.set(True)
                else:
                    var.set(False)
        except IndexError:
            pass  # Ignore if no sailor is selected

    def save_qualifications_to_db():
        """Saves the selected qualifications to the sailor in the database."""
        try:
            selection = sailor_listbox.curselection()[0]
            last_name = sailor_listbox.get(selection).split()[1]
            selected_qualifications = [qual for qual, var in checkboxes.items() if var.get()]
            update_sailor_qualifications(last_name, selected_qualifications)
            
            # Update the status_label and schedule timeout
            status_label.config(text="Qualifications saved")
            assign_window.after(2000, lambda: status_label.config(text=""))  # 2 seconds
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a sailor.")

    assign_window = tk.Toplevel(root)
    assign_window.title("Assign Qualifications")

    # --- Sailor Listbox ---
    sailor_listbox = tk.Listbox(assign_window, width=30)
    sailor_listbox.pack(side="left", fill="y", padx=10, pady=10)
    
    # Bind the on_sailor_select function to the ListboxSelect event
    sailor_listbox.bind("<<ListboxSelect>>", on_sailor_select)

    # --- Update listbox with sailor names from the database ---
    for rank, last_name, _ in get_sailors():
        sailor_listbox.insert(tk.END, f"{rank} {last_name}")

    # --- Qualifications Frame ---
    qualifications_frame = tk.Frame(assign_window)
    qualifications_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    checkboxes = {}
    update_qualification_checkboxes()

    # --- Status Label ---
    status_label = tk.Label(assign_window, text="")
    status_label.pack(pady=5)

    # --- Save Button ---
    save_button = tk.Button(assign_window, text="Save Qualifications", command=save_qualifications_to_db)
    save_button.pack(pady=5)


def manage_watchstations():
    """Opens a new window to manage watch stations."""

    def add_watchstation():
        """Adds a new watch station to the database."""
        station_name = station_entry.get()
        if not station_name:
            messagebox.showwarning("Missing Information", "Please enter a watch station name.")
            return  # Exit early if no name is entered

        try:
            # Get the next display order
            cursor.execute("SELECT MAX(display_order) FROM watchstations")
            max_order = cursor.fetchone()[0]
            new_order = max_order + 1 if max_order is not None else 0 # Handle empty table

            cursor.execute("INSERT INTO watchstations (name, display_order) VALUES (?, ?)", (station_name, new_order))
            conn.commit()
            update_watchstation_list()  # Update the Listbox after adding
            station_entry.delete(0, tk.END)  # Clear the entry field
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate Entry", "This watch station already exists.")

    def remove_watchstation():
        """Removes the selected watch station from the database."""
        try:
            selection = watchstation_listbox.curselection()[0]
            station_name = watchstation_listbox.get(selection)
            cursor.execute("DELETE FROM watchstations WHERE name=?", (station_name,))
            conn.commit()
            update_watchstation_list()  # Update Listbox after removing
            update_display_order()  # Fix display order after removal

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch station to remove.")

    def rename_watchstation():
        """Renames the selected watch station."""
        try:
            selection = watchstation_listbox.curselection()[0]
            old_name = watchstation_listbox.get(selection)

            def save_rename():
                """Saves the renamed watch station to the database."""
                new_name = rename_entry.get()
                if not new_name:
                    messagebox.showwarning("Missing Information", "Please enter a new name.")
                    return

                try:
                    cursor.execute("UPDATE watchstations SET name=? WHERE name=?", (new_name, old_name))
                    conn.commit()
                    update_watchstation_list()  # Update the Listbox after renaming
                    rename_window.destroy()
                except sqlite3.IntegrityError:
                    messagebox.showwarning("Duplicate Entry", "This watch station already exists.")

            rename_window = tk.Toplevel(watchstation_window)  # watchstation_window as parent
            rename_window.title("Rename Watch Station")

            tk.Label(rename_window, text="New Name:").grid(row=0, column=0)
            rename_entry = tk.Entry(rename_window)
            rename_entry.grid(row=0, column=1)

            save_button = tk.Button(rename_window, text="Save", command=save_rename)
            save_button.grid(row=1, column=0, columnspan=2, pady=10)

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch station to rename.")

    def move_watchstation_up():
        try:
            selection = watchstation_listbox.curselection()[0]
            if selection > 0:  # Check if it's not the first item
                watchstation_listbox.insert(selection - 1, watchstation_listbox.get(selection))
                watchstation_listbox.delete(selection + 1)  # delete the original item
                update_display_order()
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch station to move.")

    def move_watchstation_down():
        try:
            selection = watchstation_listbox.curselection()[0]
            last_index = watchstation_listbox.size() - 1
            if selection < last_index:  # Check if it's not the last item
                watchstation_listbox.insert(selection + 2, watchstation_listbox.get(selection)) # Insert after the next item
                watchstation_listbox.delete(selection) # Delete the original item
                update_display_order()

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch station to move.")



    def update_display_order():
        """Updates the display_order in the database to match the listbox order."""
        order = list(watchstation_listbox.get(0, tk.END))
        for index, station_name in enumerate(order):
            cursor.execute("UPDATE watchstations SET display_order = ? WHERE name = ?", (index, station_name))
        conn.commit()


    def update_watchstation_list():
        watchstation_listbox.delete(0, tk.END)
        cursor.execute("SELECT name FROM watchstations ORDER BY display_order")
        for row in cursor.fetchall():
            watchstation_listbox.insert(tk.END, row[0])

    # Create the watch station management window
    watchstation_window = tk.Toplevel(root)
    watchstation_window.title("Manage Watch Stations")

    # --- Entry field for new watch station name ---
    tk.Label(watchstation_window, text="Watch Station:").grid(row=0, column=0)
    station_entry = tk.Entry(watchstation_window)
    station_entry.grid(row=0, column=1)

    # --- Listbox ---
    watchstation_listbox = tk.Listbox(watchstation_window)
    watchstation_listbox.grid(row=1, column=0, columnspan=2, pady=10)
    update_watchstation_list()  # Initialize listbox with data from the database

    # --- Buttons ---
    add_button = tk.Button(watchstation_window, text="Add", command=add_watchstation)
    add_button.grid(row=2, column=0, pady=10)

    remove_button = tk.Button(watchstation_window, text="Remove", command=remove_watchstation)
    remove_button.grid(row=2, column=1, pady=10)
    

    move_up_button = tk.Button(watchstation_window, text="Move Up", command=move_watchstation_up)
    move_up_button.grid(row=4, column=0, pady=5)

    move_down_button = tk.Button(watchstation_window, text="Move Down", command=move_watchstation_down)
    move_down_button.grid(row=4, column=1, pady=5)

    rename_button = tk.Button(watchstation_window, text="Rename", command=rename_watchstation)
    rename_button.grid(row=5, column=0, columnspan=2, pady=5)


def manage_watch_times():
    """Opens a new window to manage watch times."""

    def add_watch_time():
        start_time = start_time_entry.get()
        end_time = end_time_entry.get()

        if not start_time or not end_time:
            messagebox.showwarning("Missing Information", "Please enter both start and end times.")
            return

        try:
            cursor.execute("INSERT INTO watch_times (start_time, end_time) VALUES (?, ?)", (start_time, end_time))
            conn.commit()
            update_watch_time_list()
            start_time_entry.delete(0, tk.END)
            end_time_entry.delete(0, tk.END)

        except sqlite3.IntegrityError:  # Handle potential duplicate entry errors
            messagebox.showwarning("Error", "A watch time with these start and/or end times already exists.")



    def remove_watch_time():
        try:
            selection = watch_times_listbox.curselection()[0]
            watch_time_string = watch_times_listbox.get(selection)
            watch_time_id = int(watch_time_string.split(" - ")[0]) # Extract ID correctly

            cursor.execute("DELETE FROM watch_times WHERE id=?", (watch_time_id,))
            conn.commit()
            update_watch_time_list()

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch time to remove.")


    def rename_watch_time():
        try:
            selection = watch_times_listbox.curselection()[0]
            watch_time_id = watch_times_listbox.get(selection)[0]

            def save_rename():
                new_start = rename_start_entry.get()
                new_end = rename_end_entry.get()
                if not new_start or not new_end:
                    messagebox.showwarning("Missing Information", "Enter both start and end times.")
                    return
                try:
                    cursor.execute("UPDATE watch_times SET start_time=?, end_time=? WHERE id=?", (new_start, new_end, watch_time_id))
                    conn.commit()
                    update_watch_time_list()
                    rename_window.destroy()

                except sqlite3.IntegrityError:
                    messagebox.showwarning("Error", "A watch time with these times already exists.")

            rename_window = tk.Toplevel(watch_times_window)
            rename_window.title("Rename Watch Time")

            tk.Label(rename_window, text="New Start Time:").grid(row=0, column=0)
            rename_start_entry = tk.Entry(rename_window)
            rename_start_entry.grid(row=0, column=1)

            tk.Label(rename_window, text="New End Time:").grid(row=1, column=0)
            rename_end_entry = tk.Entry(rename_window)
            rename_end_entry.grid(row=1, column=1)

            save_button = tk.Button(rename_window, text="Save", command=save_rename)
            save_button.grid(row=2, column=0, columnspan=2, pady=10)

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a watch time to rename.")



    def update_watch_time_list():
        watch_times_listbox.delete(0, tk.END)
        cursor.execute("SELECT id, start_time, end_time FROM watch_times")
        for _id, start, end in cursor.fetchall():
            watch_times_listbox.insert(tk.END, f"{_id} - {start} - {end}")



    # --- Create watch times table if it doesn't exist ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watch_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            UNIQUE(start_time, end_time)  -- Prevent duplicate entries
        )
    ''')
    conn.commit()

    # --- Watch Times Window Setup ---
    watch_times_window = tk.Toplevel(root)
    watch_times_window.title("Manage Watch Times")


    tk.Label(watch_times_window, text="Start Time:").grid(row=0, column=0)
    start_time_entry = tk.Entry(watch_times_window)
    start_time_entry.grid(row=0, column=1)

    tk.Label(watch_times_window, text="End Time:").grid(row=1, column=0)
    end_time_entry = tk.Entry(watch_times_window)
    end_time_entry.grid(row=1, column=1)

    add_button = tk.Button(watch_times_window, text="Add", command=add_watch_time)
    add_button.grid(row=2, column=0, columnspan=2, pady=(10, 0)) # Add pady


    watch_times_listbox = tk.Listbox(watch_times_window, width=40)  # Adjust width as needed
    watch_times_listbox.grid(row=3, column=0, columnspan=2, pady=10)

    update_watch_time_list()

    remove_button = tk.Button(watch_times_window, text="Remove", command=remove_watch_time)
    remove_button.grid(row=4, column=0, pady=10)

    rename_button = tk.Button(watch_times_window, text="Rename", command=rename_watch_time)
    rename_button.grid(row=4, column=1, pady=10)

import random
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime

# ... (your existing database setup and other functions) ...

def generate_watchbill():
    """Generates and displays the watchbill."""

    try:
        def create_watchbill(selected_date):
            """Generates the watchbill data for the selected date."""
            try:
                cursor.execute("SELECT name FROM watchstations ORDER BY display_order")
                watchstations = [row[0] for row in cursor.fetchall()]

                cursor.execute("SELECT start_time, end_time FROM watch_times")
                watchtimes = cursor.fetchall()

                if not watchstations or not watchtimes:
                    messagebox.showwarning("Missing Data", "Add watch stations and times.")
                    return

                cursor.execute("SELECT s.last_name, l.start_date, l.end_date FROM leaves l JOIN sailors s ON l.sailor_id = s.id")
                leaves = cursor.fetchall()

                sailors_on_leave = []
                for last_name, start_date, end_date in leaves:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    if start_date <= selected_date <= end_date:
                        sailors_on_leave.append(last_name)

                cursor.execute(
                    "SELECT last_name, qualifications FROM sailors WHERE last_name NOT IN ({})".
                    format(','.join(['?'] * len(sailors_on_leave))), sailors_on_leave)
                sailors = cursor.fetchall()

                sailor_data = {}
                for rank, last_name, _ in get_sailors():
                    sailor_data[last_name] = f"{rank} {last_name}"

                watchbill_data = {}
                assigned_ood = set()

                for station in watchstations:
                    watchbill_data[station] = {}
                    if station not in ("OOD", "Internal Rover"):  # Prioritize same sailor for other stations
                        qualified_sailors = []
                        for last_name, qualifications in sailors:
                            if qualifications:
                                sailor_quals = qualifications.split(',')
                                if any(station == qual or (station.startswith(qual) and station[len(qual):].isdigit()) for qual in sailor_quals):
                                    if last_name not in assigned_ood:
                                        qualified_sailors.append(last_name)

                        if qualified_sailors:
                            chosen_sailor = random.choice(qualified_sailors)
                            for start, end in watchtimes:
                                watchbill_data[station][f"{start} - {end}"] = sailor_data.get(chosen_sailor, "CLICK TO ASSIGN")
                        else:
                            for start, end in watchtimes:
                                watchbill_data[station][f"{start} - {end}"] = "CLICK TO ASSIGN"
                    else:
                        for start, end in watchtimes:
                            qualified_sailors = []  # Find qualified sailors *inside* the loop
                            for last_name, qualifications in sailors:
                                if qualifications:
                                    sailor_quals = qualifications.split(',')
                                    if any(station == qual or (station.startswith(qual) and station[len(qual):].isdigit()) for qual in sailor_quals):
                                        if station == "OOD":
                                            if last_name not in assigned_ood:
                                                qualified_sailors.append(last_name)
                                        # Add this condition for Internal Rover:
                                        elif station == "Internal Rover": 
                                            qualified_sailors.append(last_name)  # No OOD check needed
                                        elif last_name not in assigned_ood:
                                            qualified_sailors.append(last_name)


                            if qualified_sailors:
                                chosen_sailor = random.choice(qualified_sailors)
                                watchbill_data[station][f"{start} - {end}"] = sailor_data.get(chosen_sailor, "CLICK TO ASSIGN")
                                if station == "OOD":
                                    assigned_ood.add(chosen_sailor)  # Add only for OOD
                            else:
                                watchbill_data[station][f"{start} - {end}"] = "CLICK TO ASSIGN"  # Handle the case with no qualified sailors

                # Display Watchbill (in Treeview)
                display_watchbill(selected_date, watchbill_data, watchstations, watchtimes)  # Call new function

            except Exception as e:
                messagebox.showerror("Error", f"Watchbill generation error: {e}")

        def display_watchbill(selected_date, watchbill_data, watchstations, watchtimes):
            """Displays the watchbill data in a Treeview.""" # New function to handle display logic
            watchbill_window = tk.Toplevel(root)
            watchbill_window.title(f"Watchbill - {selected_date.strftime('%Y-%m-%d')}")

            watchbill_tree = ttk.Treeview(
                watchbill_window,
                columns=["Watch Station"] + [f"{start} - {end}" for start, end in watchtimes],
                show="headings"
            )
            watchbill_tree.heading("Watch Station", text="Watch Station")
            for start, end in watchtimes:
                watchbill_tree.heading(f"{start} - {end}", text=f"{start} - {end}")

            for station in watchstations:
                values = [station] + [watchbill_data[station].get(f"{start} - {end}", "") for start, end in watchtimes]
                watchbill_tree.insert("", tk.END, values=values)

            def on_double_click(event):
                """Handles double-click on a Treeview cell to assign a sailor."""
                rowid = watchbill_tree.identify_row(event.y)
                colid = watchbill_tree.identify_column(event.x)

                if rowid and colid and colid != '#0':  # Check for valid row and column (not the heading)
                    try:
                        time_index = int(colid[1:]) - 2  # colid starts from #1
                        if 0 <= time_index < len(watchtimes):
                            start_time, end_time = watchtimes[time_index]
                            station = watchbill_tree.item(rowid)['values'][0]  # Get the station name

                            def select_sailor(sailor_info):
                                """Assigns the selected sailor to the watch station and time."""
                                rank, sailor_name = sailor_info
                                full_name = f"{rank} {sailor_name}"
                                watchbill_data[station][f"{start_time} - {end_time}"] = full_name
                                watchbill_tree.set(rowid, colid, full_name)  # Update Treeview
                                sailor_select_window.destroy()

                            # --- Sailor Selection Window ---
                            sailor_select_window = tk.Toplevel(watchbill_window)
                            sailor_select_window.title("Select Sailor")

                            sailor_listbox = tk.Listbox(sailor_select_window)
                            qualified_sailors = []

                            for rank, last_name, quals in get_sailors():
                                if quals:
                                    sailor_quals = quals.split(',')
                                    if any(station == qual or (station.startswith(qual) and station[len(qual):].isdigit()) for qual in sailor_quals):
                                        display_string = f"{rank} {last_name}"
                                        sailor_listbox.insert(tk.END, display_string)
                                        qualified_sailors.append((rank, last_name))  # Store rank and name

                            sailor_listbox.pack(fill=tk.BOTH, expand=True)
                            sailor_listbox.bind("<Double-Button-1>", lambda event: select_sailor(qualified_sailors[sailor_listbox.curselection()[0]]))

                    except (IndexError, ValueError) as e:
                        print(f"Error handling double-click: {e}")


                pass  # Replace this with your code


            watchbill_tree.bind("<Double-Button-1>", on_double_click)
            watchbill_tree.pack()



        # Date Selection Window
        date_window = tk.Toplevel(root)
        date_window.title("Select Date")

        tk.Label(date_window, text="Select Date:").pack(pady=5)
        date_entry = DateEntry(date_window, width=12, background='darkblue', foreground='white', borderwidth=2)
        date_entry.pack(pady=5)

        select_button = tk.Button(date_window, text="Select", command=lambda: create_watchbill(date_entry.get_date()))
        select_button.pack(pady=5)

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")



def manage_leave():
    """Opens a new window to manage Leave/Availability."""

    def add_leave_to_db():
        try:
            selection = sailor_listbox.curselection()[0]
            last_name = sailor_listbox.get(selection).split()[1]
            sailor_id = get_sailor_id(last_name)

            start_date = start_date_entry.get_date()
            end_date = end_date_entry.get_date()
            leave_type = leave_type_entry.get()
            notes = notes_entry.get("1.0", tk.END).strip()

            if not leave_type:
                messagebox.showwarning("Missing Information", "Please enter a leave type.")
                return

            if start_date >= end_date:
                messagebox.showwarning("Invalid Dates", "End date must be after start date.")
                return

            add_leave(sailor_id, start_date, end_date, leave_type, notes)
            update_leave_list()
            clear_entries()

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a sailor.")

    def remove_leave_from_db():
        try:
            selection = leave_listbox.curselection()[0]
            leave_id = int(leave_listbox.get(selection).split()[0])  # Get leave ID
            remove_leave(leave_id)
            update_leave_list()
        except IndexError:
            messagebox.showwarning("No Selection", "Please select a leave entry to remove.")

    def clear_entries():
        start_date_entry.set_date(None)
        end_date_entry.set_date(None)
        leave_type_entry.delete(0, tk.END)
        notes_entry.delete("1.0", tk.END)

    def update_leave_list():
        leave_listbox.delete(0, tk.END)
        
        # Calculate spacing (adjust these values as needed)
        id_spacing = 5
        rank_spacing = 5
        name_spacing = 15
        date_spacing = 15
        type_spacing = 15
        notes_spacing = 30  # Adjust as needed for longer notes

        # Create the header string
        header_string = (
            f"{'ID':<{id_spacing}}"  # Add the ID column header back
            f"{'RANK':<{rank_spacing}}"
            f"{'NAME':<{name_spacing}}"
            f"{'START DATE':<{date_spacing}}"
            f"{'END DATE':<{date_spacing}}"
            f"{'TYPE':<{type_spacing}}"
            f"{'NOTES':<{notes_spacing}}"
    )

        leave_listbox.insert(tk.END, header_string)  # Insert the header

        for leave_id, last_name, start_date, end_date, leave_type, notes, rank in get_leaves():
            formatted_start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d %b %Y")
            formatted_end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d %b %Y")

            # Format the string with fixed-width font and spacing
            entry_string = (
                f"{leave_id:<{id_spacing}}"  # Include the leave_id in the display
                f"{rank:<{rank_spacing}}"
                f"{last_name:<{name_spacing}}"
                f"{formatted_start_date:<{date_spacing}}"
                f"{formatted_end_date:<{date_spacing}}"
                f"{leave_type:<{type_spacing}}"
                f"{notes:<{notes_spacing}}"
            )

            leave_listbox.insert(tk.END, entry_string)
            leave_listbox.config(font="Courier")  # Set the font to Courier

    def edit_leave_in_db():
        try:
            selection = leave_listbox.curselection()[0]
            leave_id = int(leave_listbox.get(selection).split()[0])  # Get leave ID

            # Fetch existing leave details from the database
            cursor.execute("SELECT l.start_date, l.end_date, l.type, l.notes, s.last_name "
                           "FROM leaves l "
                           "JOIN sailors s ON l.sailor_id = s.id "
                           "WHERE l.id=?", (leave_id,))
            start_date, end_date, leave_type, notes, last_name = cursor.fetchone()

            def save_changes_to_db():
                new_start_date = edit_start_date_entry.get_date()
                new_end_date = edit_end_date_entry.get_date()
                new_leave_type = edit_leave_type_entry.get()
                new_notes = edit_notes_entry.get("1.0", tk.END).strip()

                if new_start_date >= new_end_date:
                    messagebox.showwarning("Invalid Dates", "End date must be after start date.")
                    return

                edit_leave(leave_id, new_start_date, new_end_date, new_leave_type, new_notes)
                update_leave_list()
                edit_window.destroy()

            edit_window = tk.Toplevel(leave_window)
            edit_window.title(f"Edit Leave for {last_name}")

            tk.Label(edit_window, text="Start Date:").grid(row=0, column=0)
            edit_start_date_entry = DateEntry(edit_window, width=12, background='darkblue', foreground='white', borderwidth=2)
            edit_start_date_entry.set_date(datetime.strptime(start_date, "%Y-%m-%d").date())  # Set initial date
            edit_start_date_entry.grid(row=0, column=1)

            tk.Label(edit_window, text="End Date:").grid(row=1, column=0)
            edit_end_date_entry = DateEntry(edit_window, width=12, background='darkblue', foreground='white', borderwidth=2)
            edit_end_date_entry.set_date(datetime.strptime(end_date, "%Y-%m-%d").date())  # Set initial date
            edit_end_date_entry.grid(row=1, column=1)

            tk.Label(edit_window, text="Leave Type:").grid(row=2, column=0)
            edit_leave_type_entry = tk.Entry(edit_window)
            edit_leave_type_entry.insert(0, leave_type)  # Set initial value
            edit_leave_type_entry.grid(row=2, column=1)

            tk.Label(edit_window, text="Notes:").grid(row=3, column=0)
            edit_notes_entry = tk.Text(edit_window, height=5, width=20)
            edit_notes_entry.insert(tk.END, notes)  # Set initial value
            edit_notes_entry.grid(row=3, column=1)

            save_button = tk.Button(edit_window, text="Save Changes", command=save_changes_to_db)
            save_button.grid(row=4, column=0, columnspan=2, pady=10)

        except IndexError:
            messagebox.showwarning("No Selection", "Please select a leave entry to edit.")

    leave_window = tk.Toplevel(root)
    leave_window.title("Manage Leave/Availability")

    # --- Sailor Listbox ---
    sailor_listbox = tk.Listbox(leave_window, width=30)
    sailor_listbox.pack(side="left", fill="y", padx=10, pady=10)

    # --- Update listbox with sailor names from the database ---
    for rank, last_name, _ in get_sailors():
        sailor_listbox.insert(tk.END, f"{rank} {last_name}")

    # --- Leave Details Frame ---
    leave_details_frame = tk.Frame(leave_window)
    leave_details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    tk.Label(leave_details_frame, text="Start Date:").grid(row=0, column=0)
    start_date_entry = DateEntry(leave_details_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
    start_date_entry.grid(row=0, column=1)

    tk.Label(leave_details_frame, text="End Date:").grid(row=1, column=0)
    end_date_entry = DateEntry(leave_details_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
    end_date_entry.grid(row=1, column=1)

    tk.Label(leave_details_frame, text="Leave Type:").grid(row=2, column=0)
    leave_type_entry = tk.Entry(leave_details_frame)
    leave_type_entry.grid(row=2, column=1)

    tk.Label(leave_details_frame, text="Notes:").grid(row=3, column=0)
    notes_entry = tk.Text(leave_details_frame, height=5, width=20)
    notes_entry.grid(row=3, column=1)

    # --- Leave Listbox ---
    leave_listbox = tk.Listbox(leave_details_frame, width=100)
    leave_listbox.grid(row=4, column=0, columnspan=2, pady=10)
    update_leave_list()

    # --- Buttons ---
    add_button = tk.Button(leave_details_frame, text="Add Leave", command=add_leave_to_db)
    add_button.grid(row=5, column=0, pady=10)

    remove_button = tk.Button(leave_details_frame, text="Remove Leave", command=remove_leave_from_db)
    remove_button.grid(row=5, column=1, pady=10)

    edit_button = tk.Button(leave_details_frame, text="Edit Leave", command=edit_leave_in_db)
    edit_button.grid(row=6, column=0, columnspan=2, pady=10)  # Added edit button

def about():
    messagebox.showinfo("About", "Navy Inport Watchbill Generator\nVersion 1.0")

# --- Menu Bar ---
root = tk.Tk()
root.title("Navy Inport Watchbill Generator")

menubar = tk.Menu(root)

# Personnel menu
personnelmenu = tk.Menu(menubar, tearoff=0)
personnelmenu.add_command(label="Manage Sailors", command=manage_sailors)
personnelmenu.add_command(label="Qualifications", command=manage_qualifications)
personnelmenu.add_command(label="Assign Qualifications", command=assign_qualifications)
personnelmenu.add_command(label="Leave/Availability", command=manage_leave)  # Updated command
menubar.add_cascade(label="Personnel", menu=personnelmenu)

# Watchbill menu
watchbillmenu = tk.Menu(menubar, tearoff=0)
watchbillmenu.add_command(label="Watch Stations", command=manage_watchstations)
watchbillmenu.add_command(label="Watch Times", command=manage_watch_times)
watchbillmenu.add_command(label="Generate Watchbill", command=generate_watchbill)
menubar.add_cascade(label="Watchbill", menu=watchbillmenu) 

root.config(menu=menubar)

root.mainloop()  

conn.close()  # Close the connection when the mainloop ends
