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


def get_viewable_record_or_404(queryset, user, **kwargs):
    return get_object_or_404(scope_viewable_records(queryset, user), **kwargs)


def get_manageable_record_or_404(queryset, user, **kwargs):
    return get_object_or_404(scope_manageable_records(queryset, user), **kwargs)


def get_user_record_or_404(queryset, user, **kwargs):
    return get_viewable_record_or_404(queryset, user, **kwargs)
