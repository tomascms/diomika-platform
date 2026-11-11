"""state_store: ficheiro por omissão; tabela app_state com STATE_STORE=supabase (Render)."""
from types import SimpleNamespace

from core import state_store


def test_ficheiro_ida_e_volta(tmp_path, monkeypatch):
    monkeypatch.delenv("STATE_STORE", raising=False)
    monkeypatch.setattr(state_store, "DATA_DIR", tmp_path)
    assert state_store.load("x", {"vazio": True}) == {"vazio": True}
    state_store.save("x", {"a": 1})
    assert state_store.load("x", None) == {"a": 1}


def test_supabase_ida_e_volta(monkeypatch):
    rows = {}

    class Table:
        def select(self, *_):
            return self

        def eq(self, _col, key):
            self.key = key
            return self

        def limit(self, _n):
            return self

        def upsert(self, row):
            rows[row["key"]] = row["value"]
            return self

        def execute(self):
            key = getattr(self, "key", None)
            return SimpleNamespace(data=[{"value": rows[key]}] if key in rows else [])

    import core.database

    monkeypatch.setenv("STATE_STORE", "supabase")
    monkeypatch.setattr(core.database, "get_db", lambda: SimpleNamespace(table=lambda _n: Table()))
    assert state_store.load("admin_users", {"users": []}) == {"users": []}
    state_store.save("admin_users", {"users": [{"username": "a"}]})
    assert state_store.load("admin_users", None) == {"users": [{"username": "a"}]}
