import factory


class ChatThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.ChatThread"


class ChatMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.ChatMessage"


class UploadedFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.UploadedFile"


class ParsedEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.ParsedEmail"


class ParsedEmailAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "poc.ParsedEmailAttachment"
