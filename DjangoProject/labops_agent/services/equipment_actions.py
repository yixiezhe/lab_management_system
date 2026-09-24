import uuid
from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied, ValidationError

from equipment.models import Equipment
from equipment.services.query_service import EquipmentQueryService

from .equipment_context import EquipmentContextService


class EquipmentReservationActionService:
    SUPPORTED_MODES = {
        Equipment.BOOKING_MODE_STANDARD,
        Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
        Equipment.BOOKING_MODE_XRD,
    }

    @staticmethod
    def _assert_admin(actor):
        if not (
            getattr(actor, "is_authenticated", False)
            and (
                getattr(actor, "is_superuser", False)
                or getattr(actor, "is_system_admin", False)
            )
        ):
            raise PermissionDenied("只有系统管理员可以使用预约预填功能。")

    @classmethod
    def _resolve_equipment(cls, actor, equipment_id, query):
        visible = EquipmentQueryService.visible_equipment(actor)
        if equipment_id is not None:
            try:
                return visible.get(pk=equipment_id)
            except Equipment.DoesNotExist as exc:
                raise PermissionDenied("无权预约该仪器或仪器不存在。") from exc

        candidates = EquipmentContextService().search_candidates(actor, query or "")
        if not candidates:
            return None, []
        if len(candidates) > 1 and candidates[0]["match_score"] == candidates[1]["match_score"]:
            return None, candidates
        try:
            return visible.get(pk=candidates[0]["id"])
        except Equipment.DoesNotExist as exc:
            raise PermissionDenied("无权预约该仪器或仪器不存在。") from exc

    @staticmethod
    def _time_text(value):
        return value.strftime("%H:%M")

    @classmethod
    def _resolve_end_time(cls, start_time, end_time, duration_minutes):
        start_dt = datetime.combine(datetime.today().date(), start_time)
        if end_time is None:
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            if end_dt.date() != start_dt.date():
                raise ValidationError("预约时段不能跨越零点。")
            return end_dt.time().replace(second=0, microsecond=0)
        if duration_minutes is not None:
            expected = start_dt + timedelta(minutes=duration_minutes)
            if expected.time().replace(second=0, microsecond=0) != end_time:
                raise ValidationError("结束时间与预约时长不一致。")
        return end_time

    @classmethod
    def prepare(cls, actor, args):
        cls._assert_admin(actor)
        resolved = cls._resolve_equipment(
            actor,
            args.get("equipment_id"),
            args.get("equipment_query"),
        )
        if isinstance(resolved, tuple):
            _, candidates = resolved
            return {
                "status": "needs_information",
                "missing_fields": ["equipment"],
                "candidates": candidates,
                "message": "未能唯一确定仪器，请让用户确认具体仪器。",
            }
        equipment = resolved
        if equipment.booking_mode not in cls.SUPPORTED_MODES:
            return {
                "status": "needs_information",
                "missing_fields": ["ball_mill_parameters"],
                "message": "球磨机预约还需要工位、转速和研磨时长，暂不生成预填动作。",
            }

        position_no = args.get("position_no")
        extracted_position = EquipmentContextService.extract_position_no(
            args.get("equipment_query")
        )
        if position_no is None:
            position_no = extracted_position
        elif extracted_position is not None and position_no != extracted_position:
            raise ValidationError("仪器描述中的通道号与 position_no 不一致。")
        if equipment.is_electrochemical_workstation() and position_no is None:
            return {
                "status": "needs_information",
                "missing_fields": ["position_no"],
                "resolved": {"equipment_id": equipment.id, "equipment_name": equipment.name},
                "message": "请确认要预约的输力强通道号。",
            }
        if not equipment.is_electrochemical_workstation():
            position_no = None

        start_time = args["start_time"]
        end_time = cls._resolve_end_time(
            start_time,
            args.get("end_time"),
            args.get("duration_minutes"),
        )
        if start_time >= end_time:
            raise ValidationError("开始时间必须早于结束时间。")

        availability = EquipmentQueryService.get_available_slots(
            actor,
            equipment_id=equipment.id,
            target_date=args["target_date"],
            position_no=position_no,
        )
        start_text = cls._time_text(start_time)
        end_text = cls._time_text(end_time)
        selected_slots = [
            slot
            for slot in availability["slots"]
            if slot["start"] >= start_text and slot["end"] <= end_text
        ]
        aligned = (
            selected_slots
            and selected_slots[0]["start"] == start_text
            and selected_slots[-1]["end"] == end_text
        )
        if not aligned:
            raise ValidationError(
                f"预约时间必须按该仪器的 {equipment.time_unit_minutes} 分钟时段对齐。"
            )
        blocked = [slot for slot in selected_slots if not slot.get("available")]
        if blocked:
            return {
                "status": "unavailable",
                "equipment": {"id": equipment.id, "name": equipment.name},
                "position_no": position_no,
                "date": args["target_date"].isoformat(),
                "blocked_slots": [
                    {"start": row["start"], "end": row["end"], "reason": row.get("reason")}
                    for row in blocked
                ],
                "message": "所选时间范围包含不可预约时段。",
            }

        duration = int(
            (
                datetime.combine(args["target_date"], end_time)
                - datetime.combine(args["target_date"], start_time)
            ).total_seconds()
            // 60
        )
        preview = {
            "equipment_id": equipment.id,
            "equipment_name": equipment.name,
            "booking_mode": equipment.booking_mode,
            "target_date": args["target_date"].isoformat(),
            "start_time": start_text,
            "end_time": end_text,
            "duration_minutes": duration,
            "position_no": position_no,
        }
        return {
            "status": "ready",
            "message": "预约信息已校验，可打开预约页预填；最终提交仍由用户完成。",
            "action": {
                "id": f"equipment-prefill-{uuid.uuid4().hex}",
                "type": "equipment_reservation_prefill",
                "status": "pending_user_submit",
                "title": "预填仪器预约",
                "confirm_label": "打开预约页并预填",
                "preview": preview,
            },
        }
