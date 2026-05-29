import asyncio
from datetime import datetime, timezone, timedelta
from uuid import UUID

from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import PendingRollbackError, IntegrityError

from core.models import *


test_user_data = {
    "max_id": 322,
    "chat_id": 322,
    "first_name": "Jake",
    "last_name": "Smith",
    "username": "jake",
    "is_bot": False,
    "last_activity_time": 123892183,
}

test_mylist_data = {
    "title": "Название",
    "description": "Описание",
    "type": "Тип",
}


async def create_user(session: AsyncSession, user_data: dict) -> User | None:
    if "user_id" in user_data:
        user_data["max_id"] = user_data["user_id"]
        user_data.pop("user_id")

    user_data.pop("status", None)

    user = User(**user_data)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_mylist(session: AsyncSession, user_id: int) -> MyList | None:
    try:
        user = await get_user_by_max_id(session, user_id)
        mylist = MyList()
        mylist.create_time = datetime.now(timezone(timedelta(hours=3))).replace(microsecond=0)

        link = UserMyListAssociation(
            user=user,
            mylist=mylist,
            role=MyListUserRole.AUTHOR,
        )

        session.add(mylist)
        session.add(link)

        await session.commit()
        await session.refresh(mylist)
        await session.refresh(link)
        return mylist
    except Exception as e:
        print(e)
        return None

async def create_mylist_value(
    session: AsyncSession, mylist_uuid: UUID, value: str
) -> MyListValue | None:
    try:
        mylist_value = MyListValue(value=value, mylist_uuid=mylist_uuid)
        session.add(mylist_value)
        await session.commit()
        await session.refresh(mylist_value)
        return mylist_value
    except:
        return None


async def get_user_id_by_max_id(session: AsyncSession, max_id: int) -> int | None:
    subquery = select(User.id).where(User.max_id == max_id)

    result = await session.execute(subquery)
    target_id = result.scalar()

    if target_id is None:
        return None

    return target_id


async def get_user_by_max_id(session: AsyncSession, max_id: int) -> User | None:
    stmt = select(User).where(User.max_id == max_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    return user


async def get_mylist_by_uuid(session: AsyncSession, mylist_uuid: UUID) -> MyList | None:
    stmt = (
        select(MyList)
        .where(MyList.uuid == mylist_uuid)
    )
    result = await session.execute(stmt)
    mylist = result.scalar_one_or_none()

    if mylist is None:
        return None

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
        return None

    return mylist


async def get_mylist_with_values_with_users_by_uuid(
    session: AsyncSession,
    mylist_uuid: UUID,
) -> MyList | None:
    stmt = (
        select(MyList)
        .where(MyList.uuid == mylist_uuid)
        .options(
            selectinload(MyList.values),
            selectinload(MyList.user_links)
            .joinedload(UserMyListAssociation.user),
        )
    )

    result = await session.execute(stmt)
    mylist = result.scalar_one_or_none()
    return mylist


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


async def update_made_of_mylist_value(
    session: AsyncSession, value_id: int
) -> None:
    stmt = (
        update(MyListValue)
        .where(MyListValue.id == value_id)
        .values(made=~MyListValue.made)
    )

    await session.execute(stmt)

    await session.commit()


async def get_mylist_value_id_by_number(
    session: AsyncSession, mylist_uuid: UUID, number: int
) -> int | None:
    stmt = (
        select(MyListValue.id)
        .where(MyListValue.mylist_uuid == mylist_uuid)
        .order_by(MyListValue.id)
        .limit(1)
        .offset(number)
    )

    result = await session.execute(stmt)
    target_id = result.scalar()

    if target_id is None:
        return None
    return target_id


async def get_mylists_by_max_id(
    session: AsyncSession, max_id: int, page: int = 1, deleted: bool = False
) -> list[MyList] | None:
    user = await get_user_by_max_id(session, max_id)

    if user is None:
        return

    if not deleted:
        stmt = (
            select(MyList)
            .join(MyList.user_links)
            .where(
                UserMyListAssociation.user_id == user.id,
                MyList.deleted == False
            )
            .order_by(MyList.id)
            .limit(11)
            .offset((page - 1) * 10)
            .options(selectinload(MyList.user_links))
        )
    else:
        stmt = (
            select(MyList)
            .join(MyList.user_links)
            .where(
                UserMyListAssociation.user_id == user.id,
                UserMyListAssociation.role == MyListUserRole.AUTHOR,
                MyList.deleted == True
            )
            .order_by(MyList.id)
            .limit(11)
            .offset((page - 1) * 10)
            .options(selectinload(MyList.user_links))
        )

    result = await session.execute(stmt)
    mylists = result.scalars().all() or None

    return mylists


async def update_delete_to_mylist_by_uuid(
    session: AsyncSession, mylist_uuid: UUID
) -> None:
    dtime = datetime.now(timezone(timedelta(hours=3))).replace(microsecond=0)
    stmt = (
        update(MyList)
        .where(MyList.uuid == mylist_uuid)
        .values(
            deleted=True,
            delete_time=dtime,
        )
    )

    await session.execute(stmt)
    await session.commit()


async def delete_deleted_mylists_by_max_id(
    session: AsyncSession, max_id: int
) -> None:
    user = await get_user_by_max_id(session, max_id)

    stmt = (
        select(MyList)
        .join(MyList.user_links)
        .where(
            UserMyListAssociation.user_id == user.id,
            MyList.deleted.is_(True)
        )
        .options(selectinload(MyList.user_links))
    )

    result = await session.execute(stmt)
    mylists = result.scalars().all()

    for mylist in mylists:
        await session.delete(mylist)
        await delete_associations_by_id(session, mylist.id)

    await session.commit()


async def delete_user_from_mylist_by_max_id_and_uuid(
    session: AsyncSession, mylist_uuid: UUID, max_id: int
):
    user = await get_user_by_max_id(session, max_id)
    mylist = await get_mylist_by_uuid(session, mylist_uuid)

    stmt = (
        delete(UserMyListAssociation)
        .where(UserMyListAssociation.user_id == user.id,
               UserMyListAssociation.mylist_id == mylist.id)
    )

    await session.execute(stmt)
    await session.commit()


async def delete_associations_by_id(
    session: AsyncSession, mylist_id: int
) -> None:
    stmt = (
        delete(UserMyListAssociation)
        .where(UserMyListAssociation.mylist_id == mylist_id)
    )

    await session.execute(stmt)
    await session.commit()


async def delete_deleted_from_mylists_by_uuid(
    session: AsyncSession, mylist_uuid: UUID
) -> None:
    stmt = (
        update(MyList)
        .where(MyList.uuid == mylist_uuid)
        .values(
            deleted=False,
            delete_time=None,
        )
    )

    await session.execute(stmt)
    await session.commit()


async def add_user_to_list(session: AsyncSession, mylist_uuid: UUID, user_data: dict) -> None:
    user = await get_user_by_max_id(session, user_data["user_id"])
    if user is None:
        user = await create_user(session, user_data)

    mylist = await get_mylist_by_uuid(session, mylist_uuid)

    link = UserMyListAssociation(
        user=user,
        mylist=mylist,
        role=MyListUserRole.USER,
    )

    try:
        session.add(link)
        await session.commit()
        await session.refresh(user)
        await session.refresh(link)
    except IntegrityError:
        return None


async def add_telephone_to_user_by_max_id(
    session: AsyncSession, max_id: int, telephone: str
):
    stmt = (
        update(User)
        .where(User.max_id == max_id)
        .values(
            telephone=telephone,
        )
    )

    await session.execute(stmt)
    await session.commit()


async def get_users_with_roles_by_mylist_uuid(
    session: AsyncSession,
    mylist_uuid: UUID,
) -> list[tuple[User, MyListUserRole]]:
    stmt = (
        select(UserMyListAssociation)
        .join(UserMyListAssociation.mylist)
        .join(UserMyListAssociation.user)
        .where(MyList.uuid == mylist_uuid)
        .options(joinedload(UserMyListAssociation.user))
    )

    result = await session.execute(stmt)
    links = result.scalars().all()

    return [(link.user, link.role) for link in links]


async def get_user_from_association_by_number(
    session: AsyncSession,
    mylist_id: int,
    number: int,
) -> UserMyListAssociation | None:
    stmt = (
        select(UserMyListAssociation)
        .where(UserMyListAssociation.mylist_id == mylist_id,
               UserMyListAssociation.role != MyListUserRole.AUTHOR)
        .offset(number - 1)
        .limit(1)
    )

    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    return user


async def delete_user_from_association_by_id(
        session: AsyncSession,
        mylist_id: int,
        user_id: int,
) -> None:
    print("mylist_id:", mylist_id, "user_id:", user_id)

    stmt = (
        delete(UserMyListAssociation)
        .where(UserMyListAssociation.mylist_id == mylist_id,
               UserMyListAssociation.user_id == user_id)
    )

    await session.execute(stmt)
    await session.commit()


async def main() -> None:
    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_with_users_by_uuid(session, UUID("4b7d5ef664364ae5b3c338d70d6cd0af"))
        print([link.user for link in mylist.user_links])


if __name__ == "__main__":
    asyncio.run(main())