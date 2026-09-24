from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView


class SafeTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ObjectDoesNotExist as exc:
            raise InvalidToken("用户不存在或登录状态已失效。") from exc
