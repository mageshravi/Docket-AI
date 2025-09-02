import factory


class LitigantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.Litigant"


class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.Case"


class CaseLitigantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.CaseLitigant"


class ChatThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.ChatThread"
