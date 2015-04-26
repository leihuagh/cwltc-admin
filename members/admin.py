from django.contrib import admin
from members.models import (Person, Membership, Fees, Invoice, Payment, ItemType, InvoiceItem,
     Subscription, BarTransaction)
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Admin mods to support Excel import export
class PersonResource(resources.ModelResource):

    class Meta:
        model = Person

class MembershipResource(resources.ModelResource):

    class Meta:
        model = Membership

class FeesResource(resources.ModelResource):

    class Meta:
        model = Fees

class InvoiceResource(resources.ModelResource):

    class Meta:
        model = Invoice
 
class PaymentResource(resources.ModelResource):

    class Meta:
        model = Payment

class ItemTypeResource(resources.ModelResource):

    class Meta:
        model = ItemType
  
class InvoiceItemResource(resources.ModelResource):

    class Meta:
        model = InvoiceItem

class SubscriptionResource(resources.ModelResource):

    class Meta:
        model = Subscription
                     
class BarTransactionResource(resources.ModelResource):

    class Meta:
        model = BarTransaction

# Define admin classes
class PersonAdmin(ImportExportModelAdmin):
    resource_class = PersonResource
    pass

class MembershipAdmin(ImportExportModelAdmin):
    resource_class = MembershipResource
    pass

class SubscriptionAdmin(ImportExportModelAdmin):
    resource_class = Subscription
    pass

class FeesAdmin(ImportExportModelAdmin):
    resource_class = FeesResource
    pass

class InvoiceAdmin(ImportExportModelAdmin):
    resource_class = InvoiceResource
    pass

class PaymentAdmin(ImportExportModelAdmin):
    resource_class = PaymentResource
    pass

class ItemTypeAdmin(ImportExportModelAdmin):
    resource_class = ItemTypeResource
    pass
  
class InvoiceItemAdmin(ImportExportModelAdmin):
    resource_class = InvoiceItem
    pass

class ItemTypeAdmin(ImportExportModelAdmin):
    resource_class = ItemType
    pass

class BarTransactionAdmin(ImportExportModelAdmin):
    resource_class = MembershipResource
    pass

admin.site.register(Person, PersonAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Fees, FeesAdmin)
admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(ItemType, ItemTypeAdmin)
admin.site.register(InvoiceItem, InvoiceItemAdmin)
admin.site.register(BarTransaction, BarTransactionAdmin)