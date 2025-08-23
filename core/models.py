from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    is_patient = models.BooleanField(default=False)
    is_doctor = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255) 
    age = models.IntegerField(null=True, blank=True)
    mobile_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.full_name  
    


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    
    
    def __str__(self):
        return self.user.full_name  

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    degree = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    
    def __str__(self):
        return self.user.full_name  
    


SYMPTOM_CHOICES = [
    ('fever', 'Fever'),
    ('headache', 'Headache'),
    ('nausea', 'Nausea'),
    ('fatigue', 'Fatigue'),
    ('joint pain', 'Joint Pain'),
    ('rashes', 'Rashes'),
    ('back pain', 'Back Pain'),
    ('eye pain', 'Eye Pain'),
    ('vomiting', 'Vomiting'),
    ('abdominal pain', 'Abdominal Pain'),
    ('bleeding gums', 'Bleeding (Gums/Nose)'),
    ('vomiting blood', 'Vomiting Blood'),
    ('blood in stool', 'Blood in Stool'),
    ('rapid pulse', 'Rapid or Falling Pulse'),
    ('low blood pressure', 'Low Blood Pressure'),
    ('cold extremities', 'Cold Hands & Feet'),
    ('breathing difficulty', 'Difficulty Breathing'),
    ('severe abdominal pain', 'Severe Abdominal Pain'),
    ('persistent vomiting', 'Persistent Vomiting'),
    ('drowsiness', 'Drowsiness or Confusion'),
]

class SymptomLog(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    symptom = models.CharField(max_length=50, choices=SYMPTOM_CHOICES)
    severity = models.IntegerField(choices=[(i, i) for i in range(4)])
    date_logged = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.symptom} ({self.severity}) on {self.date_logged}"




class AppointmentSchedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    available_days = models.CharField(max_length=255)
    available_time = models.CharField(max_length=255)
    appointment_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('available', 'Available'), ('on_leave', 'On Leave')], default='available')

    def __str__(self):
        return f"Schedule for {self.doctor.user.full_name}"
    




class AppointmentBooking(models.Model):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    DONE = 'Done'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (REJECTED, 'Rejected'),
        ( DONE , 'Done')
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    schedule = models.ForeignKey(AppointmentSchedule, on_delete=models.CASCADE)
    booked_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING) 
    booking_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Appointment with {self.schedule.doctor.user.full_name} for {self.patient.user.full_name} - Status: {self.get_status_display()}"
