from django.apps import AppConfig


class NotifChatappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notif_chatapp'

    def ready(self):
        from apps.notif_chatapp import signals  # noqa
