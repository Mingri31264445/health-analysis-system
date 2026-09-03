from .views.permissions import can_view_all_records


def navigation_roles(request):
    user = request.user
    return {
        "show_dashboard_link": user.is_authenticated and can_view_all_records(user),
    }
