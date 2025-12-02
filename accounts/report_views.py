from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum
from .models import FeeRecord

class FeeSummaryView(APIView):
    """Return total paid, pending, and overdue fee amounts"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        paid = FeeRecord.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        pending = FeeRecord.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
        overdue = FeeRecord.objects.filter(status='overdue').aggregate(Sum('amount'))['amount__sum'] or 0

        data = {
            "paid": paid,
            "pending": pending,
            "overdue": overdue
        }
        return Response(data)
