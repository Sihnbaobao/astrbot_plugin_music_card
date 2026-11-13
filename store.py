"""听歌记录、评论记录和登录态的本地存储。

全部是普通 JSON / JSONL 文件：出问题时可以直接打开看，换机器把目录拷走就行。
"""

import json
import os
from datetime import datetime
from pathlib import Path


def _today() -> str:
    """返回本地日期，格式 YYYY-MM-DD。"""
    return datetime.now().strftime("%Y-%m-%d")


class MusicStore:
    """插件本地状态的唯一入口。

    Args:
        root: 插件数据目录。
    """

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.auth_path = self.root / "auth.json"
        self.listened_path = self.root / "listened.jsonl"
        self.comments_path = self.root / "comments.jsonl"
        self.replies_path = self.root / "replies.jsonl"
        self.recommendations_path = self.root / "recommendations.json"
        self.recommendations_log_path = self.root / "recommendations.jsonl"

    # ── 登录态 ──

    def load_auth(self) -> dict:
        """读取登录态。

        Returns:
            包含 cookie、昵称、头像的字典；没有登录或文件损坏时返回空字典。
        """
        try:
            data = json.loads(self.auth_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save_auth(self, data: dict) -> None:
        """原子写入登录态。

        Args:
            data: 要保存的登录信息。
        """
        tmp = self.auth_path.with_name(self.auth_path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.auth_path)

    def clear_auth(self) -> None:
        """清除登录态。"""
        try:
            self.auth_path.unlink()
        except FileNotFoundError:
            pass

    @property
    def cookie(self) -> str:
        """当前登录态的 Cookie 字符串，没登录时为空串。"""
        return str(self.load_auth().get("cookie") or "")

    # ── 听歌记录 ──

    def add_listened(self, entry: dict) -> None:
        """追加一条听歌记录。

        Args:
            entry: 听歌记录，至少包含 at / song_id / name。
        """
        self._append(self.listened_path, entry)

    def recent_listened(self, limit: int = 50) -> list[dict]:
        """按时间倒序返回最近的听歌记录。

        Args:
            limit: 最多返回多少条。

        Returns:
            听歌记录列表。
        """
        return self._recent(self.listened_path, limit)

    def listened_counts(self, limit: int = 200) -> list[dict]:
        """按听歌次数聚合歌曲。

        Args:
            limit: 最多返回多少首。

        Returns:
            包含 song_id、name、artist、count、last_at 的列表，按次数倒序。
        """
        counts = {}
        for item in self._read(self.listened_path):
            song_id = str(item.get("song_id") or "")
            if not song_id:
                continue
            entry = counts.setdefault(
                song_id,
                {
                    "song_id": song_id,
                    "name": str(item.get("name") or ""),
                    "artist": str(item.get("artist") or ""),
                    "count": 0,
                    "last_at": "",
                },
            )
            entry["count"] += 1
            at = str(item.get("at") or "")
            if at >= entry["last_at"]:
                entry["last_at"] = at
                entry["name"] = str(item.get("name") or entry["name"])
                entry["artist"] = str(item.get("artist") or entry["artist"])
        items = sorted(
            counts.values(),
            key=lambda item: (item["count"], item["last_at"]),
            reverse=True,
        )
        return items[: max(1, min(int(limit or 200), 1000))]

    # ── 评论记录 ──

    def add_comment(self, entry: dict) -> None:
        """追加一条评论记录。

        Args:
            entry: 评论记录，至少包含 at / song_id / content / ok。
        """
        self._append(self.comments_path, entry)

    def recent_comments(self, limit: int = 50) -> list[dict]:
        """按时间倒序返回最近的评论记录。

        Args:
            limit: 最多返回多少条。

        Returns:
            评论记录列表。
        """
        return self._recent(self.comments_path, limit)

    def comments_today(self) -> int:
        """今天成功发出的评论条数。

        Returns:
            当日成功评论数。
        """
        today = _today()
        return sum(
            1
            for item in self._read(self.comments_path)
            if item.get("ok") and str(item.get("at", "")).startswith(today)
        )

    def has_commented(self, song_id) -> bool:
        """是否已经在这首歌下发过评论。

        Args:
            song_id: 网易云歌曲 ID。

        Returns:
            True 表示已经成功评论过。
        """
        target = str(song_id or "")
        return any(
            item.get("ok") and str(item.get("song_id")) == target
            for item in self._read(self.comments_path)
        )

    # ── 收到的回复 ──

    def add_reply(self, entry: dict) -> None:
        """追加一条收到的回复记录。

        Args:
            entry: 回复记录，至少包含 reply_id / song_id / content。
        """
        self._append(self.replies_path, entry)

    def recent_replies(self, limit: int = 50) -> list[dict]:
        """按时间倒序返回最近的回复记录。

        Args:
            limit: 最多返回多少条。

        Returns:
            回复记录列表。
        """
        return self._recent(self.replies_path, limit)

    def seen_reply_ids(self) -> set[str]:
        """已经记录过的回复 ID 集合。

        Returns:
            回复 ID 集合。
        """
        return {
            str(item.get("reply_id"))
            for item in self._read(self.replies_path)
            if item.get("reply_id")
        }

    def replies_today(self) -> int:
        """今天已经自动回复的条数。

        Returns:
            当日已回复数。
        """
        today = _today()
        return sum(
            1
            for item in self._read(self.replies_path)
            if item.get("my_reply") and str(item.get("at", "")).startswith(today)
        )

    # ── 推荐记录 ──

    def record_recommendation(self, song, chat="", user=""):
        """记录一次歌曲推荐。

        Args:
            song: 推荐出去的歌名。
            chat: 发生推荐的会话标识，可为空。
            user: 推荐给谁，可为空。
        """
        song = str(song or "").strip()
        if not song:
            return
        now = datetime.now().isoformat(timespec="seconds")
        self._append(
            self.recommendations_log_path,
            {"at": now, "song": song, "chat": str(chat or ""), "user": str(user or "")},
        )
        data = self._read_json(self.recommendations_path)
        entry = data.get(song)
        if not isinstance(entry, dict):
            entry = {"count": 0}
        entry["count"] = int(entry.get("count") or 0) + 1
        entry["last_at"] = now
        entry["last_chat"] = str(chat or "")
        entry["last_user"] = str(user or "")
        data[song] = entry
        try:
            self.recommendations_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def recent_recommendation_events(self, limit=20):
        """按时间倒序返回推荐事件。

        Args:
            limit: 最多返回多少条。

        Returns:
            包含 at、song、chat、user 的事件列表。
        """
        return self._recent(self.recommendations_log_path, limit)

    def recent_recommendations(self, limit=50):
        """按推荐次数倒序返回记录。

        Args:
            limit: 最多返回多少条。

        Returns:
            包含 song、count、last_at 的列表。
        """
        data = self._read_json(self.recommendations_path)
        items = [
            {"song": song, **entry}
            for song, entry in data.items()
            if isinstance(entry, dict)
        ]
        items.sort(
            key=lambda item: (
                int(item.get("count") or 0),
                str(item.get("last_at") or ""),
            ),
            reverse=True,
        )
        return items[: max(1, min(int(limit or 50), 200))]

    def _read_json(self, path):
        """读取 JSON 文件，损坏时返回空字典。

        Args:
            path: JSON 文件路径。

        Returns:
            字典内容。
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    # ── 内部读写 ──

    def _append(self, path: Path, entry: dict) -> None:
        """向 JSONL 文件追加一行。"""
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _read(self, path: Path) -> list[dict]:
        """读取 JSONL 文件，坏行静默跳过。"""
        if not path.exists():
            return []
        items = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                items.append(item)
        return items

    def _recent(self, path: Path, limit: int) -> list[dict]:
        """返回 JSONL 的最后 N 条，按时间倒序。"""
        limit = max(1, min(int(limit or 50), 500))
        return list(reversed(self._read(path)[-limit:]))
