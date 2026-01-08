from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('trello_backend/stores/', include('stores.urls')),
    path('trello_backend/users/', include('users.urls')),
    path('trello_backend/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('trello_backend/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)