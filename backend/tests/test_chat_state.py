from backend.api.routes.chat import ChatState


class My:
    def __init__(self, val: int):
        self.val = val


def test_val():
    v = My(val=3)
    assert v.val == 3
    v.val +=


def test_init():
    state = ChatState(max_turns=12)
    assert isinstance(state.history, list)
    assert len(state.history) == 0
    assert state.max_turns == 12
    assert state.turn_count == 0


def test_add_user_history():
    state = ChatState(max_turns=12)

    # add message
    msg = "test user message"
    state.add_user_history(content=msg)
    assert len(state.history) == 1

    last_message = state.history[-1]

    # check keys
    keys = list(last_message.keys())
    assert keys[0] == "role"
    assert keys[1] == "content"

    # check values
    values = list(last_message.values())
    assert values[0] == "user"
    assert values[1] == msg


def test_add_system_history():
    statee = ChatState(max_turns=11)
    assert statee.max_turns == 11
    print(f"the current state {statee.history}")

    assert len(statee.history) == 0

    # add message
    msg = "test system message"
    statee.add_system_history(content=msg)
    assert len(statee.history) == 1

    last_message = statee.history[-1]

    # check keys
    keys = list(last_message.keys())
    assert keys[0] == "role"
    assert keys[1] == "content"

    # check values
    values = list(last_message.values())
    assert values[0] == "system"
    assert values[1] == msg
