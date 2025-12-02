from rest_framework import serializers
from .models import FeeRecord, Holiday, Student, Faculty, Course, Announcement
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, IntegrityError

User = get_user_model()


# --- Course Serializer ---
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


# --- Faculty Serializer ---
class FacultySerializer(serializers.ModelSerializer):
    # read/write mapped to the related User.email
    email = serializers.EmailField(source='user.email', required=True, write_only=False)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Faculty
        fields = ['id', 'username', 'email', 'department', 'designation', 'join_date', 'phone', 'assigned_courses']
        extra_kwargs = {
            "user": {"read_only": True},
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["email"] = instance.user.email if instance.user else None
        rep["username"] = instance.user.username if instance.user else None
        rep["assigned_courses"] = instance.assigned_courses if hasattr(instance, "assigned_courses") else []
        return rep

    def update(self, instance, validated_data):
        """
        Update Faculty without creating/updating a duplicate related user record.
        Email updates are applied to the related User model.
        """
        validated_data.pop('user', None)  # prevent DRF trying to overwrite user relation

        # update simple Faculty fields
        instance.department = validated_data.get('department', instance.department)
        instance.designation = validated_data.get('designation', instance.designation)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.join_date = validated_data.get('join_date', instance.join_date)
        instance.assigned_courses = validated_data.get('assigned_courses', instance.assigned_courses)

        # handle email on related user if provided
        if 'email' in validated_data:
            email_val = validated_data['email']
            if instance.user:
                instance.user.email = email_val
                instance.user.save()

        instance.save()
        return instance

    def create(self, validated_data):
        """
        Create a linked User and Faculty. Accepts 'user': {'email': ...} (because of source)
        Falls back to request.data['email'] if needed.
        """
        phone = validated_data.pop('phone', None)
        user_data = validated_data.pop('user', {}) or {}
        email = user_data.get('email')

        if not email:
            request = self.context.get('request')
            email = request.data.get('email') if request else None

        if not email:
            raise serializers.ValidationError({"email": "Email is required."})

        username = email.split("@")[0]
        password = "faculty123"

        try:
            with transaction.atomic():
                # try find existing user (case-insensitive)
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    # ensure minimum fields and role
                    if not user.username:
                        user.username = username
                    user.role = getattr(user, "role", "faculty")
                    user.email = email
                    user.save()
                else:
                    # create new user
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role="faculty"
                    )

                faculty = Faculty.objects.create(user=user, phone=phone, **validated_data)
                return faculty

        except IntegrityError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


# --- Student Serializer (ready to drop) ---
class StudentSerializer(serializers.ModelSerializer):
    """
    Handles both student creation (from admission form) and listing.
    - email: writable (write_only=True) so form POSTs include it and create() can use it.
    - name: writable CharField so DRF form shows Name and create() receives the student's full name.
    - username: read-only field coming from related User.
    """

    # ===== CHANGED/ADDED FIELDS (key fixes) =====
    # Make email writable (frontend must POST "email"). Previously it was read-only or computed,
    # which removed it from validated_data and broke create().
    email = serializers.EmailField(write_only=True, required=True)

    # Keep a writable name field so DRF form shows Name and create() can save it.
    # (If your Student model already has `name` this maps directly to it).
    name = serializers.CharField(required=False, allow_blank=True)

    # Username is read-only and pulled from linked User (if exists)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Student
        fields = "__all__"
        extra_kwargs = {
            "user": {"read_only": True},
            "course": {"required": True},
        }

    # ---------------------------
    # Representation (output)
    # ---------------------------
    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # Always include student's name from Student model (if present)
        rep["name"] = getattr(instance, "name", "") or ""

        # If user exists, include email & username as readable fields in output
        if hasattr(instance, "user") and instance.user:
            rep["email"] = getattr(instance.user, "email", None)
            rep["username"] = getattr(instance.user, "username", None)

            # If Student.name is empty, try to build name from user first/last
            full_name = f"{getattr(instance.user, 'first_name', '')} {getattr(instance.user, 'last_name', '')}".strip()
            if full_name and not rep["name"]:
                rep["name"] = full_name

        # readable course name & seat info for frontend convenience
        rep["course_name"] = instance.course.name if instance.course else None
        rep["seats_available"] = getattr(instance.course, "seats_available", None)

        return rep

    # ---------------------------
    # Create (uses writable email & name)
    # ---------------------------
    def create(self, validated_data):
        # IMPORTANT: email must be present (we declared it write_only required=True)
        email = validated_data.pop("email", None)
        # take name from validated_data if provided (writable)
        student_name = validated_data.get("name") or ""

        if not email:
            raise serializers.ValidationError({"email": "Email is required."})

        username = email.split("@")[0]
        password = "student123"

        # default values
        validated_data["admission_date"] = validated_data.get("admission_date") or timezone.now().date()
        validated_data["fees_paid"] = validated_data.get("fees_paid") or 0
        validated_data["total_fees"] = validated_data.get("total_fees") or 0

        # course is expected to be a Course instance (PrimaryKeyRelatedField in view)
        course = validated_data.get("course")

        try:
            with transaction.atomic():
                # lock course row to prevent race conditions
                if course is not None:
                    # course may already be an instance; ensure fresh select_for_update
                    course = Course.objects.select_for_update().get(pk=course.pk)
                    if course.seats_available <= 0:
                        raise serializers.ValidationError({"course": "No seats available in selected department."})

                # find or create user by email
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    # ensure username exists for display/login
                    if not user.username:
                        user.username = username
                    user.role = "student"
                    user.email = email
                    user.save()
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role="student"
                    )

                # attach user to student data
                validated_data["user"] = user

                # Ensure student's name saved to Student model (prefer posted name)
                if not validated_data.get("name"):
                    # fallback to user's full name or username
                    fallback_name = user.get_full_name() or user.username
                    validated_data["name"] = fallback_name
                else:
                    # If the student supplied a name and the user has no first/last,
                    # try to split it into first/last for user display consistency.
                    full_name = validated_data.get("name")
                    if full_name and not user.first_name:
                        parts = full_name.split(" ", 1)
                        user.first_name = parts[0]
                        user.last_name = parts[1] if len(parts) > 1 else ""
                        user.save()

                # create Student
                student = Student.objects.create(**validated_data)

                # decrement seats
                if course is not None:
                    course.seats_available = max(0, course.seats_available - 1)
                    course.save()

                # return fully populated instance
                student = Student.objects.select_related("user", "course").get(id=student.id)
                return student

        except IntegrityError as exc:
            raise serializers.ValidationError({"detail": f"Database error: {exc}"})
        
            
# --- User Serializer ---
class UserSerializer(serializers.ModelSerializer):
    """For returning user data (profile)."""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'enrollment_no'
        ]


# --- Fee Record Serializer ---
class FeeRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source="student.user.email", read_only=True)
    student_reg_no = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    mobile = serializers.SerializerMethodField()
    total_fees = serializers.SerializerMethodField()
    due = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()
    last_paid = serializers.SerializerMethodField()

    class Meta:
        model = FeeRecord
        fields = [
            "id",
            "student",
            "student_name",
            "student_email",
            "student_reg_no",
            "department",
            "mobile",
            "total_fees",
            "amount",
            "due",
            "overdue",
            "last_paid",
            "status",
            "date_paid",
        ]

    # ✅ Student name (Full)
    def get_student_name(self, obj):
        user = getattr(obj.student, "user", None)
        if not user:
            return "Unknown Student"
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username

    # ✅ Student registration number
    def get_student_reg_no(self, obj):
        return getattr(obj.student, "roll_number", "Not Assigned")

    # ✅ Department auto-fetch from student's course
    def get_department(self, obj):
        course = getattr(obj.student, "course", None)
        return getattr(course, "name", "-")

    # ✅ Mobile number (from student’s parent_contact if available)
    def get_mobile(self, obj):
        return getattr(obj.student, "parent_contact", "N/A")

    # ✅ Total fees
    def get_total_fees(self, obj):
        return float(getattr(obj.student, "total_fees", 0))

    # ✅ Due fees (total - paid)
    def get_due(self, obj):
        total = getattr(obj.student, "total_fees", 0) or 0
        paid = getattr(obj.student, "fees_paid", 0) or 0
        return float(total - paid)

    # ✅ Overdue (if pending for >30 days)
    def get_overdue(self, obj):
        from datetime import date
        if obj.status == "overdue":
            return float(obj.amount)
        return 0.0

    # ✅ Last paid (auto)
    def get_last_paid(self, obj):
        return obj.date_paid
    
        
# --- Register Serializer ---
class RegisterSerializer(serializers.ModelSerializer):
    """For registration (signup)."""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'password', 'password2', 'email',
            'first_name', 'last_name', 'role', 'department', 'enrollment_no'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# --- Announcement Serializer ---
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'target_audience', 'created_at']


# --- Holiday Serializer ---
class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'title', 'date']