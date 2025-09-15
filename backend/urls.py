from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from codes.views import (
    import_codes_view,
    import_giftcards_view,
    import_stockblecode_view,
)
from payments.views import webhook_fars, codeepay_webhook

api_v1_patterns = [
    path("api/v1/", include("api.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("liveconfigs/", include("liveconfigs.urls"), name="liveconfigs"),
    path("import/uccodes/", import_codes_view, name="import_codes"),
    path("import/giftcards/", import_giftcards_view, name="import_giftcards"),
    path("import/stockblecode/", import_stockblecode_view, name="import_stockblecode"),
    path("webhook/fars/", webhook_fars, name="webhook_fars"),
    path("webhook/codeepay/", codeepay_webhook, name="webhook_codeepay"),
    path("", include(api_v1_patterns)),
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(patterns=api_v1_patterns),
        name="schema",
    ),
    path("api/v1/docs/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path(
        "api/v1/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
