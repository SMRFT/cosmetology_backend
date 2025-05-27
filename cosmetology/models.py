# models.py
from django.utils import timezone
from datetime import timedelta,datetime
from dateutil.parser import parse
from django.db import models
import re

class AuditModel(models.Model):
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    lastmodified_by = models.CharField(max_length=100, blank=True, null=True)
    lastmodified_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.created_by:
            self.created_by = "system"
        self.lastmodified_by = self.lastmodified_by or "system"
        super().save(*args, **kwargs)



class Register(AuditModel):
    id = models.CharField(max_length=500, primary_key=True)
    name = models.CharField(max_length=500)
    role = models.CharField(max_length=500)
    branch_code = models.JSONField(default=list)  # Change to JSONField
    contact = models.CharField(max_length=500)
    password = models.CharField(max_length=500)

class Login(models.Model):
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=120)

class Pharmacy(AuditModel):
    medicine_name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=50, blank=True, null=True)  
    medicine_category = models.CharField(max_length=50, null=True, blank=True)
    company_name = models.CharField(max_length=255,null=True, blank=True)
    price = models.CharField(max_length=255,null=True, blank=True)
    CGST_percentage = models.CharField(max_length=200,null=True, blank=True)
    CGST_value = models.CharField(max_length=200,null=True, blank=True)
    SGST_percentage = models.CharField(max_length=200,null=True, blank=True)
    SGST_value = models.CharField(max_length=200,null=True, blank=True)
    new_stock = models.IntegerField(null=True, blank=True)
    old_stock = models.IntegerField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=255,null=True, blank=True)

    def __str__(self):
        return self.medicine_name

    def is_quantity_low(self):
        # Ensure old_stock is not None before comparison
        if self.old_stock is None:
            return False
        return self.old_stock <= 15

    def is_expiry_near(self):
        try:
            # Ensure `expiry_date` is a valid date
            if isinstance(self.expiry_date, str):
                expiry_date = parse(self.expiry_date).date()
            else:
                expiry_date = self.expiry_date

            # Check if expiry date is near
            return (expiry_date - timezone.now().date()) <= timedelta(days=10)
        except Exception as e:
            # Handle invalid dates gracefully
            return False

class Patient(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patientName = models.CharField(max_length=255)  # Mandatory
    mobileNumber = models.CharField(max_length=11)  # Mandatory
    age = models.IntegerField()  # New field for age, replacing dateOfBirth
    gender = models.CharField(max_length=10, blank=True, null=True)  # Optional
    patientUID = models.CharField(max_length=10, primary_key=True, blank=True, editable=False)
    email = models.EmailField(blank=True, null=True)  # Optional
    language = models.CharField(max_length=10, blank=True, null=True)  # Optional
    purposeOfVisit = models.CharField(max_length=500, blank=True, null=True)  # Optional
    address = models.TextField(blank=True, null=True)  # Optional
    def save(self, *args, **kwargs):
        if not self.patientUID:
            last_patient = Patient.objects.all().values_list('patientUID', flat=True)
            max_id = 0  # Default starting value
            # Extract the numeric part and find the maximum
            for uid in last_patient:
                match = re.search(r'SHC0(\d+)', uid)
                if match:
                    max_id = max(max_id, int(match.group(1)))
            self.patientUID = f'SHC0{max_id + 1:03}'  # Generates SHC001, SHC002, ..., SHC097
        super(Patient, self).save(*args, **kwargs)
    def __str__(self):
        return self.patientName
    

class Appointment(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patientUID = models.CharField(max_length=10)
    patientName = models.CharField(max_length=255)
    mobileNumber = models.CharField(max_length=11)
    appointmentTime = models.CharField(max_length=1000)
    appointmentDate = models.DateField()
    purposeOfVisit = models.CharField(max_length=500)
    gender = models.CharField(max_length=10)

    def __str__(self):
        return self.patientUID


class SummaryDetail(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patientName = models.CharField(max_length=100)
    patientUID = models.CharField(max_length=100)
    mobileNumber = models.CharField(max_length=100)
    diagnosis = models.CharField(max_length=1500,blank=True)
    complaints = models.JSONField()
    findings = models.CharField(max_length=1500,blank=True)
    prescription = models.CharField(max_length=1500,blank=True)
    plans = models.CharField(max_length=1500,blank=True)
    tests = models.CharField(max_length=1500,blank=True)
    vital = models.JSONField()
    proceduresList = models.JSONField()
    nextVisit = models.CharField(max_length=100,blank=True, null=True)
    appointmentDate = models.CharField(max_length=100,blank=True)
    time = models.CharField(max_length=8, blank=True)
    def save(self, *args, **kwargs):
        # Set current Indian Standard Time (IST)
        tz = timezone.get_current_timezone()
        current_time = timezone.localtime(timezone.now(), tz).strftime('%H:%M:%S')
        self.time = current_time
        super().save(*args, **kwargs)
    def __str__(self):
        return self.diagnosis

class Visit(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    visit_date = models.DateTimeField(auto_now_add=True)

class Vital(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patientUID = models.CharField(max_length=10)
    patientName = models.CharField(max_length=100)
    mobileNumber = models.CharField(max_length=15)
    height = models.CharField(max_length=10)
    weight = models.CharField(max_length=10)
    pulseRate = models.CharField(max_length=10)
    bloodPressure = models.CharField(max_length=10)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patientUID} - {self.recorded_at}"

class BillingData(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    patientUID = models.CharField(max_length=10)
    patientName = models.CharField(max_length=100)
    appointmentDate = models.CharField(max_length=500)
    table_data = models.JSONField()
    netAmount = models.CharField(max_length=500)
    discount = models.CharField(max_length=500)
    paymentType = models.CharField(max_length=10, choices=[('Cash', 'Cash'), ('Card', 'Card')])
    billNumber = models.CharField(max_length=50)


class Diagnosis(AuditModel):
    diagnosis= models.CharField(max_length=100)

class Complaints(AuditModel):
    complaints= models.CharField(max_length=100)

class Findings(AuditModel):
    findings= models.CharField(max_length=100)

class Tests(AuditModel):
    test= models.CharField(max_length=500)

class Procedure(AuditModel):
    procedure= models.CharField(max_length=500) 

class ProcedureBill(AuditModel):
    branch_code = models.CharField(max_length=50, blank=True, null=True)  # Add branch_code field
    appointmentDate = models.CharField(max_length=255)
    patientName = models.CharField(max_length=255)
    patientUID = models.CharField(max_length=255)
    procedures = models.JSONField()
    procedureNetAmount = models.CharField(max_length=255)
    consumerNetAmount = models.CharField(max_length=255)
    consumer = models.JSONField()

    # Add paymentType and billNumber for both consumer and procedure
    PaymentType = models.CharField(max_length=10, choices=[('Cash', 'Cash'), ('Card', 'Card')])
    consumerBillNumber = models.CharField(max_length=50)
    procedureBillNumber = models.CharField(max_length=50)