import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import csv
import logging
import os

DB_FILENAME = "usda.db"
LOG_FILENAME = "import.log"

DEFAULT_FOOD_CSV = "food.csv"
DEFAULT_FOOD_NUTRIENT_CSV = "food_nutrient.csv"
DEFAULT_NUTRIENT_CSV = "nutrient.csv"

def safe_insert(cursor, insert_query, row, log_msg):
    try:
        cursor.execute(insert_query, row)
    except sqlite3.IntegrityError as e:
        logging.info("%s - Row data: %s - Error: %s", log_msg, row, e)

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("DROP TABLE IF EXISTS food_nutrient;")
    cursor.execute("DROP TABLE IF EXISTS nutrient;")
    cursor.execute("DROP TABLE IF EXISTS food;")
    cursor.execute(
        """
        CREATE TABLE food (
            fdc_id INTEGER PRIMARY KEY,
            data_type TEXT,
            description TEXT,
            food_category_id INTEGER,
            publication_date TEXT
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE nutrient (
            nutrient_id INTEGER PRIMARY KEY,
            name TEXT,
            unit_name TEXT,
            nutrient_nbr TEXT,
            rank INTEGER
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE food_nutrient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdc_id INTEGER,
            nutrient_id INTEGER,
            amount REAL,
            data_points INTEGER,
            derivation_id INTEGER,
            min REAL,
            max REAL,
            median REAL,
            footnote TEXT,
            min_year_acquired INTEGER,
            FOREIGN KEY(fdc_id) REFERENCES food(fdc_id),
            FOREIGN KEY(nutrient_id) REFERENCES nutrient(nutrient_id)
        );
        """
    )
    conn.commit()

def import_csv_data(conn, food_csv, food_nutrient_csv, nutrient_csv):
    cursor = conn.cursor()
    with open(food_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        insert_query = (
            "INSERT INTO food (fdc_id, data_type, description, food_category_id, publication_date) "
            "VALUES (?, ?, ?, ?, ?);"
        )
        for row in reader:
            if row.get("data_type") == "foundation_food":
                safe_insert(
                    cursor,
                    insert_query,
                    (
                        row.get("fdc_id"),
                        row.get("data_type"),
                        row.get("description"),
                        row.get("food_category_id"),
                        row.get("publication_date"),
                    ),
                    "Could not insert into food",
                )
            else:
                logging.info("Skipped non-foundation_food row in food.csv: %s", row)
    with open(nutrient_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        insert_query = "INSERT INTO nutrient (nutrient_id, name, unit_name, nutrient_nbr, rank) VALUES (?, ?, ?, ?, ?);"
        for row in reader:
            safe_insert(
                cursor,
                insert_query,
                (
                    row.get("nutrient_id"),
                    row.get("name"),
                    row.get("unit_name"),
                    row.get("nutrient_nbr"),
                    row.get("rank"),
                ),
                "Could not insert into nutrient",
            )
    with open(food_nutrient_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        insert_query = (
            "INSERT INTO food_nutrient (fdc_id, nutrient_id, amount, data_points, derivation_id, min, max, median, footnote, min_year_acquired) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        )
        for row in reader:
            safe_insert(
                cursor,
                insert_query,
                (
                    row.get("fdc_id"),
                    row.get("nutrient_id"),
                    row.get("amount"),
                    row.get("data_points"),
                    row.get("derivation_id"),
                    row.get("min"),
                    row.get("max"),
                    row.get("median"),
                    row.get("footnote"),
                    row.get("min_year_acquired"),
                ),
                "Could not insert into food_nutrient",
            )
    conn.commit()

def ensure_working_directory():
    user_home = os.path.expanduser("~")
    target = os.path.join(user_home, "projects", "diet")
    os.makedirs(target, exist_ok=True)
    os.chdir(target)
    logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)
    return target

class BuildDBApp:
    def __init__(self, root):
        self.root = root
        root.title("USDA DB Builder")

        ttk.Label(root, text="Food CSV:").grid(row=0, column=0, sticky="e")
        self.food_entry = ttk.Entry(root, width=40)
        self.food_entry.grid(row=0, column=1, padx=5, pady=2)
        self.food_entry.insert(0, DEFAULT_FOOD_CSV)
        ttk.Button(root, text="Browse", command=self.browse_food).grid(row=0, column=2, padx=5)

        ttk.Label(root, text="Food Nutrient CSV:").grid(row=1, column=0, sticky="e")
        self.fn_entry = ttk.Entry(root, width=40)
        self.fn_entry.grid(row=1, column=1, padx=5, pady=2)
        self.fn_entry.insert(0, DEFAULT_FOOD_NUTRIENT_CSV)
        ttk.Button(root, text="Browse", command=self.browse_fn).grid(row=1, column=2, padx=5)

        ttk.Label(root, text="Nutrient CSV:").grid(row=2, column=0, sticky="e")
        self.nutrient_entry = ttk.Entry(root, width=40)
        self.nutrient_entry.grid(row=2, column=1, padx=5, pady=2)
        self.nutrient_entry.insert(0, DEFAULT_NUTRIENT_CSV)
        ttk.Button(root, text="Browse", command=self.browse_nutrient).grid(row=2, column=2, padx=5)

        ttk.Button(root, text="Build Database", command=self.build_db).grid(row=3, column=0, columnspan=3, pady=10)

    def browse_food(self):
        path = filedialog.askopenfilename(title="Select food.csv")
        if path:
            self.food_entry.delete(0, tk.END)
            self.food_entry.insert(0, path)

    def browse_fn(self):
        path = filedialog.askopenfilename(title="Select food_nutrient.csv")
        if path:
            self.fn_entry.delete(0, tk.END)
            self.fn_entry.insert(0, path)

    def browse_nutrient(self):
        path = filedialog.askopenfilename(title="Select nutrient.csv")
        if path:
            self.nutrient_entry.delete(0, tk.END)
            self.nutrient_entry.insert(0, path)

    def build_db(self):
        food_csv = self.food_entry.get()
        fn_csv = self.fn_entry.get()
        nutrient_csv = self.nutrient_entry.get()
        if not all(map(os.path.isfile, [food_csv, fn_csv, nutrient_csv])):
            messagebox.showerror("Error", "One or more CSV files do not exist")
            return
        if os.path.exists(DB_FILENAME):
            os.remove(DB_FILENAME)
        conn = sqlite3.connect(DB_FILENAME)
        create_tables(conn)
        import_csv_data(conn, food_csv, fn_csv, nutrient_csv)
        conn.close()
        messagebox.showinfo("Done", f"Database created at {os.path.abspath(DB_FILENAME)}")


def main():
    workdir = ensure_working_directory()
    root = tk.Tk()
    app = BuildDBApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
