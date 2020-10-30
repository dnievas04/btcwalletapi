# BTC Wallet

BTC Wallet is a sample API that "simulates" a platform that allow users to register,
create own BTC wallets and transfer BTC to other wallets inside it. Platform makes 1.5% profit from the transactions between users.

## Requirements

-   Python: 3.8
-   Django: 2.2
-   Django Rest Framework: 3.11
-   PostgreSQL: 12.2

## Docker QuickStart

1. Clone the project:

    ```bash
    $ git clone https://github.com/dnievas04/btcwalletapi.git
    ```

2. Run docker-compose commands to build and start containers:

    ```bash
    $ docker-compose up -d --build
    ```

3. Test if API is running at http://localhost:8000/api/v1/users/

## Settings

Some settings are required to configure the API. Use the .env file in the project root to
change default values, os just define the required OS environment variables.

#### PLATFORM_ADMIN_TOKEN

Hardcoded Token to authenticate the administrator. Required for statistics

#### PLATFORM_WALLET_ADDRESS

Hardcoded wallet address used by the platform to perform transactions between platform and users. For example to grant bitcoins when users create a wallet

#### PLATFORM_WALLET_USER_NAME / PLATFORM_WALLET_USER_PASSWORD

Username and password for the user platform who owns the platform wallet.

#### PLATFORM_TRANSACTION_LIMITS

Refers to the minimum bitcoins amount allowed to transfer between different users

#### PLATFORM_PROFIT

Transaction costs of the transferred amount (profit of the platform) if transferred to a wallet of another user. Hardcoded at 1.5%

## Tests

Tests can be run as follow:

```bash
$ docker-compose exec web python manage.py test
```

## Manually API test

The API uses the TokenAuthentication scheme provided by DRF. This is a simple token-based HTTP Authentication scheme.
To obtain a valid token, you must first create a user. The endpoint to create users is `/api/v1/users` and accepts POST requests. The endpoint returns the token that is required to authenticate all other requests for this user.

> The following examples uses [HTTPie](https://httpie.org/) to consume the API endpoints via the terminal.

```bash
$ http post http://localhost:8000/api/v1/users/ username=test password=123
```

The response body:

```json
{
	"token": "9c6ded39ecdb4568f562e5bd2bc31195cdf3e147"
}
```

In order to access the protected views (the API endpoints that require authentication), you should include the **token** in the header of all requests. For example create BTC wallet for the authenticated user:

```
$ http post http://localhost:8000/api/v1/wallets/ "Authorization: Token 9c6ded39ecdb4568f562e5bd2bc31195cdf3e147"
```

Check the [docs](https://btcwallet.docs.apiary.io/#) for all available endpoints.
