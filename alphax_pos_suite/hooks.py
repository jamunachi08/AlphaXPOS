app_name = "alphax_pos_suite"
app_title = "AlphaX Bonanza POS Pack"
app_publisher = "AlphaX"
app_description = "Bonanza POS Pack (XPOS + αPOS): unified Restaurant/Cafe/Retail POS extensions for ERPNext"
app_email = "support@alphax.local"
app_license = "MIT"

# NOTE:
# We intentionally do NOT ship Role / Custom Field as fixtures because the
# standard fixture importer expects full exported docs including a `name`.
# Instead, we create required Roles & Custom Fields during app installation.
fixtures = [
    "Print Format",
]

# Create required roles / custom fields programmatically
after_install = "alphax_pos_suite.alphax_pos_suite.install.after_install"

doc_events = {
    "Sales Invoice": {
        "validate": "alphax_pos_suite.alphax_pos_suite.integrations.card_capture.sales_invoice_validate",
        "before_submit": "alphax_pos_suite.alphax_pos_suite.integrations.card_capture.sales_invoice_before_submit",
        "on_submit": [
            "alphax_pos_suite.alphax_pos_suite.integrations.card_capture.sales_invoice_on_submit",
            "alphax_pos_suite.alphax_pos_suite.pos.processing.on_sales_invoice_submit",
        ]
    },
    "AlphaX POS Order": {
        "on_submit": "alphax_pos_suite.alphax_pos_suite.pos.posting.on_order_submit",
        "on_cancel": "alphax_pos_suite.alphax_pos_suite.pos.posting.on_order_cancel",
    }
}

scheduler_events = {
    "daily": [
        "alphax_pos_suite.alphax_pos_suite.pos.maintenance.daily_cleanup",
    ]
}

app_include_js = [
    "/assets/alphax_pos_suite/js/sales_invoice_terminal_capture.js",
    "/assets/alphax_pos_suite/js/bonanza_pos_warnings.js",
]


website_route_rules = [
    {"from_route": "/bonanza/order/<token>", "to_route": "bonanza_order"},
]
