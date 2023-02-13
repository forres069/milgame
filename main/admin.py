from django.contrib import admin
from adminsortable2.admin import SortableTabularInline, SortableAdminBase


from . import models


class QuestionInline(SortableTabularInline):
    model = models.Question
    extra = 0


class CollectionAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [QuestionInline]
