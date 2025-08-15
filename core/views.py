from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages  
from django.contrib.auth import logout, login, authenticate
from .forms import PatientSignUpForm, DoctorSignUpForm, SymptomLogForm, AppointmentScheduleForm
from .models import User, Patient, Doctor, SymptomLog, SYMPTOM_CHOICES, AppointmentSchedule, AppointmentBooking
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date
from collections import defaultdict
import joblib
import pandas as pd
from datetime import timedelta
from django.db.models import Sum



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









#######################################################################################
#                                   PATIENT
#######################################################################################



###         BASE DASHBOARD
def patient_dashboard(request):
    return render(request, 'core/base_p_dashboard.html')



# Load the model and features once when the server starts
try:
    # UPDATED: Use the new file names
    model = joblib.load('ml_model/risk_model.pkl')
    model_features = joblib.load('ml_model/features.pkl')
except FileNotFoundError:
    print("Warning: ML model files not found. Run ml_model.py to create them.")
    model = None
    model_features = []

# Define high-risk symptoms for a clear rule-based override
HIGH_RISK_SYMPTOMS = [
    'bleeding gums', 'vomiting blood', 'blood in stool', 'rapid pulse',
    'low blood pressure', 'cold extremities', 'breathing difficulty',
    'severe abdominal pain', 'persistent vomiting', 'drowsiness',
]

def get_patient_features(patient):
    """
    Extracts features from patient logs in the format the model expects.
    UPDATED: Now includes the count of non-severe symptoms.
    """
    last_7_days = timezone.now().date() - timedelta(days=7)
    recent_logs = SymptomLog.objects.filter(patient=patient, date_logged__gte=last_7_days)

    features = {feature: 0 for feature in model_features}

    if recent_logs.exists():
        features['age'] = patient.user.age if patient.user.age else 30
        features['days_with_symptoms'] = (timezone.now().date() - recent_logs.order_by('date_logged').first().date_logged).days + 1
        
        # Calculate the non-severe symptom count
        non_severe_count = 0
        for log in recent_logs:
            if log.symptom not in HIGH_RISK_SYMPTOMS:
                non_severe_count += 1
        features['non_severe_symptom_count'] = non_severe_count

        # Set flags for high-risk symptoms
        for symptom in HIGH_RISK_SYMPTOMS:
            feature_name = f'has_{symptom.replace(" ", "_")}'
            if recent_logs.filter(symptom=symptom).exists():
                features[feature_name] = 1

    return pd.DataFrame([features], columns=model_features)



@login_required
def patientDashboard(request):
    appointments = None
    message = "Your health risk is currently low. Keep logging your symptoms."
    risk_level = 'low'
    risk_score = 0.0  # Default risk score

    # Define a threshold for a high number of non-severe symptoms
    NON_SEVERE_SYMPTOM_THRESHOLD = 7

    try:
        patient_instance = Patient.objects.get(user=request.user)

        # 1. Rule-Based Override for Immediate Critical Symptoms
        last_24_hours = timezone.now() - timedelta(hours=24)
        critical_logs = SymptomLog.objects.filter(
            patient=patient_instance,
            date_logged__gte=last_24_hours,
            symptom__in=HIGH_RISK_SYMPTOMS
        )
        
        if critical_logs.exists():
            # If severe symptoms are detected, set the risk level to high
            severe_symptoms_logged = [log.symptom for log in critical_logs]
            risk_level = 'high'
            risk_score = 1.0  # Severe symptoms set risk to 100%
            message = f"**Severe symptoms detected:** {', '.join(severe_symptoms_logged)}. Please visit a hospital immediately. ⚠️"
        
        else:
            # 2. Rule-based check for a high number of non-severe symptoms
            recent_non_severe_logs = SymptomLog.objects.filter(
                patient=patient_instance,
                date_logged__gte=last_24_hours,
            ).exclude(symptom__in=HIGH_RISK_SYMPTOMS)

            if recent_non_severe_logs.count() >= NON_SEVERE_SYMPTOM_THRESHOLD:
                # If the number of non-severe symptoms exceeds the threshold, set medium risk
                risk_level = 'medium'
                risk_score = 0.5  # Medium risk
                message = f"**Multiple symptoms detected:** You have logged a high number of non-severe symptoms in the last 24 hours. Please monitor your condition closely and consider consulting a doctor. ⚠️"
            
            else:
                # 3. AI-Powered Risk Analysis (only if no other rules are triggered)
                if model and model_features:
                    patient_features_df = get_patient_features(patient_instance)
                    
                    # Predict the probability of a severe outcome (class 1)
                    raw_score = model.predict_proba(patient_features_df)[0][1] * 100
                    
                    # Define risk thresholds based on the model's output
                    if raw_score > 70:
                        risk_level = 'high'
                        risk_score = 1.0  # Set risk to 100% for high risk
                        message = "Your risk level is high. Please consult a doctor immediately. ⚠️"
                    elif raw_score > 30:
                        risk_level = 'medium'
                        risk_score = 0.5  # Set risk to 50% for medium risk
                        message = "Your risk level is medium. Monitor your symptoms closely and consider a doctor's consultation. ⚠️"
                    else:
                        risk_level = 'low'
                        risk_score = (raw_score * 0.3)  # Set risk to a dynamic value between 0 and 30%
                        message = "Your health risk is currently low. Keep logging your symptoms. ✅"
                else:
                    message = "The risk analysis model is not available. Please contact support."

        # 4. Fetch Appointments
        appointments = AppointmentBooking.objects.filter(patient=patient_instance).order_by('-booked_on')
        if not appointments:
            message = "No appointments scheduled."

    except Patient.DoesNotExist:
        message = "No patient data found for this account. Please ensure your profile is complete."

    return render(request, 'core/patientDashboard.html', {
        'appointments': appointments,
        'message': message,
        'risk_level': risk_level,
        'risk_score': risk_score * 100,  # Send percentage for visual display
    })






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









#######################################################################################
#                                   DOCTOR
#######################################################################################



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




@login_required
def view_appointments(request):
    try:
        # Get the logged-in doctor instance
        doctor_instance = Doctor.objects.get(user=request.user)

        # Fetch all appointments related to the doctor
        appointments = AppointmentBooking.objects.filter(schedule__doctor=doctor_instance).order_by('-booked_on')

    except Doctor.DoesNotExist:
        appointments = None
        messages.error(request, "Doctor not found.")

    return render(request, 'core/view_appointments.html', {
        'appointments': appointments
    })



@login_required
def change_appointment_status(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(AppointmentBooking, id=appointment_id)

        # Ensure that the logged-in doctor is the one associated with this appointment
        if appointment.schedule.doctor.user == request.user:
            new_status = request.POST.get('status')
            if new_status in ['pending', 'confirmed', 'rejected']:
                appointment.status = new_status
                appointment.save()
                messages.success(request, 'Appointment status updated successfully!')
            else:
                messages.error(request, 'Invalid status selected.')
        else:
            messages.error(request, 'You do not have permission to change this appointment.')

    return redirect('view_appointments')



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
