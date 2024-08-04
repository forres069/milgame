from django.contrib import admin
from adminsortable2.admin import SortableStackedInline, SortableAdminBase
from .models import Collection, Question
from django import forms

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('question_type', None)

class QuestionInline(SortableStackedInline):
    model = Question
    extra = 0
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset

class CollectionAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [QuestionInline]

admin.site.register(Collection, CollectionAdmin)
