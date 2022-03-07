import peewee
# from models.base import Model
from base import Model


class Website(Model):

    domain = peewee.CharField(index=True, null=True)
    securityTxtUrl = peewee.CharField(index=True, null=True)
    email = peewee.CharField(index=True, null=True)

    def select_equivalent(self):
        return self.__class__.get_or_none(self.__class__.domain == self.domain)