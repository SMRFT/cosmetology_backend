from django.urls import path
from .views import registration,login,pharmacy_data,check_medicine_status,pharmacy_upload,delete_medicine,check_upcoming_visits,PatientDetailsView,save_billing_data,upload_file,get_file,update_stock,delete_billing_data,Complaints_list,Findings_list,Tests_list,Procedure_list,diagnosis_list,delete_procedure_data
from .views import get_pdf_file, upload_pdf,Patients_data,PatientView,Appointmentpost,AppointmentView,SummaryDetailCreate,vitalform,get_medicine_price,get_summary_by_interval,get_billing_by_interval,get_procedurebilling_by_interval,medical_history,update_billing_data,post_procedures_bill,get_procedures_bill,summary_get

urlpatterns = [
    path('registration/', registration, name='registration'),
    path('login/', login, name='login'),
    path('pharmacy/data/', pharmacy_data, name='pharmacy_data'),
    path('pharmacy/data/<str:medicine_name>/', delete_medicine, name='delete_medicine'),
    path('update_stock/', update_stock, name='update_stock'),
    path('pharmacy/upload/', pharmacy_upload, name='pharmacy_upload'),
    path('check_medicine_status/', check_medicine_status, name='check_medicine_status'),
    path('Patients_data/', Patients_data, name='Patients_data'),
    path('Patients_data/<str:patientUID>/', Patients_data, name='Patients_data_update'),
    path('patients/', PatientView, name='PatientView'),
    path('patients/<str:patientUID>/', PatientView, name='patient-detail'),
    path('Appointmentpost/', Appointmentpost, name='Appointmentpost'),
    path('AppointmentView/', AppointmentView, name='AppointmentView'),
    path('summary/post/', SummaryDetailCreate, name='summary-create'),
    path('summary/post/patient_details/', PatientDetailsView, name='patient-details'),
    path('summary_get/', summary_get, name='summary_get'),
    path('medicine_name/data/', get_medicine_price, name='get_medicine_price'),
    path('summary/<str:interval>/', get_summary_by_interval, name='summary-by-interval'),
    path('billing/<str:interval>/', get_billing_by_interval, name='get_billing_by_interval'),
    path('procedurebilling/<str:interval>/', get_procedurebilling_by_interval, name='get_procedurebilling_by_interval'),
    path('check_upcoming_visits/', check_upcoming_visits, name='check-upcoming-visits'),
    path('vitalform/', vitalform, name='vitalform'),
    path('diagnoses/', diagnosis_list, name='diagnosis-list'),
    path('complaints/', Complaints_list, name='Complaints_list'),
    path('Findings/', Findings_list, name='Findings_list'),
    path('Tests/', Tests_list, name='Tests_list'),
    path('Procedure/', Procedure_list, name='Procedure_list'),
    path('save/billing/data/', save_billing_data, name='save_billing_data'),
    path('update/billing/data/', update_billing_data, name='update_billing_data'),
    path('delete/billing/data/', delete_billing_data, name='delete_billing_data'),
    path('Post_Procedure_Bill/', post_procedures_bill, name='Procedure_post'),
    path('get_procedures_bill/', get_procedures_bill, name='Procedure_get'),
    path('get_patient_details/', medical_history, name='MedicalHistory'),
    path('upload_file/', upload_file, name='upload_file'),
    path('get_file/', get_file, name='get_file'),
    path('upload_pdf/', upload_pdf, name='upload_pdf'),
    path('delete_procedure_data/', delete_procedure_data, name='delete_procedure_data'),
    path('get_pdf_file/', get_pdf_file, name='get_pdf_file'),




]