from django.http import Http404
from django.db import transaction
from django.db.models import Q, Sum

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .utils.authentication import TokenAdminAuthentication

from .serializers import (
    UserCreateSerializer,
    WalletSerializer,
    TransactionSerializer,
    StatisticsSerializer,
)
from .models import Wallet, Transaction, Statistics


class UserCreateView(APIView):
    """
    Create a user and returns a token that will authenticate
    all other requests for this user.
    """

    serializer_class = UserCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response({"token": token.key}, status=status.HTTP_201_CREATED)


class WalletCreateView(APIView):
    """
    Create BTC wallet for the authenticated user. 1 BTC is
    automatically granted to the new wallet upon creation.
    User may register only up to 10 wallets.
    Returns wallet address and current balance in BTC and USD.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WalletSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer_class(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED,)


class WalletDetailView(APIView):
    """
    Returns wallet address and current balance in BTC and USD.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WalletSerializer

    def get_object(self, address, user):
        try:
            return Wallet.objects.get(address=address, user=user)
        except Exception:
            raise Http404

    def get(self, request, address):
        user = request.user
        wallet = self.get_object(address, user)
        serializer = self.serializer_class(wallet)
        return Response(serializer.data)


class TransactionCreateListView(APIView):
    """
    Transfers BTCs from one wallet to another.
    Transaction is free if transferred to own wallet.
    Transaction costs 1.5% of the transferred amount (profit of the platform) if
    transferred to a wallet of another user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        transactions = Transaction.objects.filter(
            Q(wallet_from__user=user) | Q(wallet_to__user=user)
        )
        serializer = self.serializer_class(transactions, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        user = request.user
        transfer = request.data
        serializer = self.serializer_class(data=transfer, context={"user": user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TransactionDetailView(APIView):
    """
    Returns all transactions related to specific wallet
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_object(self, address, user):
        try:
            return Wallet.objects.get(address=address, user=user)
        except Exception:
            raise Http404

    def get(self, request, address):
        user = request.user
        wallet = self.get_object(address, user)
        transactions = Transaction.objects.filter(
            Q(wallet_from=wallet) | Q(wallet_to=wallet)
        )
        serializer = self.serializer_class(transactions, many=True)
        return Response(serializer.data)


class StatisticsView(APIView):
    """
    Returns the total number of transactions and platform profit.
    Profit amount unit is BTC
    """

    authentication_classes = [TokenAdminAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = StatisticsSerializer

    def get(self, request, *args, **kwargs):
        stats = Statistics.objects.aggregate(
            transactions=Sum("transactions"), profit=Sum("profit")
        )
        serializer = self.serializer_class(stats)
        return Response(serializer.data)
