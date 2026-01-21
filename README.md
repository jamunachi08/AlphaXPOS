# AlphaX Bonanza POS Pack (Frappe / ERPNext v15+)

**AlphaX Bonanza POS Pack** (XPOS + αPOS) is a **ready-to-install Frappe app** for **ERPNext v15+** that bundles POS extensions for **Restaurant / Café / Retail**.

The pack is designed to:
- Post to standard **ERPNext Sales Invoice (POS)**
- Support **multi-outlet / multi-terminal** setups
- Provide restaurant workflows: **tables/floors**, kitchen stations, and KDS tickets
- Automate optional inventory consumption using simple recipes
- Add operational controls: shifts, day close, audit-friendly documents

## Modules included

### POS operations (XPOS)
- POS Order / Order Item doctypes
- Outlet, Terminal, Theme, Return Reasons
- Shift & day close (with denominations / payments)
- KDS tickets and kitchen stations
- Report email setup (scheduled reports)
- Card-terminal capture integration hooks on Sales Invoice
- Barcode scale rules (item + weight parsing support)

### Restaurant add-ons (αPOS)
- Floor, Table, Table Session
- Offers (Offer Items / Alternate Items)
- Recipes (finished item -> consumed materials)
- Optional background processing that creates a **Material Issue Stock Entry** on POS Sales Invoice submit based on configured recipe items

## Installation (bench)

```bash
bench get-app https://github.com/jamunachi08/alphax_pos_suite
bench --site <your-site> install-app alphax_pos_suite
bench --site <your-site> migrate
```

> If you are installing from a local folder: copy this repo into `apps/alphax_pos_suite` and run `bench --site <your-site> install-app alphax_pos_suite`.

## Quick setup

1. Open **AlphaX POS Suite > Setup** (or search for the relevant doctypes).
2. Create **AlphaX POS Outlet** (company, default warehouse, branch/outlet mapping).
3. Create **AlphaX POS Terminal** (outlet, default mode of payment, naming series).
4. Create **AlphaX POS Profile** and link allowed payment methods.
5. (Restaurant) Create **Floor** and **Tables** and start a **Table Session**.
6. (Optional inventory consumption)
   - Create **AlphaX POS Recipe** for your sold item.
   - Add material items with quantities.
   - Ensure the POS Sales Invoice has a warehouse (set_warehouse / warehouse).

## Notes
- Inventory consumption (recipes) is optional. If no recipe is found, no stock entry is created.
- This app is intended for **Frappe/ERPNext v15+**.

## License
MIT (see `license.txt`)
