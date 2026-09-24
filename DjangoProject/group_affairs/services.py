from django.db.models import Q

from users.models import UserProfile

from .models import GroupAffairAdmin, GroupAffairBoard


SYSTEM_ADMIN_ROLE = "系统管理员"
TUTOR_ROLE = "导师用户"
LAND_HOST_ROLE = "land设备主机"


def has_role(user, role_name):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.roles.filter(name=role_name).exists()


def is_system_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "is_system_admin", False) or has_role(user, SYSTEM_ADMIN_ROLE)


def is_tutor(user):
    return has_role(user, TUTOR_ROLE)


def is_land_host(user):
    return getattr(user, "is_land_host", False) or has_role(user, LAND_HOST_ROLE)


def get_user_group_tutor(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if is_tutor(user):
        return user
    return getattr(user, "assigned_tutor", None)


def get_group_members_queryset(tutor):
    return (
        UserProfile.objects
        .filter(Q(id=tutor.id) | Q(assigned_tutor=tutor))
        .distinct()
        .order_by("name", "username", "id")
    )


def is_group_member(user, tutor):
    if not user or not tutor:
        return False
    return user.id == tutor.id or getattr(user, "assigned_tutor_id", None) == tutor.id


def get_or_create_board_for_tutor(tutor):
    return GroupAffairBoard.objects.get_or_create(tutor=tutor)


def ensure_boards_for_all_tutors():
    tutors = UserProfile.objects.filter(roles__name=TUTOR_ROLE).distinct()
    for tutor in tutors:
        get_or_create_board_for_tutor(tutor)


def can_access_board(user, board):
    if is_land_host(user):
        return False
    if is_system_admin(user):
        return True
    return is_group_member(user, board.tutor)


def can_manage_board(user, board):
    if is_land_host(user):
        return False
    if is_system_admin(user):
        return True
    if user.id == board.tutor_id:
        return True
    return GroupAffairAdmin.objects.filter(tutor=board.tutor, user=user).exists()
