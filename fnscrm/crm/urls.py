from django.urls import include, re_path, path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    re_path(r'^$', login_required(views.ARMSpecialist.as_view()), name='index'),
    re_path(r'^test/(?P<pk>[-\w]+)$', login_required(views.ARMSpecialist.as_view()), name='test'),
    re_path(r'^data-base/(?P<pk>[-\w]+)$', login_required(views.LogMessagesListView.as_view()), name='data_base'),
    re_path(r'^log-messages$', login_required(views.LogMessagesListView.as_view()), name='log_messages'),
    re_path(r'^statistic-base$', login_required(views.StatisticListView.as_view()), name='statistic_base'),
    re_path(r'^statistic-detail', login_required(views.StatisticDetailtView.as_view()), name='statistic_detail'),
    re_path(r'^api/smart-response$', views.smart_response, name='smart_response'),
    re_path(r'^api/send-moder-response$', views.send_moder_response, name='send_moder_response'),
    re_path(r'^api/update-posts$', views.update_posts, name='update_posts'),
    re_path(r'^api/update-question-answer$', views.update_question_answer, name='update_question_answer'),
    re_path(r'^api/update-chat-members-count$', views.update_chat_members_count, name='update_chat_members_count'),
    re_path(r'^api/update-tags$', views.update_tags, name='update_tags'),
    re_path(r'^api/update-score-answer$', views.update_score_answer, name='update_score_answer'),
    re_path(r'^api/update-like-and-dislike-posts$', views.update_like_and_dislike_posts, name='update_like_and_dislike_posts'),
    re_path(r'^api/update-id-messages$', views.update_id_messages, name='update_id_messages'),
    re_path(r'^api/create-users-for-posts$', views.create_users_for_posts, name='create_users_for_posts'),
    re_path(r'^api/update-messages-it-last-message-in-dialog$', views.update_messages_it_last_message_in_dialog, name='update_messages_it_last_message_in_dialog'),
    re_path(r'^api$', include('rest_framework.urls')),
    re_path(r'^webpush/', include('webpush.urls')),
    re_path(r'^api/delete-response$', views.delete_response, name='delete_response'),
    re_path(r'^download-statistic$', login_required(views.download_statistic), name='download_statistic'),
    re_path(r'^moders$', login_required(views.RequestToAddModeratorsListView.as_view()), name='moders'),
    re_path(r'^moders-add$', login_required(views.RequestToAddModeratorsFormtView.as_view()), name='moders_add'),

    re_path(r'^moders-edit-request$', views.request_to_edit_moderators, name='moders_edit'),
    re_path(r'^moders-edit-request/(?P<pk>[-\w]+)$', views.request_to_edit_moderators_user, name='moders_edit_user'),
    re_path(r'^moders-edit-request-create$', views.request_to_edit_moderators_update, name='moders_edit_create'),
    re_path(r'^moders-edit-action/(?P<pk>[-\w]+)$', login_required(views.RequestToEditModeratorsAction.as_view()), name='moders-edit-acrion'),

    re_path(r'^moders-delete-request$', login_required(views.RequestToDeleteModeratorsFormtView.as_view()), name='moders_delete'),
    re_path(r'^moders-delete-action/(?P<pk>[-\w]+)$', login_required(views.RequestToDeleteModeratorsAction.as_view()), name='moders-delete-acrion'),

    re_path(r'^moders-create/(?P<pk>[-\w]+)$', login_required(views.RequestToAddModeratorsCreate.as_view()), name='moders_create'),
    re_path(r'^moders-delete/(?P<pk>[-\w]+)$', login_required(views.RequestToAddModeratorsDelete.as_view()), name='delete_request_moder'),
    re_path(r'^feedback$', login_required(views.FeedbackFromUsersListView.as_view()), name='feedback'),
    re_path(r'^feedback-add$', login_required(views.FeedbackFromUsersFormtView.as_view()), name='feedback_add'),
    re_path(r'^feedback-delete/(?P<pk>[-\w]+)$', login_required(views.FeedbackFromUsersDelete.as_view()), name='feedback_delete'),
    re_path(r'^feedback-update/(?P<pk>[-\w]+)$', login_required(views.FeedbackFromUsersUpdate.as_view()), name='feedback_update'),
    re_path(r'^update-like-dislike-feedback/(?P<pk>[-\w]+)/(?P<score>[-\w]+)$', views.update_like_dislike_feedback, name='update_like_dislike_feedback'),
]