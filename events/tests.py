import factory
import datetime
from factory.django import DjangoModelFactory
from django.test import TestCase
from .models import *
from members.models import Person, InvoiceItem, ItemType, Subscription
import logging

logger = logging.getLogger('factory').setLevel(logging.WARNING)

class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event
    name =  factory.Sequence(lambda n: f'event_name_{n}')
    cost = 10
    active = True


class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Sequence(lambda n: f'first_name_{n}')


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription


class TournamentFactory(DjangoModelFactory):
    class Meta:
        model = Tournament
    event_cost = 5
    draw_date = datetime.datetime.now()
    finals_date = draw_date

class ItemTypeFactory(DjangoModelFactory):
    class Meta:
        model = ItemType
    id = ItemType.SOCIAL


class TournamentItemTypeFactory(ItemTypeFactory):
    id = ItemType.TOURNAMENT


class EventTestCase(TestCase):

    def test_bill_social_event(self):
        social = ItemTypeFactory()
        event = EventFactory(active=False, item_type=social)
        event.description = 'My event'
        for i in range(10):
            event.add_person(PersonFactory())
        bill_data = event.billing_data()
        bill_data.process()
        items = InvoiceItem.objects.all()
        self.assertEqual(len(items), 10)
        for i in range(10):
            self.assertEqual(items[i].amount, 10)
            self.assertEqual(items[i].item_type_id, ItemType.SOCIAL)
            self.assertEqual(items[i].description, 'My event')
            self.assertEqual(items[i].person.first_name, f'first_name_{i}')

    def test_bill_tournament(self):
        TournamentItemTypeFactory()
        tournament = TournamentFactory()
        tournament.add_standard_events()
        main_events = Event.objects.filter(active=True)
        self.assertEqual(main_events.count(), 5)
        plate_events = Event.objects.filter(active=False)
        self.assertEqual(plate_events.count(), 3)
        # Each main event has 1 entrant so 5 people
        for event in main_events:
            event.add_person(PersonFactory())
        # Each plate event has 2 entrants so 6 people
        for event in plate_events:
            event.add_person(PersonFactory(), partner=PersonFactory())
        self.assertEqual(tournament.billed, False)
        # generate bills should return 0 because tournament is active
        self.assertEqual(tournament.generate_bills(), 0 )
        tournament.make_active(False)
        self.assertEqual(Event.objects.filter(active=True).count(), 0),
        self.assertEqual(tournament.generate_bills(), 5)
        self.assertEqual(InvoiceItem.objects.filter(amount=5).count(), 5)


