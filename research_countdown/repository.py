from .database import get_db


FIELDS = "title, start_date, deadline, category, description, color, completed"


def list_countdowns():
    return get_db().execute(
        "SELECT * FROM countdowns ORDER BY completed, deadline, created_at"
    ).fetchall()


def list_milestones(item_id):
    return get_db().execute(
        "SELECT * FROM milestones WHERE countdown_id = ? ORDER BY sort_order, deadline",
        (item_id,),
    ).fetchall()


def get_milestone(node_id):
    return get_db().execute(
        "SELECT * FROM milestones WHERE id = ?", (node_id,)
    ).fetchone()


def create_milestone(item_id, data):
    db = get_db()
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM milestones WHERE countdown_id = ?",
        (item_id,),
    ).fetchone()[0]
    cursor = db.execute(
        """INSERT INTO milestones
           (countdown_id, title, start_date, deadline, sort_order, completed)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (item_id, data["title"], data["start_date"], data["deadline"], next_order, data["completed"]),
    )
    db.commit()
    return get_milestone(cursor.lastrowid)


def update_milestone(node_id, data):
    db = get_db()
    db.execute(
        """UPDATE milestones
           SET title = ?, start_date = ?, deadline = ?, completed = ?
           WHERE id = ?""",
        (data["title"], data["start_date"], data["deadline"], data["completed"], node_id),
    )
    db.commit()
    return get_milestone(node_id)


def delete_milestone(node_id):
    db = get_db()
    cursor = db.execute("DELETE FROM milestones WHERE id = ?", (node_id,))
    db.commit()
    return cursor.rowcount > 0


def get_countdown(item_id):
    return get_db().execute(
        "SELECT * FROM countdowns WHERE id = ?", (item_id,)
    ).fetchone()


def create_countdown(data):
    db = get_db()
    values = tuple(data[key] for key in FIELDS.split(", "))
    cursor = db.execute(
        f"INSERT INTO countdowns ({FIELDS}) VALUES (?, ?, ?, ?, ?, ?, ?)", values
    )
    _replace_milestones(cursor.lastrowid, data.get("milestones", []), db)
    db.commit()
    return get_countdown(cursor.lastrowid)


def update_countdown(item_id, data):
    db = get_db()
    values = tuple(data[key] for key in FIELDS.split(", ")) + (item_id,)
    db.execute(
        f"UPDATE countdowns SET {', '.join(f'{key} = ?' for key in FIELDS.split(', '))} WHERE id = ?",
        values,
    )
    _replace_milestones(item_id, data.get("milestones", []), db)
    db.commit()
    return get_countdown(item_id)


def delete_countdown(item_id):
    db = get_db()
    cursor = db.execute("DELETE FROM countdowns WHERE id = ?", (item_id,))
    db.commit()
    return cursor.rowcount > 0


def set_countdown_archived(item_id, archived):
    db = get_db()
    db.execute(
        "UPDATE countdowns SET archived = ? WHERE id = ?",
        (1 if archived else 0, item_id),
    )
    db.commit()
    return get_countdown(item_id)


def _replace_milestones(item_id, milestones, db):
    db.execute("DELETE FROM milestones WHERE countdown_id = ?", (item_id,))
    db.executemany(
        """INSERT INTO milestones
           (countdown_id, title, start_date, deadline, sort_order, completed)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (
                item_id,
                node["title"],
                node["start_date"],
                node["deadline"],
                node["sort_order"],
                node["completed"],
            )
            for node in milestones
        ],
    )
