# core/models.py
from django.db import models
from django.contrib.auth.models import User,BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.conf import settings
class CustomUserManager(BaseUserManager):
    def create_user(self,full_name,email,username,phone,password=None,**extra_fields):
        """
        Creates and saves a User with the given email, username, phone, and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
       
        user = self.model(full_name=full_name,email=email, username=username, phone=phone, **extra_fields)
        user.set_password(password) # This hashes the password securely
        user.save(using=self._db)
        return user
    def create_superuser(self,full_name, email, username, phone, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email, username, phone, and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(full_name,email, username, phone, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True) # Use email for login
    username = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=15, unique=True) # Added phone field
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    objects = CustomUserManager() # Use the manager we just defined

    USERNAME_FIELD = 'email' # Use email to log in
    REQUIRED_FIELDS = ['full_name','username', 'phone'] # Required fields for 'createsuperuser'

    def __str__(self):
        return self.email
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
    
class Test(models.Model):
    """Like SSC CGL Mock 1, SSC CGL Mock 2 etc"""
    title = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField()    
    test_series = models.ForeignKey(TestSeries,on_delete=models.CASCADE)
    marks_correct = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    marks_incorrect = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    def __str__(self):
        return self.title

class Section(models.Model):
    name=models.CharField(max_length=100)
    number_of_questions =models.PositiveIntegerField()
    test = models.ForeignKey(Test, related_name='sections', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.test.title} - {self.name}"
    

class Question(models.Model):
    section = models.ForeignKey(Section,related_name='questions',on_delete=models.CASCADE)
    question_text = models.TextField()
    option_a = models.CharField(max_length=15)
    option_b = models.CharField(max_length=15)
    option_c = models.CharField(max_length=15)
    option_d = models.CharField(max_length=15)
    correct_option = models.CharField(max_length=1,choices=[('a','A'), ('b','B'), ('c','C'), ('d','D')])
    explanation = models.TextField(blank=True)

    # class Meta:
    #     ordering =['id']

    def __str__(self):
        return f"{self.section.test} - {self.section.name} - {self.question_text[:30]}..."
    


    

# Add these two new classes to the end of your core/models.py file

class TestResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"


# --- THIS IS THE CORRECTED MODEL ---
class UserResponse(models.Model):
    # This is the new, direct parent-child link.
    test_result = models.ForeignKey(TestResult, related_name='responses', on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, blank=True, null=True)
    marked_for_review = models.BooleanField(default=False)
    
   

    def __str__(self):
        return f"Response for Q{self.question.id}"