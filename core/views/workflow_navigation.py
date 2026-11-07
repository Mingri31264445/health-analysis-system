from urllib.parse import urlencode

from django.urls import reverse

from ..services.subjects import get_subject_display_name
from .permissions import can_view_all_records


def workflow_navigation(request, subject_user=None, record_type=None, selected_ids=None):
    if subject_user and subject_user.pk != request.user.pk and can_view_all_records(request.user):
        workflow_url = reverse("subject_detail", args=[subject_user.pk])
        workflow_label = "返回受測者工作台"
    elif subject_user is None and can_view_all_records(request.user):
        workflow_url = reverse("dashboard")
        workflow_label = "返回管理後台"
    else:
        workflow_url = reverse("start_analysis")
        workflow_label = "返回四項檢測"

    context = {"workflow_url": workflow_url, "workflow_label": workflow_label}
    if record_type:
        list_url = reverse(f"{record_type}_list")
        upload_name = {
            "bfs": "upload_bfs_test",
            "meridian": "upload_meridian_result",
            "face": "upload_face_diagnosis",
        }[record_type]
        upload_url = reverse(upload_name)
        if subject_user and subject_user.pk != request.user.pk and can_view_all_records(request.user):
            query = urlencode({"subject": subject_user.pk})
            list_url = f"{list_url}?{query}"
            upload_url = f"{upload_url}?{urlencode({'subject': subject_user.pk, 'patient_name': get_subject_display_name(subject_user)})}"
        return_url = list_url
        if selected_ids:
            separator = "&" if "?" in return_url else "?"
            return_url += f"{separator}{urlencode({'selected': ','.join(map(str, selected_ids))})}"
        context.update({
            "record_list_url": list_url,
            "record_return_url": f"{return_url}#records",
            "record_upload_url": upload_url,
        })
    return context
