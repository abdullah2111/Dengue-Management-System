
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/',views.login_user, name='login' ),
    path('signup/', views.signup_view, name='signup' ),
    path('logout/', views.logout_user, name='logout'),


    path('patient_dashboard/', views.patient_dashboard, name='patient_dashboard'), 
    path('patientDashboard/', views.patientDashboard, name='PatientDashboard'), 
    path('check_dengue/', views.check_dengue, name='check_dengue'),
    path('track_symptoms/', views.track_symptoms, name='track_symptoms'),
    path('edit_symptom_log/<int:log_id>/', views.edit_symptom_log, name='edit_symptom_log'),
    path('delete_symptom_log/<int:log_id>/', views.delete_symptom_log, name='delete_symptom_log'),
    path('doctor_appointment/', views.doctor_appointment, name='doctor_appointment'),
    path('profile/',views.patient_profile, name='patient_profile'),
    path('edit_patient_profile/', views.edit_patient_profile, name='edit_patient_profile'),

    path('doctor_dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctorDashboard/', views.doctorDashboard, name='doctorDashboard'),
    path('appointment_schedule/', views.appointment_schedule, name='appointment_schedule'),
    path('edit_appointment_schedule/', views.edit_schedule, name='edit_appointment_schedule'),
    path('delete_appointment_schedule/<int:schedule_id>/', views.delete_schedule, name='delete_appointment_schedule'),
    path('view_appointments/', views.view_appointments, name='view_appointments'),
    path('change_appointment_status/<int:appointment_id>/', views.change_appointment_status, name='change_appointment_status'),
    path('view_patients/', views.view_patients, name='view_patients'),
    path('doctor_profile/', views.doctor_profile, name='doctor_profile'),
    path('edit_doctor_profile/', views.edit_doctor_profile, name='edit_doctor_profile'),
    
]