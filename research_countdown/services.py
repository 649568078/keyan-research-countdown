from datetime import date, datetime


CATEGORIES = ("论文", "基金", "实验", "会议", "课程", "其他")
COLORS = ("#536dfe", "#00a896", "#f59e0b", "#ef476f", "#8b5cf6", "#0ea5e9")


class ValidationError(ValueError):
    pass


def parse_iso_date(value, field_name):
    if not value:
        raise ValidationError(f"{field_name}不能为空")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name}格式应为 YYYY-MM-DD") from exc


def validate_payload(payload):
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValidationError("事项名称不能为空")
    if len(title) > 80:
        raise ValidationError("事项名称不能超过 80 个字符")

    start = parse_iso_date(payload.get("start_date"), "开始日期")
    deadline = parse_iso_date(payload.get("deadline"), "截止日期")
    if deadline < start:
        raise ValidationError("截止日期不能早于开始日期")

    category = str(payload.get("category", "其他")).strip()
    if category not in CATEGORIES:
        category = "其他"
    color = str(payload.get("color", COLORS[0])).strip().lower()
    if color not in COLORS:
        color = COLORS[0]

    milestones = []
    raw_milestones = payload.get("milestones", [])
    if not isinstance(raw_milestones, list):
        raise ValidationError("时间节点格式不正确")
    for index, raw in enumerate(raw_milestones):
        node_title = str(raw.get("title", "")).strip()
        if not node_title:
            raise ValidationError(f"第 {index + 1} 个时间节点名称不能为空")
        node_start = parse_iso_date(raw.get("start_date"), f"第 {index + 1} 个节点开始日期")
        node_deadline = parse_iso_date(raw.get("deadline"), f"第 {index + 1} 个节点截止日期")
        if node_deadline < node_start:
            raise ValidationError(f"第 {index + 1} 个节点截止日期不能早于开始日期")
        if node_start < start or node_deadline > deadline:
            raise ValidationError(f"第 {index + 1} 个时间节点需位于事项总时间范围内")
        milestones.append({
            "id": raw.get("id"),
            "title": node_title[:80],
            "start_date": node_start.isoformat(),
            "deadline": node_deadline.isoformat(),
            "completed": 1 if raw.get("completed") in (True, 1, "1") else 0,
            "sort_order": index,
        })

    return {
        "title": title,
        "start_date": start.isoformat(),
        "deadline": deadline.isoformat(),
        "category": category,
        "description": str(payload.get("description", "")).strip()[:500],
        "color": color,
        "completed": 1 if payload.get("completed") in (True, 1, "1") else 0,
        "milestones": milestones,
    }


def validate_milestone_payload(payload, parent):
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValidationError("节点名称不能为空")
    start = parse_iso_date(payload.get("start_date"), "节点开始日期")
    deadline = parse_iso_date(payload.get("deadline"), "节点截止日期")
    if deadline < start:
        raise ValidationError("节点截止日期不能早于开始日期")
    parent_start = date.fromisoformat(parent["start_date"])
    parent_deadline = date.fromisoformat(parent["deadline"])
    if start < parent_start or deadline > parent_deadline:
        raise ValidationError(
            f"节点需位于主事项范围 {parent['start_date']} 至 {parent['deadline']} 内"
        )
    return {
        "title": title[:80],
        "start_date": start.isoformat(),
        "deadline": deadline.isoformat(),
        "completed": 1 if payload.get("completed") in (True, 1, "1") else 0,
    }


def _status_for(deadline, completed, today):
    days_left = (deadline - today).days
    if completed:
        return days_left, "completed", "已完成"
    if days_left < 0:
        return days_left, "overdue", "已逾期"
    if days_left <= 3:
        return days_left, "urgent", "非常紧急"
    if days_left <= 14:
        return days_left, "soon", "即将截止"
    return days_left, "normal", "进行中"


def serialize_countdown(row, today=None, milestones=None):
    today = today or date.today()
    deadline = date.fromisoformat(row["deadline"])
    start = date.fromisoformat(row["start_date"])
    completed = bool(row["completed"])
    archived = bool(row["archived"]) if "archived" in row.keys() else False
    days_left, status, status_label = _status_for(deadline, completed, today)

    total_days = max((deadline - start).days, 1)
    elapsed = (today - start).days
    progress = 100 if completed else max(0, min(100, round(elapsed / total_days * 100)))
    serialized_milestones = []
    for node in milestones or []:
        node_deadline = date.fromisoformat(node["deadline"])
        node_days, node_status, node_label = _status_for(
            node_deadline, completed or bool(node["completed"]), today
        )
        serialized_milestones.append({
            "id": node["id"],
            "title": node["title"],
            "start_date": node["start_date"],
            "deadline": node["deadline"],
            "completed": bool(node["completed"]),
            "days_left": node_days,
            "status": node_status,
            "status_label": node_label,
        })

    next_milestone = next(
        (node for node in serialized_milestones if not node["completed"] and node["days_left"] >= 0),
        None,
    )
    return {
        "id": row["id"],
        "title": row["title"],
        "start_date": row["start_date"],
        "deadline": row["deadline"],
        "category": row["category"],
        "description": row["description"],
        "color": row["color"],
        "completed": completed,
        "archived": archived,
        "days_left": days_left,
        "status": status,
        "status_label": status_label,
        "progress": progress,
        "milestones": serialized_milestones,
        "next_milestone": next_milestone,
    }
