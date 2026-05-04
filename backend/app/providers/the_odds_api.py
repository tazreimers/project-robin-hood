from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.constants import THE_ODDS_API_DEFAULT_MARKETS
from app.core.logging import redact_secrets
from app.providers.base import (
    OddsProvider,
    OddsProviderConfigurationError,
    OddsProviderError,
    ProviderApiUsage,
    ProviderBookmaker,
    ProviderEvent,
    ProviderMarket,
    ProviderOutcome,
    ProviderSport,
)

SPORT_KEY_ALIASES = {
    "afl": "aussierules_afl",
    "nrl": "rugbyleague_nrl",
}


class TheOddsApiProvider(OddsProvider):
    provider_name = "the_odds_api"
    base_url = "https://api.the-odds-api.com"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        usage_callback: Callable[[ProviderApiUsage], None] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(base_url=self.base_url, timeout=20.0)
        self.usage_callback = usage_callback

    def fetch_sports(self) -> list[ProviderSport]:
        payload = self._get(
            "/v4/sports/",
            params={},
            endpoint="/v4/sports/",
            sport_key=None,
            regions="",
            markets="",
            estimated_cost=0,
        )
        if not isinstance(payload, list):
            raise OddsProviderError("Unexpected sports response from The Odds API")

        sports: list[ProviderSport] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            key = str(item.get("key") or "").strip()
            name = str(item.get("title") or item.get("name") or key).strip()
            if key:
                sports.append(
                    ProviderSport(
                        key=key,
                        name=name,
                        is_active=bool(item.get("active", True)),
                    )
                )

        return sports

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        """Fetch decimal head-to-head odds for one configured sport key."""
        provider_sport_key = SPORT_KEY_ALIASES.get(sport_key, sport_key)
        endpoint = f"/v4/sports/{provider_sport_key}/odds/"
        regions = self.settings.odds_regions
        markets = THE_ODDS_API_DEFAULT_MARKETS
        payload = self._get(
            endpoint,
            params={
                "regions": regions,
                "markets": markets,
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            endpoint=endpoint,
            sport_key=provider_sport_key,
            regions=regions,
            markets=markets,
            estimated_cost=estimate_request_cost(regions=regions, markets=markets),
        )
        if not isinstance(payload, list):
            raise OddsProviderError("Unexpected odds response from The Odds API")

        return [event for item in payload if isinstance(item, dict) for event in [self._parse_event(item)] if event]

    def _get(
        self,
        path: str,
        params: dict[str, str],
        endpoint: str,
        sport_key: str | None,
        regions: str,
        markets: str,
        estimated_cost: int,
    ) -> Any:
        if not self.settings.odds_api_key:
            raise OddsProviderConfigurationError("ODDS_API_KEY is not configured")

        request_params = {"apiKey": self.settings.odds_api_key, **params}
        try:
            response = self.client.get(path, params=request_params)
            self._record_usage(
                endpoint=endpoint,
                sport_key=sport_key,
                regions=regions,
                markets=markets,
                headers=response.headers,
                estimated_cost=estimated_cost,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            response_text = redact_secrets(exc.response.text[:200])
            raise OddsProviderError(
                f"The Odds API returned HTTP {exc.response.status_code}: {response_text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OddsProviderError(f"Failed to call The Odds API: {redact_secrets(exc)}") from exc

        return response.json()

    def _record_usage(
        self,
        endpoint: str,
        sport_key: str | None,
        regions: str,
        markets: str,
        headers: httpx.Headers,
        estimated_cost: int,
    ) -> None:
        """Forward quota headers to the quota guard without coupling the provider to the database."""
        if self.usage_callback is None:
            return

        self.usage_callback(
            ProviderApiUsage(
                provider=self.provider_name,
                endpoint=endpoint,
                sport_key=sport_key,
                regions=regions,
                markets=markets,
                requests_remaining=parse_header_int(headers.get("x-requests-remaining")),
                requests_used=parse_header_int(headers.get("x-requests-used")),
                requests_last=parse_header_int(headers.get("x-requests-last")),
                estimated_cost=estimated_cost,
                captured_at=datetime.now(timezone.utc),
            )
        )

    def _parse_event(self, item: dict[str, Any]) -> ProviderEvent | None:
        external_id = str(item.get("id") or "").strip()
        sport_key = str(item.get("sport_key") or "").strip()
        sport_name = str(item.get("sport_title") or sport_key).strip()
        home_team = str(item.get("home_team") or "").strip()
        away_team = str(item.get("away_team") or "").strip()
        start_time = self._parse_datetime(item.get("commence_time"))

        if not external_id or not sport_key or not home_team or not away_team or start_time is None:
            return None

        bookmakers = [
            bookmaker
            for bookmaker_item in item.get("bookmakers", [])
            if isinstance(bookmaker_item, dict)
            for bookmaker in [self._parse_bookmaker(bookmaker_item)]
            if bookmaker
        ]

        return ProviderEvent(
            external_id=external_id,
            sport_key=sport_key,
            sport_name=sport_name,
            home_team=home_team,
            away_team=away_team,
            start_time=start_time,
            bookmakers=bookmakers,
        )

    def _parse_bookmaker(self, item: dict[str, Any]) -> ProviderBookmaker | None:
        key = str(item.get("key") or "").strip()
        name = str(item.get("title") or key).strip()
        last_update = self._parse_datetime(item.get("last_update"))

        if not key or not name:
            return None

        markets = [
            market
            for market_item in item.get("markets", [])
            if isinstance(market_item, dict)
            for market in [self._parse_market(market_item)]
            if market
        ]

        return ProviderBookmaker(
            key=key,
            name=name,
            region=self.settings.odds_regions,
            last_update=last_update,
            markets=markets,
        )

    def _parse_market(self, item: dict[str, Any]) -> ProviderMarket | None:
        market_type = str(item.get("key") or "").strip()
        if market_type != "h2h":
            return None

        outcomes = [
            outcome
            for outcome_item in item.get("outcomes", [])
            if isinstance(outcome_item, dict)
            for outcome in [self._parse_outcome(outcome_item)]
            if outcome
        ]

        return ProviderMarket(
            market_type=market_type,
            line=self._parse_decimal(item.get("point")),
            is_suspended=self._is_suspended(item),
            outcomes=outcomes,
        )

    def _parse_outcome(self, item: dict[str, Any]) -> ProviderOutcome | None:
        name = str(item.get("name") or "").strip()
        decimal_odds = self._parse_decimal(item.get("price"))

        if not name or decimal_odds is None:
            return None

        return ProviderOutcome(
            name=name,
            decimal_odds=decimal_odds,
            is_suspended=self._is_suspended(item),
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None

        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _is_suspended(item: dict[str, Any]) -> bool:
        value = item.get("is_suspended", item.get("suspended", False))
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes"}
        return bool(value)


def parse_header_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def estimate_request_cost(regions: str, markets: str) -> int:
    region_count = len([region.strip() for region in regions.split(",") if region.strip()])
    market_count = len([market.strip() for market in markets.split(",") if market.strip()])
    if region_count == 0 or market_count == 0:
        return 0
    return region_count * market_count
