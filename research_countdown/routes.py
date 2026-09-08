from flask import Blueprint, jsonify, render_template, request

from . import repository
from .services import (
    CATEGORIES,
    COLORS,
    ValidationError,
    serialize_countdown,
    validate_milestone_payload,
    validate_payload,
)


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html", categories=CATEGORIES, colors=COLORS)


@bp.get("/health")
def health():
    return "ok"


@bp.get("/api/countdowns")
def countdown_list():
    return jsonify([
        serialize_countdown(row, milestones=repository.list_milestones(row["id"]))
        for row in repository.list_countdowns()
    ])


@bp.post("/api/countdowns")
def countdown_create():
    try:
        data = validate_payload(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    row = repository.create_countdown(data)
    return jsonify(serialize_countdown(row, milestones=repository.list_milestones(row["id"]))), 201


@bp.put("/api/countdowns/<int:item_id>")
def countdown_update(item_id):
    if repository.get_countdown(item_id) is None:
        return jsonify({"error": "事项不存在"}), 404
    try:
        data = validate_payload(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    row = repository.update_countdown(item_id, data)
    return jsonify(serialize_countdown(row, milestones=repository.list_milestones(item_id)))


@bp.patch("/api/countdowns/<int:item_id>/toggle")
def countdown_toggle(item_id):
    row = repository.get_countdown(item_id)
    if row is None:
        return jsonify({"error": "事项不存在"}), 404
    data = dict(row)
    data["completed"] = not bool(row["completed"])
    data["milestones"] = [dict(node) for node in repository.list_milestones(item_id)]
    data = validate_payload(data)
    row = repository.update_countdown(item_id, data)
    return jsonify(serialize_countdown(row, milestones=repository.list_milestones(item_id)))


@bp.delete("/api/countdowns/<int:item_id>")
def countdown_delete(item_id):
    if not repository.delete_countdown(item_id):
        return jsonify({"error": "事项不存在"}), 404
    return "", 204


def _milestone_response(node):
    return jsonify({
        "id": node["id"],
        "countdown_id": node["countdown_id"],
        "title": node["title"],
        "start_date": node["start_date"],
        "deadline": node["deadline"],
        "completed": bool(node["completed"]),
    })


@bp.post("/api/milestones")
def milestone_create():
    payload = request.get_json(silent=True) or {}
    try:
        item_id = int(payload.get("countdown_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "请选择所属事项"}), 400
    parent = repository.get_countdown(item_id)
    if parent is None:
        return jsonify({"error": "所属事项不存在"}), 404
    try:
        data = validate_milestone_payload(payload, parent)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return _milestone_response(repository.create_milestone(item_id, data)), 201


@bp.put("/api/milestones/<int:node_id>")
def milestone_update(node_id):
    node = repository.get_milestone(node_id)
    if node is None:
        return jsonify({"error": "节点不存在"}), 404
    parent = repository.get_countdown(node["countdown_id"])
    try:
        data = validate_milestone_payload(request.get_json(silent=True) or {}, parent)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return _milestone_response(repository.update_milestone(node_id, data))


@bp.patch("/api/milestones/<int:node_id>/toggle")
def milestone_toggle(node_id):
    node = repository.get_milestone(node_id)
    if node is None:
        return jsonify({"error": "节点不存在"}), 404
    data = dict(node)
    data["completed"] = not bool(node["completed"])
    return _milestone_response(repository.update_milestone(node_id, data))


@bp.delete("/api/milestones/<int:node_id>")
def milestone_delete(node_id):
    if not repository.delete_milestone(node_id):
        return jsonify({"error": "节点不存在"}), 404
    return "", 204
