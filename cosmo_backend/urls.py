from django.contrib import admin
from django.urls import include, path
# project/urls.py
handler404 = 'cosmetology.views.custom_page_not_found'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cosmetology.urls')),
    path('_b_a_c_k_e_n_d/Cosmetology/', include('cosmetology.urls')),
]
