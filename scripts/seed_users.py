"""Seed akun dummy (superadmin, manager, marketing).

Jalankan: python -m scripts.seed_users
"""
from app.core.seed import DEFAULT_USERS, seed_default_users
from app.db.session import SessionLocal, init_db


def main() -> None:
    init_db()
    with SessionLocal() as db:
        created = seed_default_users(db)
    if created:
        print(f"Akun baru dibuat: {', '.join(created)}")
    else:
        print("Semua akun dummy sudah ada, tidak ada yang dibuat.")
    print("\nDaftar akun uji coba:")
    for user in DEFAULT_USERS:
        print(f"  - {user['role']:<11} | {user['username']:<12} | {user['password']}")


if __name__ == "__main__":
    main()
