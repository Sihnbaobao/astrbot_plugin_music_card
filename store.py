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
