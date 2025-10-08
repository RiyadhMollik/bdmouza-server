from django.contrib import admin
from solo.admin import SingletonModelAdmin
from lmsfeatures.models import CourseAudience, CourseContents, CourseFaqs, CourseLevel, CourseMilestones, CourseModules, CoursePrerequisit, CourseTopics, CourseType, Courses, EnrollCourse, InstallationStatus, Payment, PaymentMethods, SSLcommerceSettings

# Register your models here.
admin.site.register(CourseType)
admin.site.register(CourseLevel)
admin.site.register(CourseTopics)
admin.site.register(CourseFaqs)
admin.site.register(CoursePrerequisit)
admin.site.register(CourseAudience)
admin.site.register(CourseContents)
admin.site.register(CourseModules)
admin.site.register(CourseMilestones)
admin.site.register(Courses)
admin.site.register(EnrollCourse)
admin.site.register(Payment)
admin.site.register(InstallationStatus)
admin.site.register(PaymentMethods)
@admin.register(SSLcommerceSettings)
class SSLcommerceSettingsAdmin(SingletonModelAdmin):
    pass