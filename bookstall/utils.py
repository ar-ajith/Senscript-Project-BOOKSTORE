import threading
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.html import strip_tags


class EmailThread(threading.Thread):
    def __init__(self,subject,message,recipient_list,is_html=True):
        self.subject=subject
        self.message=message
        self.is_html = is_html
        self.recipient_list=recipient_list
        threading.Thread.__init__(self)

    def run(self):
        if self.is_html:
            email = EmailMultiAlternatives(
                self.subject,
                strip_tags(self.message),  # fallback plain text
                settings.EMAIL_HOST_USER,
                self.recipient_list
            )
            email.attach_alternative(self.message, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=self.subject,
                message=self.message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=self.recipient_list,
                fail_silently=False
            )  