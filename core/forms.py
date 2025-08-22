from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .models import SymptomLog
from .models import AppointmentSchedule
from .models import Doctor
from .models import Patient



class BaseSignUpForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your full name'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'age', 'mobile_number', 'password1', 'password2']

class PatientSignUpForm(BaseSignUpForm):
    def save(self, commit=True):
        # Create the User object
        user = super().save(commit=False)
        user.is_patient = True
        user.is_doctor = False
        user.email = self.cleaned_data.get('email')
        user.full_name = self.cleaned_data.get('full_name')
        user.age = self.cleaned_data.get('age')
        user.mobile_number = self.cleaned_data.get('mobile_number')
        user.save()
        
        # Create the Patient object
        patient = Patient.objects.create(
            user=user,
            # Add any additional patient-specific fields if you have them
        )
        return user

class DoctorSignUpForm(UserCreationForm):
    # Add the fields from the Doctor model
    full_name = forms.CharField(max_length=255, required=True, label='Full Name')
    degree = forms.CharField(max_length=100, required=True, label='Degree')
    specialty = forms.CharField(max_length=100, required=True, label='Specialty')
    registration_number = forms.CharField(max_length=100, required=True, label='Registration Number')
    designation = forms.CharField(max_length=100, required=True, label='Designation')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('full_name', 'email', 'mobile_number', 'age')

    # Override the save method to create both User and Doctor instances
    def save(self, commit=True):
        # Create the User object
        user = super().save(commit=False)
        user.is_doctor = True
        user.is_patient = False
        user.email = self.cleaned_data.get('email') 
        user.full_name = self.cleaned_data.get('full_name')
        user.age = self.cleaned_data.get('age')
        user.mobile_number = self.cleaned_data.get('mobile_number')
        user.save()

        # Create the Doctor object
        doctor = Doctor.objects.create(
            user=user,
            degree=self.cleaned_data['degree'],
            specialty=self.cleaned_data['specialty'],
            registration_number=self.cleaned_data['registration_number'],
            designation=self.cleaned_data['designation']
        )
        return user # Return the User object




class SymptomLogForm(forms.ModelForm):
    class Meta:
        model = SymptomLog
        fields = ['symptom', 'severity']

        widgets = {
            'symptom': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
        }




class AppointmentScheduleForm(forms.ModelForm):
    class Meta:
        model = AppointmentSchedule
        fields = ['available_days', 'available_time', 'appointment_fee', 'status']

    available_days = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Sun-Mon, Fri-Sat'}))
    available_time = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., 5 PM - 10 PM'}))
    appointment_fee = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    status = forms.ChoiceField(choices=[('available', 'Available'), ('on_leave', 'On Leave')], widget=forms.Select(attrs={'class': 'form-select'}))
