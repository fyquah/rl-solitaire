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
  { suit  : suit;
    rank  : rank;
  }


module Visible_pile = struct
  type t =
    | Empty
    | Visible_pile of (card * card list)
end


module Tableau = struct
  type t =
    | Empty
    | Something of {
        hidden  : int;
        visible : card list;
        top     : card;
      }
end


module Maybe_card = struct
  type t =
    | Hidden_but_known of card
    | Unknown
end


type state =
  { foundation           : rank option array;
    tableau              : Tableau.t array;
    mutable visible_pile : Visible_pile.t;
    mutable hidden_pile  : Maybe_card.t list;
    mutable num_steps     : int;
    mutable unseen_cards : card list;
  }

(* something something  *)
type step_result =
  | Illegal_move
  | Won
  | Accepted

let is_move_compatible ~(to_ : Tableau.t) ~(from : card) =
  match to_ with
  | Empty -> (from.rank = RKing)
  | Something { top; _ } ->
    Obj.magic top.rank - 1 = Obj.magic from.rank
    && (Obj.magic top.rank mod 2) <> (Obj.magic from.rank mod 2)
;;

(* TODO: Possible to get rid of allocation here? *)
let find_move_index ~from:tbl_from ~to_:tbl_to =
  match tbl_from with
  | Tableau.Empty -> None
  | Tableau.Something { visible ; top; hidden = _ } ->
    top :: visible
    |> List.mapi (fun i a -> (i, a))
    |> List.find_opt (fun (i, from_card) ->
        is_move_compatible ~to_:tbl_to ~from:from_card)
    |> function
      | None -> None
      | Some x -> Some (fst x)
;;

let is_some = function | Some _ -> true | None -> false

let is_action_legal state action =
  match action with
  | Draw -> true
  | Move (idx_a, idx_b) -> 
    let tbl_from = state.tableau.(Obj.magic idx_a) in
    let tbl_to = state.tableau.(Obj.magic idx_b) in
    is_some (find_move_index ~from:tbl_from ~to_:tbl_to)

  | Promote (idx_tableau : tableau) ->
    let tableau_from = state.tableau.(Obj.magic idx_tableau) in
    begin match tableau_from with
    | Tableau.Empty  ->
      false
    | Something { top; hidden = _; visible = _ } ->
      let foundation =
        match state.foundation.(Obj.magic top.suit) with
        | None ->  (-1)
        | Some x -> Obj.magic x
      in
      Obj.magic top.rank = foundation - 1
    end
;;

let unveil_unseen_card state =
  let card = List.hd state in
  state.unseen_cards <- List.tl state.unseen_cards;
  card
;;

let step state action =
  if not (is_action_legal state action) then
    Illegal_move
  else begin
    begin match action with
    | Promote idx_tbl -> ()
    | Move    idx_tbl -> ()
    | Draw ->
      let card = unveil_unseen_card state in
      match state.hidden_pile with
      | [] -> 
      | hd :: tl ->
        let card =
          match hd with
          | Maybe_card.Hidden_but_known card -> card
          | Maybe_card.Unknown -> unveil_unseen_card state
        in
        state.visible_pile <- visible_pile
        state.hidden_pile <- tl
    end;
    state.num_steps <- state.num_steps + 1;
    Accepted
  end
;;
