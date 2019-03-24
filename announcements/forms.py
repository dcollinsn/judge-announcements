from django import forms

from announcements.models import ManualSource, ManualAnnouncement


class ManualAnnouncementForm(forms.ModelForm):
    headline = forms.CharField(required=False)
    url = forms.URLField(required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Set the choices for the MessageSource field
        self.fields['source'].choices = []
        for source in ManualSource.objects.filter(authorized_users=user):
          self.fields['source'].choices.append((source.id, source))


    def clean(self):
        super().clean()

        # Validate that we have some message
        if not self.cleaned_data['headline'] and\
           not self.cleaned_data['text']:
            self.add_error(None, forms.ValidationError(
                'You must provide at least a Headline or a Text body.'
            ))

        # Validate the MessageSource field
        if self.user not in self.cleaned_data['source'].subclass.authorized_users.all():
            self.add_error('source', forms.ValidationError(
                'You must choose a Source which you are allowed to post to.'
            ))

    def save(self):
        self.instance.user = self.user
        return super().save()

    class Meta:
        fields = ('source', 'headline', 'text', 'url')
        model = ManualAnnouncement
