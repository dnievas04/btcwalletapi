from django.urls import path
from .views import (
    UserCreateView,
    WalletCreateView,
    WalletDetailView,
    TransactionCreateListView,
    TransactionDetailView,
    StatisticsView,
)

urlpatterns = [
    path("users/", UserCreateView.as_view(), name="user-create"),
    path("wallets/", WalletCreateView.as_view(), name="wallet-create"),
    path("wallets/<str:address>", WalletDetailView.as_view(), name="wallet-detail"),
    path(
        "wallets/<str:address>/transactions/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    path("transactions/", TransactionCreateListView.as_view(), name="transaction-list"),
    path("statistics/", StatisticsView.as_view(), name="statistics"),
]
