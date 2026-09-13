from infrastructure.email.tasks import send_email_task
from infrastructure.email.main_schemas import MailEvent


class MailGateway:

    @staticmethod
    def publish(event: MailEvent):

        payload = {
            "subject": event.subject,
            "body": event.body,
            "to": event.recipients,
            "html": event.html,
            "context": event.context,
        }

        send_email_task.delay(payload)