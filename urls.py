"""judge_announcements URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic.base import TemplateView

from announcements import views, jobs

urlpatterns = [
    path('admin/', admin.site.urls),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('',
         TemplateView.as_view(template_name='announcements/homepage.html'),
         name='home'),
    path('docs/',
         TemplateView.as_view(template_name='announcements/docs.html'),
         name='docs'),
    path('terms/',
         TemplateView.as_view(template_name='announcements/terms.html'),
         name='terms'),
    path('privacy/',
         TemplateView.as_view(template_name='announcements/privacy.html'),
         name='privacy'),
    path('support/',
         TemplateView.as_view(template_name='announcements/support.html'),
         name='support'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('status/', views.StatusView.as_view(), name='site_status'),
    path('status/run_fetch/', jobs.RunAnnouncementFetchJobNowView.as_view(),
         name='run_fetch'),
    path('status/run_router/', jobs.RunMessageRouterJobNowView.as_view(),
         name='run_router'),
    path('status/run_delivery/', jobs.RunMessageDeliveryJobNowView.as_view(),
         name='run_delivery'),

    path('destinations/list/', views.DestinationList.as_view(),
         name='destination_list'),
    path('destinations/detail/<int:pk>/', views.DestinationDetail.as_view(),
         name='destination_detail'),
    path('destinations/<int:pk>/remove/', views.DestinationRemoveAdmin.as_view(),
         name='destination_remove_admin'),

    path('announcements/create/',
         views.CreateAnnouncementView.as_view(),
         name='create_announcement'),
    path('announcements/success/',
         views.CreateAnnouncementSuccessView.as_view(),
         name='create_announcement_success'),

    path('slack/', views.SlackConnectView.as_view(), name='slack_connect'),
    path('slack/callback/', views.SlackCallbackView.as_view(), name='slack_callback'),
]
