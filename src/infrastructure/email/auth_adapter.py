from allauth.account.adapter import DefaultAccountAdapter
from .tasks import send_email_task


class CustomAccountAdapter(DefaultAccountAdapter):

    def send_mail(self, template_prefix, email, context):

        msg = self.render_mail(template_prefix, email, context)

        html_body = None

        if msg.alternatives:
            html_body = msg.alternatives[0][0]

        payload = {
            "subject": msg.subject,
            "body": msg.body,
            "from_email": msg.from_email,
            "to": [email],
            "html_body": html_body,
        }

        send_email_task.delay(payload)



