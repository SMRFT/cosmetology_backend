from django.urls import path
from . import views

urlpatterns = [
    path('registration/', views.registration, name='registration'),
    path('login/', views.login, name='login'),
    path('branches/', views.get_branches, name='get_branches'),
    path('pharmacy/data/', views.pharmacy_data, name='pharmacy_data'),
    path('pharmacy/data/<str:medicine_name>/', views.delete_medicine, name='delete_medicine'),
    path('update_stock/', views.update_stock, name='update_stock'),
    path('pharmacy/upload/', views.pharmacy_upload, name='pharmacy_upload'),
    path('check_medicine_status/', views.check_medicine_status, name='check_medicine_status'),
    path('Patients_data/', views.Patients_data, name='Patients_data'),
    path('Patients_data/<str:patientUID>/', views.Patients_data, name='Patients_data_update'),
    path('patients/', views.PatientView, name='PatientView'),
    path('patients/<str:patientUID>/', views.PatientView, name='patient-detail'),
    path('Appointmentpost/', views.Appointmentpost, name='Appointmentpost'),
    path('AppointmentView/', views.AppointmentView, name='AppointmentView'),
    path('summary/post/', views.SummaryDetailCreate, name='summary-create'),
    path('summary/post/patient_details/', views.PatientDetailsView, name='patient-details'),
    path('summary_get/', views.summary_get, name='summary_get'),
    path('medicine_name/data/', views.get_medicine_price, name='get_medicine_price'),
    path('summary/<str:interval>/', views.get_summary_by_interval, name='summary-by-interval'),
    path('billing/<str:interval>/', views.get_billing_by_interval, name='get_billing_by_interval'),
    path('procedurebilling/<str:interval>/', views.get_procedurebilling_by_interval, name='get_procedurebilling_by_interval'),
    path('check_upcoming_visits/', views.check_upcoming_visits, name='check-upcoming-visits'),
    path('vitalform/', views.vitalform, name='vitalform'),
    path('diagnoses/', views.diagnosis_list, name='diagnosis-list'),
    path('complaints/', views.Complaints_list, name='Complaints_list'),
    path('Findings/', views.Findings_list, name='Findings_list'),
    path('Tests/', views.Tests_list, name='Tests_list'),
    path('Procedure/', views.Procedure_list, name='Procedure_list'),
    path('save/billing/data/', views.save_billing_data, name='save_billing_data'),
    path('update/billing/data/', views.update_billing_data, name='update_billing_data'),
    path('delete/billing/data/', views.delete_billing_data, name='delete_billing_data'),
    path('Post_Procedure_Bill/', views.post_procedures_bill, name='Procedure_post'),
    path('get_procedures_bill/', views.get_procedures_bill, name='Procedure_get'),
    path('get_patient_details/', views.medical_history, name='MedicalHistory'),
    path('upload_file/', views.upload_file, name='upload_file'),
    path('get_file/', views.get_file, name='get_file'),
    path('upload_pdf/', views.upload_pdf, name='upload_pdf'),
    path('delete_procedure_data/', views.delete_procedure_data, name='delete_procedure_data'),
    path('get_pdf_file/', views.get_pdf_file, name='get_pdf_file'),




]