import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=100, blank=True, null=True)
    enrollment_no = models.CharField(max_length=50, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

# --- Course Model ---
class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    credits = models.IntegerField(default=3)
    total_seats = models.PositiveIntegerField(default=60)  # <-- new field
    seats_available = models.PositiveIntegerField(default=60)

    def __str__(self):
        return f"{self.name} ({self.code})"


# --- Faculty Model ---
class Faculty(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    assigned_courses = models.JSONField(default=list, blank=True)
    join_date = models.DateField()
    email = models.EmailField()
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department}"


# --- Student Model ---
class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name=models.CharField(max_length=100, null=True,blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    admission_date = models.DateField()
    roll_number = models.CharField(max_length=64, unique=True)
    fees_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # --- NEW admission / personal fields ---
    # Government IDs
    aadhar = models.CharField(max_length=12, blank=True, null=True, help_text="Aadhar (12 digits)")
    abc_id = models.CharField(max_length=16, blank=True, null=True, help_text="ABC ID (16 digits)")

    # Contact & address
    address = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)

    # Academic + admission-specific
    ojee_rank = models.CharField(max_length=50, blank=True, null=True, help_text="OJEE rank or ID")
    marksheet_ref = models.CharField(max_length=100, blank=True, null=True, help_text="Uploaded marksheet filename or ref")
    university_reg_no = models.CharField(max_length=64, blank=True, null=True, help_text="University registration no")
    
    MODE_CHOICES = [
        ("Regular", "Regular"),
        ("Lateral", "Lateral"),
    ]
    mode_of_entry = models.CharField(max_length=20, choices=MODE_CHOICES, default="Regular")
    
    # Fees fields (if not present)
    fees_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # Parent details
    parent_name = models.CharField(max_length=128, blank=True, null=True)
    parent_contact = models.CharField(max_length=30, blank=True, null=True)

    # Meta / timestamps (if you want)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def pending_fees(self):
        return self.total_fees - self.fees_paid

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.roll_number})"


# --- Fee Record Model ---
class FeeRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    status_choices = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='paid')

    def __str__(self):
        return f"{self.student.user.username} - {self.status}"


# --- Holiday Model ---
class Holiday(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.date})"
    
# --- Announcement Model ---
class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    target_choices = [
        ('all', 'All'),
        ('students', 'Students'),
        ('faculty', 'Faculty'),
    ]
    target_audience = models.CharField(max_length=10, choices=target_choices, default='all')

    def __str__(self):
        return f"{self.title} ({self.target_audience})"


# --- simple password-reset model ---
class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    code = models.CharField(max_length=6, null=True, blank=True)  # optional OTP
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)  # 15 min expiry
        super().save(*args, **kwargs)

    def is_valid(self):
        return timezone.now() <= self.expires_at