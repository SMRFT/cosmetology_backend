PAGE_MAPPING = {

    # ==================== AUTH ====================
    '/_b_a_c_k_e_n_d/Cosmetology/get_roles/': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/get_roles/(\?.*)?$': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/registration/': 'SCC-P-USER',

    # ==================== BRANCH ====================
    '/_b_a_c_k_e_n_d/Cosmetology/branches/': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/toggle-branch-status/': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/user-branches/[^/]+/(\?.*)?$': 'SCC-P-USER',

    # ==================== PHARMACY ====================
    r'^/_b_a_c_k_e_n_d/Cosmetology/pharmacy/data/(\?.*)?$': 'SCC-P-PD',
    r'^/_b_a_c_k_e_n_d/Cosmetology/update_stock/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/check_medicine_status/(\?.*)?$': 'SCC-P-USER',

    # ==================== PATIENT ====================
    '/_b_a_c_k_e_n_d/Cosmetology/Patients_data/': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/Patients_data/[^/]+/$': 'SCC-P-USER',

    '/_b_a_c_k_e_n_d/Cosmetology/patients/': 'SCC-P-GP',
    r'^/_b_a_c_k_e_n_d/Cosmetology/patients/[^/]+/$': 'SCC-P-GP',

    # ==================== APPOINTMENT ====================
    '/_b_a_c_k_e_n_d/Cosmetology/Appointmentpost/': 'SCC-P-USER',
    # '/_b_a_c_k_e_n_d/Cosmetology/AppointmentView/': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/AppointmentView/(\?.*)?$': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/appointment/cancel/': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/get_doctors/(\?.*)?$': 'SCC-P-USER',

    # ==================== SUMMARY ====================
    r'^/_b_a_c_k_e_n_d/Cosmetology/summary/post/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/summary_get/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/summary/[^/]+/(\?.*)?$': 'SCC-P-SD',

    # ==================== BILLING ====================
    r'^/_b_a_c_k_e_n_d/Cosmetology/billing/[^/]+/(\?.*)?$': 'SCC-P-BD',
    r'^/_b_a_c_k_e_n_d/Cosmetology/procedurebilling/[^/]+/(\?.*)?$': 'SCC-P-PBD',

    '/_b_a_c_k_e_n_d/Cosmetology/save/billing/data/': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/update/billing/data/': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/delete/billing/data/': 'SCC-P-USER',

    r'^/_b_a_c_k_e_n_d/Cosmetology/get_patientbilling_data/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/get_patient_procedurebill_data/(\?.*)?$': 'SCC-P-USER',

    r'^/_b_a_c_k_e_n_d/Cosmetology/getnewbill/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/getnewprocedurebill/(\?.*)?$': 'SCC-P-USER',

    # ==================== MEDICAL ====================
    r'^/_b_a_c_k_e_n_d/Cosmetology/vitalform/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/diagnoses/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/complaints/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/Findings/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/Tests/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/Procedure/(\?.*)?$': 'SCC-P-USER',

    # ==================== PROCEDURE ====================
    '/_b_a_c_k_e_n_d/Cosmetology/Post_Procedure_Bill/': 'SCC-P-USER',
    '/_b_a_c_k_e_n_d/Cosmetology/delete_procedure_data/': 'SCC-P-USER',

    # ==================== OTHER ====================
    r'^/_b_a_c_k_e_n_d/Cosmetology/get_patient_details/(\?.*)?$': 'SCC-P-MH',
    r'^/_b_a_c_k_e_n_d/Cosmetology/check_upcoming_visits/(\?.*)?$': 'SCC-P-USER',
    r'^/_b_a_c_k_e_n_d/Cosmetology/get_medicine_price/(\?.*)?$': 'SCC-P-USER',
}


PAGE_ACTION_MAPPING = {
    'xxx': {
        'DELETE':'RWD',
    },
}

GEN_ACTION_MAPPING = {
    'POST': 'RW',
    'PUT': 'RW',
    'PATCH': 'RW',
    'DELETE': 'RW',
    'GET': 'R',
}
