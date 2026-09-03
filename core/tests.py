from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from .forms import RegisterForm
from .models import BFSTest, Questionnaire
from .services.subjects import get_subject_display_name
from .views.permissions import (
    RESEARCHER_GROUP_NAME,
    can_manage_record,
    can_view_all_records,
    scope_manageable_records,
    scope_viewable_records,
)


class RecordPermissionTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="0911111111", password="pass")
        self.user_b = User.objects.create_user(username="0922222222", password="pass")
        self.researcher = User.objects.create_user(username="0933333333", password="pass")
        self.staff = User.objects.create_user(
            username="0944444444",
            password="pass",
            is_staff=True,
        )

        researcher_group, _ = Group.objects.get_or_create(name=RESEARCHER_GROUP_NAME)
        self.researcher.groups.add(researcher_group)

        self.record_a = BFSTest.objects.create(user=self.user_a, patient_name="User A")
        self.record_b = BFSTest.objects.create(user=self.user_b, patient_name="User B")

    def test_regular_user_can_only_view_own_records(self):
        records = scope_viewable_records(BFSTest.objects.all(), self.user_a)

        self.assertQuerySetEqual(records, [self.record_a], transform=lambda item: item)

    def test_researcher_can_view_all_but_not_manage_others_records(self):
        viewable_records = scope_viewable_records(BFSTest.objects.all(), self.researcher)
        manageable_records = scope_manageable_records(BFSTest.objects.all(), self.researcher)

        self.assertTrue(can_view_all_records(self.researcher))
        self.assertQuerySetEqual(
            viewable_records.order_by("id"),
            [self.record_a, self.record_b],
            transform=lambda item: item,
        )
        self.assertQuerySetEqual(manageable_records, [], transform=lambda item: item)
        self.assertFalse(can_manage_record(self.researcher, self.record_a))

    def test_staff_can_manage_all_records(self):
        manageable_records = scope_manageable_records(BFSTest.objects.all(), self.staff)

        self.assertQuerySetEqual(
            manageable_records.order_by("id"),
            [self.record_a, self.record_b],
            transform=lambda item: item,
        )
        self.assertTrue(can_manage_record(self.staff, self.record_a))


class DashboardRoleTests(TestCase):
    def create_questionnaire(self, user, name):
        return Questionnaire.objects.create(
            user=user,
            name=name,
            gender="M",
            blood_type="O",
            height=170,
            weight=60,
            birth_date=date(2000, 1, 1),
            sleep_hours=7,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_regular_user_is_redirected_to_questionnaire_before_dashboard(self):
        user = User.objects.create_user(username="0955555555", password="pass")
        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/questionnaire/", response.url)

    def test_regular_user_with_questionnaire_is_redirected_to_analysis(self):
        user = User.objects.create_user(username="0955555555", password="pass")
        self.create_questionnaire(user, "一般受測者")
        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/start/")

    def test_researcher_sees_research_dashboard(self):
        researcher = User.objects.create_user(username="0966666666", password="pass")
        researcher_group, _ = Group.objects.get_or_create(name=RESEARCHER_GROUP_NAME)
        researcher.groups.add(researcher_group)
        self.client.force_login(researcher)

        response = self.client.get("/dashboard/")

        self.assertContains(response, "研究資料工作台")
        self.assertContains(response, "研究人員")

    def test_staff_sees_admin_dashboard(self):
        staff = User.objects.create_user(
            username="0977777777",
            password="pass",
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get("/dashboard/")

        self.assertContains(response, "系統管理工作台")
        self.assertContains(response, "管理員")

    def test_staff_can_search_dashboard_subjects(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        user_a = User.objects.create_user(
            username="0988888888",
            email="subject@example.com",
            password="pass",
        )
        user_b = User.objects.create_user(
            username="0966666666",
            email="other@example.com",
            password="pass",
        )
        self.create_questionnaire(user_a, "陳怡君")
        self.create_questionnaire(user_b, "王小明")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/", {"q": "陳"})

        self.assertContains(response, "找到 1 位受測者")
        self.assertContains(response, "陳怡君")
        self.assertNotContains(response, "王小明")

    def test_staff_can_search_subject_account_without_questionnaire(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        User.objects.create_user(
            username="0966889536",
            email="subject@example.com",
            password="pass",
        )
        self.client.force_login(staff)

        response = self.client.get("/dashboard/", {"q": "0966889536"})

        self.assertContains(response, "找到 1 位受測者")
        self.assertContains(response, "0966889536")
        self.assertContains(response, "待建立")

    def test_staff_health_profile_is_in_subject_workbench(self):
        staff = User.objects.create_user(
            username="0971602980",
            email="admin@example.com",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
        self.create_questionnaire(staff, "林志明")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/")

        self.assertContains(response, "目前登入帳號")
        self.assertContains(response, "林志明")

    def test_unlinked_bfs_record_does_not_complete_account_status(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        User.objects.create_user(
            username="0966889536",
            email="subject@example.com",
            password="pass",
        )
        BFSTest.objects.create(patient_name="0966889536")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/", {"q": "0966889536"})

        self.assertContains(response, "0/4")
        self.assertContains(response, "BFS")
        self.assertContains(response, "待建立")

    def test_staff_dashboard_shows_activity_filters(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        self.create_questionnaire(staff, "陳怡君")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/")

        self.assertContains(response, "最近資料更新")
        self.assertContains(response, 'data-record-filter="all"')
        self.assertContains(response, 'data-record-filter="questionnaire"')
        self.assertContains(response, 'data-record-filter="face"')
        self.assertContains(response, 'data-record-filter="bfs"')
        self.assertContains(response, 'data-record-filter="meridian"')

    def test_staff_can_filter_subjects_by_missing_bfs(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        user_without_bfs = User.objects.create_user(
            username="0988888888",
            email="missing@example.com",
            password="pass",
        )
        user_with_bfs = User.objects.create_user(
            username="0966666666",
            email="complete@example.com",
            password="pass",
        )
        self.create_questionnaire(user_without_bfs, "缺BFS的人")
        self.create_questionnaire(user_with_bfs, "已有BFS的人")
        BFSTest.objects.create(user=user_with_bfs, patient_name="已有BFS的人")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/", {"subject_status": "missing_bfs"})

        self.assertContains(response, "缺BFS的人")
        self.assertContains(
            response,
            f'data-subject-tab="subject-{user_without_bfs.pk}"',
        )
        self.assertNotContains(
            response,
            f'data-subject-tab="subject-{user_with_bfs.pk}"',
        )
        self.assertContains(response, 'class="is-active"')

    def test_staff_can_open_subject_detail_page(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        subject = User.objects.create_user(
            username="0988888888",
            email="subject@example.com",
            password="pass",
        )
        self.create_questionnaire(subject, "陳怡君")
        BFSTest.objects.create(user=subject, patient_name="陳怡君")
        BFSTest.objects.create(user=subject, patient_name="陳怡君")
        self.client.force_login(staff)

        response = self.client.get(f"/dashboard/subjects/{subject.pk}/")

        self.assertContains(response, "受測者詳細資料")
        self.assertContains(response, "陳怡君")
        self.assertContains(response, "0988888888 / subject@example.com")
        self.assertContains(response, "四項檢測狀態")
        self.assertContains(response, "BFS")
        self.assertContains(response, "2 筆")

    def test_researcher_can_view_subject_detail_page(self):
        researcher = User.objects.create_user(username="0966666666", password="pass")
        researcher_group, _ = Group.objects.get_or_create(name=RESEARCHER_GROUP_NAME)
        researcher.groups.add(researcher_group)
        subject = User.objects.create_user(
            username="0988888888",
            email="subject@example.com",
            password="pass",
        )
        self.create_questionnaire(subject, "陳怡君")
        self.client.force_login(researcher)

        response = self.client.get(f"/dashboard/subjects/{subject.pk}/")

        self.assertContains(response, "受測者詳細資料")
        self.assertContains(response, "陳怡君")

    def test_regular_user_cannot_view_other_subject_detail_page(self):
        user_a = User.objects.create_user(username="0911111111", password="pass")
        user_b = User.objects.create_user(username="0922222222", password="pass")
        self.create_questionnaire(user_a, "使用者甲")
        self.create_questionnaire(user_b, "使用者乙")
        self.client.force_login(user_a)

        response = self.client.get(f"/dashboard/subjects/{user_b.pk}/")

        self.assertEqual(response.status_code, 404)


class RegisterFormTests(TestCase):
    def test_register_requires_name(self):
        form = RegisterForm(
            data={
                "last_name": "",
                "first_name": "",
                "username": "0966889536",
                "email": "subject@example.com",
                "password1": "SafePass12345!",
                "password2": "SafePass12345!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)
        self.assertIn("first_name", form.errors)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username="0911111111",
            email="subject@example.com",
            password="pass",
        )
        form = RegisterForm(
            data={
                "last_name": "王",
                "first_name": "小明",
                "username": "0966889536",
                "email": "subject@example.com",
                "password1": "SafePass12345!",
                "password2": "SafePass12345!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_saves_split_name_fields(self):
        form = RegisterForm(
            data={
                "last_name": "王",
                "first_name": "小明",
                "username": "0966889536",
                "email": "subject2@example.com",
                "password1": "SafePass12345!",
                "password2": "SafePass12345!",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.username, "0966889536")
        self.assertEqual(user.last_name, "王")
        self.assertEqual(user.first_name, "小明")
        self.assertEqual(get_subject_display_name(user), "王小明")

    def test_register_rejects_invalid_name_parts(self):
        form = RegisterForm(
            data={
                "last_name": "096",
                "first_name": "test@example.com",
                "username": "0966889536",
                "email": "subject3@example.com",
                "password1": "SafePass12345!",
                "password2": "SafePass12345!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)
        self.assertIn("first_name", form.errors)

    def test_questionnaire_syncs_name_to_account_fields(self):
        user = User.objects.create_user(
            username="0966889536",
            email="subject4@example.com",
            password="pass",
        )

        Questionnaire.objects.create(
            user=user,
            name="王小明",
            gender="M",
            blood_type="O",
            height=170,
            weight=60,
            birth_date=date(2000, 1, 1),
            sleep_hours=7,
        )
        user.refresh_from_db()

        self.assertEqual(user.last_name, "王")
        self.assertEqual(user.first_name, "小明")

    def test_unlinked_bfs_record_does_not_create_subject_account(self):
        staff = User.objects.create_user(
            username="0977777777",
            email="admin@example.com",
            password="pass",
            is_staff=True,
        )
        legacy_user = User.objects.create_user(
            username="wpc",
            email="legacy@example.com",
            password="pass",
        )
        BFSTest.objects.create(patient_name="wpc")
        self.client.force_login(staff)

        response = self.client.get("/dashboard/")

        self.assertNotContains(
            response,
            f'data-subject-tab="subject-{legacy_user.pk}"',
        )
