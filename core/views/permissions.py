from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


RESEARCHER_GROUP_NAME = "研究人員"
RESEARCHER_GROUP_ALIAS = "researcher"


def is_system_admin(user):
    return user.is_staff or user.is_superuser


def is_researcher(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(
        name__in=[RESEARCHER_GROUP_NAME, RESEARCHER_GROUP_ALIAS]
    ).exists()


def can_view_all_records(user):
    return is_system_admin(user) or is_researcher(user)


def can_manage_all_records(user):
    return is_system_admin(user)


def can_upload_records(user):
    """只有管理員能上傳面診、BFS、經絡儀；受測者與研究人員都不行。"""
    return user.is_authenticated and is_system_admin(user)


def can_manage_record(user, record):
    return can_manage_all_records(user) or record.user_id == user.id


def scope_viewable_records(queryset, user):
    if can_view_all_records(user):
        return queryset
    return queryset.filter(user=user)


def scope_manageable_records(queryset, user):
    if can_manage_all_records(user):
        return queryset
    return queryset.filter(user=user)


def scope_user_records(queryset, user):
    return scope_viewable_records(queryset, user)

#驗證使用者是否有檢視的權限
def get_viewable_record_or_404(queryset, user, **kwargs):
    return get_object_or_404(scope_viewable_records(queryset, user), **kwargs)

#驗證使用者是否有管理的權限
def get_manageable_record_or_404(queryset, user, **kwargs):
    return get_object_or_404(scope_manageable_records(queryset, user), **kwargs)


def get_user_record_or_404(queryset, user, **kwargs):
    return get_viewable_record_or_404(queryset, user, **kwargs)



def admin_upload_required(view_func):
    """上傳頁專用：未登入導向登入頁，非管理員直接 403。"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "login")
        if not can_upload_records(request.user):
            raise PermissionDenied("僅管理員可上傳檢測資料。")
        return view_func(request, *args, **kwargs)

    return wrapper
