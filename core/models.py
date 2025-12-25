# core/models.py
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.conf import settings
from django.utils import timezone
class CustomUserManager(BaseUserManager):
    def create_user(self,first_name,last_name,email,phone,password=None,**extra_fields):
        """
        Creates and saves a User with the given email, username, phone, and password.
        """
        if not email:
            raise ValueError('The Email field must be set') # <-- This line is correct
        
        email = self.normalize_email(email.strip()) # <-- Use strip() here
       
        user = self.model(first_name=first_name,last_name=last_name ,email=email, phone=phone, **extra_fields)
        user.set_password(password) # This hashes the password securely
        user.save(using=self._db)
        return user
    def create_superuser(self,first_name, last_name,email, phone, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email, phone, and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(first_name,last_name,email, phone, password, **extra_fields)

from django.db import models

class CurrentAffair(models.Model):
    CATEGORY_CHOICES = [
        ('NAT', 'National'),
        ('INT', 'International'),
        ('ECO', 'Economy'),
        ('SPT', 'Sports'),
        ('SCI', 'Science & Tech'),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    summary = models.TextField(help_text="Short description for the card")
    content = models.TextField(help_text="Full detail for the detail view")
    
    # Media
    image_url = models.URLField(blank=True, null=True)
    source_name = models.CharField(max_length=100, default="PIB")
    source_link = models.URLField(blank=True, null=True)

    # Exam Specifics
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    is_hot_topic = models.BooleanField(default=False, help_text="Show in Hero Section")
    tags = models.CharField(max_length=255, help_text="Comma separated tags e.g. #G20, #ISRO")
    
    # Meta
    date = models.DateField(db_index=True) # Important for the Date Strip
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} - {self.title}"




class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True) # Use email for login
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True) # Added phone field
    is_pro_member = models.BooleanField(default=False) # Legacy static field (keep for safety or migration)
    pro_expiry_date = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_pro_member = models.BooleanField(default=False)
    objects = CustomUserManager() # Use the manager we just defined
    
    USERNAME_FIELD = 'email' # Use email to log in
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone'] # Required fields for 'createsuperuser'

    def __str__(self):
        return self.email
    
    @property
    def is_pro_active(self):
        """
        Returns True if the user has an active pro subscription.
        Checks if pro_expiry_date is set and is in the future.
        """
        if self.pro_expiry_date and self.pro_expiry_date > timezone.now():
            return True
        return False
    

class Notification(models.Model):
    TYPE_CHOICES = (
        ('TEST', 'Test Series'),    # Blue/Book icon
        ('RESULT', 'Result'),       # Green/Chart icon
        ('SYSTEM', 'System Update'),# Orange/Cog icon
        ('GENERAL', 'General'),     # Gray/Info icon
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='GENERAL')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Newest first

    def __str__(self):
        return f"{self.title} - {self.user.email}"


class ExamName(models.Model):
    """Exam name is SSC, Bank etc"""
    name=models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class TestSeries(models.Model):
    """Like SSC CGL, SSC CHSL"""
    name=models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(ExamName,on_delete=models.CASCADE)
 
    def __str__(self):
        return self.name
    
class TestStage(models.Model):
    name = models.CharField(max_length=100, help_text="e.g. Tier-1, Prelims")
    test_series = models.ForeignKey(TestSeries, related_name='stages', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1, help_text="Order to display tabs (1, 2, 3)")

    def __str__(self):
        return f"{self.test_series.name} - {self.name}"

class Test(models.Model):
    """Like SSC CGL Mock 1, SSC CGL Mock 2 etc"""
    title = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField()
    is_free = models.BooleanField(default=False)    
    test_series = models.ForeignKey(TestSeries,on_delete=models.CASCADE)
    stage = models.ForeignKey(TestStage, related_name='tests', on_delete=models.CASCADE, null=True, blank=True)

    marks_correct = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    marks_incorrect = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Only run automation on creation (no ID yet)
        if not self.pk:
            existing_count = 0
            
            if self.stage:
                # If stage exists, check how many tests are in THIS stage
                existing_count = Test.objects.filter(stage=self.stage).count()
            else:
                # Fallback: check series if no stage is assigned
                existing_count = Test.objects.filter(test_series=self.test_series).count()
            
            # If count is 0 (First test of the stage/series), make it free
            if existing_count == 0:
                self.is_free = True
            else:
                self.is_free = False
                
        super().save(*args, **kwargs)


class Section(models.Model):
    name=models.CharField(max_length=100)
    number_of_questions =models.PositiveIntegerField()
    test = models.ForeignKey(Test, related_name='sections', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.test.title} - {self.name}"
    

class Question(models.Model):
    section = models.ForeignKey(Section, related_name='questions', on_delete=models.CASCADE)
    
    # English Content
    question_text = models.TextField(verbose_name="Question (English)")
    option_a = models.CharField(max_length=255, verbose_name="Option A (English)")
    option_b = models.CharField(max_length=255, verbose_name="Option B (English)")
    option_c = models.CharField(max_length=255, verbose_name="Option C (English)")
    option_d = models.CharField(max_length=255, verbose_name="Option D (English)")
    explanation = models.TextField(blank=True, verbose_name="Explanation (English)")

    # Hindi Content (Optional - use blank=True)
    question_text_hi = models.TextField(blank=True, null=True, verbose_name="Question (Hindi)")
    option_a_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option A (Hindi)")
    option_b_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option B (Hindi)")
    option_c_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option C (Hindi)")
    option_d_hi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Option D (Hindi)")
    explanation_hi = models.TextField(blank=True, null=True, verbose_name="Explanation (Hindi)")

    correct_option = models.CharField(max_length=1, choices=[('a','A'), ('b','B'), ('c','C'), ('d','D')])

    def __str__(self):
        return f"{self.section.test} - {self.section.name} - {self.question_text[:30]}..."
    


    

# Add these two new classes to the end of your core/models.py file

class TestResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    completed_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    time_remaining=models.IntegerField(default=0, help_text="Time remaining in seconds")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.test.title}"


# --- THIS IS THE CORRECTED MODEL ---
class UserResponse(models.Model):
    # This is the new, direct parent-child link.
    test_result = models.ForeignKey(TestResult, related_name='responses', on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, blank=True, null=True)
    marked_for_review = models.BooleanField(default=False)
    
   

    def __str__(self):
        return f"Response for Q{self.question_id}"

class PhoneOTP(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    count = models.IntegerField(default=0, help_text="Number of OTP sent")
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} - {self.otp}"