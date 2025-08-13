from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages  
from django.contrib.auth import logout, login, authenticate
from .forms import PatientSignUpForm, DoctorSignUpForm, SymptomLogForm, AppointmentScheduleForm
from .models import User, Patient, Doctor, SymptomLog, SYMPTOM_CHOICES, AppointmentSchedule, AppointmentBooking
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date
from collections import defaultdict



# Create your views here.
def home(req):
    return render(req, 'core/index.html')


def logout_user(request):
    logout(request)  # Logs out the user
    messages.success(request, 'You have logged out successfully.')  # Show success message
    return redirect('home')


# core/views.py

def signup_view(request):
    if request.method == 'POST':
        user_type = request.POST.get('userType')
        
        if user_type == 'patient':
            form = PatientSignUpForm(request.POST)
        else:
            form = DoctorSignUpForm(request.POST) # Use the DoctorSignUpForm
        
        if form.is_valid():
            user = form.save()  # This now creates both User and Doctor/Patient
            
            # The following block is now redundant and should be removed.
            # if user_type == 'doctor':
            #     Doctor.objects.create(
            #         user=user,
            #         degree=form.cleaned_data['degree'],
            #         specialty=form.cleaned_data['specialty'],
            #         registration_number=form.cleaned_data['registration_number'],
            #         designation=form.cleaned_data['designation']
            #     )
            # else:
            #     # If the user is a patient, create the Patient instance
            #     Patient.objects.create(user=user)
            
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = None
        user_type = 'patient'

    return render(request, 'core/signup.html', {
        'form': form,
        'user_type': request.POST.get('userType', 'patient') if request.method == 'POST' else user_type
    })


def login_user(request):
    if request.method == 'POST':
        user_type = request.POST.get('userType')
        username = request.POST.get('username') 
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if (user_type == 'doctor' and user.is_doctor) or (user_type == 'patient' and user.is_patient):
                login(request, user)
                if user.is_doctor:
                    return redirect('doctor_dashboard')
                else:
                    return redirect('patient_dashboard')
            else:
                messages.error(request, 'Invalid user type for this account')
        else:
            messages.error(request, 'Invalid username or password')  # Optional: Update wording
    return render(request, 'core/login.html')





def patient_dashboard(request):
    return render(request, 'core/base_p_dashboard.html')



def check_dengue(request):
    symptoms = [
        ('fever', 'Fever'),
        ('headache', 'Headache'),
        ('nausea', 'Nausea'),
        ('fatigue', 'Fatigue'),
        ('joint_pain', 'Joint Pain'),
        ('rashes', 'Rashes'),
        ('back_pain', 'Back Pain'),
        ('eye_pain', 'Eye Pain'),
        ('vomiting', 'Vomiting'),
        ('abdominal_pain', 'Abdominal Pain'),
    ]
    return render(request, 'core/check_dengue.html', {'symptoms': symptoms})






@login_required
def track_symptoms(request):
    try:
        patient_instance = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient_instance = None
        symptom_logs_by_date = {}

    if request.method == 'POST' and patient_instance:
        symptom = request.POST.get('symptom')
        severity = request.POST.get('severity')

        print(f"Symptom: {symptom}, Severity: {severity}")  # Debugging line to check form data

        if symptom and severity:  # Check if data is not empty
            SymptomLog.objects.create(
                patient=patient_instance,
                symptom=symptom,
                severity=severity,
            )
            messages.success(request, "Symptom logged successfully.")
        else:
            messages.error(request, "Please select a symptom and severity.")

        return redirect('track_symptoms')

    if patient_instance:
        # Fetch ALL symptom logs for the patient, ordered by date_logged descending
        all_logs = SymptomLog.objects.filter(patient=patient_instance).order_by('-date_logged')

        # Group logs by date
        symptom_logs_by_date = defaultdict(list)
        for log in all_logs:
            symptom_logs_by_date[log.date_logged].append(log)
    else:
        symptom_logs_by_date = {}

    context = {
        'symptom_choices': SYMPTOM_CHOICES,
        'symptom_logs_by_date': dict(symptom_logs_by_date),
    }
    return render(request, 'core/track_symptoms.html', context)


@login_required
def edit_symptom_log(request, log_id):
    if request.method == 'POST':
        try:
            patient_instance = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return redirect('some_error_page')

        log = get_object_or_404(SymptomLog, id=log_id, patient=patient_instance)
        
        new_severity = request.POST.get('severity')
        
        if new_severity is not None:
            log.severity = int(new_severity)
            log.save()
            
    return redirect('track_symptoms')

@login_required
def delete_symptom_log(request, log_id):
    try:
        patient_instance = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        return redirect('some_error_page')

    log = get_object_or_404(SymptomLog, id=log_id, patient=patient_instance)
    log.delete()
    return redirect('track_symptoms')








@login_required
def doctor_appointment(request):
    try:
        patient_instance = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('home')

    # Get the available appointment schedules for all doctors
    schedules = AppointmentSchedule.objects.filter(status='available')
    
    # Handle appointment booking if the patient is making a request
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        schedule = get_object_or_404(AppointmentSchedule, id=schedule_id)
        if not AppointmentBooking.objects.filter(patient=patient_instance, schedule=schedule).exists():
            # Create a new booking
            AppointmentBooking.objects.create(patient=patient_instance, schedule=schedule)
            messages.success(request, f"Appointment booked with Dr. {schedule.doctor.user.full_name}!")
        else:
            messages.warning(request, 'You have already booked this appointment.')

    context = {
        'schedules': schedules,
    }
    return render(request, 'core/doctor_appointment.html', context)




@login_required
def patient_profile(request):
    patient = Patient.objects.get(user=request.user)
    return render(request, 'core/patientProfile.html', {'patient': patient})

@login_required
def edit_patient_profile(request):
    patient = Patient.objects.get(user=request.user)

    if request.method == 'POST':
        # Update user model fields
        user = patient.user
        user.full_name = request.POST.get('full_name')
        user.email = request.POST.get('email')
        user.age = request.POST.get('age')
        user.mobile_number = request.POST.get('mobile_number')
        user.save()

        return redirect('patient_profile')






def doctor_dashboard(request):
    return render(request, 'core/base_d_dashboard.html')


def doctorDashboard(request):
    return render(request, 'core/doctorDashboard.html')

@login_required
def appointment_schedule(request):
    try:
        doctor_instance = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You must be a registered doctor to view this page.')
        return redirect('home')

    if request.method == 'POST':
        form = AppointmentScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.doctor = doctor_instance
            schedule.save()
            messages.success(request, 'Appointment schedule added successfully!')
            return redirect('appointment_schedule')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = AppointmentScheduleForm()

    schedules = AppointmentSchedule.objects.filter(doctor=doctor_instance)

    context = {
        'form': form,
        'schedules': schedules,
        'doctor_instance': doctor_instance,
    }
    return render(request, 'core/appointment_schedule.html', context)


@login_required
def edit_schedule(request, schedule_id):
    schedule = get_object_or_404(AppointmentSchedule, pk=schedule_id, doctor__user=request.user)
    if request.method == 'POST':
        form = AppointmentScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule updated successfully!')
            return redirect('appointment_schedule')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = AppointmentScheduleForm(instance=schedule)

    return render(request, 'core/edit_schedule.html', {'form': form, 'schedule': schedule})

@login_required
def delete_schedule(request, schedule_id):
    # Ensure the schedule belongs to the logged-in doctor
    schedule = get_object_or_404(AppointmentSchedule, id=schedule_id, doctor__user=request.user)

    # Only allow POST requests for deletion for security
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'Schedule deleted successfully!')
        return redirect('appointment_schedule')  # Redirect to the appointment schedule page

    # For non-POST requests, you could render a confirmation page or redirect
    return redirect('appointment_schedule')


# @login_required
# def edit_schedule(request, schedule_id):
#     schedule = get_object_or_404(AppointmentSchedule, pk=schedule_id, doctor__user=request.user)

#     if request.method == 'POST':
#         form = AppointmentScheduleForm(request.POST, instance=schedule) # <-- Removed request.FILES
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Schedule updated successfully!')
#             return redirect('appointment_schedule')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
#     else:
#         form = AppointmentScheduleForm(instance=schedule)

#     return render(request, 'core/edit_schedule.html', {'form': form, 'schedule': schedule})




def view_appointments(request):
    return render(request, 'core/view_appointments.html')

def view_patients(request):
    return render(request, 'core/view_patients.html')

@login_required
def doctor_profile(request):
    doctor = Doctor.objects.get(user=request.user)
    return render(request, 'core/doctor_profile.html', {'doctor': doctor})


@login_required
def edit_doctor_profile(request):
    doctor = Doctor.objects.get(user=request.user)

    if request.method == 'POST':
        # Update user fields
        doctor.user.full_name = request.POST.get('full_name')
        doctor.user.email = request.POST.get('email')
        doctor.user.age = request.POST.get('age')
        doctor.user.mobile_number = request.POST.get('mobile_number')
        doctor.user.save()

        # Update doctor fields
        doctor.degree = request.POST.get('degree')
        doctor.specialty = request.POST.get('specialty')
        doctor.designation = request.POST.get('designation')
        doctor.registration_number = request.POST.get('registration_number')
        doctor.save()

        return redirect('doctor_profile')
