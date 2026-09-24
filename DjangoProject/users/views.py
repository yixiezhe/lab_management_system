from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from .models import UserProfile, Role, PasswordResetRequest
from .serializers import UserProfileSerializer, TutorSerializer
from procurement.permissions import IsTutor


class RegistrationAPIView(generics.CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def create(self, request, *args, **kwargs):
        identity = request.data.get('identity')

        if identity == '导师':
            role_name = '导师用户'
        else:
            # 【修正】根据您的截图，将角色名改回 '普通学生用户'
            role_name = '普通学生用户'

        mutable_data = request.data.copy()
        mutable_data['role_name'] = role_name

        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            {"message": "User registration successful!", "user": serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class TutorListAPIView(generics.ListAPIView):
    queryset = UserProfile.objects.filter(roles__name='导师用户')
    serializer_class = TutorSerializer


class CurrentUserAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class UserListAPIView(generics.ListAPIView):
    """
    Provides a list of all users for frontend filter dropdowns.
    """
    queryset = UserProfile.objects.all().order_by('name')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]


class ToggleTeamProcurementAPIView(APIView):
    permission_classes = [IsTutor]

    def post(self, request, *args, **kwargs):
        user = request.user
        user.team_procurement_enabled = not user.team_procurement_enabled
        user.save(update_fields=['team_procurement_enabled'])

        return Response(
            {
                'message': 'Settings updated successfully',
                'team_procurement_enabled': user.team_procurement_enabled
            },
            status=status.HTTP_200_OK
        )


class MyStudentsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsTutor]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(assigned_tutor=self.request.user).order_by('name')


class ManageStudentRoleAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTutor]

    def post(self, request, student_id, *args, **kwargs):
        return self._manage_role(request, student_id, action='assign')

    def delete(self, request, student_id, *args, **kwargs):
        return self._manage_role(request, student_id, action='remove')

    def _manage_role(self, request, student_id, action):
        tutor = request.user
        try:
            student = UserProfile.objects.get(id=student_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        if student.assigned_tutor != tutor:
            return Response({"error": "You do not have permission to manage this student."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            procurement_role = Role.objects.get(name='小组采购人员')
        except Role.DoesNotExist:
            return Response({"error": "The '小组采购人员' role is not defined in the system."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if action == 'assign':
            student.roles.add(procurement_role)
            message = f"{student.name} has been successfully designated as a group procurement officer."
        else:  # remove
            student.roles.remove(procurement_role)
            message = f"The group procurement officer role has been successfully removed from {student.name}."

        return Response({"message": message}, status=status.HTTP_200_OK)


class PasswordResetRequestAPIView(APIView):
    """
    Handles the creation of a password reset request from an unauthenticated user.
    """
    permission_classes = []

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        new_password = request.data.get('new_password')

        if not username or not new_password:
            return Response(
                {"error": "必须提供学号/工号和新密码。"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "该用户不存在。"},
                status=status.HTTP_404_NOT_FOUND
            )

        if PasswordResetRequest.objects.filter(user=user, status='pending').exists():
            return Response(
                {"error": "已存在待处理的重置申请，请勿重复提交。"},
                status=status.HTTP_400_BAD_REQUEST
            )

        password_hash = make_password(new_password)

        PasswordResetRequest.objects.create(
            user=user,
            new_password_hash=password_hash
        )

        return Response(
            {
                "message": "密码重置申请已成功提交，请联系管理员进行线下核实批准。"},
            status=status.HTTP_201_CREATED
        )


# ====== 新增：系统管理员分配/撤销“走廊显示屏管理人员”角色 ======
class ManageCorridorScreenManagerRoleAPIView(APIView):
    """
    仅系统管理员可用：给任意用户分配/撤销 “走廊显示屏管理人员” 角色
    POST   /api/users/<user_id>/corridor-screen-manager/    -> 分配角色
    DELETE /api/users/<user_id>/corridor-screen-manager/    -> 撤销角色
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, *args, **kwargs):
        return self._manage(request, user_id, action='assign')

    def delete(self, request, user_id, *args, **kwargs):
        return self._manage(request, user_id, action='remove')

    def _manage(self, request, user_id, action: str):
        # 仅系统管理员允许操作
        if not getattr(request.user, 'is_system_admin', False):
            return Response({"error": "无权限操作：仅系统管理员可分配走廊显示屏管理角色。"},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            target_user = UserProfile.objects.get(id=user_id)
        except UserProfile.DoesNotExist:
            return Response({"error": "目标用户不存在。"}, status=status.HTTP_404_NOT_FOUND)

        # 若角色不存在，自动创建（避免部署后忘了手动建角色）
        screen_role, _ = Role.objects.get_or_create(name='走廊显示屏管理人员')

        if action == 'assign':
            target_user.roles.add(screen_role)
            return Response({"message": f"已为 {target_user.name} 分配走廊显示屏管理人员角色。"},
                            status=status.HTTP_200_OK)

        # remove
        target_user.roles.remove(screen_role)
        return Response({"message": f"已撤销 {target_user.name} 的走廊显示屏管理人员角色。"},
                        status=status.HTTP_200_OK)
# ==========================================================
