from django.contrib import admin
from adminsortable2.admin import SortableTabularInline, SortableAdminBase


from . import models


class QuestionInline(SortableTabularInline):
    model = models.Question


class CollectionAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [QuestionInline]


admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.Game)
