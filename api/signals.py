from datetime import date
from .models import Statistics, Transaction


# @receiver(post_save, sender=Transaction)
def update_statistics(sender, instance, **kwargs):
    today = date.today()
    obj, created = Statistics.objects.get_or_create(date=today)
    obj.transactions += 1
    if instance.transaction_type == Transaction.PLATFORM_PROFIT:
        obj.profit += instance.amount
    obj.save()
