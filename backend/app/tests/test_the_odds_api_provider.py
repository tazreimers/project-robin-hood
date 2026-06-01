from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.core.config import Settings
from app.providers.the_odds_api import TheOddsApiProvider


class TheOddsApiProviderTest(unittest.TestCase):
    def test_fetches_configured_featured_and_event_markets(self) -> None:
        commence_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        later_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/v4/sports/aussierules_afl/odds/":
                self.assertEqual(request.url.params.get("markets"), "h2h")
                return httpx.Response(
                    200,
                    headers={"x-requests-last": "1"},
                    json=[
                        {
                            "id": "event-1",
                            "sport_key": "aussierules_afl",
                            "sport_title": "AFL",
                            "home_team": "Collingwood",
                            "away_team": "Sydney",
                            "commence_time": commence_time,
                            "bookmakers": [
                                {
                                    "key": "sportsbet",
                                    "title": "SportsBet",
                                    "markets": [
                                        {
                                            "key": "h2h",
                                            "outcomes": [
                                                {"name": "Collingwood", "price": 1.9},
                                                {"name": "Sydney", "price": 1.9},
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                )
            if request.url.path == "/v4/sports/aussierules_afl/events":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "event-1",
                            "sport_key": "aussierules_afl",
                            "sport_title": "AFL",
                            "home_team": "Collingwood",
                            "away_team": "Sydney",
                            "commence_time": commence_time,
                        },
                        {
                            "id": "event-2",
                            "sport_key": "aussierules_afl",
                            "sport_title": "AFL",
                            "home_team": "Carlton",
                            "away_team": "Richmond",
                            "commence_time": later_time,
                        },
                    ],
                )
            if request.url.path == "/v4/sports/aussierules_afl/events/event-1/odds":
                self.assertEqual(request.url.params.get("markets"), "player_disposals_over")
                return httpx.Response(
                    200,
                    headers={"x-requests-last": "1"},
                    json={
                        "id": "event-1",
                        "sport_key": "aussierules_afl",
                        "sport_title": "AFL",
                        "home_team": "Collingwood",
                        "away_team": "Sydney",
                        "commence_time": commence_time,
                        "bookmakers": [
                            {
                                "key": "sportsbet",
                                "title": "SportsBet",
                                "markets": [
                                    {
                                        "key": "player_disposals_over",
                                        "outcomes": [
                                            {
                                                "name": "Over",
                                                "description": "Nick Daicos",
                                                "price": 1.87,
                                                "point": 24.5,
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                )

            return httpx.Response(404, json={"message": "unexpected path"})

        client = httpx.Client(base_url=TheOddsApiProvider.base_url, transport=httpx.MockTransport(handler))
        provider = TheOddsApiProvider(
            settings=Settings(
                odds_api_key="test-key",
                odds_regions="au",
                odds_markets="h2h",
                odds_event_markets="player_disposals_over",
                odds_event_market_max_events=1,
            ),
            client=client,
        )

        events = provider.fetch_odds("afl")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].external_id, "event-1")
        self.assertEqual(len(events[0].bookmakers), 1)
        markets = events[0].bookmakers[0].markets
        self.assertEqual([market.market_type for market in markets], ["h2h", "player_disposals_over"])
        prop_outcome = markets[1].outcomes[0]
        self.assertEqual(prop_outcome.description, "Nick Daicos")
        self.assertEqual(prop_outcome.line, Decimal("24.5"))
        self.assertIn("/v4/sports/aussierules_afl/events/event-1/odds", calls)
        self.assertNotIn("/v4/sports/aussierules_afl/events/event-2/odds", calls)


if __name__ == "__main__":
    unittest.main()
