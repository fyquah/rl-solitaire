import collections
import enum
import random

import numpy as np

STEPS_CAP = 50000

class GameStatus(enum.IntEnum):

    NOT_FINISHED = 0
    EXCEEDED_LIMIT = 1
    OUT_OF_STEPS = 2
    WON = 3


class Rank(enum.IntEnum):

    ACE = 1
    DEUCE = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    def pprint(self):
        if int(self) <= 10:
            return str(int(self))
        elif self == self.JACK:
            return "J"
        elif self == self.QUEEN:
            return "Q"
        elif self == self.KING:
            return "K"

class Color(enum.IntEnum):

    RED = 0
    BLACK = 1

class Suit(enum.IntEnum):

    DIAMOND = 0
    CLUBS = 1
    HEARTS = 2
    SPADES = 3

    def pprint(self):
        return str(self)[5]

    def color(self):
        if self == Suit.DIAMOND or self == Suit.HEARTS:
            return Color.RED
        else:
            return Color.BLACK


class CardBase(object):
    pass

class CardKnown(collections.namedtuple("CardKnownBase", ["suit", "rank"]), CardBase):

    def is_known(self):
        return True

    def pprint(self):
        return "[" + self.rank.pprint() + self.suit.pprint() + "]"

class CardUnknown(object):

    def is_known(self):
        return False

    def pprint(self):
        return "[?]"


Pile = collections.namedtuple("Pile", ["hidden_left", "visible"])

class LocationBase(object):
    pass

class LocationPile(LocationBase):

    def __init__(self, a):
        self.id = a

    def __eq__(self, other):
        if isinstance(other, LocationPile):
            return self.id == other.id
        else:
            return False

    def __repr__(self):
        return "MainPile[%d]" % self.id

class LocationFoundation(LocationBase):

    def __init__(self, a):
        self.id = a

    def __eq__(self, other):
        if isinstance(other, LocationFoundation):
            return self.id == other.id
        else:
            return False

    def __repr__(self):
        return "Foundation[%d]" % self.id

class LocationVisiblePile(LocationBase):

    def __eq__(self, other):
        return isinstance(other, LocationVisiblePile)

    def __repr__(self):
        return "VisiblePile"


class ActionBase(object):
    pass


class ActionMove(ActionBase, collections.namedtuple(
        "ActionMoveBase",
        ["src", "dest"])):
    pass

class ActionDraw(ActionBase):

    def __repr__(self):
        return "ActionDraw"


def check_compatible(back, front):
    if front is None:
        return False

    assert (
            (back is None or isinstance(back, CardKnown)) and
            isinstance(front, CardKnown)
    )

    return (
            (back is None and front.rank == Rank.KING) or
            (back is not None and
             int(front.rank) == int(back.rank) - 1 and
             front.suit.color() != back.suit.color())
    )


def _construct_actions():
    actions = []
    locations = []

    # main piles
    for i in range(7):
        locations.append(LocationPile(i))

    # foundation
    for i in range(4):
        locations.append(LocationFoundation(i))

    # Junk tableau
    locations.append(LocationVisiblePile())

    for src in locations:
        for dest in locations:
            if src != dest and not isinstance(dest, LocationVisiblePile):
                actions.append(ActionMove(src=src, dest=dest))

    actions.append(ActionDraw())

    return actions

ACTIONS = _construct_actions()


class IllegalMove(Exception):
    pass


def build_initial_game_state(seed=None):
    all_cards = []
    for r in Rank:
        for s in Suit:
            all_cards.append(CardKnown(suit=s, rank=r))

    np.random.seed(seed)
    np.random.shuffle(all_cards)

    piles = []
    foundations = [[], [], [], []]
    visible_pile = []
    hidden_pile = [CardUnknown() for _ in range(24)]

    for i in range(0, 7):
        hidden_left = i
        visible = (all_cards.pop(),)
        piles.append(Pile(hidden_left=hidden_left, visible=visible))

    unseen_cards = all_cards
    assert (len(all_cards) == 45)
    return GameState(
            num_steps = 0,
            piles=tuple(piles),
            foundations=tuple(foundations),
            visible_pile=tuple(visible_pile),
            hidden_pile=tuple(hidden_pile),
            unseen_cards=tuple(all_cards))

GameStateBase = collections.namedtuple("GameStateBase",
        ["piles", "foundations", "visible_pile", "hidden_pile",
            "unseen_cards", "num_steps"])

def draw_from_unseen_cards(unseen_cards):
    unseen_cards = list(unseen_cards)
    idx = random.randint(0, len(unseen_cards) - 1)
    rand_elem = unseen_cards.pop(idx)
    return tuple(unseen_cards), rand_elem

def pop_from_tuple(tpl):
    return (tpl[:-1], tpl[-1])


class GameState(GameStateBase):

    def _is_won(self):
        # when everything has been revealed, it means the game is definitely
        # won
        return (
                len(self.visible_pile) == 0
                and len(self.hidden_pile) == 0
                and len(self.unseen_cards) == 0
        )

    def status(self):
        if self._is_won():
            return GameStatus.WON
        elif self.num_steps > STEPS_CAP:
            return GameStatus.EXCEEDED_LIMIT
        elif len(self.legal_actions()) == 0:
            return GameStatus.OUT_OF_STEPS
        else:
            return GameStatus.NOT_FINISHED

    def _get_top_most_card(self, location_src):

        if isinstance(location_src, LocationPile):
            try:
                return self.piles[location_src.id].visible[-1]
            except IndexError:
                return None
        elif isinstance(location_src, LocationFoundation):
            return self.foundations[location_src.id][-1]
        elif isinstance(location_src, LocationVisiblePile):
            return self.visible_pile[-1]
        else:
            raise RuntimeError("Unknown location")

    def legal_actions(self):
        return [action for action in ACTIONS if self.is_move_legal(action)]

    def is_move_legal(self, action):
        try:
            _ = self.execute_action(action)
            return True
        except IllegalMove:
            return False

    def _take_from_main_pile(self, index, offset):
        src_pile = self.piles[index]
        taken = src_pile.visible[offset:]

        if offset == 0 and src_pile.hidden_left != 0:
            unseen_cards, new_card = draw_from_unseen_cards(self.unseen_cards)
            src_pile = Pile(
                    hidden_left=src_pile.hidden_left - 1,
                    visible=(new_card,))
        else:
            unseen_cards = self.unseen_cards
            src_pile = Pile(
                    hidden_left=src_pile.hidden_left,
                    visible=src_pile.visible[:offset])

        return src_pile, unseen_cards, taken

    def _promote_to_foundation(self, location_src):

        piles = list(self.piles)
        foundations = list(self.foundations)
        visible_pile = self.visible_pile
        unseen_cards = self.unseen_cards

        if isinstance(location_src, LocationPile):
            piles[location_src.id], unseen_cards, new_card = (
                    self._take_from_main_pile(
                        location_src.id,
                        len(piles[location_src.id].visible) - 1))
            assert len(new_card) == 1
            new_card = new_card[0]

        elif isinstance(location_src, LocationVisiblePile):
            visible_pile, new_card = pop_from_tuple(visible_pile)
        else:
            assert False

        foundations[int(new_card.suit)] = \
                foundations[int(new_card.suit)] + [new_card]

        return GameState(
                num_steps=self.num_steps + 1,
                piles=tuple(piles),
                foundations=tuple(foundations),
                visible_pile=tuple(visible_pile),
                hidden_pile=self.hidden_pile,  # hidden pile unmodified
                unseen_cards=tuple(unseen_cards))

    def _simple_move(self, location_src, location_dest):
        piles = list(self.piles)
        foundations = list(self.foundations)
        visible_pile = self.visible_pile
        unseen_cards = self.unseen_cards

        if isinstance(location_src, LocationPile):
            piles[location_src.id], unseen_cards, new_card = (
                    self._take_from_main_pile(
                        location_src.id,
                        len(piles[location_src.id].visible) - 1))
            assert len(new_card) == 1
            new_card = new_card[0]

        elif isinstance(location_src, LocationFoundation):
            foundations[location_src.id], new_card = \
                    pop_from_tuple(foundations[location_src.id])

        elif isinstance(location_src, LocationVisiblePile):
            visible_pile, new_card = pop_from_tuple(visible_pile)
        else:
            assert False

        if isinstance(location_dest, LocationPile):
            p = piles[location_dest.id]
            piles[location_dest.id] = Pile(
                    visible=p.visible + (new_card,),
                    hidden_left=p.hidden_left)

        elif isinstance(location_dest, LocationFoundation):
            foundations[location_dest.id] = \
                    foundations[location_dest.id] + (new_card,)

        else:
            assert False

        return GameState(
                num_steps = self.num_steps + 1,
                piles=tuple(piles),
                foundations=tuple(foundations),
                visible_pile=tuple(visible_pile),
                hidden_pile=self.hidden_pile,  # hidden pile unmodified
                unseen_cards=tuple(unseen_cards))


    def _transfer_between_piles(self, location_src, src_offset, location_dest):
        """
        Assumes that the source and dest are compatible!
        """
        assert isinstance(location_src, LocationPile)
        assert isinstance(location_dest, LocationPile)
        src_pile = self.piles[location_src.id]
        dest_pile = self.piles[location_dest.id]

        dest_pile = Pile(
                hidden_left=dest_pile.hidden_left,
                visible=dest_pile.visible + src_pile.visible[src_offset:]
        )
        src_pile, unseen_cards, taken = self._take_from_main_pile(
                location_src.id, src_offset)
        assert taken == self.piles[location_src.id].visible[src_offset:]

        piles = list(self.piles)
        piles[location_src.id] = src_pile
        piles[location_dest.id] = dest_pile

        return GameState(
                num_steps = self.num_steps + 1,
                piles=tuple(piles),
                foundations=self.foundations,
                visible_pile=self.visible_pile,
                hidden_pile=self.hidden_pile,
                unseen_cards=unseen_cards)

    def execute_action(self, action):
        assert isinstance(action, ActionBase)

        if isinstance(action, ActionDraw):
            if len(self.hidden_pile) == 0:
                next_state = GameState(
                        num_steps = self.num_steps + 1,
                        piles=self.piles,
                        foundations=self.foundations,
                        unseen_cards=self.unseen_cards,
                        visible_pile=(),
                        hidden_pile=tuple(reversed(self.visible_pile)))
            else:
                new_card = self.hidden_pile[-1]
                if not new_card.is_known():
                    unseen_cards, new_card = draw_from_unseen_cards(
                            self.unseen_cards)
                    assert isinstance(unseen_cards, tuple)
                    assert isinstance(new_card, CardKnown)
                else:
                    unseen_cards = self.unseen_cards
                next_state = GameState(
                        num_steps = self.num_steps + 1,
                        piles=self.piles,
                        foundations=self.foundations,
                        unseen_cards=unseen_cards,
                        visible_pile=(self.visible_pile + (new_card,)),
                        hidden_pile=self.hidden_pile[:-1])

            return next_state

        location_src = action.src
        location_dest = action.dest
        src = None
        dest = None

        # Make sure there is actually something at the source
        if isinstance(location_src, LocationPile):
            if len(self.piles[location_src.id].visible) == 0:
                raise IllegalMove("Cannot moeve from empty main pile")

        elif isinstance(location_src, LocationFoundation):
            if len(self.foundations[location_src.id]) == 0:
                raise IllegalMove("Cannot moeve from empty foundation pile")

        elif isinstance(location_src, LocationVisiblePile):
            if len(self.visible_pile) == 0:
                raise IllegalMove("Cannot moeve from empty visible pile")

        if isinstance(location_dest, LocationPile):
            if isinstance(location_src, LocationPile):
                # Interpile Transfer
                dest = self._get_top_most_card(location_dest)
                for i, src in enumerate(self.piles[location_src.id].visible):
                    if check_compatible(back=dest, front=src):
                        return self._transfer_between_piles(
                                location_src=location_src,
                                src_offset=i,
                                location_dest=location_dest
                        )

                raise IllegalMove(
                        "Cannot find compatible transfer from pile %d to \
                         pile %d"
                        % (location_src.id, location_dest.id))

            elif isinstance(location_src, LocationFoundation) or \
                    isinstance(location_src, LocationVisiblePile):
                # Moving the top card from one pile to another
                src = self._get_top_most_card(location_src)
                dest = self._get_top_most_card(location_dest)
                if not check_compatible(back=dest, front=src):
                    raise IllegalMove(
                            "Top card in %s is not compatible with top \
                                    card in %s"
                                    % (str(location_src), str(location_dest)))

                return self._simple_move(location_src, location_dest)

            assert False

        elif isinstance(location_dest, LocationFoundation):
            # Promoting to foundations
            src = self._get_top_most_card(location_src)

            # So that specific suit gets into specific locations
            if int(src.suit) != location_dest.id:
                raise IllegalMove(
                        "Promoting to to incorrect foundation deck")

            foundation = self.foundations[location_dest.id]

            if src.rank == Rank.ACE:
                if len(foundation) != 0:
                    raise IllegalMove("Inconsistency!")
            else:
                if len(foundation) == 0:
                    raise IllegalMove("Cannot promote non-ace to empty \
                            foundation")

                if int(foundation[-1].rank) != int(src.rank) - 1:
                    raise IllegalMove("Not compatible in foundation")

            return self._promote_to_foundation(location_src)

        else:
            raise RuntimeError("Unexpected destination location type")

    def pprint(self):
        output = []
        row = []

        # Foundation deck
        for foundation in self.foundations:
            if len(foundation) == 0:
                row.append("[-]")
            else:
                row.append(foundation[-1].pprint())

        row.extend([" "] * 3)

        # Draw Pile
        if len(self.visible_pile) == 0:
            row.append("[-]")
        else:
            row.append(self.visible_pile[-1].pprint())

        # Junk Pile
        row.append(str(len(self.hidden_pile)) + " cards in hidden pile")

        output.append(row)
        output.append([])  # for reading clarity
        del row

        # Now, print all the piles, each pile can contain up to 13 cards
        for i in range(13):
            row = []
            for pile in self.piles:
                if i < pile.hidden_left:
                    row.append("[?]")
                elif i < pile.hidden_left + len(pile.visible):
                    row.append(pile.visible[i - pile.hidden_left].pprint())
                else:
                    row.append("[-]")
            output.append(row)
        
        return "\n".join("\t".join(row) for row in output)
