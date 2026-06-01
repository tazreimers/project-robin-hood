from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings, get_settings
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
        """Fetch decimal odds for configured sport, featured markets, and event-level markets."""
        provider_sport_key = SPORT_KEY_ALIASES.get(sport_key, sport_key)
        events: list[ProviderEvent] = []
        featured_markets = ",".join(self.settings.odds_market_list)
        if featured_markets:
            events.extend(self._fetch_featured_odds(provider_sport_key, featured_markets))

        event_markets = ",".join(self.settings.odds_event_market_list)
        if event_markets:
            events.extend(self._fetch_event_market_odds(provider_sport_key, event_markets))

        return merge_events(events)

    def _fetch_featured_odds(self, provider_sport_key: str, markets: str) -> list[ProviderEvent]:
        endpoint = f"/v4/sports/{provider_sport_key}/odds/"
        regions = self.settings.odds_regions
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

    def _fetch_event_market_odds(self, provider_sport_key: str, markets: str) -> list[ProviderEvent]:
        endpoint = f"/v4/sports/{provider_sport_key}/events"
        events_payload = self._get(
            endpoint,
            params={"dateFormat": "iso"},
            endpoint=endpoint,
            sport_key=provider_sport_key,
            regions="",
            markets="",
            estimated_cost=0,
        )
        if not isinstance(events_payload, list):
            raise OddsProviderError("Unexpected events response from The Odds API")

        now = datetime.now(timezone.utc)
        events = [
            event
            for item in events_payload
            if isinstance(item, dict)
            for event in [self._parse_event(item)]
            if event and event.start_time > now
        ]
        events.sort(key=lambda event: event.start_time)
        max_events = self.settings.odds_event_market_max_events
        if max_events <= 0:
            return []
        events = events[:max_events]

        regions = self.settings.odds_regions
        responses: list[ProviderEvent] = []
        for event in events:
            event_endpoint = f"/v4/sports/{provider_sport_key}/events/{event.external_id}/odds"
            payload = self._get(
                event_endpoint,
                params={
                    "regions": regions,
                    "markets": markets,
                    "oddsFormat": "decimal",
                    "dateFormat": "iso",
                },
                endpoint=event_endpoint,
                sport_key=provider_sport_key,
                regions=regions,
                markets=markets,
                estimated_cost=estimate_request_cost(regions=regions, markets=markets),
            )
            if not isinstance(payload, dict):
                continue
            parsed_event = self._parse_event(payload)
            if parsed_event is not None:
                responses.append(parsed_event)

        return responses

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
        allowed_market_keys = {*self.settings.odds_market_list, *self.settings.odds_event_market_list}
        if allowed_market_keys and market_type not in allowed_market_keys:
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
        description = str(item.get("description") or "").strip() or None
        line = self._parse_decimal(item.get("point"))

        if not name or decimal_odds is None:
            return None

        return ProviderOutcome(
            name=name,
            decimal_odds=decimal_odds,
            description=description,
            line=line,
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


def merge_events(events: list[ProviderEvent]) -> list[ProviderEvent]:
    """Merge featured and event-level responses for the same provider event id."""
    merged_by_id: dict[str, ProviderEvent] = {}
    for event in events:
        existing = merged_by_id.get(event.external_id)
        if existing is None:
            merged_by_id[event.external_id] = event
            continue

        merged_by_id[event.external_id] = ProviderEvent(
            external_id=existing.external_id,
            sport_key=existing.sport_key,
            sport_name=existing.sport_name,
            home_team=existing.home_team,
            away_team=existing.away_team,
            start_time=existing.start_time,
            bookmakers=merge_bookmakers([*existing.bookmakers, *event.bookmakers]),
        )

    return list(merged_by_id.values())


def merge_bookmakers(bookmakers: list[ProviderBookmaker]) -> list[ProviderBookmaker]:
    merged_by_key: dict[str, ProviderBookmaker] = {}
    for bookmaker in bookmakers:
        existing = merged_by_key.get(bookmaker.key)
        if existing is None:
            merged_by_key[bookmaker.key] = bookmaker
            continue

        merged_by_key[bookmaker.key] = ProviderBookmaker(
            key=existing.key,
            name=existing.name,
            region=existing.region,
            markets=[*existing.markets, *bookmaker.markets],
            last_update=bookmaker.last_update or existing.last_update,
        )

    return list(merged_by_key.values())
