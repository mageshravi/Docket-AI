import factory


class TimelineFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Timeline {n}")
    case = factory.SubFactory("cases.tests.factories.CaseFactory")

    class Meta:
        model = "events.Timeline"
