import asyncio
from uuid import UUID

from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from core.models.user import User
from core.models.mylist import MyList
from core.models.mylist_value import MyListValue


async def create_user(session: AsyncSession, user_data: dict) -> User | None:
    if "user_id" in user_data:
        user_data["max_id"] = user_data["user_id"]
        user_data.pop("user_id")

    user_data.pop("status", None)

    user = User(**user_data)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    print("user created:", user)
    return user


async def create_mylist(session: AsyncSession, user_id: int) -> MyList | None:
    try:
        mylist = MyList(user_id=user_id)
        session.add(mylist)
        await session.commit()
        await session.refresh(mylist)
        print(f"mylist by user {user_id} created:", mylist)
        return mylist
    except:
        print(f"something went wrong with creating mylist by user {user_id}")


async def create_mylist_value(
    session: AsyncSession, mylist_uuid: UUID, value: str
) -> MyListValue | None:
    try:
        mylist_value = MyListValue(value=value, mylist_uuid=mylist_uuid)
        session.add(mylist_value)
        await session.commit()
        await session.refresh(mylist_value)
        print(f"mylistvalue by mylist {mylist_uuid} created, value:", mylist_value)
        return mylist_value
    except:
        print(f"something went wrong with creating mylistvalue by mylist {mylist_uuid}")


async def get_user_id_by_max_id(session: AsyncSession, max_id: int) -> int | None:
    subquery = select(User.id).where(User.max_id == max_id)

    result = await session.execute(subquery)
    target_id = result.scalar()

    if target_id is None:
        print(f"NOT FOUND user with max_id={max_id}")
        return None

    print(f"found user.id with max_id={max_id}")

    return target_id


async def get_user_by_max_id(session: AsyncSession, max_id: int) -> User | None:
    stmt = select(User).where(User.max_id == max_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        print(f"NOT FOUND user with max_id={max_id}")
        return None

    print("found user:", user.max_id, user)

    return user


async def get_mylist_by_uuid(session: AsyncSession, mylist_uuid: UUID) -> MyList | None:
    stmt = select(MyList).where(MyList.uuid == mylist_uuid)
    result = await session.execute(stmt)
    mylist = result.scalar_one_or_none()

    if mylist is None:
        print(f"NOT FOUND mylist with uuid={mylist_uuid}")
        return None

    print("found mylist:", mylist)

    return mylist


async def get_mylist_with_values_by_uuid(
    session: AsyncSession,
    mylist_uuid: UUID,
) -> MyList | None:
    stmt = (
        select(MyList)
        .where(MyList.uuid == mylist_uuid)
        .options(selectinload(MyList.values))
    )

    result = await session.execute(stmt)
    mylist = result.scalar_one_or_none()

    if mylist is None:
        print(f"NOT FOUND mylist with uuid={mylist_uuid}")
        return None

    print("found mylist:", mylist.user_id, mylist)

    for value in mylist.values:
        print("*", value)

    return mylist


async def get_users_with_mylists_with_values(session: AsyncSession):
    stmt = (
        select(User)
        .options(selectinload(User.mylists).selectinload(MyList.values))
        .order_by(User.id)
    )
    users = await session.scalars(stmt)

    for user in users:
        print("***" * 60)
        print(user)
        for mylist in user.mylists:
            print("-", mylist)
            for value in mylist.values:
                print("\t*", value)


async def get_mylist_value_by_id(
    session: AsyncSession, mylist_value_id: int
) -> None | MyListValue:
    stmt = select(MyListValue).where(MyListValue.id == mylist_value_id)

    result = await session.execute(stmt)

    mylist_value = result.scalar_one_or_none()

    return mylist_value


async def update_mylist_value_value_by_id(
    session: AsyncSession, mylist_value_id: int, value: str
) -> None:
    stmt = (
        update(MyListValue)
        .where(MyListValue.id == mylist_value_id)
        .values({MyListValue.value: value})
    )

    await session.execute(stmt)

    await session.commit()


async def delete_mylist_value_by_id(
    session: AsyncSession, mylist_value_id: int
) -> None:
    stmt = delete(MyListValue).where(MyListValue.id == mylist_value_id)

    await session.execute(stmt)

    await session.commit()


async def update_mylist_field(
    session: AsyncSession,
    mylist_uuid: UUID,
    field: Literal["title", "description", "type"],
    value: str,
) -> None:
    column = getattr(MyList, field)
    stmt = update(MyList).where(MyList.uuid == mylist_uuid).values({column: value})

    await session.execute(stmt)

    await session.commit()


async def delete_mylist_with_values_by_uuid(
    session: AsyncSession, mylist_uuid: UUID
) -> None:
    stmt1 = delete(MyListValue).where(MyListValue.mylist_uuid == mylist_uuid)
    stmt2 = delete(MyList).where(MyList.uuid == mylist_uuid)

    await session.execute(stmt1)
    await session.execute(stmt2)

    await session.commit()


async def update_made_of_mylist_value(
    session: AsyncSession, mylist_uuid: UUID, number: int
) -> bool:
    subquery = (
        select(MyListValue.id)
        .where(MyListValue.mylist_uuid == mylist_uuid)
        .order_by(MyListValue.id)
        .limit(1)
        .offset(number - 1)
    )

    result = await session.execute(subquery)
    target_id = result.scalar()

    if target_id is None:
        print(f"NOT FOUND mylist_value with number={number} uuid={mylist_uuid}")
        return False

    stmt = (
        update(MyListValue)
        .where(MyListValue.id == target_id)
        .values(made=~MyListValue.made)
    )

    await session.execute(stmt)

    await session.commit()

    return True
