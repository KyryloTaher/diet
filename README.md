# diet

This repository contains a simple Tkinter-based application for generating optimized diets from the USDA database.

## Usage
Run `python diet_app.py` and fill in the required fields. The application now stores the last entered values in `last_setup.json` inside `C:\Users\<username>\projects\diet` (or the equivalent home folder on non-Windows systems) and reloads them on startup so you do not need to re-enter data each time.

### Manual Price Entry
In the "Price Table" fields of the application you can manually enter lines of the form `fdc_id,price_per_gram`. This allows you to specify or adjust prices without using the "Add Product" helper. If the weight field is left empty when adding a product, the value in the price field is treated directly as `price_per_gram`.

## Building the USDA Database
Use `python build_db_app.py` to open a helper application for creating `usda.db` from the USDA CSV exports. The application places the working directory in `C:\Users\<username>\projects\diet` (or the equivalent home folder on non-Windows systems) and allows you to select the CSV files via a simple GUI.
