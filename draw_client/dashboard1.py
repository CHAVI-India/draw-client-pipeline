"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'draw-client-main.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)

        # append a group for "Administration" & "Applications"
        # self.children.append(modules.Group(
        #     _('Group: Administration & Applications'),
        #     column=1,
        #     collapsible=True,
        #     children = [
        #         modules.AppList(
        #             _('Administration'),
        #             column=2,
        #             collapsible=False,
        #             models=('django.contrib.*',),
        #         ),
        #         modules.AppList(
        #             _('Applications'),
        #             column=2,
        #             css_classes=('collapse closed',),
        #             exclude=('django.contrib.*',),
        #         )
        #     ]
        # ))

        # self.children.append(modules.ModelList(
        #     _('Configurations'),
        #     collapsible=True,
        #     column=1,
        #     css_classes=('collapse closed',),
        #     models=('dicom_handler.CopyDICOM',),
        #             ),
        # )


        # # append an app list module for "Applications"
        # self.children.append(modules.AppList(
        #     _('AppList: Applications'),
        #     collapsible=True,
        #     column=1,
        #     css_classes=('collapse closed',),
        #     exclude=('django.contrib.*',),
        # ))

        # append an app list module for "Applications"
        # self.children.append(modules.AppList(
        #     _('AppList: Accounts'),
        #     collapsible=True,
        #     column=1,
        #     css_classes=('collapse closed',),
        #     exclude=('django.accounts.*',),
        # ))

         # Add DICOM Handler Models module
        self.children.append(modules.ModelList(
            _('DICOM Management'),
            column=1,
            collapsible=True,
            css_classes=('collapse closed',),
            models=(
                'dicom_handler.*',  # This will include all models from dicom_handler
            )
        ))

         # Add django-apscheduler module
        self.children.append(modules.ModelList(
            _('Scheduled Jobs'),
            column=1,
            collapsible=True,
            css_classes=('collapse closed',),
            models=(
                'django_apscheduler.models.DjangoJob',
                'django_apscheduler.models.DjangoJobExecution',
            ),
        ))

        # Add social accounts module
        self.children.append(modules.ModelList(
            _('Social Accounts'),
            column=1,
            collapsible=True,
            css_classes=('collapse closed',),
            models=(
                'allauth.socialaccount.models.SocialApp',
                'allauth.socialaccount.models.SocialAccount',
                'allauth.socialaccount.models.SocialToken',
            ),
        ))

        # append an app list module for "Administration"
        self.children.append(modules.ModelList(
            _('Administration'),
            column=1,
            collapsible=False,
            models=('django.contrib.*',),
        ))



        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('DRAW Template'),
            column=2,
            children=[
                {
                    'title': _('Create DRAW Template'),
                    'url': '/create-yml/',
                    'external': False,
                },
                {
                    'title': _('View DRAW Templates'),
                    'url': '/view-yml/',
                    'external': False,
                },
            ]
        ))

        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Support'),
            column=2,
            children=[
                {
                    'title': _('User Guide'),
                    'url': '',
                    'external': True,
                },
                {
                    'title': _('Source Code'),
                    'url': '',
                    'external': True,
                },
                {
                    'title': _('Report a Bug'),
                    'url': '',
                    'external': True,
                }
            ]
        ))

        # append a feed module
        self.children.append(modules.Feed(
            _('Latest Django News'),
            column=2,
            feed_url='http://www.djangoproject.com/rss/weblog/',
            limit=5
        ))

        # # append a recent actions module
        # self.children.append(modules.RecentActions(
        #     _('Recent actions'),
        #     limit=5,
        #     collapsible=False,
        #     column=3,
        # ))


