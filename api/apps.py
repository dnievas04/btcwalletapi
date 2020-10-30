from django.db.models.signals import post_save
from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        from .signals import update_statistics

        Transaction = self.get_model("Transaction")
        post_save.connect(update_statistics, sender=Transaction)
