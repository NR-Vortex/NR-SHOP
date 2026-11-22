from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Wallet, WalletTransaction


async def get_wallet(session: AsyncSession, user_id: int) -> Wallet:
    wallet = (await session.execute(select(Wallet).where(Wallet.telegram_user_id == user_id))).scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(telegram_user_id=user_id, balance=0)
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
    return wallet


async def get_transactions(session: AsyncSession, user_id: int, limit: int = 20):
    return (await session.execute(
        select(WalletTransaction).join(Wallet).where(Wallet.telegram_user_id == user_id).order_by(WalletTransaction.id.desc()).limit(limit)
    )).scalars().all()


async def get_or_create_wallet(session: AsyncSession, user_id: int) -> Wallet:
    wallet = (await session.execute(select(Wallet).where(Wallet.telegram_user_id == user_id).with_for_update())).scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(telegram_user_id=user_id, balance=0)
        session.add(wallet)
        await session.flush()
    return wallet


async def credit_wallet(session: AsyncSession, user_id: int, amount: int, reference: str, description: str | None = None):
    if amount <= 0: raise ValueError("amount must be positive")
    existing = (await session.execute(select(WalletTransaction).where(WalletTransaction.reference == reference))).scalar_one_or_none()
    if existing: return existing, False
    wallet = await get_or_create_wallet(session, user_id)
    wallet.balance += amount
    tx = WalletTransaction(wallet_id=wallet.id, kind="credit", amount=amount, balance_after=wallet.balance, reference=reference, description=description)
    session.add(tx); await session.commit(); await session.refresh(tx)
    return tx, True


async def debit_wallet(session: AsyncSession, user_id: int, amount: int, reference: str, description: str | None = None):
    if amount <= 0: raise ValueError("amount must be positive")
    existing = (await session.execute(select(WalletTransaction).where(WalletTransaction.reference == reference))).scalar_one_or_none()
    if existing: return existing, False
    wallet = await get_or_create_wallet(session, user_id)
    if wallet.balance < amount: raise ValueError("insufficient wallet balance")
    wallet.balance -= amount
    tx = WalletTransaction(wallet_id=wallet.id, kind="debit", amount=amount, balance_after=wallet.balance, reference=reference, description=description)
    session.add(tx); await session.commit(); await session.refresh(tx)
    return tx, True
