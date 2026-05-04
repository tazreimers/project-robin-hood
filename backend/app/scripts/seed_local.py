from __future__ import annotations

from app.db.session import SessionLocal
from app.services.demo_seed import seed_demo_data


def main() -> None:
    with SessionLocal() as db:
        summary = seed_demo_data(db)
        db.commit()

    print("Seeded local demo data:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
