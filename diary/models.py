from datetime import datetime
from django.db import models
from members.models import Person
from django.core.mail import send_mail

class Booking(models.Model):
    date = models.DateField()
    time = models.TimeField()
    court = models.PositiveSmallIntegerField()
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True)
    player_2 = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='player_2')
    player_3 = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='player_3')
    player_4 = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='player_4')
    note = models.CharField(max_length=100, blank=True)
    blocked = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.date} {self.time} {self.court} {self.person.fullname}'

    def mail_players(self, update=False, delete=False):
        """ mail all the players included in a booking"""
        subject = "Coombe Wood Court Booking"
        from_email = "bookings@coombewoodltc.co.uk"
        recipient_list = [self.person.email, self.player_2.email]
        players = f'{self.person.fullname}, {self.player_2.fullname}'
        if self.player_3:
            recipient_list.append(self.player_3.email)
            players += f', {self.player_3.fullname}'
        if self.player_4:
            recipient_list.append(self.player_4.email)
            players += f', {self.player_4.fullname}'
        action = 'deleted the booking for' if delete else 'booked'

        message = f'''{self.person.fullname} has {action} court {self.court} on {str(self.date)} at {str(self.time)}.'''
        message += f'\nPlayers: {players}\n{self.note}'''
        if update:
            message += '\nThis is an update to an existing booking.'
        message += '\nReplies to this email are ignored.'
        send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list)

    @classmethod
    def delete_expired(cls):
        bookings = Booking.objects.filter(date__lt=datetime.now())
        bookings.delete()