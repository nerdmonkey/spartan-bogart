from datetime import datetime
from typing import List, Tuple

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.exceptions.user import (
    DuplicateUserError,
    InvalidSortFieldException,
    UserNotFoundException,
)
from app.models.user import User
from app.requests.user import UserCreateRequest, UserUpdateRequest
from app.responses.user import UserCreateResponse, UserResponse, UserUpdateResponse


class UserService:
    """
    Service class for managing user-related operations.
    """

    def __init__(self, db: Session):
        """
        Initialize the UserService class.

        Args:
            db (Session): The database session.
        """
        self.db = db

    def get_by_id(self, id: int) -> User:
        """
        Retrieve a user by their ID.

        Args:
            id (int): The ID of the user.

        Returns:
            User: The user object.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = self.db.query(User).filter(User.id == id).first()
        if not user:
            raise UserNotFoundException("User not found")
        return user

    def filter(self, *conditions):
        for condition in conditions:
            if isinstance(condition, list):
                start_date, end_date = condition
                self.filtered_users = [
                    user
                    for user in self.filtered_users
                    if start_date <= user.created_at <= end_date
                ]
            else:
                attribute = condition.left.key
                value = condition.right.value
                self.filtered_users = [
                    user
                    for user in self.filtered_users
                    if getattr(user, attribute) == value
                ]
        return self

    def all(
        self,
        page: int = 1,
        items_per_page: int = 10,
        sort_type: str = "asc",
        sort_by: str = "id",
        username: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> Tuple[List[UserResponse], int, int, int, int]:
        offset = (page - 1) * items_per_page
        query = self.db.query(User)

        # Apply username filter in MockSession
        if username:
            query = query.filter(User.username == username)

        # Sorting logic
        if not hasattr(User, sort_by):
            raise InvalidSortFieldException("Invalid sort field or sort type")

        sort_column = getattr(User, sort_by)
        query = query.order_by(
            asc(sort_column) if sort_type == "asc" else desc(sort_column)
        )

        # Retrieve filtered and paginated results from MockSession
        users = query.offset(offset).limit(items_per_page).all()

        # Apply date filtering directly within UserService
        if start_date and end_date:
            users = [
                user for user in users if start_date <= user.created_at <= end_date
            ]

        # Convert users to response format
        users_response = [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
            for user in users
        ]

        # Pagination details
        total = query.count()
        last_page = (total - 1) // items_per_page + 1
        first_item = offset + 1
        last_item = min(offset + items_per_page, total)

        return users_response, total, last_page, first_item, last_item

    def save(self, user_request: UserCreateRequest) -> UserCreateResponse:
        """
        Save a new user to the database.

        Args:
            user_request (UserCreateRequest): The user create request object.

        Returns:
            UserCreateResponse: The response data of the created user.

        Raises:
            DuplicateUserError: If a user with the same email already exists.
        """
        existing_user = (
            self.db.query(User).filter(User.email == user_request.email).first()
        )
        if existing_user:
            raise DuplicateUserError("User with this email already exists")

        user_data = user_request.model_dump(exclude_unset=True)
        user_data["password"] = "hashed_" + user_data["password"]
        new_user = User(**user_data)

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return UserCreateResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            created_at=new_user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=new_user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def update(self, id: int, user_request: UserUpdateRequest) -> UserUpdateResponse:
        """
        Update a user in the database.
        Args:
            id (int): The ID of the user.
            user_request (UserUpdateRequest): The user update request object.
        Returns:
            UserUpdateResponse: The response data of the updated user.
        Raises:
            UserNotFoundException: If the user is not found.
        """
        user = self.get_by_id(id)
        update_data = user_request.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["password"] = "hashed_" + update_data["password"]
        for key, value in update_data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return UserUpdateResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def delete(self, id: int) -> UserResponse:
        """
        Delete a user by ID.
        Args:
            id (int): The ID of the user to delete.
        Returns:
            UserResponse: The deleted user information.
        Raises:
            UserNotFoundException: If the user is not found.
        """
        user = self.get_by_id(id)
        response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.db.delete(user)
        self.db.commit()
        return response

    def total(self) -> int:
        """
        Get the total number of users.

        Returns:
            int: The total number of users.
        """
        return self.db.query(User).count()

    def find(self, id: int) -> UserResponse:
        """
        Find a user by their ID and return the user response.
        Args:
            id (int): The ID of the user.
        Returns:
            UserResponse: The user response.
        Raises:
            UserNotFoundException: If the user is not found.
        """
        user = self.get_by_id(id)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def bulk_delete(self, user_ids: List[int]) -> List[int]:
        users_to_delete = self.db.query(User).filter(User.id.in_(user_ids)).all()

        if not users_to_delete:
            raise UserNotFoundException("No users found for the given IDs")

        deleted_user_ids = [user.id for user in users_to_delete]
        for user in users_to_delete:
            self.db.delete(user)

        self.db.commit()

        return deleted_user_ids
