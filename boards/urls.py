from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'boards', views.BoardViewSet)
router.register(r'lists', views.ListViewSet)
router.register(r'cards', views.CardViewSet)
router.register(r'comments', views.CommentViewSet)
router.register(r'checklists', views.ChecklistViewSet)
router.register(r'checklist-items', views.ChecklistItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]