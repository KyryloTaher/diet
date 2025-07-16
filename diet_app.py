import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pulp
import csv
import os
import itertools
import json

DB_FILENAME = "usda.db"
WORKDIR = os.path.join(os.path.expanduser("~"), "projects", "diet")
LAST_SETUP_FILE = os.path.join(WORKDIR, "last_setup.json")
DB_PATH = os.path.join(WORKDIR, DB_FILENAME)

class DietApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diet Generator (with Supplements as Food Items)")

        # Instance variables for storing solution and input data
        self.solution_status = None
        self.solution_x_raw = {}
        self.solution_x_cooked = {}
        self.solution_x_supp = {}
        self.food_descriptions = {}
        self.food_nutrients_dict = {}
        self.price_data_all = {}
        self.raw_price_data = {}
        self.req_data_heat = {}
        self.req_data_nonheat = {}
        self.food_energy_dict = {}
        self.calorie_min = None
        self.calorie_max = None
        self.custom_product_constraints = {}
        self.supplement_data = {}
        self.selected_fdc_id = None

        main_frame = ttk.Frame(root, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        left_canvas = tk.Canvas(main_frame)
        left_canvas.grid(row=0, column=0, sticky="nsew")
        left_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=left_canvas.yview)
        left_scrollbar.grid(row=0, column=0, sticky="nse")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        self.left_scrollable_frame = ttk.Frame(left_canvas)
        left_canvas.create_window((0, 0), window=self.left_scrollable_frame, anchor="nw")
        self.left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )

        self.right_frame = ttk.Frame(main_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew")
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(1, weight=1)

        row = 0
        ttk.Label(self.left_scrollable_frame, text="Search Product:").grid(row=row, column=0, sticky="w")
        row += 1
        search_frame = ttk.Frame(self.left_scrollable_frame)
        search_frame.grid(row=row, column=0, sticky="w")
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(search_frame, text="Search", command=self.search_products).grid(row=0, column=1, padx=5)
        row += 1
        self.search_results = tk.Listbox(self.left_scrollable_frame, width=40, height=5)
        self.search_results.grid(row=row, column=0, sticky="w")
        self.search_results.bind("<<ListboxSelect>>", self.on_result_select)
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Price ($) and Weight (g):").grid(row=row, column=0, sticky="w")
        row += 1
        pw_frame = ttk.Frame(self.left_scrollable_frame)
        pw_frame.grid(row=row, column=0, sticky="w")
        self.price_entry = ttk.Entry(pw_frame, width=10)
        self.price_entry.grid(row=0, column=0, padx=5)
        self.weight_entry = ttk.Entry(pw_frame, width=10)
        self.weight_entry.grid(row=0, column=1, padx=5)
        row += 1
        self.add_table_var = tk.StringVar(value="all")
        opt_frame = ttk.Frame(self.left_scrollable_frame)
        opt_frame.grid(row=row, column=0, sticky="w")
        ttk.Radiobutton(opt_frame, text="All Foods", variable=self.add_table_var, value="all").grid(row=0, column=0, padx=5)
        ttk.Radiobutton(opt_frame, text="Raw Foods", variable=self.add_table_var, value="raw").grid(row=0, column=1, padx=5)
        ttk.Button(opt_frame, text="Add Product", command=self.add_product).grid(row=0, column=2, padx=5)
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Price Table (All Foods) (fdc_id,price_per_gram):").grid(row=row, column=0, sticky="w")
        row += 1
        self.price_text = tk.Text(self.left_scrollable_frame, width=40, height=8)
        self.price_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Price Table (Raw Foods) (fdc_id,price_per_gram):").grid(row=row, column=0, sticky="w")
        row += 1
        self.raw_price_text = tk.Text(self.left_scrollable_frame, width=40, height=8)
        self.raw_price_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Heat-resistant Nutrient Requirements (nutrient_id,RDA,UL):").grid(row=row, column=0, sticky="w")
        row += 1
        self.heat_req_text = tk.Text(self.left_scrollable_frame, width=40, height=8)
        self.heat_req_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Non–Heat–resistant Nutrient Requirements (nutrient_id,RDA,UL):").grid(row=row, column=0, sticky="w")
        row += 1
        self.nonheat_req_text = tk.Text(self.left_scrollable_frame, width=40, height=8)
        self.nonheat_req_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Min Calories (kcal):").grid(row=row, column=0, sticky="w")
        row += 1
        self.calorie_min_entry = ttk.Entry(self.left_scrollable_frame, width=10)
        self.calorie_min_entry.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Max Calories (kcal):").grid(row=row, column=0, sticky="w")
        row += 1
        self.calorie_max_entry = ttk.Entry(self.left_scrollable_frame, width=10)
        self.calorie_max_entry.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Product Constraints (FDC_ID, min_g, [max_g]; one per line):").grid(row=row, column=0, sticky="w")
        row += 1
        self.product_constraints_text = tk.Text(self.left_scrollable_frame, width=40, height=4)
        self.product_constraints_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        ttk.Label(self.left_scrollable_frame, text="Supplements (nutrient_id,price per pill,nutrient per pill; one per line):").grid(row=row, column=0, sticky="w")
        row += 1
        self.supplement_text = tk.Text(self.left_scrollable_frame, width=40, height=4)
        self.supplement_text.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        row += 1
        generate_button = ttk.Button(self.left_scrollable_frame, text="Generate Base Diet", command=self.generate_diet)
        generate_button.grid(row=row, column=0, pady=5, sticky="w")
        row += 1
        supp_button = ttk.Button(self.left_scrollable_frame, text="Generate Diet with Supplements", command=self.generate_diet_with_supplements)
        supp_button.grid(row=row, column=0, pady=5, sticky="w")
        row += 1
        report_button = ttk.Button(self.left_scrollable_frame, text="Generate Report", command=self.generate_report)
        report_button.grid(row=row, column=0, pady=5, sticky="w")

        ttk.Label(self.right_frame, text="Final Diet Output:").grid(row=0, column=0, sticky="w")
        self.output_text = tk.Text(self.right_frame, width=80, height=40, state="normal")
        self.output_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.load_setup()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.save_setup()
        self.root.destroy()

    def save_setup(self):
        setup = {
            "price_text": self.price_text.get("1.0", tk.END),
            "raw_price_text": self.raw_price_text.get("1.0", tk.END),
            "heat_req_text": self.heat_req_text.get("1.0", tk.END),
            "nonheat_req_text": self.nonheat_req_text.get("1.0", tk.END),
            "calorie_min": self.calorie_min_entry.get(),
            "calorie_max": self.calorie_max_entry.get(),
            "product_constraints_text": self.product_constraints_text.get("1.0", tk.END),
            "supplement_text": self.supplement_text.get("1.0", tk.END)
        }
        os.makedirs(WORKDIR, exist_ok=True)
        try:
            with open(LAST_SETUP_FILE, "w", encoding="utf-8") as f:
                json.dump(setup, f)
        except Exception as e:
            print(f"Could not save setup: {e}")

    def load_setup(self):
        if not os.path.exists(LAST_SETUP_FILE):
            return
        try:
            with open(LAST_SETUP_FILE, "r", encoding="utf-8") as f:
                setup = json.load(f)
            self.price_text.insert("1.0", setup.get("price_text", ""))
            self.raw_price_text.insert("1.0", setup.get("raw_price_text", ""))
            self.heat_req_text.insert("1.0", setup.get("heat_req_text", ""))
            self.nonheat_req_text.insert("1.0", setup.get("nonheat_req_text", ""))
            self.calorie_min_entry.insert(0, setup.get("calorie_min", ""))
            self.calorie_max_entry.insert(0, setup.get("calorie_max", ""))
            self.product_constraints_text.insert("1.0", setup.get("product_constraints_text", ""))
            self.supplement_text.insert("1.0", setup.get("supplement_text", ""))
        except Exception as e:
            print(f"Could not load setup: {e}")

    def search_products(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        like_query = f"%{query}%"
        rows = cur.execute(
            "SELECT fdc_id, description FROM food WHERE description LIKE ? ORDER BY description LIMIT 50",
            (like_query,),
        ).fetchall()
        conn.close()
        self.search_results.delete(0, tk.END)
        for fid, desc in rows:
            self.search_results.insert(tk.END, f"{fid}: {desc}")

    def on_result_select(self, event):
        sel = self.search_results.curselection()
        if not sel:
            self.selected_fdc_id = None
            return
        text = self.search_results.get(sel[0])
        try:
            fid = int(text.split(":", 1)[0])
            self.selected_fdc_id = fid
        except ValueError:
            self.selected_fdc_id = None

    def add_product(self):
        fid = self.selected_fdc_id
        if fid is None:
            messagebox.showerror("Error", "Select a product from the search results")
            return
        try:
            price = float(self.price_entry.get())
            weight = float(self.weight_entry.get())
            if weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter valid price and weight")
            return
        price_per_gram = price / weight
        target = self.add_table_var.get()
        if target == "all":
            widget = self.price_text
        else:
            widget = self.raw_price_text
        lines = [ln.strip() for ln in widget.get("1.0", tk.END).splitlines() if ln.strip()]
        updated = False
        for i, ln in enumerate(lines):
            parts = [p.strip() for p in ln.split(",")]
            if parts and parts[0] == str(fid):
                lines[i] = f"{fid},{price_per_gram:.6f}"
                updated = True
        if not updated:
            lines.append(f"{fid},{price_per_gram:.6f}")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", "\n".join(lines) + ("\n" if lines else ""))
        self.save_setup()
    def prepare_data(self):
        price_data_all = {}
        for line in self.price_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                fdc_id = int(parts[0])
                price_data_all[fdc_id] = float(parts[1])
            except ValueError:
                continue
        self.price_data_all = price_data_all

        raw_price_data = {}
        for line in self.raw_price_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                fdc_id = int(parts[0])
                raw_price_data[fdc_id] = float(parts[1])
            except ValueError:
                continue
        self.raw_price_data = raw_price_data

        req_data_heat = {}
        for line in self.heat_req_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 1:
                continue
            try:
                nutrient_id = int(parts[0])
            except ValueError:
                continue
            rda = float(parts[1]) if len(parts) >= 2 and parts[1] != "" else None
            ul  = float(parts[2]) if len(parts) >= 3 and parts[2] != "" else None
            req_data_heat[nutrient_id] = (rda, ul)
        self.req_data_heat = req_data_heat

        req_data_nonheat = {}
        for line in self.nonheat_req_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 1:
                continue
            try:
                nutrient_id = int(parts[0])
            except ValueError:
                continue
            rda = float(parts[1]) if len(parts) >= 2 and parts[1] != "" else None
            ul  = float(parts[2]) if len(parts) >= 3 and parts[2] != "" else None
            req_data_nonheat[nutrient_id] = (rda, ul)
        self.req_data_nonheat = req_data_nonheat

        try:
            self.calorie_min = float(self.calorie_min_entry.get().strip()) if self.calorie_min_entry.get().strip() else None
        except ValueError:
            self.calorie_min = None
        try:
            self.calorie_max = float(self.calorie_max_entry.get().strip()) if self.calorie_max_entry.get().strip() else None
        except ValueError:
            self.calorie_max = None

        product_constraints = {}
        for line in self.product_constraints_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                fdc_id = int(parts[0])
                min_val = float(parts[1])
                if len(parts) >= 3 and parts[2] != "":
                    max_val = float(parts[2])
                else:
                    max_val = 1e6
                product_constraints[fdc_id] = (min_val, max_val)
            except ValueError:
                continue
        self.custom_product_constraints = product_constraints

        supplement_data = {}
        for line in self.supplement_text.get("1.0", tk.END).strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            try:
                nutrient_id = int(parts[0])
                price_per_pill = float(parts[1])
                nutrient_per_pill = float(parts[2])
                supplement_data[nutrient_id] = (price_per_pill, nutrient_per_pill)
            except ValueError:
                continue
        self.supplement_data = supplement_data

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        query_foods = "SELECT fdc_id, description FROM food WHERE data_type = 'foundation_food'"
        all_food_rows = cur.execute(query_foods).fetchall()
        food_nutrients_dict = {}
        food_descriptions = {}
        for fdc_id, desc in all_food_rows:
            food_descriptions[fdc_id] = desc
            query_fn = "SELECT nutrient_id, amount FROM food_nutrient WHERE fdc_id = ?"
            nutrient_rows = cur.execute(query_fn, (fdc_id,)).fetchall()
            ndict = {}
            for (nid, amt) in nutrient_rows:
                ndict[nid] = amt if amt is not None else 0.0
            food_nutrients_dict[fdc_id] = ndict
        conn.close()
        self.food_nutrients_dict = food_nutrients_dict
        self.food_descriptions = food_descriptions

        valid_food_ids_all = [fid for fid in food_nutrients_dict if fid in self.price_data_all and len(food_nutrients_dict[fid]) > 0]
        valid_food_ids_raw = [fid for fid in food_nutrients_dict if fid in self.raw_price_data and len(food_nutrients_dict[fid]) > 0]
        if not valid_food_ids_all:
            messagebox.showerror("Error", "No foundation_food items found with user-defined price for all foods.")
            return False
        if self.req_data_nonheat and not valid_food_ids_raw:
            messagebox.showerror("Error", "No foundation_food items found with user-defined raw price for non–heat–resistant nutrients.")
            return False
        for fdc_id in self.custom_product_constraints:
            if fdc_id not in valid_food_ids_all:
                messagebox.showerror("Error", f"FDC_ID {fdc_id} for product constraint not found in All Foods price table.")
                return False
        self.latest_valid_food_ids_cooked = valid_food_ids_all
        self.latest_valid_food_ids_raw = valid_food_ids_raw

        all_valid_ids = set(valid_food_ids_all) | set(valid_food_ids_raw)
        food_energy_dict = {}
        for fid in all_valid_ids:
            ndict = food_nutrients_dict[fid]
            if ndict.get(1008, 0) > 0:
                kcal = ndict[1008]
            elif ndict.get(2047, 0) > 0:
                kcal = ndict[2047]
            elif ndict.get(2048, 0) > 0:
                kcal = ndict[2048]
            else:
                protein_g = ndict.get(1003, 0.0)
                fat_1004 = ndict.get(1004, 0.0)
                fat_1085 = ndict.get(1085, 0.0)
                fat_g = fat_1004 if fat_1004 > 0.0 else fat_1085
                carbs_g = ndict.get(1005, 0.0)
                kcal = 9 * fat_g + 4 * protein_g + 4 * carbs_g
            food_energy_dict[fid] = kcal
        self.food_energy_dict = food_energy_dict
        return True
    def build_and_solve_lp(self, excluded_nutrients=set(), include_supplements=False):
        price_data_all = self.price_data_all
        raw_price_data = self.raw_price_data
        food_energy_dict = self.food_energy_dict
        food_nutrients_dict = self.food_nutrients_dict
        valid_food_ids_all = self.latest_valid_food_ids_cooked
        valid_food_ids_raw = self.latest_valid_food_ids_raw

        req_data_heat = self.req_data_heat.copy()
        req_data_nonheat = self.req_data_nonheat.copy()
        for eid in [1008, 2047, 2048]:
            req_data_heat.pop(eid, None)
            req_data_nonheat.pop(eid, None)

        problem = pulp.LpProblem("DietMinCost", pulp.LpMinimize)

        x_cooked = { fid: pulp.LpVariable(f"x_cooked_{fid}", lowBound=0, cat=pulp.LpInteger)
                     for fid in valid_food_ids_all }
        x_raw = { fid: pulp.LpVariable(f"x_raw_{fid}", lowBound=0, cat=pulp.LpInteger)
                  for fid in valid_food_ids_raw }

        y_cooked = { fid: pulp.LpVariable(f"y_cooked_{fid}", cat=pulp.LpBinary)
                     for fid in valid_food_ids_all }
        y_raw = { fid: pulp.LpVariable(f"y_raw_{fid}", cat=pulp.LpBinary)
                  for fid in valid_food_ids_raw }

        M_food = 10000
        for fid in valid_food_ids_all:
            problem += (x_cooked[fid] >= 2 * y_cooked[fid])
            problem += (x_cooked[fid] <= M_food * y_cooked[fid])
        for fid in valid_food_ids_raw:
            problem += (x_raw[fid] >= 2 * y_raw[fid])
            problem += (x_raw[fid] <= M_food * y_raw[fid])

        for fid in valid_food_ids_raw:
            has_nonheat = any(food_nutrients_dict[fid].get(nutr_id, 0) > 0 for nutr_id in req_data_nonheat.keys())
            if not has_nonheat:
                problem += (y_raw[fid] == 0)

        x_supp = {}
        if include_supplements:
            for nutr_id, (supp_price, supp_nutrient) in self.supplement_data.items():
                x_supp[nutr_id] = pulp.LpVariable(f"x_supp_{nutr_id}", lowBound=0, cat=pulp.LpInteger)

        problem += (
            pulp.lpSum([price_data_all[fid] * x_cooked[fid] for fid in valid_food_ids_all]) +
            pulp.lpSum([raw_price_data[fid] * x_raw[fid] for fid in valid_food_ids_raw]) +
            (pulp.lpSum([self.supplement_data[nid][0] * x_supp[nid] for nid in x_supp]) if include_supplements else 0)
        )

        total_cal_expr = (
            pulp.lpSum([(food_energy_dict[fid] / 100.0) * x_cooked[fid] for fid in valid_food_ids_all]) +
            pulp.lpSum([(food_energy_dict[fid] / 100.0) * x_raw[fid] for fid in valid_food_ids_raw])
        )
        if self.calorie_min and self.calorie_min > 0:
            problem += (total_cal_expr >= self.calorie_min)
        if self.calorie_max and self.calorie_max > 0:
            problem += (total_cal_expr <= self.calorie_max)

        for nutr_id, (rda, ul) in req_data_heat.items():
            if nutr_id in excluded_nutrients:
                continue
            nutr_sum = []
            for fid in valid_food_ids_all:
                if nutr_id == 1004:
                    amt = food_nutrients_dict[fid].get(1004, 0.0)
                    if amt == 0.0:
                        amt = food_nutrients_dict[fid].get(1085, 0.0)
                else:
                    amt = food_nutrients_dict[fid].get(nutr_id, 0.0)
                nutr_sum.append((amt/100.0) * x_cooked[fid])
            for fid in valid_food_ids_raw:
                if nutr_id == 1004:
                    amt = food_nutrients_dict[fid].get(1004, 0.0)
                    if amt == 0.0:
                        amt = food_nutrients_dict[fid].get(1085, 0.0)
                else:
                    amt = food_nutrients_dict[fid].get(nutr_id, 0.0)
                nutr_sum.append((amt/100.0) * x_raw[fid])
            if include_supplements and nutr_id in x_supp:
                nutr_sum.append(self.supplement_data[nutr_id][1] * x_supp[nutr_id])
            if rda is not None:
                problem += (pulp.lpSum(nutr_sum) >= rda)
            if ul is not None:
                problem += (pulp.lpSum(nutr_sum) <= ul)

        for nutr_id, (rda, ul) in req_data_nonheat.items():
            if nutr_id in excluded_nutrients:
                continue
            nutr_sum = []
            for fid in valid_food_ids_raw:
                if nutr_id == 1004:
                    amt = food_nutrients_dict[fid].get(1004, 0.0)
                    if amt == 0.0:
                        amt = food_nutrients_dict[fid].get(1085, 0.0)
                else:
                    amt = food_nutrients_dict[fid].get(nutr_id, 0.0)
                nutr_sum.append((amt/100.0) * x_raw[fid])
            if include_supplements and nutr_id in x_supp:
                nutr_sum.append(self.supplement_data[nutr_id][1] * x_supp[nutr_id])
            if rda is not None:
                problem += (pulp.lpSum(nutr_sum) >= rda)
            if ul is not None:
                problem += (pulp.lpSum(nutr_sum) <= ul)

        for fdc_id, (min_val, max_val) in self.custom_product_constraints.items():
            combined_usage = None
            if fdc_id in x_cooked and fdc_id in x_raw:
                combined_usage = x_cooked[fdc_id] + x_raw[fdc_id]
            elif fdc_id in x_cooked:
                combined_usage = x_cooked[fdc_id]
            elif fdc_id in x_raw:
                combined_usage = x_raw[fdc_id]
            if combined_usage is not None:
                if min_val > 0:
                    problem += (combined_usage >= min_val)
                problem += (combined_usage <= max_val)

        solution = problem.solve(pulp.PULP_CBC_CMD(msg=0))
        status_str = pulp.LpStatus[solution]
        if status_str != "Optimal":
            return status_str, None, None, None, None
        total_cost = 0.0
        for fid in valid_food_ids_all:
            grams = x_cooked[fid].varValue or 0.0
            total_cost += grams * price_data_all[fid]
        for fid in valid_food_ids_raw:
            grams = x_raw[fid].varValue or 0.0
            total_cost += grams * raw_price_data[fid]
        if include_supplements:
            for nutr_id in x_supp:
                pills = x_supp[nutr_id].varValue or 0.0
                total_cost += pills * self.supplement_data[nutr_id][0]
        return status_str, total_cost, x_cooked, x_raw, x_supp
    def generate_diet(self):
        if not self.prepare_data():
            return
        self.save_setup()
        status, cost, x_cooked, x_raw, _ = self.build_and_solve_lp(include_supplements=False)
        self.output_text.delete("1.0", tk.END)
        if status != "Optimal":
            self.output_text.insert("end", f"No optimal solution found. Solver status: {status}\n")
            return
        self.solution_status = status
        self.solution_x_cooked = x_cooked
        self.solution_x_raw = x_raw
        self.solution_x_supp = {}
        self.output_text.insert("end", "Optimal Base Diet Found (No Supplements):\n")
        self.output_text.insert("end", f"Total cost = ${cost:.2f}\n\n")
        self.output_text.insert("end", "Raw Foods:\n")
        for fid, var in x_raw.items():
            grams = var.varValue or 0.0
            if grams > 1e-6:
                item_cost = grams * self.raw_price_data[fid]
                desc = self.food_descriptions.get(fid, "")
                self.output_text.insert("end", f"  FDC_ID={fid} ({desc}), grams={grams:.0f}, cost=${item_cost:.2f}\n")
        self.output_text.insert("end", "\nCooked Foods:\n")
        for fid, var in x_cooked.items():
            grams = var.varValue or 0.0
            if grams > 1e-6:
                item_cost = grams * self.price_data_all[fid]
                desc = self.food_descriptions.get(fid, "")
                self.output_text.insert("end", f"  FDC_ID={fid} ({desc}), grams={grams:.0f}, cost=${item_cost:.2f}\n")

    def generate_diet_with_supplements(self):
        if not self.prepare_data():
            return
        self.save_setup()
        base_status, base_cost, base_x_cooked, base_x_raw, _ = self.build_and_solve_lp(include_supplements=False)
        if base_status != "Optimal":
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("end", f"No optimal base solution found. Solver status: {base_status}\n")
            return
        supp_status, supp_cost, supp_x_cooked, supp_x_raw, supp_vars = self.build_and_solve_lp(include_supplements=True)
        if supp_status != "Optimal":
            chosen_status, chosen_cost = base_status, base_cost
            chosen_x_cooked, chosen_x_raw, chosen_supp = base_x_cooked, base_x_raw, {}
        else:
            if supp_cost < base_cost:
                chosen_status, chosen_cost = supp_status, supp_cost
                chosen_x_cooked, chosen_x_raw, chosen_supp = supp_x_cooked, supp_x_raw, supp_vars
            else:
                chosen_status, chosen_cost = base_status, base_cost
                chosen_x_cooked, chosen_x_raw, chosen_supp = base_x_cooked, base_x_raw, {}
        self.solution_status = chosen_status
        self.solution_x_cooked = chosen_x_cooked
        self.solution_x_raw = chosen_x_raw
        self.solution_x_supp = chosen_supp
        self.output_text.delete("1.0", tk.END)
        if chosen_supp:
            supp_list = ", ".join(str(nid) for nid in sorted(chosen_supp.keys()))
            self.output_text.insert("end", f"Optimal Diet with Supplements Found: Total cost = ${chosen_cost:.2f}\n")
            self.output_text.insert("end", f"Supplements used for nutrients: {supp_list}\n\n")
        else:
            self.output_text.insert("end", f"No supplement usage improves upon base diet. Total cost = ${chosen_cost:.2f}\n\n")
        self.output_text.insert("end", "Detailed Diet Contents:\n")
        self.output_text.insert("end", "Raw Foods:\n")
        for fid, var in chosen_x_raw.items():
            grams = var.varValue or 0.0
            if grams > 1e-6:
                item_cost = grams * self.raw_price_data[fid]
                desc = self.food_descriptions.get(fid, "")
                self.output_text.insert("end", f"  FDC_ID={fid} ({desc}), grams={grams:.0f}, cost=${item_cost:.2f}\n")
        self.output_text.insert("end", "\nCooked Foods:\n")
        for fid, var in chosen_x_cooked.items():
            grams = var.varValue or 0.0
            if grams > 1e-6:
                item_cost = grams * self.price_data_all[fid]
                desc = self.food_descriptions.get(fid, "")
                self.output_text.insert("end", f"  FDC_ID={fid} ({desc}), grams={grams:.0f}, cost=${item_cost:.2f}\n")
        if chosen_supp:
            self.output_text.insert("end", "\nSupplements:\n")
            for nutr_id, var in chosen_supp.items():
                pills = var.varValue or 0.0
                if pills > 1e-6:
                    cost_val = pills * self.supplement_data[nutr_id][0]
                    self.output_text.insert("end", f"  Nutrient {nutr_id} supplement, pills={pills:.0f}, cost=${cost_val:.2f}\n")
        self.output_text.insert("end", f"\nTotal cost (including supplements) = ${chosen_cost:.2f}\n")

    def generate_report(self):
        if self.solution_status != "Optimal":
            messagebox.showwarning("Warning", "No optimal solution to report. Generate a diet first.")
            return
        if not (self.solution_x_raw or self.solution_x_cooked or self.solution_x_supp):
            messagebox.showwarning("Warning", "No solution data found. Please run 'Generate Diet' first.")
            return

        macros = [1003, 1004, 1005]
        all_nutr_ids = set(list(self.req_data_heat.keys()) + list(self.req_data_nonheat.keys()) + macros)
        all_nutr_ids = sorted(all_nutr_ids)
        csv_filename = "report.csv"
        headers = ["Type", "ID", "Description", "Amount", "Cost", "Energy"]
        for nid in all_nutr_ids:
            headers.append(f"Nutr_{nid}")
        rows = []
        totals = {"Raw": {"amount": 0.0, "cost": 0.0, "energy": 0.0, "nutr": {nid: 0.0 for nid in all_nutr_ids}},
                  "Cooked": {"amount": 0.0, "cost": 0.0, "energy": 0.0, "nutr": {nid: 0.0 for nid in all_nutr_ids}},
                  "Supplement": {"amount": 0.0, "cost": 0.0, "energy": 0.0, "nutr": {nid: 0.0 for nid in all_nutr_ids}}}
        for fid, var in self.solution_x_raw.items():
            amount = var.varValue or 0.0
            if amount <= 1e-6:
                continue
            cost_val = amount * self.raw_price_data.get(fid, 0)
            energy_val = (self.food_energy_dict.get(fid, 0) / 100.0) * amount
            nutr_values = []
            for nid in all_nutr_ids:
                amt = self.food_nutrients_dict.get(fid, {}).get(nid, 0.0)
                nutr_values.append((amt/100.0)*amount)
            row = ["Raw", fid, self.food_descriptions.get(fid, ""), amount, cost_val, energy_val] + nutr_values
            rows.append(row)
            totals["Raw"]["amount"] += amount
            totals["Raw"]["cost"] += cost_val
            totals["Raw"]["energy"] += energy_val
            for i, nid in enumerate(all_nutr_ids):
                totals["Raw"]["nutr"][nid] += nutr_values[i]
        for fid, var in self.solution_x_cooked.items():
            amount = var.varValue or 0.0
            if amount <= 1e-6:
                continue
            cost_val = amount * self.price_data_all.get(fid, 0)
            energy_val = (self.food_energy_dict.get(fid, 0) / 100.0) * amount
            nutr_values = []
            for nid in all_nutr_ids:
                amt = self.food_nutrients_dict.get(fid, {}).get(nid, 0.0)
                nutr_values.append((amt/100.0)*amount)
            row = ["Cooked", fid, self.food_descriptions.get(fid, ""), amount, cost_val, energy_val] + nutr_values
            rows.append(row)
            totals["Cooked"]["amount"] += amount
            totals["Cooked"]["cost"] += cost_val
            totals["Cooked"]["energy"] += energy_val
            for i, nid in enumerate(all_nutr_ids):
                totals["Cooked"]["nutr"][nid] += nutr_values[i]
        for nutr_id, var in self.solution_x_supp.items():
            pills = var.varValue or 0.0
            if pills <= 1e-6:
                continue
            cost_val = pills * self.supplement_data[nutr_id][0]
            nutr_list = [0]*len(all_nutr_ids)
            if nutr_id in all_nutr_ids:
                index = all_nutr_ids.index(nutr_id)
                nutr_list[index] = pills * self.supplement_data[nutr_id][1]
            row = ["Supplement", nutr_id, f"Supplement for nutrient {nutr_id}", pills, cost_val, 0] + nutr_list
            rows.append(row)
            totals["Supplement"]["amount"] += pills
            totals["Supplement"]["cost"] += cost_val
            for i, nid in enumerate(all_nutr_ids):
                totals["Supplement"]["nutr"][nid] += nutr_list[i]
        for typ in ["Raw", "Cooked", "Supplement"]:
            total_row = [f"TOTAL {typ}", "", "", totals[typ]["amount"], totals[typ]["cost"], totals[typ]["energy"]]
            for nid in all_nutr_ids:
                total_row.append(totals[typ]["nutr"][nid])
            rows.append(total_row)
        grand_amount = totals["Raw"]["amount"] + totals["Cooked"]["amount"] + totals["Supplement"]["amount"]
        grand_cost = totals["Raw"]["cost"] + totals["Cooked"]["cost"] + totals["Supplement"]["cost"]
        grand_energy = totals["Raw"]["energy"] + totals["Cooked"]["energy"] + totals["Supplement"]["energy"]
        grand_nutr = {nid: totals["Raw"]["nutr"][nid] + totals["Cooked"]["nutr"][nid] + totals["Supplement"]["nutr"][nid] for nid in all_nutr_ids}
        grand_row = ["GRAND TOTAL", "", "", grand_amount, grand_cost, grand_energy]
        for nid in all_nutr_ids:
            grand_row.append(grand_nutr[nid])
        rows.append(grand_row)
        try:
            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in rows:
                    writer.writerow(r)
            msg = f"Report generated: {os.path.abspath(csv_filename)}"
            messagebox.showinfo("Report Generated", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write report: {e}")

def main():
    os.makedirs(WORKDIR, exist_ok=True)
    root = tk.Tk()
    app = DietApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
