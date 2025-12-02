from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import Course, Student, Faculty, Holiday, FeeRecord
from .models import Announcement

admin.site.register(Course)
admin.site.register(Student)
admin.site.register(Faculty)
admin.site.register(Holiday)
admin.site.register(FeeRecord)
admin.site.register(Announcement)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'department', 'enrollment_no')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role']



