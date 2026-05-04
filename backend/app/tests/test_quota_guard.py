from __future__ import annotations

import unittest
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import ApiUsageLog, Base
from app.providers.the_odds_api import TheOddsApiProvider
from app.services.quota_guard import QuotaGuard, estimate_request_cost


class QuotaGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.settings = Settings(
            odds_api_key="test-key",
            sport_keys="test_sport",
            odds_regions="au",
            daily_quota_budget=100,
            min_requests_remaining_buffer=5,
            max_scans_per_hour=10,
            enable_quota_guard=True,
        )

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_scan_allowed_when_quota_healthy(self) -> None:
        self.db.add(
            ApiUsageLog(
                provider="the_odds_api",
                endpoint="/v4/sports/test_sport/odds/",
                sport_key="test_sport",
                regions="au",
                markets="h2h",
                requests_remaining=20,
                requests_used=10,
                requests_last=1,
                estimated_cost=1,
                captured_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

        decision = QuotaGuard(self.db, settings=self.settings).check_scan_allowed()

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.estimated_cost, 1)
        self.assertIsNone(decision.reason)

    def test_scan_blocked_when_quota_below_buffer(self) -> None:
        self.db.add(
            ApiUsageLog(
                provider="the_odds_api",
                endpoint="/v4/sports/test_sport/odds/",
                sport_key="test_sport",
                regions="au",
                markets="h2h",
                requests_remaining=5,
                requests_used=95,
                requests_last=1,
                estimated_cost=1,
                captured_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

        decision = QuotaGuard(self.db, settings=self.settings).check_scan_allowed()

        self.assertFalse(decision.allowed)
        self.assertIn("remaining quota", decision.reason or "")

    def test_usage_headers_are_saved(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "x-requests-remaining": "42",
                    "x-requests-used": "8",
                    "x-requests-last": "2",
                },
                json=[],
            )

        client = httpx.Client(
            base_url=TheOddsApiProvider.base_url,
            transport=httpx.MockTransport(handler),
        )
        guard = QuotaGuard(self.db, settings=self.settings)
        provider = TheOddsApiProvider(
            settings=self.settings,
            client=client,
            usage_callback=guard.log_api_response,
        )

        provider.fetch_odds("test_sport")
        self.db.commit()

        log = self.db.scalar(select(ApiUsageLog))
        self.assertIsNotNone(log)
        self.assertEqual(log.provider, "the_odds_api")
        self.assertEqual(log.endpoint, "/v4/sports/test_sport/odds/")
        self.assertEqual(log.sport_key, "test_sport")
        self.assertEqual(log.regions, "au")
        self.assertEqual(log.markets, "h2h")
        self.assertEqual(log.requests_remaining, 42)
        self.assertEqual(log.requests_used, 8)
        self.assertEqual(log.requests_last, 2)
        self.assertEqual(log.estimated_cost, 1)

    def test_estimated_cost_uses_markets_times_regions(self) -> None:
        guard = QuotaGuard(self.db, settings=self.settings)

        self.assertEqual(estimate_request_cost(regions="au,us", markets="h2h,spreads,totals"), 6)
        self.assertEqual(
            guard.estimate_scan_cost(
                sport_keys=["sport_a", "sport_b"],
                regions="au,us",
                markets="h2h,totals",
            ),
            8,
        )


if __name__ == "__main__":
    unittest.main()
