type suit =
  | Diamond
  | Clubs
  | Hearts
  | Spades

type rank =
  | RAce
  | R2
  | R3
  | R4
  | R5
  | R6
  | R7
  | R8
  | R9
  | R10
  | RJack
  | RQueen
  | RKing

type tableau =
  | T0
  | T1
  | T2
  | T3
  | T4
  | T5
  | T6

type foundation =
  | F0
  | F1
  | F2
  | F3

type action =
  | Promote of tableau
  | Move    of (tableau * tableau)
  | Draw

type card = 
  { suit : suit;
    rank  : rank;
  }


module Visible_pile : sig
  type t =
    | Empty
    | Visible_pile of (card * card list)
end


module Tableau  : sig
  type t =
    | Empty
    | Something of {
        hidden  : int;
        visible : card list;
        top     : card;
      }
end


module Maybe_card : sig
  type t =
    | Hidden_but_known of card
    | Unknown
end


type state =
  { foundation            : rank option array;
    tableau               : Tableau.t array;
    mutable visible_pile  : Visible_pile.t;
    mutable hidden_pile   : Maybe_card.t list;
    mutable num_steps     : int;
    mutable unseen_cards  : card list;
  }

(* something something  *)
type step_result =
  | Illegal_move
  | Won
  | Accepted

val is_action_legal : state -> action -> bool
val step : state -> action -> step_result
