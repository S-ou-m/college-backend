import random
from rest_framework import generics, permissions, status  # type: ignore
from rest_framework.response import Response  # type: ignore
from rest_framework.views import APIView  # type: ignore
from .serializers import StudentSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Student
from .models import Faculty
from .models import Announcement
from .serializers import FacultySerializer


from .models import (
    Announcement,
    User,
    Student,
    Course,
    Faculty,
    Holiday,
    FeeRecord,
    PasswordResetToken
)
from .serializers import (
    RegisterSerializer,
    StudentSerializer,
    UserSerializer,
    HolidaySerializer
)
from rest_framework.permissions import AllowAny  # ✅ allows unauthenticated requests where needed


User = get_user_model()


# ======================================================
# 👤 ADMIN PROFILE
# ======================================================
class AdminProfileView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        })

    def put(self, request):
        user = request.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.email = request.data.get("email", user.email)
        user.save()
        return Response({"detail": "Profile updated successfully."}, status=status.HTTP_200_OK)


# ======================================================
# 🎓 STUDENT MANAGEMENT (CORE FIXED SECTION)
# ======================================================
class StudentListView(APIView):
    """Fetch and filter all students"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        dept = request.query_params.get("department")
        entry_type = request.query_params.get("entry_type")
        year = request.query_params.get("year")

        students = Student.objects.all()

        # ✅ Filter by department
        if dept:
            students = students.filter(course__name__icontains=dept)

        # ✅ Filter by entry type
        if entry_type:
            students = students.filter(mode_of_entry__icontains=entry_type)

        # ✅ Filter by year (extract from roll_number prefix)
        if year:
            # e.g. year=2023 → match roll_number starting with '23'
            year_suffix = str(year)[-2:]
            students = students.filter(roll_number__startswith=year_suffix)

        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentListCreateView(generics.ListCreateAPIView):
    """
    GET → List all students
    POST → Create a new student
    """
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.AllowAny]


# ✅ FIXED DELETE ENDPOINT (Now matches /api/auth/students/<id>/)
class StudentDetailView(APIView):
    """Retrieve, update, or delete a student"""
    permission_classes = [permissions.AllowAny]

    def get_object(self, pk):
        return get_object_or_404(Student, pk=pk)

    # --- DELETE ---
    def delete(self, request, pk):
        student = self.get_object(pk)
        linked_user = student.user

        student.delete()
        if linked_user:
            linked_user.delete()

        return Response(
            {"message": f"Student '{student}' deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

    # --- PUT (for edit modal) ---
    def put(self, request, pk):
        student = self.get_object(pk)
        serializer = StudentSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Student updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class StudentStatusUpdateView(APIView):
    """Update student's status (Active / Rusticated)"""
    permission_classes = [permissions.AllowAny]

    def patch(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        new_status = request.data.get("status")

        if new_status not in ["Active", "Rusticated"]:
            return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

        student.status = new_status
        student.save()
        return Response({"message": f"Student status updated to {new_status}."}, status=status.HTTP_200_OK)
    

# ======================================================
# 👨‍🏫 FACULTY MANAGEMENT
# ======================================================

class FacultyListCreateView(generics.ListCreateAPIView):
    """
    GET → List all faculty members
    POST → Create new faculty
    """
    queryset = Faculty.objects.all().select_related("user")
    serializer_class = FacultySerializer
    permission_classes = [permissions.AllowAny]


class FacultyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET → Retrieve single faculty by ID
    PUT/PATCH → Update faculty info or assigned courses
    DELETE → Remove faculty
    """
    queryset = Faculty.objects.all().select_related("user")
    serializer_class = FacultySerializer
    permission_classes = [permissions.AllowAny]

    def delete(self, request, *args, **kwargs):
        faculty = self.get_object()
        linked_user = faculty.user
        faculty.delete()
        if linked_user:
            linked_user.delete()
        return Response(
            {"message": "Faculty deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


# ======================================================
# 🧾 AUTH & REGISTRATION
# ======================================================
class RegisterView(generics.CreateAPIView):
    """Register new user"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


# ======================================================
# 🗓️ HOLIDAYS
# ======================================================
class HolidayListView(generics.ListAPIView):
    """List all holidays"""
    queryset = Holiday.objects.all().order_by('date')
    serializer_class = HolidaySerializer
    permission_classes = [permissions.AllowAny]


# ======================================================
# 🙍 USER PROFILE (SELF)
# ======================================================
class MeView(generics.RetrieveAPIView):
    """Return logged-in user's profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ======================================================
# 🚪 LOGOUT
# ======================================================
class LogoutView(APIView):
    """Logout user and blacklist refresh token"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ======================================================
# 📊 ADMIN DASHBOARD OVERVIEW
# ======================================================
class AdminDashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = {
            "students": Student.objects.count(),
            "courses": Course.objects.count(),
            "faculty": Faculty.objects.count(),
            "holidays": Holiday.objects.count(),
            "fee_summary": {
                "paid": FeeRecord.objects.filter(status="paid").aggregate(Sum('amount'))['amount__sum'] or 0,
                "pending": FeeRecord.objects.filter(status="pending").aggregate(Sum('amount'))['amount__sum'] or 0,
                "overdue": FeeRecord.objects.filter(status="overdue").aggregate(Sum('amount'))['amount__sum'] or 0,
            },
        }
        return Response(data)


# ======================================================
# 📈 REPORTS
# ======================================================
class ReportsView(APIView):
    """Generate summarized report data"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = {
            "total_students": Student.objects.count(),
            "total_faculty": Faculty.objects.count(),
            "total_courses": Course.objects.count(),
            "total_holidays": Holiday.objects.count(),
            "total_announcements": Announcement.objects.count(),
            "fee_summary": {
                "paid": FeeRecord.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
                "total": FeeRecord.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
            }
        }
        return Response(data)

# ======================================================
# 📢 ANNOUNCEMENTS MANAGEMENT
# ======================================================
from .serializers import AnnouncementSerializer

class AnnouncementListCreateView(generics.ListCreateAPIView):
    """
    GET → List all announcements (newest first)
    POST → Create a new announcement
    """
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.AllowAny]
    
# ======================================================
# 📢 ANNOUNCEMENT DETAIL (GET, DELETE)
# ======================================================
from rest_framework import generics, permissions
from .models import Announcement
from .serializers import AnnouncementSerializer

class AnnouncementDetailView(generics.RetrieveDestroyAPIView):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.AllowAny]
    
    
# ======================================================
# 💰 FEE RECORD MANAGEMENT
# ======================================================
from .serializers import FeeRecordSerializer

class FeeRecordListCreateView(generics.ListCreateAPIView):
    """
    GET → List all fee records
    POST → Add new fee record
    """
    queryset = FeeRecord.objects.all().select_related("student__user")
    serializer_class = FeeRecordSerializer
    permission_classes = [permissions.AllowAny]


class FeeRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET → Retrieve one fee record
    PUT/PATCH → Update payment info (e.g. mark as Paid)
    DELETE → Remove a fee record
    """
    queryset = FeeRecord.objects.all().select_related("student__user")
    serializer_class = FeeRecordSerializer
    permission_classes = [permissions.AllowAny]
    
# ======================================================
# 📊 FEE SUMMARY AGGREGATION (for Dashboard)
# ======================================================
from django.db.models import Sum

class FeeSummaryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = {
            "paid": FeeRecord.objects.filter(status="paid").aggregate(Sum('amount'))['amount__sum'] or 0,
            "pending": FeeRecord.objects.filter(status="pending").aggregate(Sum('amount'))['amount__sum'] or 0,
            "overdue": FeeRecord.objects.filter(status="overdue").aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        return Response(data, status=status.HTTP_200_OK)

# ======================================================
# 🔐 CHANGE PASSWORD
# ======================================================
class ChangePasswordView(APIView):
    """Change admin password"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not check_password(old_password, user.password):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


# ======================================================
# 🔑 PASSWORD RESET (EMAIL OTP)
# ======================================================
class RequestResetView(APIView):
    """Step 1: Request a password reset - generates OTP/token and emails it"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No user found with that email"}, status=status.HTTP_404_NOT_FOUND)

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        token_entry = PasswordResetToken.objects.create(user=user, email=email, code=otp_code)

        # Send OTP Email
        try:
            send_mail(
                subject="Your Synergy Portal Password Reset OTP",
                message=(
                    f"Hello {user.username},\n\n"
                    f"Here is your password reset OTP: {otp_code}\n\n"
                    f"This OTP is valid for 10 minutes.\n\n"
                    f"If you did not request a password reset, please ignore this email.\n\n"
                    f"— Synergy Institute Portal"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Password reset OTP has been sent to your email address.",
            "token": str(token_entry.token)
        }, status=status.HTTP_200_OK)


class ConfirmResetView(APIView):
    """Step 2: Confirm password reset with OTP"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not all([email, otp, new_password]):
            return Response({"error": "Email, OTP, and new password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_entry = PasswordResetToken.objects.filter(email=email, code=otp).latest("created_at")
        except PasswordResetToken.DoesNotExist:
            return Response({"error": "Invalid OTP or email"}, status=status.HTTP_400_BAD_REQUEST)

        if not token_entry.is_valid():
            return Response({"error": "OTP expired. Please request again."}, status=status.HTTP_400_BAD_REQUEST)

        user = token_entry.user
        user.set_password(new_password)
        user.save()

        token_entry.delete()
        return Response({"message": "Password reset successful!"}, status=status.HTTP_200_OK)