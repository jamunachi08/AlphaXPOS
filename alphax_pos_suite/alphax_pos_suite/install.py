import json
import os

import frappe


def after_install():
    """Create required setup objects for AlphaX POS Suite."""
    create_roles()
    create_custom_fields()
    create_workspace()
    create_role_profiles()
    apply_permissions()


def _safe_insert(doc_dict):
    """Insert a doc if it doesn't already exist."""
    if not doc_dict.get("doctype"):
        return
    name = doc_dict.get("name")
    if name and frappe.db.exists(doc_dict["doctype"], name):
        return
    try:
        frappe.get_doc(doc_dict).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), title=f"AlphaX POS install: failed inserting {doc_dict.get('doctype')}")


def create_roles():
    """Create POS roles used for UI permission gating."""
    roles = [
        "AlphaX POS Cashier",
        "AlphaX POS Supervisor",
        "AlphaX POS Manager",
    ]

    for role in roles:
        if not frappe.db.exists("Role", role):
            doc = frappe.get_doc({"doctype": "Role", "role_name": role})
            doc.insert(ignore_permissions=True)


def create_role_profiles():
    """Optional role profiles to speed user setup."""
    if not frappe.db.exists("DocType", "Role Profile"):
        return

    profiles = [
        {
            "doctype": "Role Profile",
            "role_profile": "AlphaX POS - Cashier",
            "roles": [{"role": "AlphaX POS Cashier"}],
        },
        {
            "doctype": "Role Profile",
            "role_profile": "AlphaX POS - Supervisor",
            "roles": [{"role": "AlphaX POS Supervisor"}, {"role": "AlphaX POS Cashier"}],
        },
        {
            "doctype": "Role Profile",
            "role_profile": "AlphaX POS - Manager",
            "roles": [
                {"role": "AlphaX POS Manager"},
                {"role": "AlphaX POS Supervisor"},
                {"role": "AlphaX POS Cashier"},
            ],
        },
    ]
    for p in profiles:
        if not frappe.db.exists("Role Profile", p["role_profile"]):
            _safe_insert(p)


def create_workspace():
    """Create a workspace with shortcuts for Bonanza POS."""
    if not frappe.db.exists("DocType", "Workspace"):
        return
    ws_name = "AlphaX Bonanza POS"
    if frappe.db.exists("Workspace", ws_name):
        return

    shortcuts = [
        {"type": "doctype", "label": "POS Settings", "link_to": "AlphaX POS Settings"},
        {"type": "page", "label": "Setup Wizard", "link_to": "alphax-pos-setup"},
        {"type": "doctype", "label": "POS Terminal", "link_to": "AlphaX POS Terminal"},
        {"type": "doctype", "label": "POS Floor", "link_to": "AlphaX POS Floor"},
        {"type": "doctype", "label": "POS Table", "link_to": "AlphaX POS Table"},
        {"type": "doctype", "label": "POS Recipe", "link_to": "AlphaX POS Recipe"},
        {"type": "doctype", "label": "Processing Log", "link_to": "AlphaX POS Processing Log"},
        {"type": "doctype", "label": "Card Transactions", "link_to": "AlphaX POS Card Transaction"},
    ]

    ws = {
        "doctype": "Workspace",
        "name": ws_name,
        "title": ws_name,
        "module": "AlphaX POS Suite",
        "icon": "pos",
        "is_standard": 0,
        "content": [],
        "sequence_id": 99,
        "shortcuts": shortcuts,
    }
    _safe_insert(ws)


def apply_permissions():
    """Apply basic permissions to core suite doctypes using Custom DocPerm."""
    if not frappe.db.exists("DocType", "Custom DocPerm"):
        return

    # Minimal set: settings + key operational doctypes
    perm_map = {
        "AlphaX POS Settings": {
            "AlphaX POS Manager": {"read": 1, "write": 1, "create": 1, "delete": 0, "submit": 0, "cancel": 0},
            "AlphaX POS Supervisor": {"read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0},
            "AlphaX POS Cashier": {"read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0},
        },
        "AlphaX POS Processing Log": {
            "AlphaX POS Manager": {"read": 1, "write": 1, "create": 1, "delete": 0},
            "AlphaX POS Supervisor": {"read": 1, "write": 0, "create": 0, "delete": 0},
            "AlphaX POS Cashier": {"read": 0, "write": 0, "create": 0, "delete": 0},
        },
    }

    for doctype, roles in perm_map.items():
        for role, perms in roles.items():
            if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
                continue
            d = {
                "doctype": "Custom DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": 0,
            }
            d.update(perms)
            try:
                frappe.get_doc(d).insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), title=f"AlphaX POS install: failed custom perm {doctype} / {role}")


def _seed_custom_fields():
    seed_path = os.path.join(os.path.dirname(__file__), "data", "custom_fields_seed.json")
    if not os.path.exists(seed_path):
        return []
    with open(seed_path, encoding="utf-8") as f:
        return json.load(f)


def create_custom_fields():
    """Create Custom Fields required by the suite."""
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except Exception:
        return

    for row in _seed_custom_fields():
        if row.get("doctype") != "Custom Field":
            continue

        dt = row.get("dt")
        fieldname = row.get("fieldname")
        if not dt or not fieldname:
            continue

        if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
            continue

        df = dict(row)
        df.pop("doctype", None)
        df.pop("dt", None)

        # create_custom_field signature differs slightly across versions
        try:
            create_custom_field(dt, df, ignore_validate=True)
        except TypeError:
            create_custom_field(dt, df)
