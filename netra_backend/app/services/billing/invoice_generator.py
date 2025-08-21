"""Invoice Generator for creating and formatting invoices."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class InvoiceTemplate:
    """Invoice template configuration."""
    template_id: str
    name: str
    format_type: str  # pdf, html, json
    header_info: Dict[str, Any]
    footer_info: Dict[str, Any]
    styling: Dict[str, Any]


class InvoiceGenerator:
    """Generates invoices from bills in various formats."""
    
    def __init__(self):
        """Initialize invoice generator."""
        self.templates = {
            "default": InvoiceTemplate(
                template_id="default",
                name="Default Invoice Template",
                format_type="json",
                header_info={
                    "company_name": "Netra Apex AI",
                    "company_address": "123 AI Street, Tech City, TC 12345",
                    "company_email": "billing@netra-apex.ai",
                    "company_phone": "+1 (555) 123-4567"
                },
                footer_info={
                    "payment_terms": "Payment due within 30 days",
                    "late_fee": "1.5% monthly late fee applies",
                    "support_email": "support@netra-apex.ai"
                },
                styling={
                    "primary_color": "#2563eb",
                    "secondary_color": "#64748b",
                    "font_family": "Inter, sans-serif"
                }
            )
        }
        
        self.generated_invoices: Dict[str, Dict[str, Any]] = {}
        self.enabled = True
    
    async def generate_invoice(self, bill, template_id: str = "default", 
                             format_type: str = "json") -> Dict[str, Any]:
        """Generate an invoice from a bill."""
        if not self.enabled:
            raise RuntimeError("Invoice generator is disabled")
        
        template = self.templates.get(template_id)
        if not template:
            template = self.templates["default"]
        
        invoice_id = f"INV-{bill.bill_id}"
        
        invoice_data = {
            "invoice_id": invoice_id,
            "bill_id": bill.bill_id,
            "invoice_number": self._generate_invoice_number(bill),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "template_id": template.template_id,
            "format_type": format_type,
            
            # Company information
            "company": template.header_info,
            
            # Customer information
            "customer": {
                "user_id": bill.user_id,
                "customer_id": bill.user_id,
                "name": f"Customer {bill.user_id}",
                "email": f"user{bill.user_id}@example.com"
            },
            
            # Billing period
            "period": {
                "start": bill.period_start.isoformat(),
                "end": bill.period_end.isoformat(),
                "description": self._format_period_description(bill.period_start, bill.period_end)
            },
            
            # Line items
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "usage_type": item.usage_type,
                    "period": {
                        "start": item.period_start.isoformat(),
                        "end": item.period_end.isoformat()
                    }
                }
                for item in bill.line_items
            ],
            
            # Totals
            "totals": {
                "subtotal": float(bill.subtotal),
                "tax_amount": float(bill.tax_amount),
                "total_amount": float(bill.total_amount),
                "currency": "USD"
            },
            
            # Payment information
            "payment": {
                "due_date": bill.due_date.isoformat(),
                "status": bill.status.value,
                "paid_at": bill.paid_at.isoformat() if bill.paid_at else None,
                "payment_methods": ["credit_card", "bank_transfer", "paypal"]
            },
            
            # Footer information
            "footer": template.footer_info,
            
            # Styling (for HTML/PDF formats)
            "styling": template.styling,
            
            # Metadata
            "metadata": bill.metadata or {}
        }
        
        # Generate formatted output based on format type
        if format_type == "html":
            formatted_output = await self._generate_html_invoice(invoice_data)
        elif format_type == "pdf":
            formatted_output = await self._generate_pdf_invoice(invoice_data)
        else:
            formatted_output = invoice_data
        
        # Store generated invoice
        self.generated_invoices[invoice_id] = {
            "invoice_data": invoice_data,
            "formatted_output": formatted_output,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "invoice_id": invoice_id,
            "format_type": format_type,
            "data": formatted_output,
            "download_url": f"/api/invoices/{invoice_id}/download?format={format_type}"
        }
    
    async def get_invoice(self, invoice_id: str, format_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a generated invoice."""
        if invoice_id not in self.generated_invoices:
            return None
        
        invoice = self.generated_invoices[invoice_id]
        
        if format_type and format_type != invoice["invoice_data"]["format_type"]:
            # Regenerate in requested format
            invoice_data = invoice["invoice_data"]
            if format_type == "html":
                formatted_output = await self._generate_html_invoice(invoice_data)
            elif format_type == "pdf":
                formatted_output = await self._generate_pdf_invoice(invoice_data)
            else:
                formatted_output = invoice_data
            
            return {
                "invoice_id": invoice_id,
                "format_type": format_type,
                "data": formatted_output
            }
        
        return {
            "invoice_id": invoice_id,
            "format_type": invoice["invoice_data"]["format_type"],
            "data": invoice["formatted_output"]
        }
    
    async def list_invoices(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List generated invoices."""
        invoices = []
        
        for invoice_id, invoice in self.generated_invoices.items():
            invoice_data = invoice["invoice_data"]
            
            if user_id and invoice_data["customer"]["user_id"] != user_id:
                continue
            
            invoices.append({
                "invoice_id": invoice_id,
                "bill_id": invoice_data["bill_id"],
                "invoice_number": invoice_data["invoice_number"],
                "user_id": invoice_data["customer"]["user_id"],
                "total_amount": invoice_data["totals"]["total_amount"],
                "status": invoice_data["payment"]["status"],
                "due_date": invoice_data["payment"]["due_date"],
                "created_at": invoice_data["created_at"],
                "format_type": invoice_data["format_type"]
            })
        
        # Sort by creation date (newest first)
        return sorted(invoices, key=lambda i: i["created_at"], reverse=True)
    
    def _generate_invoice_number(self, bill) -> str:
        """Generate a formatted invoice number."""
        # Format: YYYY-MM-NNNNNN
        date_part = bill.created_at.strftime("%Y%m")
        sequence = len(self.generated_invoices) + 1
        return f"{date_part}-{sequence:06d}"
    
    def _format_period_description(self, start: datetime, end: datetime) -> str:
        """Format billing period description."""
        if start.month == end.month and start.year == end.year:
            return f"{start.strftime('%B %Y')}"
        else:
            return f"{start.strftime('%B %d, %Y')} - {end.strftime('%B %d, %Y')}"
    
    async def _generate_html_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """Generate HTML invoice."""
        # Simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Invoice {invoice_data['invoice_number']}</title>
            <style>
                body {{ font-family: {invoice_data['styling']['font_family']}; }}
                .header {{ color: {invoice_data['styling']['primary_color']}; }}
                .total {{ font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>INVOICE</h1>
                <h2>{invoice_data['company']['company_name']}</h2>
                <p>{invoice_data['company']['company_address']}</p>
            </div>
            
            <div class="invoice-details">
                <p><strong>Invoice Number:</strong> {invoice_data['invoice_number']}</p>
                <p><strong>Date:</strong> {invoice_data['created_at'][:10]}</p>
                <p><strong>Due Date:</strong> {invoice_data['payment']['due_date'][:10]}</p>
                <p><strong>Customer ID:</strong> {invoice_data['customer']['user_id']}</p>
            </div>
            
            <table>
                <thead>
                    <tr><th>Description</th><th>Quantity</th><th>Unit Price</th><th>Total</th></tr>
                </thead>
                <tbody>
        """
        
        for item in invoice_data['line_items']:
            html += f"""
                    <tr>
                        <td>{item['description']}</td>
                        <td>{item['quantity']}</td>
                        <td>${item['unit_price']:.4f}</td>
                        <td>${item['total_price']:.2f}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            
            <div class="totals">
                <p>Subtotal: ${invoice_data['totals']['subtotal']:.2f}</p>
                <p>Tax: ${invoice_data['totals']['tax_amount']:.2f}</p>
                <p class="total">Total: ${invoice_data['totals']['total_amount']:.2f}</p>
            </div>
            
            <div class="footer">
                <p>{invoice_data['footer']['payment_terms']}</p>
                <p>Support: {invoice_data['company']['company_email']}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def _generate_pdf_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """Generate PDF invoice (returns base64 encoded PDF)."""
        # For now, return HTML as placeholder
        # In production, would use library like weasyprint or reportlab
        html_content = await self._generate_html_invoice(invoice_data)
        
        # Simulate PDF generation
        import base64
        pdf_placeholder = f"PDF Invoice {invoice_data['invoice_number']}"
        return base64.b64encode(pdf_placeholder.encode()).decode()
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available invoice templates."""
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "format_type": template.format_type
            }
            for template in self.templates.values()
        ]
    
    def add_template(self, template: InvoiceTemplate) -> None:
        """Add a new invoice template."""
        self.templates[template.template_id] = template
    
    def get_stats(self) -> Dict[str, Any]:
        """Get invoice generator statistics."""
        format_counts = {}
        for invoice in self.generated_invoices.values():
            format_type = invoice["invoice_data"]["format_type"]
            format_counts[format_type] = format_counts.get(format_type, 0) + 1
        
        return {
            "enabled": self.enabled,
            "total_invoices": len(self.generated_invoices),
            "templates_available": len(self.templates),
            "invoices_by_format": format_counts
        }
