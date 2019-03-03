from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class MyOIDCAB(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user = super().create_user(claims)

        user.username = claims.get('preferred_username')
        user.first_name = claims.get('given_name')
        user.last_name = claims.get('family_name')
        user.save()

        return user

    def update_user(self, user, claims):
        user.username = claims.get('preferred_username')
        user.first_name = claims.get('given_name')
        user.last_name = claims.get('family_name')
        user.save()

        return user
