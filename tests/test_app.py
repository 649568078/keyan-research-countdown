from datetime import date

import pytest

from research_countdown import create_app
from research_countdown.services import serialize_countdown


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    return app.test_client()


def sample_payload(**changes):
    payload = {
        "title": "论文投稿",
        "start_date": "2026-09-01",
        "deadline": "2026-09-20",
        "category": "论文",
        "description": "完成终稿",
        "color": "#536dfe",
    }
    payload.update(changes)
    return payload


def test_crud_flow(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "科研倒计时" in page.get_data(as_text=True)

    created = client.post("/api/countdowns", json=sample_payload())
    assert created.status_code == 201
    item_id = created.get_json()["id"]
    assert len(client.get("/api/countdowns").get_json()) == 1

    updated = client.put(f"/api/countdowns/{item_id}", json=sample_payload(title="修改后的标题"))
    assert updated.get_json()["title"] == "修改后的标题"
    assert client.patch(f"/api/countdowns/{item_id}/toggle").get_json()["completed"] is True
    assert client.delete(f"/api/countdowns/{item_id}").status_code == 204
    assert client.get("/api/countdowns").get_json() == []


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_rejects_invalid_date_range(client):
    response = client.post("/api/countdowns", json=sample_payload(start_date="2026-10-01"))
    assert response.status_code == 400
    assert "不能早于" in response.get_json()["error"]


def test_status_calculation():
    row = {"id": 1, "title": "节点", "start_date": "2026-09-01", "deadline": "2026-09-06", "category": "其他", "description": "", "color": "#536dfe", "completed": 0}
    assert serialize_countdown(row, date(2026, 9, 4))["status"] == "urgent"
    assert serialize_countdown(row, date(2026, 9, 8))["status"] == "overdue"


def test_countdown_with_multiple_milestones(client):
    payload = sample_payload(milestones=[
        {"title": "学院提交", "start_date": "2026-09-03", "deadline": "2026-09-05"},
        {"title": "单位审核", "start_date": "2026-09-08", "deadline": "2026-09-10"},
        {"title": "纸质材料上交", "start_date": "2026-09-15", "deadline": "2026-09-15"},
    ])
    response = client.post("/api/countdowns", json=payload)
    assert response.status_code == 201
    item = response.get_json()
    assert [node["title"] for node in item["milestones"]] == ["学院提交", "单位审核", "纸质材料上交"]

    listed = client.get("/api/countdowns").get_json()[0]
    assert len(listed["milestones"]) == 3
    assert listed["milestones"][2]["start_date"] == "2026-09-15"


def test_milestone_must_be_inside_parent_range(client):
    payload = sample_payload(milestones=[
        {"title": "范围外节点", "start_date": "2026-08-30", "deadline": "2026-09-02"}
    ])
    response = client.post("/api/countdowns", json=payload)
    assert response.status_code == 400
    assert "总时间范围" in response.get_json()["error"]


def test_standalone_milestone_management(client):
    parent = client.post("/api/countdowns", json=sample_payload()).get_json()
    created = client.post("/api/milestones", json={
        "countdown_id": parent["id"],
        "title": "单位审核",
        "start_date": "2026-09-08",
        "deadline": "2026-09-10",
    })
    assert created.status_code == 201
    node_id = created.get_json()["id"]

    updated = client.put(f"/api/milestones/{node_id}", json={
        "title": "单位终审",
        "start_date": "2026-09-09",
        "deadline": "2026-09-11",
    })
    assert updated.get_json()["title"] == "单位终审"
    assert client.patch(f"/api/milestones/{node_id}/toggle").get_json()["completed"] is True
    assert client.delete(f"/api/milestones/{node_id}").status_code == 204
    assert client.get("/api/countdowns").get_json()[0]["milestones"] == []
