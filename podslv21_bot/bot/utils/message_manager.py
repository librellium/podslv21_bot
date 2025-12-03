from typing import Dict, List, Tuple


class MessageManager:
    def __init__(self, max_messages_per_chat_id: int = 5):
        self._message_ids_map: Dict[int, Tuple[int, int]] = {}
        self._chat_ids_map: Dict[int, List[int]] = {}

        self._max_messages = max_messages_per_chat_id

    def add(self, reply_to_message_id: int, group_message_id: int, chat_id: int) -> None:
        chat_id_messages = self._chat_ids_map.setdefault(chat_id, [])
        if len(chat_id_messages) >= self._max_messages:
            old_message_id = chat_id_messages.pop(0)
            self._message_ids_map.pop(old_message_id)

        chat_id_messages.append(group_message_id)
        self._message_ids_map[group_message_id] = (reply_to_message_id, chat_id)

    def get(self, message_id: int) -> tuple[int, int] | None:
        return self._message_ids_map.get(message_id)