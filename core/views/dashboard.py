from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import BFSTest, FaceDiagnosis, MeridianTest, Questionnaire
from ..services.subjects import (
    get_subject_contact_line,
    get_subject_display_name,
    get_user_identity_name,
)
from .auth import questionnaire_start_url
from .permissions import (
    RESEARCHER_GROUP_ALIAS,
    RESEARCHER_GROUP_NAME,
    can_manage_all_records,
    can_view_all_records,
    is_researcher,
    scope_viewable_records,
)

SUBJECT_PHONE_PATTERN = r"^09\d{8}$"
SUBJECT_DISPLAY_LIMIT = 25
SUBJECT_STATUS_FILTERS = [
    ("all", "全部"),
    ("incomplete", "待補資料"),
    ("complete", "四項完成"),
    ("missing_questionnaire", "缺問卷"),
    ("missing_face", "缺面診"),
    ("missing_bfs", "缺 BFS"),
    ("missing_meridian", "缺經絡儀"),
]


def get_dashboard_role(user):
    if can_manage_all_records(user):
        return {
            "role_label": "管理員",
            "role_title": "系統管理工作台",
            "role_description": "可查看與管理全部檢測資料，並進入後台調整帳號與權限。",
        }

    if is_researcher(user):
        return {
            "role_label": "研究人員",
            "role_title": "研究資料工作台",
            "role_description": "可查看全部受測者資料與檢測紀錄，協助後續資料整理與研究分析。",
        }

    return {
        "role_label": "受測者",
        "role_title": "我的健康工作台",
        "role_description": "查看自己的問卷狀態與檢測紀錄，並繼續完成健康分析流程。",
    }


def get_record_querysets(user, can_view_all):
    questionnaire_queryset = Questionnaire.objects.select_related("user")
    if not can_view_all:
        questionnaire_queryset = questionnaire_queryset.filter(user=user)

    return {
        "questionnaire": questionnaire_queryset,
        "face": scope_viewable_records(
            FaceDiagnosis.objects.select_related("user"), user
        ),
        "bfs": scope_viewable_records(BFSTest.objects.select_related("user"), user),
        "meridian": scope_viewable_records(
            MeridianTest.objects.select_related("user"), user
        ),
    }


def get_subject_user_queryset(user, can_view_all):
    subject_data_filter = (
        Q(questionnaire__isnull=False)
        | Q(face_diagnoses__isnull=False)
        | Q(bfs_tests__isnull=False)
        | Q(meridian_tests__isnull=False)
    )
    subject_account_filter = (
        Q(username__regex=SUBJECT_PHONE_PATTERN)
        & Q(is_staff=False)
        & Q(is_superuser=False)
        & ~Q(groups__name__in=[RESEARCHER_GROUP_NAME, RESEARCHER_GROUP_ALIAS])
    )

    queryset = User.objects.filter(is_active=True).filter(
        subject_account_filter | subject_data_filter
    )

    if not can_view_all:
        queryset = queryset.filter(pk=user.pk)

    return queryset.select_related("questionnaire").distinct()


def apply_dashboard_query(subject_queryset, record_querysets, query):
    if not query:
        return subject_queryset, record_querysets

    filtered_subjects = subject_queryset.filter(
        Q(username__icontains=query)
        | Q(email__icontains=query)
        | Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(questionnaire__name__icontains=query)
        | Q(questionnaire__notes__icontains=query)
        | Q(face_diagnoses__patient_name__icontains=query)
        | Q(face_diagnoses__notes__icontains=query)
        | Q(bfs_tests__patient_name__icontains=query)
        | Q(bfs_tests__notes__icontains=query)
        | Q(meridian_tests__patient_name__icontains=query)
        | Q(meridian_tests__notes__icontains=query)
    ).distinct()

    filtered_records = {
        "questionnaire": record_querysets["questionnaire"].filter(
            Q(name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(notes__icontains=query)
        ),
        "face": record_querysets["face"].filter(
            Q(patient_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(notes__icontains=query)
        ),
        "bfs": record_querysets["bfs"].filter(
            Q(patient_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(notes__icontains=query)
        ),
        "meridian": record_querysets["meridian"].filter(
            Q(patient_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(gender__icontains=query)
            | Q(birth_date__icontains=query)
            | Q(notes__icontains=query)
        ),
    }
    return filtered_subjects, filtered_records


def build_admin_actions():
    return {
        "admin_primary_action": {
            "label": "進入管理後台",
            "description": "開啟完整系統管理。",
            "url": reverse("admin:index"),
        },
        "account_admin_actions": [
            {
                "label": "使用者管理",
                "description": "新增、查看與調整帳號狀態。",
                "url": reverse("admin:auth_user_changelist"),
            },
            {
                "label": "群組權限",
                "description": "設定研究人員與管理權限。",
                "url": reverse("admin:auth_group_changelist"),
            },
        ],
        "detection_admin_actions": [
            {
                "label": "健康問卷",
                "description": "受測者基本資料、病史與生活習慣。",
                "url": reverse("admin:core_questionnaire_changelist"),
                "subactions": [],
            },
            {
                "label": "面診影像",
                "description": "臉部影像與面診分析結果。",
                "url": reverse("admin:core_facediagnosis_changelist"),
                "subactions": [],
            },
            {
                "label": "BFS資料",
                "description": "BFS 測試結果與上傳檔案。",
                "url": reverse("admin:core_bfstest_changelist"),
                "subactions": [
                    {
                        "label": "上傳檔案",
                        "url": reverse("admin:core_bfstestfile_changelist"),
                    },
                ],
            },
            {
                "label": "經絡儀資料",
                "description": "經絡儀報告、檢測結果與讀數。",
                "url": reverse("admin:core_meridiantest_changelist"),
                "subactions": [
                    {
                        "label": "經絡讀數",
                        "url": reverse("admin:core_meridianreading_changelist"),
                    },
                ],
            },
        ],
    }


def get_primary_action(user, own_questionnaire):
    if can_manage_all_records(user):
        return {
            "label": "進入管理後台",
            "description": "管理帳號、群組權限與系統資料。",
            "url": reverse("admin:index"),
        }

    if own_questionnaire:
        return {
            "label": "開始分析",
            "description": "進入四項檢測入口，依流程查看或更新資料。",
            "url": reverse("start_analysis"),
        }

    return {
        "label": "填寫健康問卷",
        "description": "先完成基本資料、病史與生活習慣。",
        "url": reverse("questionnaire"),
    }


def build_record_counts(record_querysets):
    return {
        "questionnaire": record_querysets["questionnaire"].count(),
        "face": record_querysets["face"].count(),
        "bfs": record_querysets["bfs"].count(),
        "meridian": record_querysets["meridian"].count(),
    }


def build_record_filters(record_counts, active_filter, dashboard_query, subject_filter):
    def dashboard_filter_url(record_type):
        params = {"record_type": record_type}
        if dashboard_query:
            params["q"] = dashboard_query
        if subject_filter != "all":
            params["subject_status"] = subject_filter
        return f"{reverse('dashboard')}?{urlencode(params)}#recent-records"

    return [
        {
            "key": "all",
            "label": "全部",
            "count": sum(record_counts.values()),
            "url": dashboard_filter_url("all"),
            "active": active_filter == "all",
        },
        {
            "key": "questionnaire",
            "label": "健康問卷",
            "count": record_counts["questionnaire"],
            "url": dashboard_filter_url("questionnaire"),
            "active": active_filter == "questionnaire",
        },
        {
            "key": "face",
            "label": "面診",
            "count": record_counts["face"],
            "url": dashboard_filter_url("face"),
            "active": active_filter == "face",
        },
        {
            "key": "bfs",
            "label": "BFS",
            "count": record_counts["bfs"],
            "url": dashboard_filter_url("bfs"),
            "active": active_filter == "bfs",
        },
        {
            "key": "meridian",
            "label": "經絡儀",
            "count": record_counts["meridian"],
            "url": dashboard_filter_url("meridian"),
            "active": active_filter == "meridian",
        },
    ]


def build_recent_records(record_querysets, user, can_manage_all):
    recent_records = []

    def add_recent_record(type_key, type_label, title, date, url):
        recent_records.append(
            {
                "type_key": type_key,
                "type": type_label,
                "title": title,
                "date": date,
                "url": url,
            }
        )

    for questionnaire in record_querysets["questionnaire"].order_by("-updated_at")[:6]:
        questionnaire_url = ""
        if can_manage_all:
            questionnaire_url = reverse(
                "admin:core_questionnaire_change",
                args=[questionnaire.pk],
            )
        elif questionnaire.user_id == user.id:
            questionnaire_url = reverse("questionnaire")

        add_recent_record(
            "questionnaire",
            "健康問卷",
            questionnaire.name,
            questionnaire.updated_at,
            questionnaire_url,
        )

    for diagnosis in record_querysets["face"].order_by("-diagnosis_date")[:6]:
        face_url = ""
        if can_manage_all:
            face_url = reverse(
                "admin:core_facediagnosis_change",
                args=[diagnosis.pk],
            )

        add_recent_record(
            "face",
            "面診",
            diagnosis.patient_name,
            diagnosis.diagnosis_date,
            face_url,
        )

    for test in record_querysets["bfs"].order_by("-test_date")[:6]:
        add_recent_record(
            "bfs",
            "BFS",
            test.patient_name,
            test.test_date,
            reverse("bfs_detail", args=[test.pk]),
        )

    for test in record_querysets["meridian"].order_by("-test_date")[:6]:
        add_recent_record(
            "meridian",
            "經絡儀",
            test.patient_name,
            test.test_date,
            reverse("meridian_detail", args=[test.pk]),
        )

    return sorted(recent_records, key=lambda item: item["date"], reverse=True)


def build_subject_overview(
    subject_user,
    actor,
    record_querysets,
    *,
    history_limit=5,
    group_limit=8,
):
    can_view_all = can_view_all_records(actor)
    can_manage_all = can_manage_all_records(actor)

    try:
        questionnaire = subject_user.questionnaire
    except Questionnaire.DoesNotExist:
        questionnaire = None

    subject_identity_name = get_user_identity_name(subject_user)
    subject_name = get_subject_display_name(subject_user)

    subject_face_queryset = record_querysets["face"].filter(user_id=subject_user.id)
    subject_bfs_queryset = record_querysets["bfs"].filter(user_id=subject_user.id)
    subject_meridian_queryset = record_querysets["meridian"].filter(
        user_id=subject_user.id
    )

    face_count = subject_face_queryset.count()
    bfs_count = subject_bfs_queryset.count()
    meridian_count = subject_meridian_queryset.count()
    latest_face = subject_face_queryset.order_by("-diagnosis_date").first()
    latest_bfs = subject_bfs_queryset.order_by("-test_date").first()
    latest_meridian = subject_meridian_queryset.order_by("-test_date").first()

    if can_manage_all:
        if questionnaire:
            questionnaire_url = reverse(
                "admin:core_questionnaire_change",
                args=[questionnaire.pk],
            )
        else:
            questionnaire_initial = {"user": subject_user.id}
            if subject_identity_name:
                questionnaire_initial["name"] = subject_identity_name
            questionnaire_url = (
                f"{reverse('admin:core_questionnaire_add')}?"
                f"{urlencode(questionnaire_initial)}"
            )

        subject_params = {
            "subject": subject_user.id,
            "patient_name": subject_identity_name or subject_user.username,
        }
        admin_subject_params = {"q": subject_identity_name or subject_user.username}
        admin_add_params = {
            "patient_name": subject_identity_name or subject_user.username,
            "user": subject_user.id,
        }

        face_create_url = f"{reverse('upload_face_diagnosis')}?{urlencode(subject_params)}"
        face_list_url = f"{reverse('face_list')}?{urlencode({'subject': subject_user.id})}"
        bfs_create_url = f"{reverse('upload_bfs_test')}?{urlencode(subject_params)}"
        bfs_list_url = f"{reverse('bfs_list')}?{urlencode({'subject': subject_user.id})}"
        meridian_create_url = (
            f"{reverse('upload_meridian_result')}?{urlencode(subject_params)}"
        )
        meridian_list_url = (
            f"{reverse('meridian_list')}?{urlencode({'subject': subject_user.id})}"
        )
    elif subject_user.id == actor.id:
        questionnaire_url = reverse("questionnaire")
        subject_params = {"patient_name": subject_identity_name or subject_user.username}
        # 一般使用者不能自行上傳，只能查看自己的紀錄
        bfs_create_url = ""
        bfs_list_url = reverse("bfs_list")
        meridian_create_url = ""
        meridian_list_url = reverse("meridian_list")
        face_create_url = ""
        face_list_url = reverse("face_list")
    else:
        questionnaire_url = ""
        bfs_create_url = ""
        bfs_list_url = ""
        meridian_create_url = ""
        meridian_list_url = ""
        face_create_url = ""
        face_list_url = ""

    if latest_face and can_manage_all:
        face_primary_url = reverse("face_detail", args=[latest_face.pk])
    else:
        face_primary_url = face_create_url

    latest_activity = max(
        [
            date_value
            for date_value in [
                questionnaire.updated_at if questionnaire else None,
                latest_face.diagnosis_date if latest_face else None,
                latest_bfs.test_date if latest_bfs else None,
                latest_meridian.test_date if latest_meridian else None,
                subject_user.date_joined,
            ]
            if date_value
        ]
    )

    questionnaire_complete = questionnaire is not None
    statuses = [
        {
            "key": "questionnaire",
            "number": "01",
            "label": "健康問卷",
            "state": "已完成" if questionnaire_complete else "待建立",
            "description": "基本資料、病史與生活習慣已建立。"
            if questionnaire_complete
            else "帳號已建立，尚未完成基本問卷。",
            "date": questionnaire.updated_at if questionnaire_complete else None,
            "count": 1 if questionnaire_complete else 0,
            "complete": questionnaire_complete,
            "actions": [
                {
                    "label": "編輯問卷" if questionnaire_complete else "建立問卷",
                    "url": questionnaire_url,
                    "primary": True,
                },
            ]
            if questionnaire_url
            else [],
        },
        {
            "key": "face",
            "number": "02",
            "label": "面診影像",
            "state": f"{face_count} 筆" if face_count else (
                "待管理員上傳" if subject_user.id == actor.id and not can_manage_all
                else "待建立"
            ),
            "description": "臉部影像與面診分析紀錄。",
            "date": latest_face.diagnosis_date if latest_face else None,
            "count": face_count,
            "complete": face_count > 0,
            "actions": (
                [
                    {
                        "label": "查看最新" if latest_face else "新增面診",
                        "url": face_primary_url,
                        "primary": True,
                    },
                    {
                        "label": "新增一筆" if latest_face else "查看列表",
                        "url": face_create_url if latest_face else face_list_url,
                        "primary": False,
                    },
                ]
                if can_manage_all else [
                    {"label": "查看紀錄", "url": face_list_url, "primary": True}
                ]
                if subject_user.id == actor.id and face_count else []
            ),
        },
        {
            "key": "bfs",
            "number": "03",
            "label": "BFS",
            "state": f"{bfs_count} 筆" if bfs_count else "待建立",
            "description": "生物頻譜回饋分析儀量測資料。",
            "date": latest_bfs.test_date if latest_bfs else None,
            "count": bfs_count,
            "complete": bfs_count > 0,
            "actions": [
                {
                    "label": "查看紀錄" if latest_bfs else "上傳 BFS",
                    "url": bfs_list_url if latest_bfs else bfs_create_url,
                    "primary": True,
                },
                {
                    "label": "上傳新的一筆" if latest_bfs else "查看紀錄",
                    "url": bfs_create_url if latest_bfs else bfs_list_url,
                    "primary": False,
                },
            ]
            if bfs_create_url
            else (
                [{"label": "查看紀錄", "url": bfs_list_url, "primary": True}]
                if bfs_list_url and bfs_count
                else []
            ),
        },
        {
            "key": "meridian",
            "number": "04",
            "label": "經絡儀",
            "state": f"{meridian_count} 筆" if meridian_count else "待建立",
            "description": "經絡儀 PDF、讀數與分析結果。",
            "date": latest_meridian.test_date if latest_meridian else None,
            "count": meridian_count,
            "complete": meridian_count > 0,
            "actions": [
                {
                    "label": "查看紀錄" if latest_meridian else "上傳經絡儀",
                    "url": meridian_list_url if latest_meridian else meridian_create_url,
                    "primary": True,
                },
                {
                    "label": "上傳新的一筆" if latest_meridian else "查看紀錄",
                    "url": meridian_create_url if latest_meridian else meridian_list_url,
                    "primary": False,
                },
            ]
            if meridian_create_url
            else (
                [{"label": "查看紀錄", "url": meridian_list_url, "primary": True}]
                if meridian_list_url and meridian_count
                else []
            ),
        },
    ]

    history_groups = build_subject_history_groups(
        questionnaire,
        subject_face_queryset,
        subject_bfs_queryset,
        subject_meridian_queryset,
        questionnaire_url,
        can_manage_all,
        group_limit=group_limit,
    )
    subject_history = sorted(
        [
            item
            for group in history_groups
            for item in group["items"]
        ],
        key=lambda item: item["date"],
        reverse=True,
    )
    if history_limit is not None:
        subject_history = subject_history[:history_limit]

    detail_url = ""
    if can_view_all or subject_user.id == actor.id:
        detail_url = reverse("subject_detail", args=[subject_user.pk])

    return {
        "panel_id": f"subject-{subject_user.pk}",
        "id": subject_user.pk,
        "name": subject_name,
        "needs_name": not bool(subject_identity_name),
        "account_label": "目前登入帳號" if subject_user.id == actor.id else "受測者",
        "updated_at": latest_activity,
        "contact_line": get_subject_contact_line(subject_user),
        "phone": subject_user.username,
        "email": subject_user.email or "尚未填寫",
        "date_joined": subject_user.date_joined,
        "detail_url": detail_url,
        "statuses": statuses,
        "history": subject_history,
        "history_groups": history_groups,
        "completed_count": sum(1 for status in statuses if status["complete"]),
    }


def build_subject_history_groups(
    questionnaire,
    face_queryset,
    bfs_queryset,
    meridian_queryset,
    questionnaire_url,
    can_manage_all,
    *,
    group_limit,
):
    def limit(queryset):
        return queryset if group_limit is None else queryset[:group_limit]

    groups = [
        {
            "key": "questionnaire",
            "label": "健康問卷",
            "count": 1 if questionnaire else 0,
            "items": [],
        },
        {
            "key": "face",
            "label": "面診影像",
            "count": face_queryset.count(),
            "items": [],
        },
        {
            "key": "bfs",
            "label": "BFS",
            "count": bfs_queryset.count(),
            "items": [],
        },
        {
            "key": "meridian",
            "label": "經絡儀",
            "count": meridian_queryset.count(),
            "items": [],
        },
    ]

    if questionnaire:
        groups[0]["items"].append(
            {
                "type": "健康問卷",
                "title": "基本資料與生活習慣",
                "date": questionnaire.updated_at,
                "url": questionnaire_url,
            }
        )

    for diagnosis in limit(face_queryset.order_by("-diagnosis_date")):
        diagnosis_url = ""
        if can_manage_all:
            diagnosis_url = reverse(
                "admin:core_facediagnosis_change",
                args=[diagnosis.pk],
            )
        groups[1]["items"].append(
            {
                "type": "面診",
                "title": diagnosis.patient_name,
                "date": diagnosis.diagnosis_date,
                "url": diagnosis_url,
            }
        )

    for test in limit(bfs_queryset.order_by("-test_date")):
        groups[2]["items"].append(
            {
                "type": "BFS",
                "title": test.patient_name,
                "date": test.test_date,
                "url": reverse("bfs_detail", args=[test.pk]),
            }
        )

    for test in limit(meridian_queryset.order_by("-test_date")):
        groups[3]["items"].append(
            {
                "type": "經絡儀",
                "title": test.patient_name,
                "date": test.test_date,
                "url": reverse("meridian_detail", args=[test.pk]),
            }
        )

    return groups


def subject_matches_filter(subject, filter_key):
    status_map = {status["key"]: status["complete"] for status in subject["statuses"]}

    if filter_key == "complete":
        return all(status_map.values())
    if filter_key == "incomplete":
        return not all(status_map.values())
    if filter_key == "missing_questionnaire":
        return not status_map["questionnaire"]
    if filter_key == "missing_face":
        return not status_map["face"]
    if filter_key == "missing_bfs":
        return not status_map["bfs"]
    if filter_key == "missing_meridian":
        return not status_map["meridian"]

    return True


def build_subject_filters(all_subjects, active_filter, dashboard_query, record_filter):
    def subject_filter_url(filter_key):
        params = {}
        if dashboard_query:
            params["q"] = dashboard_query
        if filter_key != "all":
            params["subject_status"] = filter_key
        if record_filter != "all":
            params["record_type"] = record_filter
        query_string = urlencode(params)
        url = reverse("dashboard")
        if query_string:
            url = f"{url}?{query_string}"
        return f"{url}#subject-tracker"

    return [
        {
            "key": filter_key,
            "label": label,
            "count": sum(
                1 for subject in all_subjects if subject_matches_filter(subject, filter_key)
            ),
            "url": subject_filter_url(filter_key),
            "active": filter_key == active_filter,
        }
        for filter_key, label in SUBJECT_STATUS_FILTERS
    ]


@login_required(login_url="login")
def dashboard_view(request):
    user = request.user
    can_view_all = can_view_all_records(user)
    can_manage_all = can_manage_all_records(user)
    dashboard_query = request.GET.get("q", "").strip()
    record_filter = request.GET.get("record_type", "all")
    subject_status_filter = request.GET.get("subject_status", "all")

    allowed_record_types = {"all", "questionnaire", "face", "bfs", "meridian"}
    allowed_subject_filters = {filter_key for filter_key, _ in SUBJECT_STATUS_FILTERS}
    if record_filter not in allowed_record_types:
        record_filter = "all"
    if subject_status_filter not in allowed_subject_filters:
        subject_status_filter = "all"

    own_questionnaire = Questionnaire.objects.filter(user=user).first()
    if not can_view_all:
        if own_questionnaire:
            return redirect("start_analysis")
        return redirect(questionnaire_start_url())

    role_context = get_dashboard_role(user)
    record_querysets = get_record_querysets(user, can_view_all)
    subject_queryset = get_subject_user_queryset(user, can_view_all)
    subject_queryset, record_querysets = apply_dashboard_query(
        subject_queryset,
        record_querysets,
        dashboard_query,
    )

    all_subject_overviews = [
        build_subject_overview(subject_user, user, record_querysets)
        for subject_user in subject_queryset.order_by("-date_joined")
    ]
    subject_filters = build_subject_filters(
        all_subject_overviews,
        subject_status_filter,
        dashboard_query,
        record_filter,
    )
    subject_overviews = [
        subject
        for subject in all_subject_overviews
        if subject_matches_filter(subject, subject_status_filter)
    ]
    selected_subject_id = request.GET.get("subject", "")
    if selected_subject_id.isdecimal():
        selected_subject_pk = int(selected_subject_id)
        subject_overviews.sort(key=lambda subject: subject["id"] != selected_subject_pk)

    record_counts = build_record_counts(record_querysets)
    recent_records = build_recent_records(record_querysets, user, can_manage_all)
    active_subject_count = get_subject_user_queryset(user, can_view_all).count()
    active_user_count = User.objects.filter(is_active=True).count()

    if can_view_all:
        stats = [
            {"label": "受測者", "value": active_subject_count},
            {"label": "面診紀錄", "value": record_querysets["face"].count()},
            {"label": "BFS紀錄", "value": record_querysets["bfs"].count()},
            {"label": "經絡紀錄", "value": record_querysets["meridian"].count()},
            {"label": "系統帳號", "value": active_user_count},
        ]
    else:
        stats = [
            {"label": "健康問卷", "value": record_querysets["questionnaire"].count()},
            {"label": "BFS紀錄", "value": record_querysets["bfs"].count()},
            {"label": "經絡紀錄", "value": record_querysets["meridian"].count()},
            {"label": "面診紀錄", "value": record_querysets["face"].count()},
        ]

    admin_actions = {
        "admin_primary_action": None,
        "account_admin_actions": [],
        "detection_admin_actions": [],
    }
    if can_manage_all:
        admin_actions = build_admin_actions()

    subject_result_count = len(subject_overviews)
    record_result_count = sum(record_counts.values())
    subject_display_count = min(subject_result_count, SUBJECT_DISPLAY_LIMIT)
    has_more_subjects = subject_result_count > subject_display_count
    visible_subjects = subject_overviews[:SUBJECT_DISPLAY_LIMIT]

    return render(
        request,
        "core/dashboard.html",
        {
            **role_context,
            **admin_actions,
            "can_view_all_records": can_view_all,
            "can_manage_all_records": can_manage_all,
            "own_questionnaire": own_questionnaire,
            "stats": stats,
            "dashboard_query": dashboard_query,
            "subject_status_filter": subject_status_filter,
            "subject_filters": subject_filters,
            "primary_action": get_primary_action(user, own_questionnaire),
            "record_filters": build_record_filters(
                record_counts,
                record_filter,
                dashboard_query,
                subject_status_filter,
            ),
            "record_filter": record_filter,
            "recent_records": recent_records,
            "subject_overviews": visible_subjects,
            "subject_result_count": subject_result_count,
            "subject_display_count": subject_display_count,
            "has_more_subjects": has_more_subjects,
            "record_result_count": record_result_count,
        },
    )


@login_required(login_url="login")
def subject_detail_view(request, subject_id):
    user = request.user
    can_view_all = can_view_all_records(user)
    record_querysets = get_record_querysets(user, can_view_all)
    subject_queryset = get_subject_user_queryset(user, can_view_all)
    subject_user = get_object_or_404(subject_queryset, pk=subject_id)
    subject = build_subject_overview(
        subject_user,
        user,
        record_querysets,
        history_limit=30,
        group_limit=None,
    )
    if subject_user.pk == user.pk:
        return_url = reverse("start_analysis")
        return_label = "返回四項檢測"
    elif can_view_all:
        return_url = f"{reverse('dashboard')}?subject={subject_user.pk}#subject-list"
        return_label = "返回受測者清單"
    else:
        return_url = reverse("start_analysis")
        return_label = "返回四項檢測"

    return render(
        request,
        "core/subject_detail.html",
        {
            "subject": subject,
            "return_url": return_url,
            "return_label": return_label,
            "can_manage_all_records": can_manage_all_records(user),
            "can_view_all_records": can_view_all,
        },
    )
