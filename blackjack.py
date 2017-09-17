import itertools

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

def get_dealer_terminal_distro_given_card_distro(card_distro, peek=True, hit_soft_17=True):
    """TODO: abstract away the state machine so this can be adapted for games
    that push on dealer 22.  Peek is generally false outside of the US.
    Calculate dealer ending card distro:
    p( FINAL_DEALER_VALUE | CURRENT_DEALER_STATE and DECK_STATE )
    I can use dynamic programming by inferrring:
    p( FINAL_DEALER_VALUE | STATE ) = SUM( p( FINAL_DEALER_VALUE | NEXT_STATE )) * p(NEXT_STATE | STATE))

    A DAG of the blackjack states:

    HARD: 2 ->3 -> 4 ->  5 ->  6 ->  7 ->  8 ->  9 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17 -> 18 -> 19 -> 20 -> 21 -> BUST
                   |     |     |     |     |     |     |          ^
                   v     v     v     v     v     v     v          |
    S: 12->13->14->15 -> 16 -> 17 -> 18 -> 19 -> 20 -> 21 --------+

    Where any hard state under 11 can become the corresponding SOFT state
    (eg, H10 -> S21) and any SOFT state can become a more advanced SOFT state or
    wrapping around to start a hard state of at least 12.

    The two exceptions are dealer starts with soft 11 or hard 10.  The next
    state can never be 21 because the dealer will peek to make sure he doesn't
    have a natural and the round won't play out.

    So I calculate p(FINAL_DEALER_VALUE) in reverse topological sort order.
    """
    dealer_distro = [[0.0 for end_total in range(23)] for upcard in range(11)]
    p_dealer_end = [[[0.0 for end_total in range(23)] for softness in range(2)] for upcard in range(23)]

    for total, is_soft in itertools.chain(blackjack_states(), [(11, True)]):
        if (total, is_soft) in (H17_END_STATES if hit_soft_17 else S17_END_STATES):
            p_dealer_end[total][is_soft][total] = 1.0
            continue
        for card in range(1,11):
            next_total, next_soft = next_state(total, is_soft, card)
            for end_total in range(17, 23):
                p_dealer_end[total][is_soft][end_total] += \
                    (p_dealer_end[next_total][next_soft][end_total] *
                    card_distro[card])
    for upcard in range(2, 10):
        dealer_distro[upcard] = p_dealer_end[upcard][False]

    # Dealer could have 21 if they don't peek to make sure they don't:
    if not peek:
        dealer_distro[1] = p_dealer_end[11][True]
        dealer_distro[10] = p_dealer_end[10][False]

        return dealer_distro

    for end_total in range(17, 23):
        # Account for Ace upcard.  Possible next hands are soft 12 through soft 20
        for next_card in range(1,10):
            dealer_distro[1][end_total] += \
                (card_distro[next_card] *
                p_dealer_end[next_card + 11][True][end_total])
        # Bayes' theorem:
        # p( card | card != 10 ) = p( card ) / p( card != 10 )
        dealer_distro[True][end_total] /= 1 - card_distro[10]

        # Account for ten upcard.  Possible next hands are hard 12 through 20
        for next_card in range(2,11):
            dealer_distro[10][end_total] += \
                (card_distro[next_card] *
                p_dealer_end[next_card + 10][False][end_total])

        # Bayes' theorem:
        # p( card | card != 1 ) = p( card ) / p( card != 1 )
        dealer_distro[10][end_total] /= 1 - card_distro[True]

    return dealer_distro


H17_END_STATES = [(total, soft) for soft in [False, True] for total in range(18 if soft else 17, 22)] + [(22, False)]
S17_END_STATES = [(total, soft) for soft in [False, True] for total in range(17, 22)] + [(22, False)]
