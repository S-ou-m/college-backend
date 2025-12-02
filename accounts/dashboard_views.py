from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Sum

from .models import Student, Course, Faculty, Holiday, FeeRecord


class AdminDashboardView(APIView):
    """Return summarized admin dashboard data"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total_students = Student.objects.count()
        total_courses = Course.objects.count()
        total_faculty = Faculty.objects.count()
        total_holidays = Holiday.objects.count()

        # Fee summary
        paid_fees = FeeRecord.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        pending_fees = FeeRecord.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
        overdue_fees = FeeRecord.objects.filter(status='overdue').aggregate(Sum('amount'))['amount__sum'] or 0

        data = {
            "students": total_students,
            "courses": total_courses,
            "faculty": total_faculty,
            "holidays": total_holidays,
            "fee_summary": {
                "paid": paid_fees,
                "pending": pending_fees,
                "overdue": overdue_fees,
            }
        }
        return Response(data)
