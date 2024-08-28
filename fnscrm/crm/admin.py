from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Field)
admin.site.register(QuestionAnswer)
admin.site.register(UserForPost)
admin.site.register(ConstantData)
admin.site.register(TagsForFind)
admin.site.register(СhatMembersCount)
admin.site.register(Department)
admin.site.register(RequestToAddModerators)
admin.site.register(StopPhrase)
admin.site.register(FeedbackFromUsers)
admin.site.register(FeedbackFromUsersLikeDislake)

@admin.register(QuestionAnswerLog)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['id_message', 'question', 'answer_text']
    search_fields = ("id_message", "question__icontains")