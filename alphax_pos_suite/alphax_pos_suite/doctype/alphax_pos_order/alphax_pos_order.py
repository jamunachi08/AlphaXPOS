import frappe
from frappe.model.document import Document

class AlphaXPOSOrder(Document):
    def before_insert(self):
        if not getattr(self, "client_uuid", None):
            self.client_uuid = frappe.generate_hash(length=20)
