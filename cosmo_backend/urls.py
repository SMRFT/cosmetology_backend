from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cosmetology.urls')),
    path('_b_a_c_k_e_n_d/Cosmetology/', include('cosmetology.urls')),
]
