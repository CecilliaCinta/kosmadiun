from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chatbot/", views.chatbot, name="chatbot"),
    path("rekomendasi/", views.rekomendasi, name="rekomendasi"),
    path("data-kos/", views.data_kos, name="data_kos"),
    path("pencarian-kos/", views.pencarian_kos, name="pencarian_kos"),
    path("analisis-harga/", views.analisis_harga, name="analisis_harga"),
    path("sebaran-kos/", views.sebaran_kos, name="sebaran_kos"),
    path("chatbot-ai/", views.halaman_chatbot, name="halaman_chatbot"),
    path("", views.dashboard, name="dashboard"),
    path("jelaskan-grafik/", views.jelaskan_grafik, name="jelaskan_grafik"),
]