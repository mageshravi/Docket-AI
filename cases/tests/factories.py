import factory


class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "cases.Case"


class CaseLitigantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "cases.CaseLitigant"
