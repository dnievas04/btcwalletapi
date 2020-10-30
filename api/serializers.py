import uuid
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings

from rest_framework import serializers

from .models import Wallet, Transaction, Statistics, get_platform_wallet


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Basic serializer used to create users. Uses django'user model
    """

    class Meta:
        model = User
        fields = ("username", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User(username=validated_data["username"])
        user.set_password(validated_data["password"])
        user.save()
        return user


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer used to create BTC wallet and view detail.
    After wallet creation, platform transfer (grant) 1 BTC
    to the owner of the wallet.
    """

    address = serializers.ReadOnlyField()
    balance = serializers.ReadOnlyField()

    class Meta:
        model = Wallet
        fields = ("address", "alias", "balance")

    def validate(self, data):
        user = self.context.get("user")
        user_wallets = Wallet.objects.filter(user=user).count()
        if user_wallets >= 10:
            raise serializers.ValidationError(
                "User may register only up to 10 wallets."
            )
        return data

    def validate_alias(self, value):
        user = self.context.get("user")
        try:
            Wallet.objects.get(user=user, alias=value)
            raise serializers.ValidationError("Alias already exists for another wallet")
        except Wallet.DoesNotExist:
            pass
        return value

    def create(self, validated_data):
        user = self.context.get("user")
        alias = (validated_data.get("alias", "")).strip()
        address = uuid.uuid4()
        if alias == "" or alias is None:
            alias = str(address)
        last_updated = timezone.now()
        user_wallet = Wallet(
            address=address, alias=alias, user=user, last_updated=last_updated
        )
        user_wallet.save()
        # Grant 1 BTC after wallet creation
        platform_wallet = get_platform_wallet()
        transfer_grant_btc = {
            "wallet_from": str(platform_wallet.address),
            "wallet_to": str(user_wallet.address),
            "transaction_type": Transaction.PLATFORM,
            "amount": 1.00000000,
            "created_at": last_updated,
            "extra": "Platform grants 1 BTC after wallet creation.",
        }
        serializer = TransactionSerializer(
            data=transfer_grant_btc, context={"user": platform_wallet.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return user_wallet


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer used to create transactions when transfer bitcoins
    between wallets, used to list those transactions.
    """

    wallet_from = serializers.UUIDField()
    wallet_to = serializers.UUIDField()
    details = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()

    class Meta:
        model = Transaction
        fields = (
            "transaction_type",
            "wallet_from",
            "wallet_to",
            "amount",
            "details",
            "extra",
            "created_at",
        )

    def create(self, validated_data):
        """
        Transfer BTCs from one wallet to another wallet.
        """
        wallet_from = Wallet.objects.get(address=validated_data["wallet_from"])
        wallet_to = Wallet.objects.get(address=validated_data["wallet_to"])
        transaction = Wallet.transfer(
            wallet_from=wallet_from,
            wallet_to=wallet_to,
            transaction_type=validated_data["transaction_type"],
            amount=validated_data["amount"],
            extra=validated_data.get("extra", ""),
        )
        return transaction

    def validate(self, data):
        """
        Performs all required validations before init transactions
        """
        user = self.context.get("user")
        transaction_type = data.get("transaction_type")
        wallet_to = data.get("wallet_to")
        wallet_from = data.get("wallet_from")
        amount = data.get("amount")

        wallet = self.validate_origin_address(wallet_from, user)
        self.validate_wallet_funds(wallet, amount, transaction_type)

        if transaction_type == Transaction.SENT_INTERNAL:
            self.validate_internal_destination_address(wallet_to, user)

        if transaction_type == Transaction.SENT_EXTERNAL:
            self.validate_external_destination_address(wallet_to, user)
            self.validate_minimum_transaction_amount(amount)
        return data

    def validate_origin_address(self, address, user):
        """
        Check wallet address belongs to the user who want to transfer BTCs
        """
        try:
            return Wallet.objects.get(user=user, address=address)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                f"Invalid from wallet with address {address}"
            )

    def validate_internal_destination_address(self, address, user):
        """
        Checks that the internal address to transfer to, belongs to the user
        who performs the transaction.
        """
        try:
            Wallet.objects.get(user=user, address=address)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid internal wallet/address to transfer."
            )

    def validate_external_destination_address(self, address, user):
        """
        Checks that the external address to transfer to, not belongs to the user
        who performs the transaction.
        """
        try:
            Wallet.objects.get(~Q(user=user), address=address)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid external wallet/address to transfer."
            )

    def validate_minimum_transaction_amount(self, amount):
        """
        Transfers to others users requiere a minimum amount to transfer
        """
        minimum_amount = Decimal(settings.PLATFORM_TRANSACTION_LIMITS)
        if amount < minimum_amount:
            raise serializers.ValidationError(
                f"The minimum amount of bitcoins you can send in a transaction "
                f"to another user is {minimum_amount} BTCs"
            )

    def validate_wallet_funds(self, wallet, amount, transaction_type):
        """
        Checks the user's wallet has enough funds to transfer the specified
        amount, including profit if required
        """
        balance = wallet.balance_btc
        profit = Transaction.calculate_profit(amount, transaction_type)
        if balance - amount - (amount * profit) < 0:
            raise serializers.ValidationError(
                f"Insufficient funds in wallet with address {wallet.address}"
            )


class StatisticsSerializer(serializers.ModelSerializer):
    transactions = serializers.ReadOnlyField()

    class Meta:
        model = Statistics
        fields = (
            "transactions",
            "profit",
        )
        extra_kwargs = {
            "profit": {"max_digits": 16, "decimal_places": 8, "read_only": True}
        }
