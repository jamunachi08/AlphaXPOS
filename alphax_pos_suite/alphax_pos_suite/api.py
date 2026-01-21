import frappe

@frappe.whitelist()
def ping():
    return {"ok": True, "app": "alphax_pos_suite"}

@frappe.whitelist()
def redeem_credit_note(credit_note, invoice, amount=None):
    # Accounting-specific: implement Payment Entry / Journal Entry allocations based on your COA.
    return {
        "ok": False,
        "message": "Credit note redemption needs accounting mapping (Payment Entry/Journal Entry). Implement in next iteration based on your Chart of Accounts."
    }

import frappe
from frappe import _
import json
from alphax_pos_suite.integrations.erpnext_stock import create_material_request_from_ck_request, create_stock_entry_from_ck_request


@frappe.whitelist()
def get_pos_boot(terminal):
    if not terminal or not frappe.db.exists("AlphaX POS Terminal", terminal):
        frappe.throw(_("Terminal not found."))

    t = frappe.get_doc("AlphaX POS Terminal", terminal)
    prof_name = getattr(t, "pos_profile", None)
    payload = {"profile": None, "theme": None, "payment_methods": [], "scale": {"generic": None, "prefix_map": []}}

    if prof_name and frappe.db.exists("AlphaX POS Profile", prof_name):
        p = frappe.get_doc("AlphaX POS Profile", prof_name)
        payload["profile"] = {"name": p.name, "pos_type": p.pos_type, "enable_shortcuts": int(p.enable_shortcuts or 0),
                              "enable_scale": int(p.enable_weighing_scale or 0)}
        if p.theme and frappe.db.exists("AlphaX POS Theme", p.theme):
            th = frappe.get_doc("AlphaX POS Theme", p.theme)
            payload["theme"] = {
                "primary": th.primary_color, "secondary": th.secondary_color, "accent": th.accent_color,
                "danger": th.danger_color, "bg": th.bg_color, "card": th.card_bg, "text": th.text_color,
                "radius": int(th.button_radius or 12), "touch": int(th.touch_mode or 0), "font": th.font_family
            }

        if int(p.use_profile_payment_methods or 0) == 1:
            rows = sorted(p.payment_methods or [], key=lambda r: int(getattr(r, "sort_order", 0) or 0))
            payload["payment_methods"] = [{"mode_of_payment": r.mode_of_payment, "is_default": int(r.is_default or 0), "color": r.button_color} for r in rows]

        if int(p.enable_weighing_scale or 0) == 1:
            if p.generic_scale_definition and frappe.db.exists("AlphaX POS Scale Barcode Definition", p.generic_scale_definition):
                d = frappe.get_doc("AlphaX POS Scale Barcode Definition", p.generic_scale_definition)
                payload["scale"]["generic"] = _def_to_dict(d)

            rules = sorted(p.scale_rules or [], key=lambda r: int(getattr(r, "priority", 10) or 10))
            for r in rules:
                if r.applies_to == "Barcode Prefix" and r.barcode_prefix and r.definition and frappe.db.exists("AlphaX POS Scale Barcode Definition", r.definition):
                    d = frappe.get_doc("AlphaX POS Scale Barcode Definition", r.definition)
                    payload["scale"]["prefix_map"].append({"prefix": r.barcode_prefix, "defn": _def_to_dict(d)})

    return payload

def _def_to_dict(d):
    return {
        "prefix": d.prefix or "",
        "total_length": int(d.total_length or 0),
        "mapping_type": d.mapping_type,
        "qty_divider": float(d.qty_divider or 1),
        "rate_divider": float(d.rate_divider or 1),
        "use_qty_from_barcode": int(d.use_qty_from_barcode or 0),
        "use_rate_from_barcode": int(d.use_rate_from_barcode or 0),
        "item_start": int(d.item_start or 1), "item_length": int(d.item_length or 4),
        "qty_start": int(d.qty_start or 5), "qty_length": int(d.qty_length or 4),
        "rate_start": int(d.rate_start or 9), "rate_length": int(d.rate_length or 4),
    }

@frappe.whitelist()
def get_kb_articles(role=None):
    roles = set(frappe.get_roles(frappe.session.user))
    kb_roles = []
    if "System Manager" in roles or "POS Manager" in roles:
        kb_roles = ["Cashier","Supervisor","Manager","Implementer"]
    elif "POS Supervisor" in roles:
        kb_roles = ["Cashier","Supervisor"]
    else:
        kb_roles = ["Cashier"]
    if role and role in kb_roles:
        kb_roles = [role]
    return frappe.get_all("AlphaX POS KB Article",
        filters={"enabled":1, "role":["in", kb_roles]},
        fields=["name","title","role","section","shortcut","content"],
        order_by="role asc, section asc, title asc"
    )

@frappe.whitelist()
def terminal_capture_start(mode_of_payment, amount, currency=None, terminal=None):
    return {
        "status": "PENDING",
        "mode_of_payment": mode_of_payment,
        "amount": amount,
        "currency": currency,
        "message": "Terminal integration is enabled but driver is not configured yet."
    }


# --------------------
# Phase-2 Boosters API
# --------------------

import json
from frappe.utils import now_datetime

@frappe.whitelist()
def submit_qr_order(token: str, items, customer_name: str = ""):
    """Create a Draft AlphaX POS Order from QR ordering.
    `items` can be a JSON string or list of dicts: [{item_code, qty}].
    """
    try:
        if isinstance(items, str):
            items = json.loads(items or "[]")
        items = items or []
        if not token:
            return {"ok": False, "message": "Missing token"}

        tok = frappe.get_all("AlphaX POS QR Table Token",
                             filters={"token": token, "is_active": 1},
                             fields=["name", "table"])
        if not tok:
            return {"ok": False, "message": "Invalid / inactive table token"}

        table = tok[0]["table"]
        # Create POS Order (Draft)
        order = frappe.new_doc("AlphaX POS Order")
        order.table = table
        order.customer_name = customer_name
        order.order_source = "QR"
        order.status = "Draft"
        for row in items:
            if not row or not row.get("item_code"):
                continue
            it = order.append("items", {})
            it.item_code = row.get("item_code")
            it.qty = float(row.get("qty") or 1)
        order.insert(ignore_permissions=True)

        frappe.db.set_value("AlphaX POS QR Table Token", tok[0]["name"], "last_used_on", now_datetime())

        return {"ok": True, "order": order.name}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Bonanza QR Order Failed")
        return {"ok": False, "message": str(e)}

@frappe.whitelist()
def compute_recipe_cost(item_code: str):
    """Compute recipe cost for a sellable item using AlphaX POS Recipe.
    Fallbacks to Item.valuation_rate where available.
    """
    if not item_code:
        return {"ok": False, "message": "Missing item_code"}

    rec = frappe.get_all("AlphaX POS Recipe", filters={"item": item_code}, fields=["name"])
    if not rec:
        # fallback valuation_rate
        val = frappe.db.get_value("Item", item_code, "valuation_rate") or 0
        return {"ok": True, "item_code": item_code, "recipe": None, "cost": float(val or 0)}

    recipe = frappe.get_doc("AlphaX POS Recipe", rec[0]["name"])
    total = 0.0
    for r in recipe.items or []:
        rate = frappe.db.get_value("Item", r.item_code, "valuation_rate") or 0
        total += float(r.qty or 0) * float(rate or 0)
    return {"ok": True, "item_code": item_code, "recipe": recipe.name, "cost": total}

@frappe.whitelist()
def create_central_kitchen_request(outlet: str, items, from_warehouse: str = None, to_warehouse: str = None, reference_sales_invoice: str = None):
    """Create a Central Kitchen Request (Draft) from POS sales/recipe demand."""
    try:
        if isinstance(items, str):
            items = json.loads(items or "[]")
        items = items or []
        doc = frappe.new_doc("AlphaX POS Central Kitchen Request")
        doc.outlet = outlet
        doc.from_warehouse = from_warehouse
        doc.to_warehouse = to_warehouse
        doc.reference_sales_invoice = reference_sales_invoice
        doc.status = "Draft"
        for row in items:
            if not row or not row.get("item_code"):
                continue
            it = doc.append("items", {})
            it.item_code = row.get("item_code")
            it.qty = float(row.get("qty") or 1)
            it.uom = row.get("uom")
        doc.insert(ignore_permissions=True)
        # Auto-create ERPNext Material Request if integration is enabled
        try:
            create_material_request_from_ck_request(doc.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Auto MR Failed")
        return {"ok": True, "request": doc.name, "material_request": getattr(doc, 'erpnext_material_request', None)}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Central Kitchen Request Failed")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def fulfill_central_kitchen_request(request_name: str):
    """Marks Central Kitchen Request as Fulfilled and (optionally) creates ERPNext Stock Entry."""
    try:
        if not request_name or not frappe.db.exists("AlphaX POS Central Kitchen Request", request_name):
            frappe.throw(_("Central Kitchen Request not found."))
        se = None
        try:
            se = create_stock_entry_from_ck_request(request_name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Auto Stock Entry Failed")
        # Ensure status updated even if ERPNext not available
        req = frappe.get_doc("AlphaX POS Central Kitchen Request", request_name)
        if (req.status or "") != "Fulfilled":
            req.status = "Fulfilled"
            req.fulfilled_on = frappe.utils.now_datetime()
            req.save(ignore_permissions=True)
        return {"ok": True, "stock_entry": se, "status": "Fulfilled"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fulfill Central Kitchen Request Failed")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def create_material_request_for_central_kitchen_request(request_name: str):
    """Manually create ERPNext Material Request for a Central Kitchen Request.

    This will run only when ERPNext is installed and Central Kitchen integration is enabled.
    It ignores the 'auto-create MR' toggle (i.e., force=True) so that managers can create
    an MR on-demand.
    """
    try:
        if not request_name or not frappe.db.exists("AlphaX POS Central Kitchen Request", request_name):
            frappe.throw(_("Central Kitchen Request not found."))

        mr = create_material_request_from_ck_request(request_name, force=True)
        if not mr:
            return {
                "ok": False,
                "message": _("Material Request was not created. Please ensure ERPNext is installed and Central Kitchen integration is enabled in AlphaX POS Settings."),
            }
        return {"ok": True, "material_request": mr}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Material Request (Central Kitchen) Failed")
        return {"ok": False, "message": str(e)}


@frappe.whitelist()
def dispatch_central_kitchen_request(request_name: str, notes: str = None):
    """Mark Central Kitchen Request as Dispatched (does not create Stock Entry)."""
    try:
        if not request_name or not frappe.db.exists('AlphaX POS Central Kitchen Request', request_name):
            frappe.throw(_('Central Kitchen Request not found.'))
        req = frappe.get_doc('AlphaX POS Central Kitchen Request', request_name)
        if req.docstatus != 1:
            frappe.throw(_('Request must be submitted before dispatching.'))
        if (req.status or '') == 'Fulfilled':
            return {'ok': True, 'status': 'Fulfilled', 'message': _('Already fulfilled.')}
        if (req.status or '') != 'Dispatched':
            req.status = 'Dispatched'
            req.dispatched_on = frappe.utils.now_datetime()
            req.dispatched_by = frappe.session.user
            if notes is not None:
                req.dispatch_notes = notes
            req.save(ignore_permissions=True)
        return {'ok': True, 'status': req.status}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Dispatch Central Kitchen Request Failed')
        return {'ok': False, 'message': str(e)}


@frappe.whitelist()
def get_central_kitchen_dashboard_data():
    """Lightweight dashboard stats for Central Kitchen."""
    try:
        from frappe.utils import nowdate
        today = nowdate()
        doctype = 'AlphaX POS Central Kitchen Request'
        # counts
        today_total = frappe.db.count(doctype, {'creation': ['>=', today + ' 00:00:00']})
        submitted = frappe.db.count(doctype, {'status': 'Submitted'})
        dispatched = frappe.db.count(doctype, {'status': 'Dispatched'})
        fulfilled = frappe.db.count(doctype, {'status': 'Fulfilled'})

        latest = frappe.get_all(doctype, fields=['name', 'status', 'outlet'], order_by='modified desc', limit_page_length=10)
        # indicator map compatible with list view
        ind = {'Fulfilled': 'green', 'Dispatched': 'blue', 'Submitted': 'orange', 'Cancelled': 'red'}
        for r in latest:
            r['indicator'] = ind.get(r.get('status'), 'gray')
        return {
            'ok': True,
            'today_total': today_total,
            'submitted': submitted,
            'dispatched': dispatched,
            'fulfilled': fulfilled,
            'latest': latest
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Central Kitchen Dashboard Failed')
        return {'ok': False, 'message': str(e)}
