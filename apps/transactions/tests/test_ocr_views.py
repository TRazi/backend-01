"""
Tests for OCR Receipt and Bill Processing
Tests AWS Textract integration, async processing, and API endpoints
"""

import io
import hashlib
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from PIL import Image

from apps.transactions.models_attachments import ReceiptAttachment, BillAttachment, ReceiptLineItem
from apps.transactions.views_ocr import (
    ReceiptOCRViewSet,
    BillOCRViewSet,
    process_receipt_async,
    process_bill_async,
)
from config.utils.ocr_service import get_textract_service

User = get_user_model()


def create_test_image():
    """Create a simple test image file."""
    from io import BytesIO
    
    # Create a simple RGB image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return SimpleUploadedFile(
        "test_receipt.png",
        img_bytes.getvalue(),
        content_type="image/png"
    )


class ReceiptOCRViewSetTestCase(APITestCase):
    """Test Receipt OCR API endpoints."""

    def setUp(self):
        """Set up test user and client."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_receipt_scan_endpoint_exists(self):
        """Test that receipt scan endpoint is available."""
        image = create_test_image()
        
        with patch('apps.transactions.views_ocr.process_receipt_async.delay') as mock_task:
            mock_task.return_value = MagicMock(id='test-task-id')
            
            response = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': image},
                format='multipart'
            )
            
            # Should return 202 Accepted for async processing
            self.assertIn(response.status_code, [202, 201, 200])

    def test_receipt_upload_creates_attachment(self):
        """Test that uploading a receipt creates ReceiptAttachment."""
        image = create_test_image()
        
        with patch('apps.transactions.views_ocr.process_receipt_async.delay') as mock_task:
            mock_task.return_value = MagicMock(id='test-task-id')
            
            response = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': image},
                format='multipart'
            )
            
            # Check that a receipt was created
            self.assertTrue(
                ReceiptAttachment.objects.filter(user=self.user).exists(),
                "Receipt attachment should be created"
            )

    def test_receipt_duplicate_detection(self):
        """Test that duplicate receipts are detected by file hash."""
        image1 = create_test_image()
        image1_data = image1.read()
        image1.seek(0)
        
        # Calculate hash
        file_hash = hashlib.sha256(image1_data).hexdigest()
        
        # Create first receipt
        receipt1 = ReceiptAttachment.objects.create(
            user=self.user,
            image=image1,
            file_hash=file_hash,
            file_size=len(image1_data),
            status="success"
        )
        
        # Try to upload same image again
        image2 = create_test_image()
        
        with patch('apps.transactions.views_ocr.process_receipt_async.delay') as mock_task:
            response = self.client.post(
                '/api/v1/receipts/scan/',
                {'image': image2},
                format='multipart'
            )
            
            # Should return conflict status
            self.assertEqual(
                response.status_code,
                status.HTTP_409_CONFLICT,
                "Duplicate receipt should return 409 Conflict"
            )

    def test_receipt_status_endpoint(self):
        """Test getting receipt processing status."""
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        receipt = ReceiptAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="testhash123",
            file_size=len(image_data),
            status="processing",
            merchant_name="Test Store"
        )
        
        response = self.client.get(f'/api/v1/receipts/{receipt.id}/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['merchant_name'], 'Test Store')

    def test_receipt_list_filtered_by_user(self):
        """Test that receipts are filtered by user."""
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        
        image1 = create_test_image()
        image2 = create_test_image()
        image1_data = image1.read()
        image1.seek(0)
        image2_data = image2.read()
        image2.seek(0)
        
        # Create receipt for test user
        receipt1 = ReceiptAttachment.objects.create(
            user=self.user,
            image=image1,
            file_hash="hash1",
            file_size=len(image1_data),
            status="success"
        )
        
        # Create receipt for other user
        receipt2 = ReceiptAttachment.objects.create(
            user=other_user,
            image=image2,
            file_hash="hash2",
            file_size=len(image2_data),
            status="success"
        )
        
        response = self.client.get('/api/v1/receipts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see own receipts
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]['id']), str(receipt1.id))


class BillOCRViewSetTestCase(APITestCase):
    """Test Bill OCR API endpoints."""

    def setUp(self):
        """Set up test user and client."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_bill_scan_endpoint_exists(self):
        """Test that bill scan endpoint is available."""
        image = create_test_image()
        
        with patch('apps.transactions.views_ocr.process_bill_async.delay') as mock_task:
            mock_task.return_value = MagicMock(id='test-task-id')
            
            response = self.client.post(
                '/api/v1/bills/scan/',
                {'image': image},
                format='multipart'
            )
            
            # Should return 202 Accepted for async processing
            self.assertIn(response.status_code, [202, 201, 200])

    def test_bill_upload_creates_attachment(self):
        """Test that uploading a bill creates BillAttachment."""
        image = create_test_image()
        
        with patch('apps.transactions.views_ocr.process_bill_async.delay') as mock_task:
            mock_task.return_value = MagicMock(id='test-task-id')
            
            response = self.client.post(
                '/api/v1/bills/scan/',
                {'image': image},
                format='multipart'
            )
            
            # Check that a bill was created
            self.assertTrue(
                BillAttachment.objects.filter(user=self.user).exists(),
                "Bill attachment should be created"
            )

    def test_bill_status_endpoint(self):
        """Test getting bill processing status."""
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        bill = BillAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="testhash456",
            file_size=len(image_data),
            status="success",
            provider_name="Electricity Co"
        )
        
        response = self.client.get(f'/api/v1/bills/{bill.id}/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['provider_name'], 'Electricity Co')


class ReceiptAsyncProcessingTestCase(TestCase):
    """Test async receipt processing."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    @patch('apps.transactions.views_ocr.get_textract_service')
    def test_receipt_processing_success(self, mock_get_textract):
        """Test successful receipt processing."""
        # Create mock Textract service
        mock_textract = MagicMock()
        mock_textract.is_enabled.return_value = True
        mock_textract.extract_receipt_data.return_value = {
            "success": True,
            "merchant_name": "Supermarket",
            "total_amount": Decimal("45.99"),
            "tax_amount": Decimal("4.59"),
            "subtotal": Decimal("41.40"),
            "date": datetime.now().date(),
            "payment_method": "card",
            "confidence_scores": {"merchant": 0.95, "total": 0.92},
            "items": [
                {
                    "description": "Milk",
                    "quantity": 1,
                    "amount": Decimal("3.50"),
                    "confidence": 0.98
                },
                {
                    "description": "Bread",
                    "quantity": 2,
                    "amount": Decimal("10.00"),
                    "confidence": 0.96
                }
            ],
            "merchant_normalized": True
        }
        
        mock_get_textract.return_value = mock_textract
        
        # Create receipt attachment
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        receipt = ReceiptAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="test_hash",
            file_size=len(image_data),
            status="pending"
        )
        
        # Process receipt
        process_receipt_async(receipt_id=str(receipt.id))
        
        # Refresh receipt from database
        receipt.refresh_from_db()
        
        # Verify receipt was updated
        self.assertEqual(receipt.status, "success")
        self.assertEqual(receipt.merchant_name, "Supermarket")
        self.assertEqual(receipt.total_amount, Decimal("45.99"))
        
        # Verify line items were created
        self.assertEqual(receipt.line_items.count(), 2)

    @patch('apps.transactions.views_ocr.get_textract_service')
    def test_receipt_processing_failure(self, mock_get_textract):
        """Test receipt processing failure."""
        # Create mock Textract service that fails
        mock_textract = MagicMock()
        mock_textract.is_enabled.return_value = True
        mock_textract.extract_receipt_data.return_value = {
            "success": False,
            "error": "Unable to read document"
        }
        
        mock_get_textract.return_value = mock_textract
        
        # Create receipt attachment
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        receipt = ReceiptAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="test_hash",
            file_size=len(image_data),
            status="pending"
        )
        
        # Process receipt
        process_receipt_async(receipt_id=str(receipt.id))
        
        # Refresh receipt from database
        receipt.refresh_from_db()
        
        # Verify receipt marked as failed
        self.assertEqual(receipt.status, "failed")
        self.assertIn("Unable to read document", receipt.error_message)

    def test_receipt_processing_nonexistent(self):
        """Test processing nonexistent receipt."""
        # This should not raise an error, just log it
        process_receipt_async(receipt_id="00000000-0000-0000-0000-000000000000")
        
        # Should complete without error


class BillAsyncProcessingTestCase(TestCase):
    """Test async bill processing."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    @patch('apps.transactions.views_ocr.get_textract_service')
    def test_bill_processing_success(self, mock_get_textract):
        """Test successful bill processing."""
        # Create mock Textract service
        mock_textract = MagicMock()
        mock_textract.is_enabled.return_value = True
        mock_textract.extract_bill_data.return_value = {
            "success": True,
            "provider_name": "Electricity Co",
            "bill_type": "electricity",
            "account_number": "123456789",
            "amount_due": Decimal("125.50"),
            "due_date": datetime.now().date(),
            "previous_balance": Decimal("50.00"),
            "confidence_scores": {"provider": 0.98, "amount": 0.95}
        }
        
        mock_get_textract.return_value = mock_textract
        
        # Create bill attachment
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        bill = BillAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="test_hash",
            file_size=len(image_data),
            status="pending"
        )
        
        # Process bill
        process_bill_async(bill_id=str(bill.id))
        
        # Refresh bill from database
        bill.refresh_from_db()
        
        # Verify bill was updated
        self.assertEqual(bill.status, "success")
        self.assertEqual(bill.provider_name, "Electricity Co")
        self.assertEqual(bill.amount_due, Decimal("125.50"))

    @patch('apps.transactions.views_ocr.get_textract_service')
    def test_bill_processing_failure(self, mock_get_textract):
        """Test bill processing failure."""
        # Create mock Textract service that fails
        mock_textract = MagicMock()
        mock_textract.is_enabled.return_value = True
        mock_textract.extract_bill_data.return_value = {
            "success": False,
            "error": "Document not recognized as bill"
        }
        
        mock_get_textract.return_value = mock_textract
        
        # Create bill attachment
        image = create_test_image()
        image_data = image.read()
        image.seek(0)
        bill = BillAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="test_hash",
            file_size=len(image_data),
            status="pending"
        )
        image = create_test_image()
        bill = BillAttachment.objects.create(
            user=self.user,
            image=image,
            file_hash="test_hash",
            status="pending"
        )
        
        # Process bill
        process_bill_async(bill_id=str(bill.id))
        
        # Refresh bill from database
        bill.refresh_from_db()
        
        # Verify bill marked as failed
        self.assertEqual(bill.status, "failed")
        self.assertIn("Document not recognized as bill", bill.error_message)


class TextractServiceTestCase(TestCase):
    """Test AWS Textract service integration."""

    @patch('boto3.client')
    def test_textract_service_initialization(self, mock_boto_client):
        """Test that Textract service initializes correctly."""
        service = get_textract_service()
        
        # Service should be initialized
        self.assertIsNotNone(service)

    @patch('boto3.client')
    def test_textract_service_enabled(self, mock_boto_client):
        """Test checking if Textract service is enabled."""
        service = get_textract_service()
        
        # Should be enabled if credentials are configured
        result = service.is_enabled()
        self.assertIsInstance(result, bool)
