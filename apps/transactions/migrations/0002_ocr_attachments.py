# Generated migration for OCR attachment models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),  # Update to your latest migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ReceiptAttachment model
        migrations.CreateModel(
            name='ReceiptAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(
                    help_text='Receipt image (JPG, PNG, PDF only)',
                    upload_to='receipts/%Y/%m/%d/',
                    validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])]
                )),
                ('file_size', models.IntegerField(help_text='File size in bytes', validators=[django.core.validators.MinValueValidator(0)])),
                ('file_hash', models.CharField(db_index=True, help_text='SHA256 hash of file for deduplication', max_length=64)),
                ('merchant_name', models.CharField(blank=True, max_length=255, null=True)),
                ('total_amount', models.DecimalField(blank=True, decimal_places=2, help_text='Total amount in NZD', max_digits=10, null=True)),
                ('tax_amount', models.DecimalField(blank=True, decimal_places=2, help_text='GST/Tax amount', max_digits=10, null=True)),
                ('subtotal', models.DecimalField(blank=True, decimal_places=2, help_text='Subtotal before tax', max_digits=10, null=True)),
                ('receipt_date', models.DateField(blank=True, null=True)),
                ('payment_method', models.CharField(blank=True, max_length=50, null=True)),
                ('confidence_scores', models.JSONField(default=dict, help_text='Confidence scores from Textract (merchant, total, date, etc.)')),
                ('extracted_data', models.JSONField(default=dict, help_text='Full extracted data including line items')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending OCR Processing'),
                        ('processing', 'Currently Processing'),
                        ('success', 'Successfully Extracted'),
                        ('partial', 'Partially Extracted (Manual Review Needed)'),
                        ('failed', 'Extraction Failed'),
                        ('manual_review', 'Requires Manual Review')
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20
                )),
                ('error_message', models.TextField(blank=True, null=True)),
                ('error_code', models.CharField(blank=True, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(help_text='Data retention expiry date (12 months per Privacy Act 2020)')),
                ('merchant_normalized', models.BooleanField(default=False, help_text='True if merchant name was normalized to major NZ retailer')),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='receipt_attachments', to='transactions.transaction')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipt_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Receipt Attachment',
                'verbose_name_plural': 'Receipt Attachments',
                'ordering': ['-created_at'],
            },
        ),
        
        # ReceiptLineItem model
        migrations.CreateModel(
            name='ReceiptLineItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=255)),
                ('quantity', models.CharField(blank=True, max_length=50, null=True)),
                ('unit_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('line_number', models.IntegerField(help_text='Order in receipt')),
                ('confidence', models.FloatField(default=0.0, help_text='Textract confidence score (0-100)', validators=[django.core.validators.MinValueValidator(0.0)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='transactions.receiptattachment')),
            ],
            options={
                'verbose_name': 'Receipt Line Item',
                'verbose_name_plural': 'Receipt Line Items',
                'ordering': ['line_number'],
            },
        ),
        
        # BillAttachment model
        migrations.CreateModel(
            name='BillAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(
                    upload_to='bills/%Y/%m/%d/',
                    validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])]
                )),
                ('file_size', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('file_hash', models.CharField(db_index=True, max_length=64)),
                ('provider_name', models.CharField(blank=True, max_length=255, null=True)),
                ('bill_type', models.CharField(
                    blank=True,
                    choices=[
                        ('electricity', 'Electricity'),
                        ('water', 'Water'),
                        ('internet', 'Internet/Broadband'),
                        ('phone', 'Phone/Mobile'),
                        ('insurance', 'Insurance'),
                        ('rent', 'Rent'),
                        ('council_rates', 'Council Rates'),
                        ('other', 'Other Utility'),
                    ],
                    max_length=20,
                    null=True
                )),
                ('account_number', models.CharField(blank=True, max_length=100, null=True)),
                ('billing_period_start', models.DateField(blank=True, null=True)),
                ('billing_period_end', models.DateField(blank=True, null=True)),
                ('amount_due', models.DecimalField(blank=True, decimal_places=2, help_text='Amount due in NZD', max_digits=10, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('previous_balance', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('confidence_scores', models.JSONField(default=dict)),
                ('extracted_data', models.JSONField(default=dict)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending OCR Processing'),
                        ('processing', 'Currently Processing'),
                        ('success', 'Successfully Extracted'),
                        ('partial', 'Partially Extracted'),
                        ('failed', 'Extraction Failed'),
                        ('manual_review', 'Requires Manual Review'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20
                )),
                ('error_message', models.TextField(blank=True, null=True)),
                ('error_code', models.CharField(blank=True, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(help_text='Data retention expiry')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bill_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bill Attachment',
                'verbose_name_plural': 'Bill Attachments',
                'ordering': ['-created_at'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='receiptattachment',
            index=models.Index(fields=['user', '-created_at'], name='transactions_receipt_user_idx'),
        ),
        migrations.AddIndex(
            model_name='receiptattachment',
            index=models.Index(fields=['status', 'created_at'], name='transactions_receipt_status_idx'),
        ),
        migrations.AddIndex(
            model_name='receiptattachment',
            index=models.Index(fields=['expires_at'], name='transactions_receipt_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='billattachment',
            index=models.Index(fields=['user', '-created_at'], name='transactions_bill_user_idx'),
        ),
        migrations.AddIndex(
            model_name='billattachment',
            index=models.Index(fields=['status', 'created_at'], name='transactions_bill_status_idx'),
        ),
        migrations.AddIndex(
            model_name='billattachment',
            index=models.Index(fields=['expires_at'], name='transactions_bill_expires_idx'),
        ),
    ]
