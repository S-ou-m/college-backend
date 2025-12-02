from django.urls import path
from .views import (
    AdminProfileView, AnnouncementDetailView, AnnouncementListCreateView, ChangePasswordView, FeeRecordDetailView, FeeRecordListCreateView, HolidayListView,
    RegisterView, MeView, LogoutView, ReportsView,
    RequestResetView, ConfirmResetView,
    StudentListCreateView,
    StudentDetailView,
    StudentStatusUpdateView,
    
)

from .views import AnnouncementListCreateView, AnnouncementDetailView
from .dashboard_views import AdminDashboardView
from .announcement_views import AnnouncementListView
from .report_views import FeeSummaryView
from .management_views import (
    FacultyListCreateView, 
    FacultyDetailView,
    CourseListView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


# ======================================================
# ✅ URL PATTERNS (ORGANIZED)
# ======================================================

urlpatterns = [
    # ===============================
    # 🔐 AUTHENTICATION & TOKEN ROUTES
    # ===============================
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', MeView.as_view(), name='auth_me'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),   # login
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),                 # logout
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('profile/', AdminProfileView.as_view(), name='admin_profile'),

    # ===============================
    # 📊 DASHBOARD & REPORTS
    # ===============================
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('reports/', ReportsView.as_view(), name='reports'),
    path('fees/summary/', FeeSummaryView.as_view(), name='fee_summary'),

    # ===============================
    # 🧑‍🎓 STUDENT ADMISSION
    # ===============================
    
    
    # ===============================
    # 💰 Fee Records
    # ===============================
    path('fees/', FeeRecordListCreateView.as_view(), name='fee_list'),
    path('fees/<int:pk>/', FeeRecordDetailView.as_view(), name='fee_detail'),
    # 💰 Fee Summary (for Dashboard)
    path('fees/summary/', FeeSummaryView.as_view(), name='fee_summary'),

    # ===============================
    # 🧑‍🎓 STUDENT MANAGEMENT (FIXED)
    # ===============================

    path("students/", StudentListCreateView.as_view(), name="student-list-create"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
    path("student-status/<int:pk>/", StudentStatusUpdateView.as_view(), name="student-status"),

    # ===============================
    # 👨‍🏫 FACULTY MANAGEMENT
    # ===============================
    path('faculty/', FacultyListCreateView.as_view(), name='faculty_list'),
    path('faculty/<int:pk>/', FacultyDetailView.as_view(), name='faculty_detail'),

    # ===============================
    # 📚 COURSES
    # ===============================
    path('courses/', CourseListView.as_view(), name='course_list'),

    # ===============================
    # 📢 ANNOUNCEMENTS
    # ===============================
    path('announcements/', AnnouncementListCreateView.as_view(), name='announcement-list-create'),
    path('announcements/<int:pk>/', AnnouncementDetailView.as_view(), name='announcement-detail'),        
    # ===============================
    # 🗓️ HOLIDAYS
    # ===============================
    path('holidays/', HolidayListView.as_view(), name='holiday_list'),

    # ===============================
    # 🔑 PASSWORD RESET (OTP)
    # ===============================
    path("forgot-password/", RequestResetView.as_view(), name="forgot-password"),
    path("reset-password/", ConfirmResetView.as_view(), name="reset-password"),
]