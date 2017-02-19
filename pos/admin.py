from django.contrib import admin
from .models import *
admin.site.register(Item)
admin.site.register(Layout)
admin.site.register(Location)
admin.site.register(Transaction)
admin.site.register(LineItem)
# Register your models here.
