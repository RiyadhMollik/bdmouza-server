from django.db.models.signals import post_save, pre_delete,pre_save,m2m_changed
from django.dispatch import receiver

from lmsfeatures.models import Courses, EnrollCourse, Payment

@receiver(post_save, sender=Payment)
def shifts_effecter(sender, instance, created, **kwargs):
    print(instance)
    if instance.payment_status == "confirm":
        # Check if enrollment already exists
        enroll_course = EnrollCourse.objects.filter(course_id=instance.course_id, user_id=instance.user_id).first()

        if not enroll_course:
            # If no existing enrollment, create a new one
            enroll_course = EnrollCourse.objects.create(
                course_id=instance.course_id,
                user_id=instance.user_id,
                payment_type=instance.payment_type,
                amount=instance.amount
            )
            if instance.payment_type == "installment":
                enroll_course.installation_status.set(instance.installation_status.all())  # or use specific installments
                enroll_course.save()

        else:
            # Update the existing enrollment
            enroll_course.payment_type = instance.payment_type
            enroll_course.amount = enroll_course.amount+instance.amount

            if instance.payment_type == "installment":
                enroll_course.installation_status.add(*instance.installation_status.all())  # Update installment status

            enroll_course.save()
            print(f"Updated enrollment for user {instance.user_id} in course {instance.course_id}")