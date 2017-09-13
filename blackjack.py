def blackjack_states():
    """A generator to return all possible blackjack states of a hand in reverse
    topological order.
    """
    for total in range(22, 11, -1):
        yield total, False
    for total in range(21, 11, -1):
        yield total, True
    for total in range(11, 1, -1):
        yield total, False

def next_state(total, is_soft, card):
    """A function that returns the next blackjack state, given the next card
    drawn."""
    total += card

    if is_soft:
        if total > 21:
            return (total - 10, False) # Hand turned hard
        else:
            return (total, True)
    
    if card == 1 and total < 12:
        return (total + 10, True) # Hand turned soft
    else:
        return (min(22, total), False) # 22 is bust.

H17_END_STATES = [(total, soft) for soft in [False, True] for total in range(18 if soft else 17, 22)] + [(22, False)]
S17_END_STATES = [(total, soft) for soft in [False, True] for total in range(17, 22)] + [(22, False)]
