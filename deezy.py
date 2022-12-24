import json
import time
import requests
from functools import lru_cache


class Network:
    testnet = 0
    mainnet = 1


class SwapResponse:
    def __init__(self, bolt11_invoice: str, fee_sats: int):
        self.bolt11_invoice: str = bolt11_invoice
        self.fee_sats: int = fee_sats


class SwapInfo:
    def __init__(
        self,
        liquidity_fee_ppm: int,
        on_chain_bytes_estimate: int,
        max_swap_amount_sats: int,
        min_swap_amount_sats: int,
        available: bool,
    ):
        self.liquidity_fee_ppm: int = liquidity_fee_ppm
        self.on_chain_bytes_estimate: int = on_chain_bytes_estimate
        self.max_swap_amount_sats: int = max_swap_amount_sats
        self.min_swap_amount_sats: int = min_swap_amount_sats
        self.available: bool = available


def lru_with_ttl(*, ttl_seconds, maxsize=128):
    def deco(foo):
        @lru_cache(maxsize=maxsize)
        def cached_with_ttl(*args, ttl_hash, **kwargs):
            return foo(*args, **kwargs)

        def inner(*args, **kwargs):
            return cached_with_ttl(
                *args, ttl_hash=round(time.time() / ttl_seconds), **kwargs
            )

        return inner

    return deco


class Deezy:
    def __init__(self, mode: Network = Network.mainnet, version: str = "1"):
        self.mode: Network = mode
        self.version: str = version

    @property
    def __prefix(self):
        return ("api-testnet.", "api.")[self.mode == Network.mainnet]

    @property
    def __fqdn(self):
        return f"https://{self.__prefix}deezy.io"

    @property
    def __url(self):
        return f"{self.__fqdn}/v{self.version}"

    @lru_with_ttl(ttl_seconds=60)
    def info(self):
        return SwapInfo(**requests.get(f"{self.__url}/swap/info").json())

    def amount_sats_is_above_max(self, amount_sats: str):
        return amount_sats > self.info().max_swap_amount_sats

    def amount_sats_is_below_min(self, amount_sats: str):
        return amount_sats < self.info().min_swap_amount_sats

    def estimate_cost(self, amount_sats: int, fee_rate: int, mp_fee: int):
        r = self.info()
        if amount_sats < r.min_swap_amount_sats:
            raise Exception(f"Min amount is: {r.min_swap_amount_sats}")
        if amount_sats > r.max_swap_amount_sats:
            raise Exception(f"Max amount is: {r.max_swap_amount_sats}")
        routing_rate = amount_sats * fee_rate / 1e6
        deezy_liq_rate = amount_sats * r.liquidity_fee_ppm / 1e6
        deezy_chain_rate = mp_fee * r.on_chain_bytes_estimate
        total_fee = int(routing_rate + deezy_liq_rate + deezy_chain_rate)
        return total_fee

    def swap(self, amount_sats: int, address: str, mp_fee: int):
        return SwapResponse(
            **requests.post(
                f"{self.__url}/swap",
                headers={"content-type": "application/json"},
                data=json.dumps(
                    {
                        "amount_sats": amount_sats,
                        "on_chain_address": address,
                        "on_chain_sats_per_vbyte": mp_fee,
                    }
                ),
            ).json()
        )
