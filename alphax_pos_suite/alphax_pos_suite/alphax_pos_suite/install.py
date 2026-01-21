import frappe


def after_install():
    """Run once after app install.

    We create the minimum required Roles and Custom Fields in code to avoid
    fixture-import issues on Frappe Cloud.
    """
    create_roles()
    create_custom_fields()


def create_roles():
    roles = [
        "AlphaX POS Cashier",
        "AlphaX POS Supervisor",
        "AlphaX POS Manager",
    ]

    for r in roles:
        if frappe.db.exists("Role", r):
            continue
        doc = frappe.new_doc("Role")
        doc.role_name = r
        doc.insert(ignore_permissions=True)


def create_custom_fields():
    """Create custom fields required by AlphaX POS Suite.

    Uses create_custom_field helper so re-install / patch is safe.
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    fields = [
        # Mode of Payment
        {
            "dt": "Mode of Payment",
            "fieldname": "alphax_capture_terminal_data",
            "label": "Capture Terminal Data",
            "fieldtype": "Check",
            "insert_after": "type",
            "default": 0,
        },
        {
            "dt": "Mode of Payment",
            "fieldname": "alphax_terminal_settings",
            "label": "Terminal Settings",
            "fieldtype": "Link",
            "options": "AlphaX POS Payment Terminal Settings",
            "insert_after": "alphax_capture_terminal_data",
        },
        {
            "dt": "Mode of Payment",
            "fieldname": "alphax_require_terminal_approval",
            "label": "Require Terminal Approval",
            "fieldtype": "Check",
            "insert_after": "alphax_terminal_settings",
            "default": 1,
        },
        {
            "dt": "Mode of Payment",
            "fieldname": "alphax_allow_manual_ref",
            "label": "Allow Manual Reference (Fallback)",
            "fieldtype": "Check",
            "insert_after": "alphax_require_terminal_approval",
            "default": 0,
        },

        # Item
        {
            "dt": "Item",
            "fieldname": "alphax_is_weighing_item",
            "label": "Is Weighing Item",
            "fieldtype": "Check",
            "insert_after": "is_stock_item",
            "default": 0,
        },
        {
            "dt": "Item",
            "fieldname": "alphax_scale_barcode_prefix",
            "label": "Scale Barcode Prefix",
            "fieldtype": "Data",
            "insert_after": "alphax_is_weighing_item",
        },

        # Sales Invoice Payment child table
        {
            "dt": "Sales Invoice Payment",
            "fieldname": "alphax_card_txn_id",
            "label": "Card Transaction",
            "fieldtype": "Link",
            "options": "AlphaX POS Card Transaction",
            "insert_after": "amount",
            "read_only": 1,
        },
        {
            "dt": "Sales Invoice Payment",
            "fieldname": "alphax_card_capture_time",
            "label": "Card Capture Time",
            "fieldtype": "Datetime",
            "insert_after": "alphax_card_txn_id",
            "read_only": 1,
        },
        {
            "dt": "Sales Invoice Payment",
            "fieldname": "alphax_rrn",
            "label": "RRN",
            "fieldtype": "Data",
            "insert_after": "alphax_card_capture_time",
            "read_only": 1,
        },
        {
            "dt": "Sales Invoice Payment",
            "fieldname": "alphax_auth_code",
            "label": "Auth Code",
            "fieldtype": "Data",
            "insert_after": "alphax_rrn",
            "read_only": 1,
        },
    ]

    for f in fields:
        dt = f.pop("dt")
        fieldname = f.get("fieldname")
        # create_custom_field is idempotent (creates if missing)
        try:
            create_custom_field(dt, f, ignore_validate=True)
        except TypeError:
            # for older frappe versions that don't accept ignore_validate
            create_custom_field(dt, f)
        except Exception:
            # don't block install due to a single field conflict
            frappe.log_error(
                title="AlphaX POS Suite: create_custom_fields failed",
                message=f"Failed creating field {dt}.{fieldname}",
            )
