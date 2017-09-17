"""
This simulation derives deviation indices for Spanish 21, given the bonuses and
lack of tens:

* Dealer blackjack doesn't defeat player blackjack (and you always get 3:2)
* Player hand of 21 always wins (no 3:2 if not a natural blackjack though)
* Dealer hits soft 17 (h17)
* Double even on 3 or more cards
* Redouble possible.  So is re-re-double (for a total of 8x original wager)
* Double after split allowed
* Surrender after double down allowed
* You can hit split aces.
* You can also double down on split aces
* Late surrender allowed

* 5-card 21: pays 3:2
* 6-card 21: pays 2:1
* 7+card 21: pays 3:1
* 6-7-8 mixed suit: 3:2
* 6-7-8 suited: 2:1
* 6-7-8 spades: 3:1
* 7-7-7 mixed suit: 3:2
* 7-7-7 suited: 2:1
* 7-7-7 spades: 3:1
* Doubling voids these 21 payouts.

* Super bonus:
* on 7-7-7 spades, if dealer upcard is a 7, pays out $1000 on a $5-24 bet, $5000 on a $25+ bet.
* Super bonus void by splitting or doubling.

For calculating the deviation indices, ignore 6-7-8 and 7-7-7 bonuses for now.
It should be fairly obvious what to do in practice.

At about 10000 trials, it gives a strategy that almost always matches basic strategy.
"""

import tabulate
import sys
import random

import deck
import blackjack

def format_table(table):
    """Reformat a table as indexed by surrender_index for easy reading."""
    upcard_sequence = table[2:11]
    # Compose this so the ace is the last column:
    upcard_sequence.append(table[1])

    table = [["%.1f" % (y[False][x]/2.0) for y in upcard_sequence] for x in range(17, 11, -1)]
    for x in range(17, 11, -1):
        table[17-x].insert(0, x)

    table.insert(0, ["+", 2,3,4,5,6,7,8,9,"X","A"])

    return table

TRIALS = int(sys.argv[1])
output = open("results_for_spanish21_indices_%d_trials.txt" % TRIALS, "w")


DECKS = 8
PENETRATION = 0.75
# The best count I've found is same as HiLo, but Ace is -2:
spanish_21_count = deck.LUTCount([0,-2,1,1,1,1,1,0,0,0,-1])
d = deck.Deck(DECKS, [1,2,3,4,5,6,7,8,9,10,10,10], [spanish_21_count])

COUNT_CAP = 14 # Actually seven since this is count halves.
COUNT_INDICES = 2*COUNT_CAP + 1


# Use brute force to find the conditional distribution of what the next card
# will be given the true count:
distros = [[0 for card in range(11)] for count in range(COUNT_INDICES)]

while([sum(x) for x in distros].count(TRIALS) < COUNT_INDICES):
    d.shuffle()
    
    while d.penetration() < PENETRATION:
        rc = spanish_21_count.count
        int_count = int(round(2*d.get_true_count(rc)))
        if (int_count < -COUNT_CAP or
                int_count > COUNT_CAP or
                sum(distros[int_count]) >= TRIALS):
            d.draw()
            continue

        distros[int_count][d.draw().value] += 1

for int_count in range(COUNT_INDICES):
    for card in range(11):
        distros[int_count][card] /= float(TRIALS)

# Indices: [count][upcard][end_total]
dealer_distro = [blackjack.get_dealer_terminal_distro_given_card_distro(distros[int_count]) for int_count in range(COUNT_INDICES)]
charlie_bonus = [1,1,1.5,1,1,1.5,2,3] # Specific to Spanish 21.

# Indices: [number_of_cards_you_already_have][true_count][dealer_upcard][is_soft][total]
hit_ev = [[[[[0 for x in range(21)] for softness in range(2)] for y in range(11)] for z in range(COUNT_INDICES)] for w in range(7)]
stay_ev = [[[[[0 for x in range(21)] for softness in range(2)] for y in range(11)] for z in range(COUNT_INDICES)] for w in range(7)]
hand_ev = [[[[[0 for x in range(23)] for softness in range(2)] for y in range(11)] for z in range(COUNT_INDICES)] for w in range(8)]
stay_index = [[[[None for x in range(21)] for softness in range(2)] for y in range(11)] for w in range(7)]
surrender_index = [[[None for x in range(21)] for softness in range(2)] for y in range(11)]

# Put the seven card charlies in the hand evs:
for int_count in range(-COUNT_CAP, COUNT_CAP+1):
    for upcard in range(1,11):
        hand_ev[7][int_count][upcard][False][21] = charlie_bonus[7]
        hand_ev[7][int_count][upcard][True][21] = charlie_bonus[7]

# Find what the best moves are:
for cards_you_have in range(6, 1, -1):
    for int_count in range(-COUNT_CAP, COUNT_CAP+1):
        for upcard in range(1,11):
            for total, is_soft in blackjack.blackjack_states():
                if total == 22:
                    hand_ev[cards_you_have][int_count][upcard][False][total] = -1
                elif total == 21:
                    hand_ev[cards_you_have][int_count][upcard][False][total] = charlie_bonus[cards_you_have]
                else:
                    curr_hit_ev = 0
                    curr_stay_ev = 0

                    for next_card in range(1,11):
                        next_total, next_soft = blackjack.next_state(total, is_soft, next_card)

                        # We can assume that if you have 6 cards, the hand EVs
                        # won't change because once you have six cards the
                        # bonuses aren't getting any better (you always draw to
                        # seven, where the charlie is capped.  Of course, if
                        # you want to reference the EV of the actual charlie
                        # bonus (ie next_total == 21), you'll want to increment.
                        if next_total != 21:
                            next_cards_you_have = min(cards_you_have+1, 6)
                        else:
                            next_cards_you_have = cards_you_have + 1

                        curr_hit_ev += hand_ev[next_cards_you_have][int_count][upcard][next_soft][next_total] * distros[int_count][next_card]
                        
                    for final_dealer_total in range(17, 23):
                        outcome = (1 if (total > final_dealer_total or final_dealer_total == 22)
                                   else (0 if total == final_dealer_total else -1))
                        curr_stay_ev += outcome * dealer_distro[int_count][upcard][final_dealer_total]

                    should_hit = curr_hit_ev > curr_stay_ev
                    curr_hand_ev = max(curr_hit_ev, curr_stay_ev)

                    hit_ev[cards_you_have][int_count][upcard][is_soft][total] = curr_hit_ev
                    stay_ev[cards_you_have][int_count][upcard][is_soft][total] = curr_stay_ev
                    hand_ev[cards_you_have][int_count][upcard][is_soft][total] = curr_hand_ev

                    if (not should_hit or int_count == COUNT_CAP) and stay_index[cards_you_have][upcard][is_soft][total] is None:
                        stay_index[cards_you_have][upcard][is_soft][total] = int_count;
                    if ((curr_hand_ev < -0.5 or int_count == COUNT_CAP) and
                            surrender_index[upcard][is_soft][total] is None and
                            cards_you_have == 2):
                        surrender_index[upcard][is_soft][total] = int_count;

for num_cards in range(2,7):
    output.write("Stay indices for %d cards:\n" % num_cards)
    output.write(tabulate.tabulate(format_table(stay_index[num_cards])))
    output.write("\n")

output.write("Surrender indices:\n")
output.write(tabulate.tabulate(format_table(surrender_index)))
output.write("\n")

output.close()
