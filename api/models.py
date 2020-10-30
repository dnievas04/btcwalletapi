import uuid
from decimal import Decimal, ROUND_DOWN

from django.utils import timezone
from django.conf import settings
from django.db import models, transaction
from django.contrib.auth.models import User

from .utils.rates import Rates


def get_platform_user():
    """
    Returns the user who owns the wallet of the platform. For
    simplicity we assume the platform grants bitcoins to other
    users using it's own wallet. Profits are transfer to this
    wallet too.
    """
    try:
        platform_user = User.objects.get(username=settings.PLATFORM_WALLET_USER_NAME)
    except User.DoesNotExist:
        platform_user = User.objects.create_user(
            username=settings.PLATFORM_WALLET_USER_NAME,
            password=settings.PLATFORM_WALLET_USER_PASSWORD,
        )
    return platform_user


def get_platform_wallet():
    """
    Returns the wallet used by the platform to transfer bitcoins
    to other wallets of the platform, or to receive bitcoins from
    profits.
    """
    platform_user = get_platform_user()
    last_updated = timezone.now()
    platform_wallet, created = Wallet.objects.get_or_create(
        address=settings.PLATFORM_WALLET_ADDRESS,
        user=platform_user,
        defaults={
            "address": settings.PLATFORM_WALLET_ADDRESS,
            "user": platform_user,
            "alias": "Platform Wallet",
            "last_updated": last_updated,
        },
    )
    # Add some BTCs
    transaction = Transaction(
        wallet_to=platform_wallet,
        transaction_type=Transaction.PLATFORM,
        amount=1000,
        details="Initial funds",
        created_at=last_updated,
    )
    transaction.save()
    return platform_wallet


class Wallet(models.Model):
    """
    Wallet model simulates a BTC Wallet. Each wallet has an address and
    belongs to a user. Users are allowed to register up to 10 wallets.
    Wallets are required to perform transactions(send and receive btc)
    between users.
    """

    address = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alias = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    created = models.DateTimeField(auto_now_add=True)
    last_updated = (
        models.DateTimeField()
    )  # Just a flag to 'associate' with the last transfer transaction

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "alias"], name="unique_user_alias")
        ]

    def __str__(self):
        return f"{str(self.address)}"

    @property
    def balance(self):
        """
        Returns current balance in BTC and USD.
        """
        total_btc = self.balance_btc
        total_usd = Rates.bitcoins_to_usd(total_btc)
        return {"btc": str(total_btc), "usd": str(total_usd)}

    @property
    def balance_btc(self):
        """
        Calculate and returns total BTCs based on transactions data.
        """
        total_debits = self.transactions_debits.filter().aggregate(
            total=models.Sum("amount")
        )["total"]

        total_credits = self.transactions_credits.filter().aggregate(
            total=models.Sum("amount")
        )["total"]
        total = (total_debits or 0) - (total_credits or 0)
        return total

    @classmethod
    def transfer(cls, wallet_from, wallet_to, transaction_type, amount, extra):
        """
        Transfers bitcoins from one wallet to another. Creates a transaction
        to register the 'movements'
        """
        with transaction.atomic():
            # Try to prevents race condition acquiring a lock on the 'from' wallet.
            # This will lock the wallet row in the database, therefore, no
            # one wil can init another transfer with the same wallet, until the
            # transaction is completed (either committed or rolled-back).
            wallet = cls.objects.select_for_update().get(address=wallet_from.address)
            balance = wallet.balance_btc
            profit = Decimal("0.0")
            if transaction_type == Transaction.SENT_EXTERNAL:
                profit = Decimal(settings.PLATFORM_PROFIT)
            if balance - amount - (amount * profit) < 0:
                raise Exception(
                    f"Insufficient funds in wallet with address {wallet.address}"
                )
            # The wallet and transactions will have the same updated flag.
            last_updated = timezone.now()

            wallet.last_updated = last_updated
            wallet.save(
                update_fields=["last_updated",]
            )

            transaction_obj = Transaction.objects.create(
                wallet_from=wallet_from,
                wallet_to=wallet_to,
                transaction_type=transaction_type,
                amount=amount,
                extra=extra,
                created_at=last_updated,
                details=f"Transfers {amount} bitcoins from {str(wallet_from.address)} "
                f"wallet to {str(wallet_to.address)} wallet.",
            )
            # If transferred to a wallet of another user, we need to
            # transfer platform profit.
            if transaction_type == Transaction.SENT_EXTERNAL:
                Transaction.objects.create(
                    wallet_from=wallet_from,
                    wallet_to=get_platform_wallet(),
                    transaction_type=Transaction.PLATFORM_PROFIT,
                    amount=Transaction.calculate_profit(amount, transaction_type),
                    created_at=last_updated,
                    details="Platform profits. 1,5% of the transferred amount",
                )
        return transaction_obj


class Transaction(models.Model):
    """
    Transaction model storage all the information related to transfers
    from one wallet to another wallet.
    For simplicity all transactions amount must be in bitcoins units,
    although balance is express in BTC and USD
    Important:
        - Debit operations add BTCs to the wallet
        - Credit operations substract BTCs from the wallet
        - Amount values must be always positive values.
    """

    SENT_EXTERNAL = "sent_external"  # Transfers to wallet of another user
    SENT_INTERNAL = "sent_internal"  # Transfers to own wallet
    PLATFORM = "platform"  # Transfers from platform(initial grant)
    PLATFORM_PROFIT = "platform_profit"  # Transfers to platform
    TRANSACTION_TYPES = [
        (SENT_EXTERNAL, "sent_external"),
        (SENT_INTERNAL, "sent_internal"),
        (PLATFORM, "platform"),
        (PLATFORM_PROFIT, "platform_profit"),
    ]
    wallet_from = models.ForeignKey(
        Wallet,
        to_field="address",
        related_name="transactions_credits",
        on_delete=models.PROTECT,
        null=True,
    )
    wallet_to = models.ForeignKey(
        Wallet,
        to_field="address",
        related_name="transactions_debits",
        on_delete=models.PROTECT,
        null=True,
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=16, decimal_places=8)
    details = models.CharField(max_length=250, blank=True)
    extra = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Transaction type:{self.transaction_type}."
            f"From address:{self.wallet_from}. To address: {self.wallet_to}"
        )

    @classmethod
    def calculate_profit(cls, amount, transaction_type):
        """
        Calculate total platform profits in bitcoins based on
        transfered amount and transaction type.
        """
        bitcoins = Decimal(".00000001")
        profit_percentage = Decimal("0.0")
        if transaction_type == cls.SENT_EXTERNAL:
            profit_percentage = Decimal(settings.PLATFORM_PROFIT)
        profit = amount * profit_percentage
        return profit.quantize(bitcoins, rounding=ROUND_DOWN).normalize()


class Statistics(models.Model):
    """
    Provides a simple class to storage some useful statistics.
    Total values are group by day. That means we could have 365
    entries per year. But gives flexibility to query range of
    dates.
    """

    date = models.DateField(unique=True)
    transactions = models.IntegerField(default=0)
    profit = models.DecimalField(max_digits=16, decimal_places=8, default=0.0)
