import factory


class LitigantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "litigants.Litigant"
