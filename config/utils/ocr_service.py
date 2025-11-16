"""
AWS Textract OCR Service for KinWise Family Finance App

Provides receipt and bill scanning with NZ-specific retailer recognition.
Complies with Privacy Act 2020 and brand requirements:
- <3 second processing target
- >95% accuracy for major NZ retailers
- Data processed in ap-southeast-2 (Sydney)
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Constants
ERROR_SERVICE_DISABLED = "AWS Textract service is not enabled"


class AWSTextractService:
    """
    Service for extracting text and structured data from receipts and bills
    using AWS Textract.
    """

    def __init__(self):
        """Initialize AWS Textract client."""
        if not settings.AWS_TEXTRACT_ENABLED:
            logger.warning(
                "AWS Textract is disabled. Set AWS_TEXTRACT_ENABLED=True to enable."
            )
            self.client = None
            return

        try:
            import boto3

            self.client = boto3.client(
                "textract",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            logger.info(
                f"AWS Textract client initialized in region {settings.AWS_REGION}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize AWS Textract client: {e}")
            self.client = None

    def is_enabled(self) -> bool:
        """Check if Textract service is available."""
        return self.client is not None and settings.AWS_TEXTRACT_ENABLED

    def validate_image(self, image_bytes: bytes) -> None:
        """
        Validate image size and format.

        Args:
            image_bytes: Raw image data

        Raises:
            ValidationError: If image is invalid
        """
        if not image_bytes:
            raise ValidationError("Image data is empty")

        file_size = len(image_bytes)
        max_size = settings.AWS_TEXTRACT_MAX_FILE_SIZE

        if file_size > max_size:
            raise ValidationError(
                f"Image size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

    def extract_text(self, image_bytes: bytes) -> Dict[str, any]:
        """
        Extract plain text from an image using Textract's detect_document_text.

        Args:
            image_bytes: Raw image data

        Returns:
            Dict with extracted text and metadata

        Raises:
            ValidationError: If service is disabled or image is invalid
        """
        if not self.is_enabled():
            raise ValidationError(ERROR_SERVICE_DISABLED)

        self.validate_image(image_bytes)

        try:
            response = self.client.detect_document_text(Document={"Bytes": image_bytes})

            # Extract all text lines
            lines = []
            full_text = []

            for block in response.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    text = block.get("Text", "")
                    lines.append(
                        {"text": text, "confidence": block.get("Confidence", 0)}
                    )
                    full_text.append(text)

            return {
                "success": True,
                "full_text": "\n".join(full_text),
                "lines": lines,
                "block_count": len(response.get("Blocks", [])),
                "raw_response": response,
            }

        except Exception as e:
            logger.error(f"Textract detect_document_text error: {e}")
            return {"success": False, "error": str(e), "full_text": "", "lines": []}

    def extract_receipt_data(self, image_bytes: bytes) -> Dict[str, any]:
        """
        Extract structured receipt data using Textract's analyze_expense.
        Optimized for NZ retailers with smart field extraction.

        Args:
            image_bytes: Raw image data

        Returns:
            Dict with structured receipt data:
            - merchant_name
            - total_amount
            - date
            - items (list)
            - tax_amount
            - payment_method
            - confidence_scores

        Raises:
            ValidationError: If service is disabled or image is invalid
        """
        if not self.is_enabled():
            raise ValidationError(ERROR_SERVICE_DISABLED)

        self.validate_image(image_bytes)

        try:
            response = self.client.analyze_expense(Document={"Bytes": image_bytes})

            parsed_data = self._parse_expense_response(response)

            # Enhance with NZ-specific processing
            parsed_data = self._enhance_nz_data(parsed_data)

            return {"success": True, **parsed_data, "raw_response": response}

        except Exception as e:
            logger.error(f"Textract analyze_expense error: {e}")
            return {
                "success": False,
                "error": str(e),
                "merchant_name": None,
                "total_amount": None,
                "date": None,
                "items": [],
                "tax_amount": None,
            }

    def extract_bill_data(self, image_bytes: bytes) -> Dict[str, any]:
        """
        Extract structured bill/invoice data.
        Specialized for utility bills, invoices, and recurring payments.

        Args:
            image_bytes: Raw image data

        Returns:
            Dict with structured bill data:
            - provider_name
            - bill_type (electricity, water, internet, etc.)
            - account_number
            - due_date
            - amount_due
            - billing_period
            - previous_balance

        Raises:
            ValidationError: If service is disabled or image is invalid
        """
        if not self.is_enabled():
            raise ValidationError(ERROR_SERVICE_DISABLED)

        self.validate_image(image_bytes)

        try:
            # Use analyze_expense for bills too
            response = self.client.analyze_expense(Document={"Bytes": image_bytes})

            parsed_data = self._parse_expense_response(response)

            # Convert to bill-specific format
            bill_data = self._convert_to_bill_format(parsed_data, response)

            return {"success": True, **bill_data, "raw_response": response}

        except Exception as e:
            logger.error(f"Textract bill extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider_name": None,
                "bill_type": None,
                "amount_due": None,
                "due_date": None,
            }

    def _parse_expense_response(self, response: Dict) -> Dict[str, any]:
        """Parse Textract analyze_expense response into structured data."""
        result = {
            "merchant_name": None,
            "total_amount": None,
            "date": None,
            "items": [],
            "tax_amount": None,
            "subtotal": None,
            "payment_method": None,
            "confidence_scores": {},
        }

        expense_documents = response.get("ExpenseDocuments", [])
        if not expense_documents:
            return result

        expense_doc = expense_documents[0]

        # Extract summary fields
        summary_fields = expense_doc.get("SummaryFields", [])
        for field in summary_fields:
            self._process_summary_field(field, result)

        # Extract line items
        line_items = expense_doc.get("LineItemGroups", [])
        for group in line_items:
            for item in group.get("LineItems", []):
                item_data = self._process_line_item(item)
                if item_data:
                    result["items"].append(item_data)

        return result

    def _process_summary_field(self, field: Dict, result: Dict) -> None:
        """Process a single summary field from Textract response."""
        field_type = field.get("Type", {}).get("Text", "")
        value_detection = field.get("ValueDetection", {})
        value = value_detection.get("Text", "")
        confidence = value_detection.get("Confidence", 0)

        if field_type in ("VENDOR_NAME", "NAME"):
            result["merchant_name"] = value
            result["confidence_scores"]["merchant"] = confidence
        elif field_type in ("TOTAL", "AMOUNT_PAID"):
            result["total_amount"] = self._parse_amount(value)
            result["confidence_scores"]["total"] = confidence
        elif field_type in ("INVOICE_RECEIPT_DATE", "DATE"):
            result["date"] = self._parse_date(value)
            result["confidence_scores"]["date"] = confidence
        elif field_type in ("TAX", "GST"):
            result["tax_amount"] = self._parse_amount(value)
        elif field_type == "SUBTOTAL":
            result["subtotal"] = self._parse_amount(value)
        elif field_type == "PAYMENT_METHOD":
            result["payment_method"] = value

    def _process_line_item(self, item: Dict) -> Dict[str, any]:
        """Process a single line item from Textract response."""
        item_data = {}
        for field in item.get("LineItemExpenseFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")

            if field_type == "ITEM":
                item_data["description"] = value
            elif field_type == "PRICE":
                item_data["amount"] = self._parse_amount(value)
            elif field_type == "QUANTITY":
                item_data["quantity"] = value

        return item_data

    def _convert_to_bill_format(self, parsed_data: Dict, response: Dict) -> Dict:
        """Convert receipt data to bill-specific format."""
        bill_data = {
            "provider_name": parsed_data.get("merchant_name"),
            "bill_type": self._detect_bill_type(parsed_data, response),
            "account_number": None,
            "due_date": parsed_data.get("date"),
            "amount_due": parsed_data.get("total_amount"),
            "billing_period": None,
            "previous_balance": None,
            "confidence_scores": parsed_data.get("confidence_scores", {}),
        }

        # Try to extract additional bill-specific fields from raw text
        full_text = self._extract_full_text(response)

        # Extract account number
        account_match = re.search(
            r"(?:account|a/c|acct)[\s#:]*([0-9\-]+)", full_text, re.IGNORECASE
        )
        if account_match:
            bill_data["account_number"] = account_match.group(1)

        # Extract due date
        due_date_match = re.search(
            r"(?:due date|payment due|pay by)[\s:]*([0-9\/\-]+)",
            full_text,
            re.IGNORECASE,
        )
        if due_date_match:
            bill_data["due_date"] = self._parse_date(due_date_match.group(1))

        return bill_data

    def _detect_bill_type(self, parsed_data: Dict, response: Dict) -> Optional[str]:
        """Detect type of bill based on merchant name and content."""
        merchant = (parsed_data.get("merchant_name") or "").lower()
        full_text = self._extract_full_text(response).lower()

        # NZ-specific utility providers
        if any(
            provider in merchant or provider in full_text
            for provider in [
                "contact energy",
                "genesis",
                "meridian",
                "mercury",
                "electric kiwi",
            ]
        ):
            return "electricity"
        elif any(
            provider in merchant or provider in full_text
            for provider in ["spark", "vodafone", "2degrees", "skinny"]
        ):
            return "phone"
        elif any(
            provider in merchant or provider in full_text
            for provider in [
                "watercare",
                "wellington water",
                "christchurch city council",
            ]
        ):
            return "water"
        elif any(
            provider in merchant or provider in full_text
            for provider in ["sky", "netflix", "spotify"]
        ):
            return "entertainment"
        elif "internet" in full_text or "broadband" in full_text:
            return "internet"
        elif "insurance" in full_text:
            return "insurance"
        elif "rent" in full_text or "tenancy" in full_text:
            return "rent"

        return "other"

    def _enhance_nz_data(self, parsed_data: Dict) -> Dict:
        """Enhance parsed data with NZ-specific processing."""
        # Normalize merchant names for major NZ retailers
        merchant = parsed_data.get("merchant_name", "")
        if merchant:
            merchant_lower = merchant.lower()

            # Major NZ retailers normalization
            nz_retailers = {
                "countdown": "Countdown",
                "pak n save": "Pak'nSave",
                "new world": "New World",
                "the warehouse": "The Warehouse",
                "z energy": "Z Energy",
                "bp": "BP",
                "mobil": "Mobil",
                "kmart": "Kmart",
                "bunnings": "Bunnings",
                "mitre 10": "Mitre 10",
            }

            for key, normalized in nz_retailers.items():
                if key in merchant_lower:
                    parsed_data["merchant_name"] = normalized
                    parsed_data["merchant_normalized"] = True
                    break

        # Ensure GST is identified (NZ-specific)
        if parsed_data.get("tax_amount") is None and parsed_data.get("total_amount"):
            # Try to calculate GST from total (15% in NZ)
            try:
                total = Decimal(str(parsed_data["total_amount"]))
                gst = total * Decimal("0.15") / Decimal("1.15")
                parsed_data["tax_amount"] = float(gst.quantize(Decimal("0.01")))
                parsed_data["tax_calculated"] = True
            except (InvalidOperation, TypeError):
                pass

        return parsed_data

    def _extract_full_text(self, response: Dict) -> str:
        """Extract all text from Textract response."""
        text_lines = []

        for doc in response.get("ExpenseDocuments", []):
            for block in doc.get("Blocks", []):
                if block.get("BlockType") == "LINE":
                    text_lines.append(block.get("Text", ""))

        return "\n".join(text_lines)

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float, handling various formats."""
        if not amount_str:
            return None

        try:
            # Remove currency symbols and whitespace
            cleaned = re.sub(r"[^\d.,\-]", "", amount_str)
            # Handle comma as thousand separator
            cleaned = cleaned.replace(",", "")
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date().isoformat()
            except ValueError:
                continue

        return None


# Singleton instance
_textract_service = None


def get_textract_service() -> AWSTextractService:
    """Get or create singleton Textract service instance."""
    global _textract_service
    if _textract_service is None:
        _textract_service = AWSTextractService()
    return _textract_service
