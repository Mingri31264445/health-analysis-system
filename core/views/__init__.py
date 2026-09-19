from .common import home
from .meridian import upload_meridian_result, meridian_list, meridian_detail, meridian_update, meridian_delete, meridian_file_view
from .bfs import bfs_list, upload_bfs_test, bfs_detail, bfs_confirm_date, bfs_update, bfs_delete, bfs_file_view
from .auth import register_view, login_view, logout_view, forgot_password_view
from .analysis_flow import start_analysis_view, questionnaire_view, feature_gate
from .dashboard import dashboard_view, subject_detail_view
