"""
TokenClient
"""
import requests

from .token import Token


class TokenClient:
    """
    Retrieves OAuth 2.0 tokens from the token endpoint and from the redis cache.

    Args:
        client_id (str)
        client_secret (str)
        token_url (str)
        redis_client (redis.Redis)
        audience (str)
        timeout (:obj:`int`, optional)
    """

    def __init__(
        self,
        client_id=None,
        client_secret=None,
        token_url=None,
        redis_client=None,
        audience=None,
        **kwargs
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.redis_client = redis_client
        self.audience = audience
        self.timeout = kwargs.get("timeout", 5)

    def fresh_token(self):
        """
        Issue a new OAuth 2.0 token.

        Returns:
            Token: A Token instance
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
        }

        response = requests.post(
            self.token_url, json=payload, allow_redirects=False, timeout=self.timeout
        )
        response.raise_for_status()
        response = response.json()

        token = Token(
            access_token=response["access_token"],
            expires_in=response["expires_in"],
            token_type=response["token_type"],
            audience=self.audience,
        )

        return self.cache_token(token)

    def cached_token(self):
        """
        Try to retrieve a cached token from Redis.

        Returns:
            None: Returns `None` in case of a cache miss
            Token: Returns a Token instance
        """
        values = self.redis_client.hgetall(self.cache_key)

        if not values:
            return None

        return Token(
            values["access_token"],
            int(values["expires_in"]),
            values["token_type"],
            values["audience"],
        )

    def cache_token(self, token):
        """
        Serialize a Token instance as a dict and save it to Redis.

        Args:
            token (Token): The token to save

        Returns:
            Token: The saved token
        """
        pipeline = self.redis_client.pipeline()

        pipeline.hmset(self.cache_key, token.asdict())
        pipeline.expire(self.cache_key, token.expires_in)
        pipeline.execute()

        return token

    @property
    def cache_key(self):
        """
        Return the cache key for the configuration.

        Returns:
            str: A cache key in the format "oauth_token_cache__<client_id>_<audience>"
        """
        return "oauth_token_cache__{client_id}_{audience}".format(
            client_id=self.client_id, audience=self.audience
        )
