from ast import Module
from rest_framework import serializers


from globalapp.serializers import GlobalSerializers
from lmsfeatures.models import CourseContents, CourseMilestones, CourseModules, Courses, EnrollCourse, InstallationStatus, Payment, PaymentMethods, SSLcommerceSettings

# class CourseSerializer(GlobalSerializers):
#     class Meta:
#         model = Courses
#         fields = '__all__'
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
        
#         # Check if there are any milestones
#         if 'milestones' in representation:
#             for milestone in representation['milestones']:
#                 # Check if there are any modules
#                 if 'modules' in milestone:
#                     for module in milestone['modules']:
#                         # Check if there are any contents
#                         if 'contents' in module:
#                             for content in module['contents']:
#                                 # Remove the 'source' field if 'preview' is False
#                                 if not content.get('preview', False):
#                                     content.pop('source', None)
        
#         return representation

class CourseContentsSerializer(GlobalSerializers):
    class Meta:
        model = CourseContents # Adjust the model name
        fields = '__all__'

class CourseModulesSerializer(GlobalSerializers):
    contents = CourseContentsSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModules # Adjust the model name
        fields = '__all__'

class CourseMilestonesSerializer(GlobalSerializers):
    modules = CourseModulesSerializer(many=True, read_only=True)

    class Meta:
        model = CourseMilestones  # Adjust the model name
        fields = '__all__'

class CourseSerializer(GlobalSerializers):
    milestones = CourseMilestonesSerializer(many=True, read_only=True)

    class Meta:
        model = Courses
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # Check if the request user is enrolled in the course
        is_enrolled = False
        user_installation_statuses = set()
        user_payment_type = None

        if request and hasattr(request, 'user'):
            enrolled_course = EnrollCourse.objects.filter(user_id=request.user.id, course_id=instance.id).first()
            if enrolled_course:
                is_enrolled = True
                # Get the installation statuses and payment type of the enrolled course
                user_installation_statuses = set(enrolled_course.installation_status.values_list('id', flat=True))
                user_payment_type = enrolled_course.payment_type

        # Ensure milestones, modules, and contents are present and iterable
        if 'milestones' in representation and isinstance(representation['milestones'], list):
            for milestone in representation['milestones']:
                if 'modules' in milestone and isinstance(milestone['modules'], list):
                    for module in milestone['modules']:
                        if 'contents' in module and isinstance(module['contents'], list):
                            for content in module['contents']:
                                # If the payment type is 'full', allow access to all sources
                                if user_payment_type == EnrollCourse.Full:
                                    continue  # Skip any further conditions and give full access to source

                                # Get content's installment statuses as a set of IDs
                                content_installation_statuses = set(content['installment_status'])

                                # Only allow access to the source if the user has matching installment status or preview is True
                                has_matching_installation_status = any(
                                    status in user_installation_statuses for status in content_installation_statuses
                                )

                                if not is_enrolled and not content.get('preview', False):
                                    content.pop('source', None)
                                elif is_enrolled and user_payment_type != EnrollCourse.Full and not has_matching_installation_status:
                                    content.pop('source', None)

        return representation
    
class PaymentSerializer(GlobalSerializers):
    class Meta:
        model = Payment
        fields = '__all__'

class PaymentMethodsSerializer(GlobalSerializers):
    class Meta:
        model = PaymentMethods
        fields = '__all__'

class InstallationStatusSerializer(GlobalSerializers):
    class Meta:
        model = InstallationStatus
        fields = '__all__'

class EnrollCourseSerializer(GlobalSerializers):
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Courses.objects.all(),  # For writing the course ID
        required=True
    )
    course_details = CourseSerializer(source='course_id', read_only=True)
    class Meta:
        model = EnrollCourse
        fields = '__all__'

class SSLcommerceSettingsSerializer(GlobalSerializers):

    class Meta:
        model = SSLcommerceSettings # Adjust the model name
        fields = ['active_status','sandbox_status']