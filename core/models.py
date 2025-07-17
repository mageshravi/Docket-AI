from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    This can be used to add additional fields or methods in the future.
    """

    # Additional fields can be added here if needed

    class Meta:
        db_table = "dkt_users"

    def __str__(self):
        return self.username
