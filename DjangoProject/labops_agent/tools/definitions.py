def _function_tool(name, description, properties):
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


NULLABLE_STRING = {"type": ["string", "null"]}
NULLABLE_INTEGER = {"type": ["integer", "null"]}
NULLABLE_NUMBER = {"type": ["number", "null"]}


TOOL_DEFINITIONS = [
    _function_tool(
        "list_procurement_requests",
        "查询当前登录用户按既有权限可见的采购申请和当前流程状态。",
        {
            "expense_type": {
                "type": ["string", "null"],
                "enum": ["public", "c2c", None],
                "description": "public 为公共经费，c2c 为个人经费；不筛选时为 null。",
            },
            "statuses": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "要筛选的内部状态列表；不筛选时为 null。",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "description": "最多返回多少条，默认意图使用 10。",
            },
        },
    ),
    _function_tool(
        "get_procurement_request",
        "按申请主键或订单编号查询一条当前用户有权查看的采购申请。",
        {
            "request_id": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "description": "采购申请主键；与订单编号二选一。",
            },
            "order_number": {
                **NULLABLE_STRING,
                "description": "订单编号；与申请主键二选一。",
            },
        },
    ),
    _function_tool(
        "prepare_procurement_request",
        "根据白名单和平台规则准备采购申请草稿；只生成待确认操作，不会提交采购申请。信息不全时返回缺失字段。",
        {
            "expense_type": {
                "type": ["string", "null"],
                "enum": ["public", "c2c", None],
                "description": "明确时填写经费类型，不确定时为 null，由后端规则解析。",
            },
            "platform": {
                **NULLABLE_STRING,
                "description": "采购平台；不确定时为 null，由白名单规则解析。",
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {**NULLABLE_STRING, "description": "白名单中的采购内容名称。"},
                        "purchase_type": {
                            "type": ["string", "null"],
                            "enum": ["consumable", "chemical", "other", None],
                            "description": "采购类型；不确定时为 null。",
                        },
                        "manufacturer": NULLABLE_STRING,
                        "parameters": NULLABLE_STRING,
                        "cas_number": NULLABLE_STRING,
                        "product_number": NULLABLE_STRING,
                        "purchase_link": NULLABLE_STRING,
                        "specifications": NULLABLE_STRING,
                        "unit_price": NULLABLE_NUMBER,
                        "quantity": NULLABLE_INTEGER,
                    },
                    "required": [
                        "content",
                        "purchase_type",
                        "manufacturer",
                        "parameters",
                        "cas_number",
                        "product_number",
                        "purchase_link",
                        "specifications",
                        "unit_price",
                        "quantity",
                    ],
                    "additionalProperties": False,
                },
            },
        },
    ),
    _function_tool(
        "search_equipment",
        "按名称、位置或简介搜索当前登录用户有权预约的仪器。",
        {
            "query": {"type": "string", "description": "搜索关键词，可为空字符串。"},
            "active_only": {
                "type": "boolean",
                "description": "通常为 true，只查询启用仪器。",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    ),
    _function_tool(
        "prepare_equipment_reservation",
        "解析并校验仪器预约需求，生成打开预约页面的预填动作；不会创建预约，最终提交必须由用户点击。",
        {
            "equipment_id": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "description": "已由搜索或候选上下文确定的仪器主键；不确定时为 null。",
            },
            "equipment_query": {
                **NULLABLE_STRING,
                "description": "用户对仪器的称呼，可含简称；如“三号输力强”。",
            },
            "target_date": {
                "type": "string",
                "format": "date",
                "description": "预约日期 YYYY-MM-DD，应根据系统当前日期解析明天等相对日期。",
            },
            "start_time": {
                "type": "string",
                "pattern": "^(?:[01]\\d|2[0-3]):[0-5]\\d$",
                "description": "开始时间 HH:MM。",
            },
            "end_time": {
                **NULLABLE_STRING,
                "description": "结束时间 HH:MM；用户只给时长时为 null。",
            },
            "duration_minutes": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "maximum": 1440,
                "description": "预约时长（分钟）；用户给出结束时间而未给时长时为 null。",
            },
            "position_no": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "description": "输力强通道号；如“三号输力强”应填写 3。其他普通仪器为 null。",
            },
        },
    ),
    _function_tool(
        "get_my_reservations",
        "查询当前登录用户自己的仪器预约，不接受其他用户标识。",
        {
            "upcoming": {
                "type": ["boolean", "null"],
                "description": "true 为未来，false 为历史，null 为全部。",
            },
            "start_date": {
                "type": ["string", "null"],
                "format": "date",
                "description": "起始日期 YYYY-MM-DD；不限制时为 null。",
            },
            "end_date": {
                "type": ["string", "null"],
                "format": "date",
                "description": "结束日期 YYYY-MM-DD；不限制时为 null。",
            },
            "statuses": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "预约状态列表；不筛选时为 null。",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 30},
        },
    ),
    _function_tool(
        "get_available_slots",
        "查询某台可见仪器在指定日期的可预约时段。",
        {
            "equipment_id": {"type": "integer", "minimum": 1},
            "target_date": {"type": "string", "format": "date"},
            "position_no": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "description": "工位或通道编号；普通设备为 null。",
            },
            "rotation_speed_rpm": {
                **NULLABLE_INTEGER,
                "minimum": 1,
                "description": "球磨机转速；不适用时为 null。",
            },
        },
    ),
    _function_tool(
        "check_reservation_conflict",
        "只读检查一个拟预约时间段是否与现有预约冲突，不会创建预约。",
        {
            "equipment_id": {"type": "integer", "minimum": 1},
            "start_at": {"type": "string", "format": "date-time"},
            "end_at": {"type": "string", "format": "date-time"},
            "position_no": {**NULLABLE_INTEGER, "minimum": 1},
            "rotation_speed_rpm": {**NULLABLE_INTEGER, "minimum": 1},
        },
    ),
]
