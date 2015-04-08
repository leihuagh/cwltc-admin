import datetime
from members.models import Membership, Person, Fees, Subscription


def sub_creator(sub_year, sub_month, size = 100000):
    expiry_date = datetime.date(sub_year, sub_month, 1)
    expired_subs = Subscription.objects.filter(
        active=True
    ).filter(
        end_date__lt=expiry_date)
    remaining = expired_subs.count()
    count = 0
    for sub in expired_subs:
        new_sub = sub.renew(sub_year, sub_month, generate_item=True)
        count += 1
        if size == count:
            remaining = remaining -count
    return remaining

