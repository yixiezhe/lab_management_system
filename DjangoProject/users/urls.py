# users/urls.py
from django.urls import path
from .views import (
    RegistrationAPIView,
    TutorListAPIView,
    CurrentUserAPIView,
    UserListAPIView,
    ToggleTeamProcurementAPIView,
    MyStudentsListView,
    ManageStudentRoleAPIView,
    # --- START OF MODIFICATION ---
    PasswordResetRequestAPIView,  # 导入我们新创建的视图
    ManageCorridorScreenManagerRoleAPIView,  # 新增：走廊显示屏管理角色分配
    # --- END OF MODIFICATION ---
)

urlpatterns = [
    path('', UserListAPIView.as_view(), name='user-list'),
    path('register/', RegistrationAPIView.as_view(), name='register'),
    path('tutors/', TutorListAPIView.as_view(), name='tutor-list'),
    path('me/', CurrentUserAPIView.as_view(), name='current-user'),
    path('toggle-team-procurement/', ToggleTeamProcurementAPIView.as_view(), name='toggle-team-procurement'),

    # --- START OF MODIFICATION ---
    # 为密码重置申请功能分配一个URL
    path('request-password-reset/', PasswordResetRequestAPIView.as_view(), name='request-password-reset'),

    # 新增：系统管理员给用户分配/撤销“走廊显示屏管理人员”角色
    # POST   /api/users/<user_id>/corridor-screen-manager/  -> 分配
    # DELETE /api/users/<user_id>/corridor-screen-manager/  -> 撤销
    path('<int:user_id>/corridor-screen-manager/', ManageCorridorScreenManagerRoleAPIView.as_view(),
         name='manage-corridor-screen-manager-role'),
    # --- END OF MODIFICATION ---

    # 获取导师名下学生列表
    path('my-students/', MyStudentsListView.as_view(), name='my-students-list'),
    # 管理具体某个学生色的角色（分配/移除）
    path('my-students/<int:student_id>/manage-role/', ManageStudentRoleAPIView.as_view(), name='manage-student-role'),
]
