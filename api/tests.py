from decimal import Decimal

from rest_framework.test import APITestCase
from rest_framework import status

from django.urls import reverse
from django.conf import settings

from .models import Transaction


class APITestBaseView(APITestCase):
    """
    Performs basic authentication setup.
    """

    def setUp(self):
        self.token = self.create_user("userA", "passA")
        self.set_api_credentials(self.token)

    def create_user(self, username, password):
        response = self.client.post(
            reverse("user-create"), {"username": username, "password": password},
        )
        return response.data

    def set_api_credentials(self, token):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token["token"])


class TestWalletCreateView(APITestBaseView):
    url = reverse("wallet-create")

    def test_authenticated_user(self):
        """
        Tests create a new wallet with an authenticated user
        """
        response = self.client.post(self.url, data={}, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Expected Response Code 201, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_unauthenticated_user(self):
        """
        Tests create a new wallet with an unauthenticated user must failed
        """
        self.client.credentials(HTTP_AUTHORIZATION="")  # Remove token
        response = self.client.post(self.url, data={}, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            "Expected Response Code 401, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_max_number_wallets_per_user(self):
        """
        Tests no more than 10 wallets per user are allowed
        """
        response = self.client.post(self.url, data={}, format="json")
        for i in range(10):
            response = self.client.post(self.url, data={}, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Expected Response Code 400, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_balance(self):
        """
        Tests balance must be 1 btc after wallet creation
        """
        response = self.client.post(self.url, data={}, format="json")
        balance = response.data.get("balance")
        self.assertEqual(
            balance["btc"],
            "1.00000000",
            "Expected balance 1 BTC, received {0} instead.".format(balance["btc"]),
        )


class TestWalletDetailView(APITestBaseView):
    def test_detail_by_address(self):
        """
        Test wallet detail 'query' by address
        """
        url_create = reverse("wallet-create")
        response_create = self.client.post(url_create, data={}, format="json")
        create_address = response_create.data.get("address")

        url_detail = reverse("wallet-detail", kwargs={"address": create_address})
        response_detail = self.client.get(url_detail, format="json")
        self.assertEqual(
            response_detail.status_code,
            status.HTTP_200_OK,
            "Expected Response Code 200, received {0} instead.".format(
                response_detail.status_code
            ),
        )
        detail_address = response_detail.data.get("address")
        self.assertEqual(
            create_address,
            detail_address,
            "Expected wallet address {0}, received {1} instead.".format(
                create_address, detail_address
            ),
        )


class TestTransactionCreateListView(APITestBaseView):
    def setUp(self):
        """
        Creates 2 users. User A and user B
        User A will own two wallets
        User B will own one wallet
        """
        self.userA = self.create_user("userA", "passA")
        self.userB = self.create_user("userB", "passB")
        self.wallet_1_user_A = self.create_wallet(self.userA)
        self.wallet_2_user_A = self.create_wallet(self.userA)
        self.wallet_1_user_B = self.create_wallet(self.userB)
        self.set_api_credentials(self.userA)  # User A will perform most of the requests

    def create_wallet(self, user_token):
        url = reverse("wallet-create")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + user_token["token"])
        response = self.client.post(url, data={}, format="json")
        return response.data.get("address")

    def transfer_to_iternal_address(self):
        amount = Decimal(settings.PLATFORM_TRANSACTION_LIMITS)
        # Perform transaction
        transaction = {
            "wallet_from": self.wallet_1_user_A,
            "wallet_to": self.wallet_2_user_A,
            "transaction_type": Transaction.SENT_INTERNAL,
            "amount": amount,
        }
        return self.client.post(self.url_transaction, data=transaction, format="json")

    def transfer_to_external_address(self):
        amount = Decimal(settings.PLATFORM_TRANSACTION_LIMITS)
        # Transaction details. Trasfer from wallet 1 user A --> wallet 1 user B
        transaction = {
            "wallet_from": self.wallet_1_user_A,
            "wallet_to": self.wallet_1_user_B,
            "transaction_type": Transaction.SENT_EXTERNAL,
            "amount": amount,
        }
        return self.client.post(self.url_transaction, data=transaction, format="json")


class TestTransactionCreateView(TestTransactionCreateListView):
    url_transaction = reverse("transaction-list")

    def test_transfer_to_internal_address(self):
        response = self.transfer_to_iternal_address()
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Expected Response Code 201, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_balance_is_ok_after_internal_transfer(self):
        amount = Decimal("0.55")
        # Transaction details. Trasfer from wallet 1 to wallet 2 from user A
        transaction = {
            "wallet_from": self.wallet_1_user_A,
            "wallet_to": self.wallet_2_user_A,
            "transaction_type": Transaction.SENT_INTERNAL,
            "amount": amount,
        }
        self.client.post(self.url_transaction, data=transaction, format="json")

        # Request Wallet 1 and Wallet 2 from user A
        wallet_A1 = self.client.get(
            reverse("wallet-detail", kwargs={"address": self.wallet_1_user_A}),
            format="json",
        )
        wallet_A2 = self.client.get(
            reverse("wallet-detail", kwargs={"address": self.wallet_2_user_A}),
            format="json",
        )
        # Check balance from Wallet 1
        self.assertEqual(
            wallet_A1.data["balance"]["btc"],
            "0.45000000",
            "Expected {0} BTC, received {1} instead.".format(
                "0.45000000", wallet_A1.data["balance"]["btc"]
            ),
        )
        # Check balance from Wallet 2
        self.assertEqual(
            wallet_A2.data["balance"]["btc"],
            "1.55000000",
            "Expected {0} BTC, received {1} instead.".format(
                "1.55000000", wallet_A2.data["balance"]["btc"]
            ),
        )

    def test_transfer_to_external_address(self):
        response = self.transfer_to_external_address()
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Expected Response Code 201, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_balance_is_ok_after_external_transfer(self):
        amount = Decimal("0.000002")
        # Transaction details. Trasfer from wallet 1 user A --> wallet 1 user B
        transaction = {
            "wallet_from": self.wallet_1_user_A,
            "wallet_to": self.wallet_1_user_B,
            "transaction_type": Transaction.SENT_EXTERNAL,
            "amount": amount,
        }
        self.client.post(self.url_transaction, data=transaction, format="json")
        # Request Wallet 1 from user A
        wallet_A1 = self.client.get(
            reverse("wallet-detail", kwargs={"address": self.wallet_1_user_A}),
            format="json",
        )
        # Request Wallet 1 from user B
        self.set_api_credentials(self.userB)
        wallet_B1_detail = self.client.get(
            reverse("wallet-detail", kwargs={"address": self.wallet_1_user_B}),
            format="json",
        )
        # Check balance from Wallet 1 User A
        self.assertEqual(
            wallet_A1.data["balance"]["btc"],
            "0.99999797",
            "Expected {0} BTC, received {1} instead.".format(
                "0.99999797", wallet_A1.data["balance"]["btc"]
            ),
        )
        # Check balance from Wallet 1 User B
        self.assertEqual(
            wallet_B1_detail.data["balance"]["btc"],
            "1.00000200",
            "Expected {0} BTC, received {1} instead.".format(
                "1.00000200", wallet_B1_detail.data["balance"]["btc"]
            ),
        )

    def test_transfer_to_external_address_fail_on_min_amount(self):
        min_amount = Decimal(settings.PLATFORM_TRANSACTION_LIMITS)
        amount = min_amount * Decimal("0.1")
        # Perform transaction
        transaction = {
            "wallet_from": self.wallet_1_user_A,
            "wallet_to": self.wallet_1_user_B,
            "transaction_type": Transaction.SENT_EXTERNAL,
            "amount": amount,
        }
        response_create = self.client.post(
            self.url_transaction, data=transaction, format="json"
        )
        self.assertEqual(
            response_create.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Expected Response Code 400, received {0} instead.".format(
                response_create.status_code
            ),
        )


class TestTransactionListView(TestTransactionCreateListView):
    url = reverse("transaction-list")

    def test_list_transaction(self):
        response = self.client.get(self.url, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Expected Response Code 200, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_list_first_transaction(self):
        response = self.client.get(self.url, format="json")
        total = len(response.data)
        self.assertEqual(
            total,
            2,
            "Expected 2 transactions after 2 wallets creation, but received {0} instead.".format(
                total
            ),
        )


class TestWalletTransactionListView(TestTransactionCreateListView):
    """
    Test transactions related to a specific wallet
    """

    def test_transactions_from_own_wallet(self):
        """
        User A, perform the request, and wallet address belongs to user A
        """
        response = self.client.get(
            reverse("transaction-detail", kwargs={"address": self.wallet_1_user_A}),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Expected Response Code 200, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_transactions_from_not_own_wallet(self):
        """
        User A, perform the request, but wallet address belongs to user B
        """
        response = self.client.get(
            reverse("transaction-detail", kwargs={"address": self.wallet_1_user_B}),
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            "Expected Response Code 404, received {0} instead.".format(
                response.status_code
            ),
        )


class TestStatisticsListView(TestTransactionCreateListView):
    url = reverse("statistics")

    def test_statistics_platform_with_valid_token(self):
        admin_token = {"token": settings.PLATFORM_ADMIN_TOKEN}
        self.set_api_credentials(admin_token)
        response = self.client.get(self.url, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Expected Response Code 200, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_statistics_platform_with_invalid_token(self):
        response = self.client.get(self.url, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Expected Response Code 403, received {0} instead.".format(
                response.status_code
            ),
        )


class TestUserCreateView(APITestCase):
    url = reverse("user-create")

    valid_payload = {
        "username": "davidn04",
        "email": "david@snow.com",
        "password": "the_password",
    }
    invalid_payload = {
        "username": "davidn04",
        "email": "david@snow.com",
    }

    def test_valid_user_payload(self):
        """
        Tests create a new user with a valid user's definition.
        """
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Expected Response Code 201, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_valid_token_response(self):
        """
        Test a valid token is returned after user creation.
        """
        pass

    def test_invalid_user_payload(self):
        """
        Tests create a new user with a invalid user's definition must fail.
        """
        response = self.client.post(self.url, data=self.invalid_payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Expected Response Code 400, received {0} instead.".format(
                response.status_code
            ),
        )

    def test_invalid_duplicate_username(self):
        """
        Tests usernames must be unique.
        """
        self.client.post(self.url, data=self.valid_payload, format="json")
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            "Expected Response Code 400, received {0} instead.".format(
                response.status_code
            ),
        )
