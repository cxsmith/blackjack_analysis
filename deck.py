import random

class Count(object):
    """This class represents an object that keeps a count of the cards drawn
    from a deck.  It is notified on card draw by the deck that it's a member
    of."""
    def __init__(self, initial_count=0):
        self.initial_count = initial_count
        self.count = initial_count

    def reset(self):
        self.count = self.initial_count

    def notify(self, card):
        pass


class HiLoCount(Count):
    def notify(self, card):
        if card.value >= 2 and card.value <= 6:
            self.count += 1
        elif card.value == 10 or card.value == 1:
            self.count += 1
        
class StiffCount(Count):
    """Given a stiff hand of value "stiff", this counts bust cards as bad and
    all other cards as good."""

    def __init__(self, stiff):
        super().__init__(self)
        self.stiff = stiff

    def notify(self, card):
        if card.value >= 22 - self.stiff:
            self.count += 21 - self.stiff
        else:
            self.count -= self.stiff - 8

class LUTCount(Count):
    def __init__(self, lookup_table, initial_count=0):
        super(LUTCount, self).__init__(initial_count)
        self.lut = lookup_table

    def notify(self, card):
        self.count += self.lut[card.value]


class Card(object):
    def __init__(self, value, suit=0):
        self.value = value
        self.turn = False
        self.suit = suit
        self.prev_exit = None
        self.exit = 0

    def turn(self):
        self.turn = not self.turn

    def set_reveal(self, deck):
        self.deck = deck

    def reveal(self):
        if deck:
            deck.reveal(self)

    def __eq__(self, other):
        if other is None:
            return False
        return self.suit == other.suit and self.value == other.value

class Deck(object):
    def __init__(self, num_decks, suit=[1,2,3,4,5,6,7,8,9,10,10,10,10], counts=[], num_suits=4):
        """Inits an UNSHUFFLED deck of blackjack cards"""

        self.deck = []
        self.deck_length = len(suit) * num_suits
        self.pointer = 0

        self.deck = [Card(x,s) for a in range(num_decks) for x in suit for s in range(num_suits)]

        self.total = len(self.deck)

        self.counts = counts
        self.unrevealed_cards = []
 

    def fraction_of_rank(self, rank):
        len([c for c in self.deck if c.value == rank]) / len(self.deck)
        
    def shuffle(self, turn_fraction=0):
        random.shuffle(self.deck)
        self.unrevealed_cards = []
        
        for count in self.counts:
            count.reset()

        self.pointer = 0

        if turn_fraction == 0:
            return

        # Turn cards:
        for card in self.deck:
            card.turn = random.uniform(0,1) < turn_fraction
 
    def edge_sort(self, turn_rule):
        for card in self.deck:
            card.turn = turn_rule(card)

    def draw(self, reveal=True):
        card = self.deck[self.pointer]

        if reveal:
            for count in self.counts:
                count.notify(card)
        else:
            card.set_reveal(self)
            self.unrevealed_cards.append(card)

        self.pointer += 1
        return card

    def reveal(self, card):
        if card in self.unrevealed_cards:
            for count in self.counts:
                count.notify(card)

    def penetration(self):
        return float(self.pointer) / float(self.total)

    def get_true_count(self, running_count):
        return float(running_count) * self.deck_length / (self.total - self.pointer)



class CSM(object):
    """
    A one2six CSM has 38 compartments with a capacity of AT LEAST 10.

    one2six patent: https://www.google.com/patents/US6659460 Proof that's one2six?  Cited here: https://www.google.com/patents/US8342525
    Note that the patent depicts 52 compartments, but I've seen youtube videos of them with around 38.
    I think that the shuffle machines for single deck carnival games have 52 compartments, but the one2six CSMs have 38.

    There's this video on youtube of this cheap-o generic shuffler with 52 compartments: https://www.youtube.com/watch?v=txl3gqIfwHM
    """
    OUTPUT_BUFFER_MIN_LEN = 5

    def __init__(self, compartments=38, compartment_capacity=10):
        self.compartments = [[] for x in range(compartments)]
        self.step = 0
        self.COMPARTMENT_CAPACITY = compartment_capacity
        self.output = []
        self.num_cards_in_compartments = 0

    def fill(self, cards):
        for card in cards:
            self.insert(card)

    def draw(self):
        while len(self.output) < CSM.OUTPUT_BUFFER_MIN_LEN:
            if sum([len(compartment) for compartment in self.compartments]) == 0:
                return None

            compart = random.randint(0, len(self.compartments)-1)
            self.output.extend(self.compartments[compart])
            self.num_cards_in_compartments -= len(self.compartments[compart])
            self.compartments[compart] = []

        card = self.output.pop(0)
        self.step += 1
        card.prev_exit = card.exit
        card.exit = self.step

        return card

    def insert(self, card):
        if self.num_cards_in_compartments >= len(self.compartments) * self.COMPARTMENT_CAPACITY:
            return False

        if card.prev_exit is None:
            card.prev_exit = self.step

        while True:
            compartment = random.randint(0,len(self.compartments)-1)
            if len(self.compartments[compartment]) < self.COMPARTMENT_CAPACITY:
                self.compartments[compartment].append(card)
                self.num_cards_in_compartments += 1
                return True


def extract_flush(hand):
    """Takes a set of cards and returns a list.  Zeroth element of the list is
    how big the biggest flush in the card set is, the following elements are
    the values of the cards in the flush.
    """

    candidate_flushes = [sorted([x.value for x in hand if x.suit == y], reverse=True) for y in range(4)]
    candidate_flushes = [[len(x)] + x for x in candidate_flushes]
    ranked_flushes = sorted(candidate_flushes, reverse=True)

    return ranked_flushes[0]

def get_flush_suit(hand, num_suits=4):
    """Takes a set of cards and returns which suit is most common.
    """
    return max([[x.suit for x in hand].count(y) for y in range(num_suits)])
