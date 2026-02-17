import factory


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "events.Event"
